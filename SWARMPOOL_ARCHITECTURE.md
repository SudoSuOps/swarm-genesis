# SWARMPOOL.ETH — DECENTRALIZED AI INFERENCE MEMPOOL

Build the mining pool for AI compute. No cloud. No middlemen. Just miners, jobs, and proofs.

## PHILOSOPHY

- Bitcoin has mempool → transactions wait for miners
- SwarmPool has jobpool → inference jobs wait for GPU miners
- Miners watch pool, claim jobs, submit proofs, get paid
- No central assignment. No API. Just signed snapshots on IPFS.

## ARCHITECTURE

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                           SWARMPOOL.ETH                                     ║
║                      The Decentralized Jobpool                              ║
║                                                                              ║
║   ┌─────────────────────────────────────────────────────────────────────┐   ║
║   │                         IPFS LAYER                                  │   ║
║   │                                                                     │   ║
║   │   /swarmpool/jobs/pending/      ← New jobs land here               │   ║
║   │   /swarmpool/jobs/claimed/      ← Miners claim here                │   ║
║   │   /swarmpool/proofs/            ← Results + proofs here            │   ║
║   │   /swarmpool/epochs/            ← Sealed epoch snapshots           │   ║
║   │   /swarmpool/miners/            ← Miner registrations              │   ║
║   │   /swarmpool/state.json         ← Current pool state (CRDT)        │   ║
║   │                                                                     │   ║
║   └─────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║   ┌─────────────────────────────────────────────────────────────────────┐   ║
║   │                       PUBSUB TOPICS                                 │   ║
║   │                                                                     │   ║
║   │   /swarmpool/jobs         ← "New job available!"                   │   ║
║   │   /swarmpool/claims       ← "I'm working on job X"                 │   ║
║   │   /swarmpool/proofs       ← "Job X complete, here's proof"         │   ║
║   │   /swarmpool/epochs       ← "Epoch sealed"                         │   ║
║   │   /swarmpool/heartbeats   ← "Miner alive" pings                    │   ║
║   │                                                                     │   ║
║   └─────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   MINER A   │    │   MINER B   │    │   MINER C   │
│             │    │             │    │             │
│ • Watches   │    │ • Watches   │    │ • Watches   │
│ • Claims    │    │ • Claims    │    │ • Claims    │
│ • Computes  │    │ • Computes  │    │ • Computes  │
│ • Proves    │    │ • Proves    │    │ • Proves    │
│             │    │             │    │             │
│ SOLO or PPS │    │ SOLO or PPS │    │ SOLO or PPS │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## CORE COMPONENTS

### 1. SWARMPOOL DAEMON (Pool Operator)

The pool operator runs this. Manages pool state, validates proofs, seals epochs.

```python
# swarmpool/daemon.py

import asyncio
import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set
from pathlib import Path

import redis.asyncio as redis
from pydantic import BaseModel

from .ipfs import IPFSClient, PubSubClient
from .crypto import verify_snapshot, sign_snapshot
from .models import Job, Claim, Proof, Epoch, MinerInfo


class PoolState(BaseModel):
    """Current state of the pool - synced via CRDT."""
    pool_id: str = "swarmpool.eth"
    version: str = "1.0.0"

    # Counters
    total_jobs: int = 0
    total_proofs: int = 0
    total_volume_usdc: float = 0.0

    # Current epoch
    current_epoch: Optional[str] = None
    epoch_jobs: int = 0
    epoch_volume: float = 0.0

    # Active state
    pending_jobs: List[str] = []      # Job CIDs waiting
    claimed_jobs: Dict[str, str] = {} # job_cid → miner_ens
    active_miners: Dict[str, dict] = {} # miner_ens → info

    # Timing
    last_updated: int = 0
    last_epoch_seal: int = 0


class SwarmPoolDaemon:
    """
    The SwarmPool daemon.

    Responsibilities:
    - Publish pool state to IPFS
    - Listen for job submissions
    - Track claims
    - Validate proofs
    - Seal epochs
    - Calculate payouts

    NO HTTP API. Only IPFS + PubSub.
    """

    def __init__(self, config: dict):
        self.config = config
        self.pool_ens = config.get('pool_ens', 'swarmpool.eth')
        self.operator_key = config.get('operator_private_key')

        self.ipfs = IPFSClient(config.get('ipfs_api', 'http://localhost:5001'))
        self.pubsub = PubSubClient(self.ipfs)
        self.redis = None

        self.state = PoolState()
        self.running = False

        # Settings
        self.epoch_duration = config.get('epoch_duration_seconds', 3600)  # 1 hour
        self.claim_timeout = config.get('claim_timeout_seconds', 300)     # 5 min
        self.min_stake = config.get('min_miner_stake', 0)                 # Optional

    async def start(self):
        """Start the pool daemon."""
        self.running = True
        self.redis = redis.from_url(self.config.get('redis_url', 'redis://localhost:6379'))

        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🏊 SWARMPOOL DAEMON STARTED                                               ║
║                                                                              ║
║   Pool:     {self.pool_ens:<50}      ║
║   Mode:     DECENTRALIZED                                                   ║
║   Epoch:    {self.epoch_duration}s                                                        ║
║                                                                              ║
║   Watching for:                                                             ║
║   • Job submissions                                                         ║
║   • Miner claims                                                            ║
║   • Proof submissions                                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)

        # Subscribe to pubsub topics
        await self._subscribe_topics()

        # Load or create initial state
        await self._load_state()

        # Open first epoch if needed
        if not self.state.current_epoch:
            await self._open_epoch("Genesis")

        # Start background tasks
        asyncio.create_task(self._state_publisher())
        asyncio.create_task(self._epoch_manager())
        asyncio.create_task(self._claim_timeout_checker())
        asyncio.create_task(self._heartbeat_monitor())

        # Main loop - process pubsub messages
        await self._main_loop()

    async def _subscribe_topics(self):
        """Subscribe to all pool topics."""
        topics = [
            f"/{self.pool_ens}/jobs",
            f"/{self.pool_ens}/claims",
            f"/{self.pool_ens}/proofs",
            f"/{self.pool_ens}/miners",
            f"/{self.pool_ens}/heartbeats",
        ]
        for topic in topics:
            await self.pubsub.subscribe(topic)
            print(f"   📡 Subscribed: {topic}")

    async def _main_loop(self):
        """Main message processing loop."""
        while self.running:
            try:
                msg = await self.pubsub.get_message(timeout=1.0)
                if msg:
                    await self._handle_message(msg)
            except Exception as e:
                print(f"⚠️ Error in main loop: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, msg: dict):
        """Route message to appropriate handler."""
        topic = msg.get('topic', '')
        data = msg.get('data')

        if '/jobs' in topic:
            await self._handle_job_submission(data)
        elif '/claims' in topic:
            await self._handle_claim(data)
        elif '/proofs' in topic:
            await self._handle_proof(data)
        elif '/miners' in topic:
            await self._handle_miner_registration(data)
        elif '/heartbeats' in topic:
            await self._handle_heartbeat(data)

    async def _handle_job_submission(self, data: dict):
        """Handle new job submission."""
        job_cid = data.get('cid')
        client_ens = data.get('client')

        print(f"\n📥 NEW JOB: {job_cid[:16]}... from {client_ens}")

        # Fetch job from IPFS
        job = await self.ipfs.fetch_json(job_cid)
        if not job:
            print(f"   ❌ Failed to fetch job from IPFS")
            return

        # Verify client signature
        valid = await self._verify_client(job, client_ens)
        if not valid:
            print(f"   ❌ Invalid client signature")
            return

        # Add to pending pool
        self.state.pending_jobs.append(job_cid)
        self.state.total_jobs += 1
        self.state.epoch_jobs += 1

        volume = float(job.get('payment', {}).get('amount', 0))
        self.state.epoch_volume += volume
        self.state.total_volume_usdc += volume

        # Pin job
        await self.ipfs.pin(job_cid)

        # Announce to miners
        await self.pubsub.publish(f"/{self.pool_ens}/jobs/new", {
            "cid": job_cid,
            "job_type": job.get('job_type'),
            "model": job.get('model'),
            "reward": job.get('payment', {}).get('amount'),
            "timestamp": int(datetime.utcnow().timestamp())
        })

        print(f"   ✅ Job added to pool. Pending: {len(self.state.pending_jobs)}")

    async def _handle_claim(self, data: dict):
        """Handle miner claiming a job."""
        job_cid = data.get('job_cid')
        miner_ens = data.get('miner')
        claim_sig = data.get('sig')

        print(f"\n⛏️ CLAIM: {miner_ens} → {job_cid[:16]}...")

        # Check job is pending
        if job_cid not in self.state.pending_jobs:
            print(f"   ❌ Job not pending (already claimed or doesn't exist)")
            return

        # Verify miner signature
        valid = await self._verify_miner(data, miner_ens)
        if not valid:
            print(f"   ❌ Invalid miner signature")
            return

        # Check miner is registered
        if miner_ens not in self.state.active_miners:
            print(f"   ❌ Miner not registered")
            return

        # Move from pending to claimed
        self.state.pending_jobs.remove(job_cid)
        self.state.claimed_jobs[job_cid] = {
            "miner": miner_ens,
            "claimed_at": int(datetime.utcnow().timestamp()),
            "timeout_at": int(datetime.utcnow().timestamp()) + self.claim_timeout
        }

        # Announce claim
        await self.pubsub.publish(f"/{self.pool_ens}/claims/accepted", {
            "job_cid": job_cid,
            "miner": miner_ens,
            "timestamp": int(datetime.utcnow().timestamp())
        })

        print(f"   ✅ Claim accepted. Timeout: {self.claim_timeout}s")

    async def _handle_proof(self, data: dict):
        """Handle proof submission from miner."""
        job_cid = data.get('job_cid')
        proof_cid = data.get('proof_cid')
        miner_ens = data.get('miner')

        print(f"\n📤 PROOF: {miner_ens} → {job_cid[:16]}...")

        # Check job was claimed by this miner
        claim = self.state.claimed_jobs.get(job_cid)
        if not claim or claim['miner'] != miner_ens:
            print(f"   ❌ Job not claimed by this miner")
            return

        # Fetch and verify proof
        proof = await self.ipfs.fetch_json(proof_cid)
        if not proof:
            print(f"   ❌ Failed to fetch proof from IPFS")
            return

        valid = await self._verify_proof(proof, job_cid, miner_ens)
        if not valid:
            print(f"   ❌ Invalid proof")
            return

        # Record completion
        del self.state.claimed_jobs[job_cid]
        self.state.total_proofs += 1

        # Update miner stats
        if miner_ens in self.state.active_miners:
            self.state.active_miners[miner_ens]['jobs_completed'] = \
                self.state.active_miners[miner_ens].get('jobs_completed', 0) + 1

        # Store proof for epoch settlement
        await self.redis.lpush(f"swarmpool:epoch:{self.state.current_epoch}:proofs", json.dumps({
            "job_cid": job_cid,
            "proof_cid": proof_cid,
            "miner": miner_ens,
            "timestamp": int(datetime.utcnow().timestamp())
        }))

        # Pin proof
        await self.ipfs.pin(proof_cid)

        # Announce completion
        await self.pubsub.publish(f"/{self.pool_ens}/proofs/accepted", {
            "job_cid": job_cid,
            "proof_cid": proof_cid,
            "miner": miner_ens,
            "timestamp": int(datetime.utcnow().timestamp())
        })

        print(f"   ✅ Proof accepted!")

    async def _handle_miner_registration(self, data: dict):
        """Handle miner registration."""
        miner_ens = data.get('miner')

        print(f"\n⛏️ MINER REGISTRATION: {miner_ens}")

        # Verify signature
        valid = await self._verify_miner(data, miner_ens)
        if not valid:
            print(f"   ❌ Invalid signature")
            return

        # Register miner
        self.state.active_miners[miner_ens] = {
            "ens": miner_ens,
            "registered_at": int(datetime.utcnow().timestamp()),
            "last_heartbeat": int(datetime.utcnow().timestamp()),
            "gpus": data.get('gpus', []),
            "models": data.get('models', []),
            "mode": data.get('mode', 'SOLO'),  # SOLO or PPS
            "jobs_completed": 0,
            "status": "online"
        }

        # Announce
        await self.pubsub.publish(f"/{self.pool_ens}/miners/joined", {
            "miner": miner_ens,
            "timestamp": int(datetime.utcnow().timestamp())
        })

        print(f"   ✅ Miner registered! Active miners: {len(self.state.active_miners)}")

    async def _handle_heartbeat(self, data: dict):
        """Handle miner heartbeat."""
        miner_ens = data.get('miner')

        if miner_ens in self.state.active_miners:
            self.state.active_miners[miner_ens]['last_heartbeat'] = \
                int(datetime.utcnow().timestamp())
            self.state.active_miners[miner_ens]['status'] = 'online'

    async def _verify_client(self, job: dict, client_ens: str) -> bool:
        """Verify job was signed by claimed client."""
        from .crypto import verify_ens_signature
        return await verify_ens_signature(job, client_ens)

    async def _verify_miner(self, data: dict, miner_ens: str) -> bool:
        """Verify data was signed by claimed miner."""
        from .crypto import verify_ens_signature
        return await verify_ens_signature(data, miner_ens)

    async def _verify_proof(self, proof: dict, job_cid: str, miner_ens: str) -> bool:
        """Verify proof is valid for job."""
        if proof.get('job_cid') != job_cid:
            return False

        from .crypto import verify_ens_signature
        if not await verify_ens_signature(proof, miner_ens):
            return False

        required = ['job_cid', 'status', 'output_cid', 'metrics', 'proof_hash']
        if not all(k in proof for k in required):
            return False

        return True

    async def _state_publisher(self):
        """Periodically publish pool state to IPFS."""
        while self.running:
            try:
                self.state.last_updated = int(datetime.utcnow().timestamp())

                state_dict = self.state.dict()
                from .crypto import sign_snapshot
                state_dict['sig'] = sign_snapshot(state_dict, self.operator_key)

                cid = await self.ipfs.upload_json(state_dict)

                await self.pubsub.publish(f"/{self.pool_ens}/state", {
                    "cid": cid,
                    "timestamp": self.state.last_updated
                })

                await self.redis.set("swarmpool:state:cid", cid)

            except Exception as e:
                print(f"⚠️ State publish error: {e}")

            await asyncio.sleep(10)

    async def _epoch_manager(self):
        """Manage epoch lifecycle."""
        while self.running:
            try:
                now = int(datetime.utcnow().timestamp())

                if self.state.last_epoch_seal + self.epoch_duration < now:
                    await self._seal_epoch()
                    await self._open_epoch(f"Epoch-{now}")

            except Exception as e:
                print(f"⚠️ Epoch manager error: {e}")

            await asyncio.sleep(60)

    async def _open_epoch(self, name: str):
        """Open new epoch."""
        epoch_id = f"epoch-{int(datetime.utcnow().timestamp())}"

        self.state.current_epoch = epoch_id
        self.state.epoch_jobs = 0
        self.state.epoch_volume = 0.0
        self.state.last_epoch_seal = int(datetime.utcnow().timestamp())

        print(f"\n📖 EPOCH OPENED: {epoch_id} ({name})")

        await self.pubsub.publish(f"/{self.pool_ens}/epochs/opened", {
            "epoch_id": epoch_id,
            "name": name,
            "timestamp": int(datetime.utcnow().timestamp())
        })

    async def _seal_epoch(self):
        """Seal current epoch and calculate settlements."""
        epoch_id = self.state.current_epoch
        if not epoch_id:
            return

        print(f"\n📕 SEALING EPOCH: {epoch_id}")

        proofs_raw = await self.redis.lrange(f"swarmpool:epoch:{epoch_id}:proofs", 0, -1)
        proofs = [json.loads(p) for p in proofs_raw]

        total_volume = self.state.epoch_volume
        settlements = self._calculate_settlements(proofs, total_volume)

        epoch_snapshot = {
            "type": "epoch",
            "version": "1.0.0",
            "epoch_id": epoch_id,
            "status": "sealed",
            "started_at": self.state.last_epoch_seal,
            "ended_at": int(datetime.utcnow().timestamp()),
            "jobs_count": self.state.epoch_jobs,
            "proofs_count": len(proofs),
            "total_volume_usdc": str(total_volume),
            "proofs": proofs,
            "settlements": settlements,
            "merkle_root": self._calculate_merkle_root(proofs),
            "pool": self.pool_ens,
            "timestamp": int(datetime.utcnow().timestamp())
        }

        from .crypto import sign_snapshot
        epoch_snapshot['sig'] = sign_snapshot(epoch_snapshot, self.operator_key)

        cid = await self.ipfs.upload_json(epoch_snapshot)
        await self.ipfs.pin(cid)

        await self.redis.set(f"swarmpool:epochs:{epoch_id}", cid)
        await self.redis.lpush("swarmpool:epochs:history", cid)

        await self.pubsub.publish(f"/{self.pool_ens}/epochs/sealed", {
            "epoch_id": epoch_id,
            "cid": cid,
            "jobs": self.state.epoch_jobs,
            "volume": str(total_volume),
            "timestamp": int(datetime.utcnow().timestamp())
        })

        print(f"   ✅ Epoch sealed: {cid[:16]}...")
        print(f"   Jobs: {self.state.epoch_jobs}, Volume: ${total_volume:.2f}")
        print(f"   Settlements:")
        for miner, amount in settlements.get('miners', {}).items():
            print(f"      {miner}: ${amount:.2f}")
        print(f"      Hive Ops: ${settlements.get('hive_ops', 0):.2f}")

    def _calculate_settlements(self, proofs: List[dict], total_volume: float) -> dict:
        """Calculate payout distribution."""
        miner_pool = total_volume * 0.75
        hive_ops = total_volume * 0.25

        miner_jobs = {}
        for proof in proofs:
            miner = proof.get('miner')
            miner_jobs[miner] = miner_jobs.get(miner, 0) + 1

        total_jobs = sum(miner_jobs.values())
        miner_payouts = {}

        if total_jobs > 0:
            for miner, jobs in miner_jobs.items():
                share = jobs / total_jobs
                miner_payouts[miner] = round(miner_pool * share, 4)

        return {
            "total_volume": total_volume,
            "miner_pool": miner_pool,
            "hive_ops": hive_ops,
            "miners": miner_payouts
        }

    def _calculate_merkle_root(self, proofs: List[dict]) -> str:
        """Calculate merkle root of proofs."""
        if not proofs:
            return "0x" + "0" * 64

        leaves = [p.get('proof_cid', '') for p in proofs]
        combined = ''.join(sorted(leaves))
        return "0x" + hashlib.sha256(combined.encode()).hexdigest()

    async def _claim_timeout_checker(self):
        """Check for timed out claims and return to pool."""
        while self.running:
            try:
                now = int(datetime.utcnow().timestamp())
                timed_out = []

                for job_cid, claim in self.state.claimed_jobs.items():
                    if claim['timeout_at'] < now:
                        timed_out.append(job_cid)

                for job_cid in timed_out:
                    miner = self.state.claimed_jobs[job_cid]['miner']
                    del self.state.claimed_jobs[job_cid]
                    self.state.pending_jobs.append(job_cid)

                    print(f"⏱️ TIMEOUT: {job_cid[:16]}... returned to pool (was: {miner})")

                    await self.pubsub.publish(f"/{self.pool_ens}/claims/timeout", {
                        "job_cid": job_cid,
                        "miner": miner,
                        "timestamp": now
                    })

            except Exception as e:
                print(f"⚠️ Timeout checker error: {e}")

            await asyncio.sleep(30)

    async def _heartbeat_monitor(self):
        """Mark miners as offline if no heartbeat."""
        while self.running:
            try:
                now = int(datetime.utcnow().timestamp())
                timeout = 120  # 2 minutes

                for miner_ens, info in self.state.active_miners.items():
                    if info['last_heartbeat'] + timeout < now:
                        if info['status'] == 'online':
                            info['status'] = 'offline'
                            print(f"💀 MINER OFFLINE: {miner_ens}")

            except Exception as e:
                print(f"⚠️ Heartbeat monitor error: {e}")

            await asyncio.sleep(30)
```

---

### 2. MINER CLI (swarm-miner)

What miners run to participate in the pool.

```python
# swarmpool/miner/cli.py

import asyncio
import json
import os
import hashlib
import click
from datetime import datetime
from pathlib import Path

from ..ipfs import IPFSClient, PubSubClient
from ..crypto import sign_snapshot, load_key_from_env


class SwarmMiner:
    """
    SwarmPool Miner

    - Connects to pool
    - Watches for jobs
    - Claims jobs (SOLO or PPS)
    - Executes inference
    - Submits proofs
    - Sends heartbeats
    """

    def __init__(self, config: dict):
        self.config = config
        self.miner_ens = config['miner_ens']
        self.private_key = config['private_key']
        self.pool_ens = config.get('pool_ens', 'swarmpool.eth')
        self.mode = config.get('mode', 'SOLO')
        self.models = config.get('models', ['queenbee-spine'])

        self.ipfs = IPFSClient(config.get('ipfs_api', 'http://localhost:5001'))
        self.pubsub = PubSubClient(self.ipfs)

        self.running = False
        self.current_job = None
        self.stats = {
            "jobs_completed": 0,
            "earnings": 0.0,
            "started_at": None
        }

    async def start(self):
        """Start mining."""
        self.running = True
        self.stats["started_at"] = int(datetime.utcnow().timestamp())

        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ⛏️ SWARM MINER STARTED                                                    ║
║                                                                              ║
║   Miner:    {self.miner_ens:<50}      ║
║   Pool:     {self.pool_ens:<50}      ║
║   Mode:     {self.mode:<50}      ║
║   Models:   {', '.join(self.models):<50}      ║
║                                                                              ║
║   Watching for jobs...                                                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)

        await self._register()

        await self.pubsub.subscribe(f"/{self.pool_ens}/jobs/new")
        await self.pubsub.subscribe(f"/{self.pool_ens}/claims/accepted")
        await self.pubsub.subscribe(f"/{self.pool_ens}/state")

        asyncio.create_task(self._heartbeat_sender())
        asyncio.create_task(self._job_watcher())

        while self.running:
            await asyncio.sleep(1)

    async def _register(self):
        """Register with pool."""
        registration = {
            "type": "registration",
            "miner": self.miner_ens,
            "gpus": self.config.get('gpus', []),
            "models": self.models,
            "mode": self.mode,
            "timestamp": int(datetime.utcnow().timestamp()),
            "nonce": os.urandom(16).hex()
        }
        registration['sig'] = sign_snapshot(registration, self.private_key)

        await self.pubsub.publish(f"/{self.pool_ens}/miners", registration)
        print(f"   📡 Registered with pool")

    async def _heartbeat_sender(self):
        """Send periodic heartbeats."""
        while self.running:
            heartbeat = {
                "miner": self.miner_ens,
                "status": "busy" if self.current_job else "idle",
                "current_job": self.current_job,
                "stats": self.stats,
                "timestamp": int(datetime.utcnow().timestamp())
            }
            heartbeat['sig'] = sign_snapshot(heartbeat, self.private_key)

            await self.pubsub.publish(f"/{self.pool_ens}/heartbeats", heartbeat)
            await asyncio.sleep(30)

    async def _job_watcher(self):
        """Watch for new jobs and claim them."""
        while self.running:
            try:
                msg = await self.pubsub.get_message(timeout=1.0)
                if msg and '/jobs/new' in msg.get('topic', ''):
                    await self._handle_new_job(msg['data'])
            except Exception as e:
                print(f"⚠️ Job watcher error: {e}")
                await asyncio.sleep(1)

    async def _handle_new_job(self, job_info: dict):
        """Handle new job announcement."""
        if self.current_job:
            return

        if job_info.get('model') not in self.models:
            return

        job_cid = job_info.get('cid')
        print(f"\n📥 NEW JOB: {job_cid[:16]}... ({job_info.get('model')})")

        await self._claim_job(job_cid)

    async def _claim_job(self, job_cid: str):
        """Attempt to claim a job."""
        claim = {
            "type": "claim",
            "job_cid": job_cid,
            "miner": self.miner_ens,
            "timestamp": int(datetime.utcnow().timestamp()),
            "nonce": os.urandom(16).hex()
        }
        claim['sig'] = sign_snapshot(claim, self.private_key)

        await self.pubsub.publish(f"/{self.pool_ens}/claims", claim)
        print(f"   ⛏️ Claiming...")

        for _ in range(10):
            msg = await self.pubsub.get_message(timeout=1.0)
            if msg and '/claims/accepted' in msg.get('topic', ''):
                data = msg['data']
                if data.get('job_cid') == job_cid and data.get('miner') == self.miner_ens:
                    print(f"   ✅ Claim accepted!")
                    self.current_job = job_cid
                    await self._execute_job(job_cid)
                    return

        print(f"   ❌ Claim not accepted (someone else got it)")

    async def _execute_job(self, job_cid: str):
        """Execute job and submit proof."""
        print(f"   ⚙️ Executing job...")

        job = await self.ipfs.fetch_json(job_cid)

        start_time = datetime.utcnow()

        # === YOUR INFERENCE CODE HERE ===
        await asyncio.sleep(5)  # Simulate
        confidence = 0.72
        output_cid = "bafybei_simulated_output"
        # ================================

        inference_time = (datetime.utcnow() - start_time).total_seconds()

        proof = {
            "type": "proof",
            "version": "1.0.0",
            "job_cid": job_cid,
            "status": "completed",
            "output_cid": output_cid,
            "metrics": {
                "inference_seconds": round(inference_time, 2),
                "confidence": confidence,
                "model": job.get('model')
            },
            "miner": self.miner_ens,
            "timestamp": int(datetime.utcnow().timestamp()),
            "proof_hash": hashlib.sha256(
                f"{job_cid}{output_cid}{self.miner_ens}".encode()
            ).hexdigest()
        }
        proof['sig'] = sign_snapshot(proof, self.private_key)

        proof_cid = await self.ipfs.upload_json(proof)

        await self.pubsub.publish(f"/{self.pool_ens}/proofs", {
            "job_cid": job_cid,
            "proof_cid": proof_cid,
            "miner": self.miner_ens,
            "timestamp": int(datetime.utcnow().timestamp())
        })

        print(f"   📤 Proof submitted: {proof_cid[:16]}...")

        self.stats["jobs_completed"] += 1
        reward = float(job.get('payment', {}).get('amount', 0)) * 0.75
        self.stats["earnings"] += reward

        print(f"   💰 Earned: ${reward:.4f} (Total: ${self.stats['earnings']:.2f})")

        self.current_job = None


@click.group()
def cli():
    """SwarmPool Miner CLI"""
    pass


@cli.command()
@click.option('--ens', required=True, help='Your miner ENS (e.g., miner.alice.eth)')
@click.option('--key', envvar='MINER_PRIVATE_KEY', help='Private key')
@click.option('--pool', default='swarmpool.eth', help='Pool ENS')
@click.option('--mode', default='SOLO', type=click.Choice(['SOLO', 'PPS']))
@click.option('--models', default='queenbee-spine', help='Comma-separated models')
def mine(ens: str, key: str, pool: str, mode: str, models: str):
    """Start mining."""
    config = {
        'miner_ens': ens,
        'private_key': key,
        'pool_ens': pool,
        'mode': mode,
        'models': models.split(','),
        'gpus': ['RTX 5090']
    }

    miner = SwarmMiner(config)
    asyncio.run(miner.start())


@cli.command()
def status():
    """Check pool status."""
    pass


if __name__ == '__main__':
    cli()
```

---

### 3. CLIENT CLI (swarm-client)

```python
# swarmpool/client/cli.py

import asyncio
import json
import os
import click
from datetime import datetime
from pathlib import Path

from ..ipfs import IPFSClient, PubSubClient
from ..crypto import sign_snapshot


@click.group()
def cli():
    """SwarmPool Client CLI"""
    pass


@cli.command()
@click.argument('job_file', type=click.Path(exists=True))
@click.option('--ens', required=True, help='Your client ENS')
@click.option('--key', envvar='CLIENT_PRIVATE_KEY')
@click.option('--pool', default='swarmpool.eth')
def submit(job_file: str, ens: str, key: str, pool: str):
    """Submit job to pool."""
    asyncio.run(_submit(job_file, ens, key, pool))


async def _submit(job_file: str, ens: str, key: str, pool: str):
    job = json.loads(Path(job_file).read_text())
    job['client'] = ens
    job['timestamp'] = int(datetime.utcnow().timestamp())
    job['nonce'] = os.urandom(16).hex()

    job['sig'] = sign_snapshot(job, key)

    ipfs = IPFSClient()
    cid = await ipfs.upload_json(job)

    click.echo(f"📤 Job uploaded: {cid}")

    pubsub = PubSubClient(ipfs)
    await pubsub.publish(f"/{pool}/jobs", {
        "cid": cid,
        "client": ens,
        "timestamp": job['timestamp']
    })

    click.echo(f"📡 Announced to pool")
    click.echo(f"⏳ Waiting for proof...")

    await pubsub.subscribe(f"/{pool}/proofs/accepted")

    for _ in range(300):
        msg = await pubsub.get_message(timeout=1.0)
        if msg and msg.get('data', {}).get('job_cid') == cid:
            proof_cid = msg['data']['proof_cid']
            click.echo(f"\n✅ JOB COMPLETE!")
            click.echo(f"   Proof: {proof_cid}")
            return

    click.echo("⏱️ Timeout")


if __name__ == '__main__':
    cli()
```

---

## DIRECTORY STRUCTURE

```
~/swarmpool/
├── swarmpool/
│   ├── __init__.py
│   ├── ipfs.py              # IPFS client + PubSub
│   ├── crypto.py            # ENS signatures
│   ├── models.py            # Pydantic models
│   ├── daemon/
│   │   ├── __init__.py
│   │   └── main.py          # Pool daemon
│   ├── miner/
│   │   ├── __init__.py
│   │   └── cli.py           # Miner CLI
│   └── client/
│       ├── __init__.py
│       └── cli.py           # Client CLI
├── scripts/
│   ├── run_daemon.py
│   ├── run_miner.py
│   └── test_flow.py
├── pyproject.toml
└── README.md
```

---

## TEST THE FULL FLOW

```bash
# Terminal 1: IPFS daemon
ipfs daemon

# Terminal 2: Redis
redis-server

# Terminal 3: Pool daemon (you run this)
python -m swarmpool.daemon

# Terminal 4: Miner A (you or anyone)
swarm-miner mine --ens miner.alice.eth --key $KEY_A --mode SOLO

# Terminal 5: Miner B (another miner)
swarm-miner mine --ens miner.bob.eth --key $KEY_B --mode SOLO

# Terminal 6: Submit job (client)
swarm-client submit job.json --ens clinic.clientswarm.eth --key $CLIENT_KEY

# Watch the race! First miner to claim wins.
```

### EXPECTED OUTPUT

```
Pool:    📥 NEW JOB: bafybei... from clinic.clientswarm.eth
         ✅ Job added to pool. Pending: 1

Miner A: 📥 NEW JOB: bafybei... (queenbee-spine)
         ⛏️ Claiming...

Miner B: 📥 NEW JOB: bafybei... (queenbee-spine)
         ⛏️ Claiming...

Pool:    ⛏️ CLAIM: miner.alice.eth → bafybei...
         ✅ Claim accepted. Timeout: 300s

Miner A: ✅ Claim accepted!
         ⚙️ Executing job...

Miner B: ❌ Claim not accepted (someone else got it)

Miner A: 📤 Proof submitted: bafyproof...
         💰 Earned: $0.075 (Total: $0.08)

Pool:    📤 PROOF: miner.alice.eth → bafybei...
         ✅ Proof accepted!

Client:  ✅ JOB COMPLETE!
         Proof: bafyproof...
```

---

## THIS IS THE FUTURE

No cloud providers taking 50% margins.
No centralized APIs to attack.
No middlemen.

Just:
- Clients post jobs (signed → IPFS)
- Miners race to claim (pubsub)
- Proofs get submitted (signed → IPFS)
- Pool seals epochs (merkle root → IPFS)
- Everyone gets paid (75% miners / 25% ops)

**BITCOIN FOR AI INFERENCE.**

---

## COMPONENTS TO BUILD

| Component | Description |
|-----------|-------------|
| Pool Daemon | swarmpool.eth operator |
| Miner CLI | swarm-miner |
| Client CLI | swarm-client |
| IPFS + PubSub | Decentralized messaging |
| ENS Signatures | Identity verification |
| Epoch Management | Seal + settle |
| Settlement Calc | Fair distribution |

**NO API. NO CLOUD. JUST SIGNED SNAPSHOTS.**

🏊⛏️🐝⚡💰
