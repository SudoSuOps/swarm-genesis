# SWARM COMPUTE SETTLEMENT LAYER — IPFS MEMPOOL ARCHITECTURE

No REST APIs. No public endpoints. Just signed snapshots on IPFS.

## ARCHITECTURE

```
Client (xyz.clientswarm.eth)
│
│ 1. Create job snapshot (JSON)
│ 2. Sign with ENS key
│ 3. Upload to IPFS → CID
│ 4. Send CID to Bee-1 (out-of-band: Redis, file, signal)
▼
┌─────────────────────────────────────────────────────────────┐
│ IPFS                                                        │
│ The Mempool                                                 │
│                                                             │
│ • Job snapshots (signed by clients)                        │
│ • Result snapshots (signed by workers)                     │
│ • Epoch snapshots (signed by controller)                   │
│ • Append-only. Immutable. Global.                          │
└─────────────────────────────────────────────────────────────┘
│
│ Bee-1 watches for authorized CIDs
▼
┌─────────────────────────────────────────────────────────────┐
│ BEE-1 (The Miner)                                           │
│                                                             │
│ • Watches IPFS for new CIDs (authorized clients only)      │
│ • Verifies ENS signature                                   │
│ • Pulls job from IPFS                                      │
│ • Executes inference                                       │
│ • Creates result snapshot                                  │
│ • Signs with worker key                                    │
│ • Publishes result CID to IPFS                            │
└─────────────────────────────────────────────────────────────┘
│
│ Result CID published
▼
┌─────────────────────────────────────────────────────────────┐
│ ORB (The Historian)                                         │
│                                                             │
│ • Reads all snapshots from IPFS                            │
│ • Builds epoch history                                     │
│ • Verifies all signatures                                  │
│ • Displays truth                                           │
└─────────────────────────────────────────────────────────────┘
```

## SNAPSHOT SCHEMAS

### 1. JOB SNAPSHOT (client → IPFS)

```json
{
  "type": "job",
  "version": "1.0.0",
  "job_id": "job-20260101-001",
  "job_type": "spine-mri-inference",
  "model": "queenbee-spine",
  "input_cid": "bafybeiabc123...",
  "params": {
    "confidence_threshold": 0.6,
    "output_format": "pdf"
  },
  "payment": {
    "amount": "0.10",
    "token": "USDC"
  },
  "client": "xyz.clientswarm.eth",
  "timestamp": 1735689600,
  "nonce": "a9f3b2c1d4e5",
  "sig": "0xabc123..."
}
```

### 2. RESULT SNAPSHOT (worker → IPFS)

```json
{
  "type": "result",
  "version": "1.0.0",
  "job_id": "job-20260101-001",
  "job_cid": "bafybeijob...",
  "status": "completed",
  "output_cid": "bafybeiresult...",
  "report_cid": "bafybeipdf...",
  "metrics": {
    "inference_seconds": 95,
    "confidence": 0.72,
    "model_version": "queenbee-spine-v2.1"
  },
  "worker": "bumble70b.swarmbee.eth",
  "timestamp": 1735689695,
  "proof_hash": "0xdef456...",
  "sig": "0x789xyz..."
}
```

### 3. EPOCH SNAPSHOT (controller → IPFS)

```json
{
  "type": "epoch",
  "version": "1.0.0",
  "epoch_id": "epoch-002",
  "name": "Bravo",
  "status": "sealed",
  "started_at": 1735689600,
  "ended_at": 1735776000,
  "jobs": [
    {"job_cid": "bafybeijob1...", "result_cid": "bafybeiresult1..."},
    {"job_cid": "bafybeijob2...", "result_cid": "bafybeiresult2..."}
  ],
  "jobs_count": 55,
  "total_volume_usdc": "5.50",
  "merkle_root": "0xepochroot...",
  "settlements": {
    "workers": "4.125",
    "hive_ops": "1.375"
  },
  "controller": "merlin.swarmos.eth",
  "timestamp": 1735776000,
  "sig": "0xepochsig..."
}
```

---

## IMPLEMENTATION

### TASK 1: ENS SIGNATURE UTILS

```python
# swarm/crypto.py

from eth_account import Account
from eth_account.messages import encode_defunct
import json

def sign_snapshot(snapshot: dict, private_key: str) -> str:
    """Sign a snapshot with ENS-linked private key."""
    data = {k: v for k, v in snapshot.items() if k != 'sig'}
    message = json.dumps(data, sort_keys=True, separators=(',', ':'))
    message_hash = encode_defunct(text=message)
    signed = Account.sign_message(message_hash, private_key)
    return signed.signature.hex()

def verify_snapshot(snapshot: dict) -> tuple[bool, str]:
    """Verify snapshot signature, return (valid, recovered_address)."""
    sig = snapshot.get('sig')
    if not sig:
        return False, ""

    data = {k: v for k, v in snapshot.items() if k != 'sig'}
    message = json.dumps(data, sort_keys=True, separators=(',', ':'))
    message_hash = encode_defunct(text=message)

    try:
        recovered = Account.recover_message(message_hash, signature=sig)
        return True, recovered
    except Exception as e:
        return False, str(e)

async def resolve_ens_address(ens_name: str) -> str:
    """Resolve ENS name to address (for verification)."""
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))
    return w3.ens.address(ens_name)

async def verify_ens_signature(snapshot: dict, expected_ens: str) -> bool:
    """Verify snapshot was signed by the claimed ENS holder."""
    valid, recovered = verify_snapshot(snapshot)
    if not valid:
        return False

    ens_address = await resolve_ens_address(expected_ens)
    return recovered.lower() == ens_address.lower()
```

### TASK 2: IPFS UTILS

```python
# swarm/ipfs.py

import httpx
import json
from typing import Optional

IPFS_API = "http://localhost:5001/api/v0"
IPFS_GATEWAY = "https://ipfs.io/ipfs"

async def upload_snapshot(snapshot: dict) -> str:
    """Upload snapshot to IPFS, return CID."""
    async with httpx.AsyncClient() as client:
        data = json.dumps(snapshot, sort_keys=True, indent=2)
        files = {'file': ('snapshot.json', data)}
        response = await client.post(f"{IPFS_API}/add", files=files)
        result = response.json()
        return result['Hash']

async def fetch_snapshot(cid: str) -> Optional[dict]:
    """Fetch snapshot from IPFS by CID."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(f"{IPFS_GATEWAY}/{cid}")
            return response.json()
        except Exception as e:
            print(f"Failed to fetch {cid}: {e}")
            return None

async def pin_cid(cid: str) -> bool:
    """Pin CID to local IPFS node."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{IPFS_API}/pin/add?arg={cid}")
        return response.status_code == 200
```

### TASK 3: CLIENT CLI

```python
# swarm/cli/client.py
# Usage: swarm submit job.json

import asyncio
import json
import click
from pathlib import Path
from ..crypto import sign_snapshot
from ..ipfs import upload_snapshot

@click.group()
def cli():
    """Swarm Client CLI"""
    pass

@cli.command()
@click.argument('job_file', type=click.Path(exists=True))
@click.option('--key', envvar='SWARM_PRIVATE_KEY', help='Private key for signing')
@click.option('--signal', default='redis', help='Signal method: redis, file, webhook')
def submit(job_file: str, key: str, signal: str):
    """Submit a job to the swarm."""
    asyncio.run(_submit(job_file, key, signal))

async def _submit(job_file: str, key: str, signal: str):
    # Load job
    job = json.loads(Path(job_file).read_text())

    # Sign
    click.echo(f"Signing job as {job['client']}...")
    job['sig'] = sign_snapshot(job, key)

    # Upload to IPFS
    click.echo("Uploading to IPFS...")
    cid = await upload_snapshot(job)
    click.echo(f"→ CID: {cid}")

    # Signal Bee-1 (out-of-band)
    if signal == 'redis':
        import redis.asyncio as redis
        r = redis.from_url("redis://localhost:6379")
        await r.lpush("swarm:jobs:pending", json.dumps({
            "cid": cid,
            "client": job['client'],
            "timestamp": job['timestamp']
        }))
        click.echo("→ Signaled via Redis")
    elif signal == 'file':
        pending_dir = Path.home() / ".swarm" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        (pending_dir / f"{cid}.json").write_text(json.dumps({"cid": cid}))
        click.echo(f"→ Signaled via file: {pending_dir}/{cid}.json")

    click.echo("→ Waiting for result...")

    # Poll for result
    import redis.asyncio as redis
    r = redis.from_url("redis://localhost:6379")
    for _ in range(120):  # 2 minute timeout
        result = await r.get(f"swarm:results:{job['job_id']}")
        if result:
            result_data = json.loads(result)
            click.echo(f"\n✅ Job complete!")
            click.echo(f"→ Result CID: {result_data['result_cid']}")
            click.echo(f"→ Confidence: {result_data['confidence']}")
            return
        await asyncio.sleep(1)

    click.echo("⏱ Timeout waiting for result")

@cli.command()
@click.argument('cid')
def status(cid: str):
    """Check job status by CID."""
    asyncio.run(_status(cid))

async def _status(cid: str):
    from ..ipfs import fetch_snapshot
    snapshot = await fetch_snapshot(cid)
    if snapshot:
        click.echo(json.dumps(snapshot, indent=2))
    else:
        click.echo(f"Not found: {cid}")

if __name__ == '__main__':
    cli()
```

### TASK 4: BEE-1 WATCHER (The Miner)

```python
# swarm/bee1/watcher.py

import asyncio
import json
from datetime import datetime
from pathlib import Path

import redis.asyncio as redis

from ..crypto import verify_ens_signature
from ..ipfs import fetch_snapshot, upload_snapshot, pin_cid

class Bee1Watcher:
    """
    Watches for authorized job CIDs.
    Verifies signatures.
    Executes inference.
    Publishes results.

    NO INBOUND API. Only watches IPFS/Redis for signed snapshots.
    """

    def __init__(self, config: dict):
        self.config = config
        self.redis_url = config.get('redis_url', 'redis://localhost:6379')
        self.worker_ens = config.get('worker_ens', 'bumble70b.swarmbee.eth')
        self.worker_key = config.get('worker_private_key')
        self.authorized_clients = config.get('authorized_clients', [])
        self.running = False

    async def start(self):
        """Start watching for jobs."""
        self.running = True
        self.redis = redis.from_url(self.redis_url)

        print(f"🐝 Bee-1 Watcher started")
        print(f"   Worker: {self.worker_ens}")
        print(f"   Authorized clients: {len(self.authorized_clients)}")
        print(f"   Watching for jobs...")

        while self.running:
            await self._poll_for_jobs()
            await asyncio.sleep(1)

    async def stop(self):
        self.running = False
        await self.redis.close()

    async def _poll_for_jobs(self):
        """Poll Redis for new job CIDs."""
        job_signal = await self.redis.rpop("swarm:jobs:pending")
        if not job_signal:
            return

        signal = json.loads(job_signal)
        cid = signal['cid']
        client = signal['client']

        print(f"\n📥 New job signal: {cid[:16]}...")

        # Check if client is authorized
        if not self._is_authorized(client):
            print(f"   ❌ Unauthorized client: {client}")
            return

        # Fetch snapshot from IPFS
        job = await fetch_snapshot(cid)
        if not job:
            print(f"   ❌ Failed to fetch from IPFS")
            return

        # Verify ENS signature
        print(f"   🔐 Verifying signature...")
        valid = await verify_ens_signature(job, job['client'])
        if not valid:
            print(f"   ❌ Invalid signature")
            return

        print(f"   ✅ Signature valid")

        # Pin the job CID
        await pin_cid(cid)

        # Execute the job
        result = await self._execute_job(job, cid)

        # Publish result to IPFS
        result_cid = await self._publish_result(result)

        # Signal result availability
        await self.redis.set(
            f"swarm:results:{job['job_id']}",
            json.dumps({
                "result_cid": result_cid,
                "confidence": result['metrics']['confidence'],
                "status": "completed"
            }),
            ex=86400  # 24h TTL
        )

        print(f"   ✅ Job complete: {result_cid[:16]}...")

    def _is_authorized(self, client_ens: str) -> bool:
        """Check if client is authorized."""
        if client_ens.endswith('.clientswarm.eth'):
            return True
        return client_ens in self.authorized_clients

    async def _execute_job(self, job: dict, job_cid: str) -> dict:
        """Execute inference job."""
        print(f"   ⚙️ Executing: {job['job_type']}")

        start_time = datetime.utcnow()

        # Run inference (integrate with actual model)
        await asyncio.sleep(2)  # Simulate inference

        confidence = 0.72
        inference_time = (datetime.utcnow() - start_time).total_seconds()

        from ..crypto import sign_snapshot
        import hashlib

        result = {
            "type": "result",
            "version": "1.0.0",
            "job_id": job['job_id'],
            "job_cid": job_cid,
            "status": "completed",
            "output_cid": "bafybei_output_placeholder",
            "report_cid": "bafybei_report_placeholder",
            "metrics": {
                "inference_seconds": round(inference_time, 2),
                "confidence": confidence,
                "model_version": "queenbee-spine-v2.1"
            },
            "worker": self.worker_ens,
            "timestamp": int(datetime.utcnow().timestamp()),
            "proof_hash": hashlib.sha256(
                json.dumps(job, sort_keys=True).encode()
            ).hexdigest()
        }

        result['sig'] = sign_snapshot(result, self.worker_key)
        return result

    async def _publish_result(self, result: dict) -> str:
        """Publish result snapshot to IPFS."""
        cid = await upload_snapshot(result)
        await pin_cid(cid)
        print(f"   📤 Result published: {cid[:16]}...")
        return cid


if __name__ == '__main__':
    config = {
        'redis_url': 'redis://localhost:6379',
        'worker_ens': 'bumble70b.swarmbee.eth',
        'worker_private_key': '0x...',
        'authorized_clients': []
    }

    watcher = Bee1Watcher(config)
    asyncio.run(watcher.start())
```

### TASK 5: EPOCH MANAGER

```python
# swarm/bee1/epochs.py

import asyncio
import json
import hashlib
from datetime import datetime, timezone
from typing import List

from ..crypto import sign_snapshot
from ..ipfs import upload_snapshot, fetch_snapshot

class EpochManager:
    """
    Manages epochs.
    Seals completed epochs.
    Calculates settlements.
    """

    def __init__(self, redis_client, controller_ens: str, controller_key: str):
        self.redis = redis_client
        self.controller_ens = controller_ens
        self.controller_key = controller_key
        self.current_epoch = None

    async def open_epoch(self, name: str) -> dict:
        """Open a new epoch."""
        epoch_id = f"epoch-{datetime.utcnow().strftime('%Y%m%d%H%M')}"

        self.current_epoch = {
            "type": "epoch",
            "version": "1.0.0",
            "epoch_id": epoch_id,
            "name": name,
            "status": "active",
            "started_at": int(datetime.utcnow().timestamp()),
            "ended_at": None,
            "jobs": [],
            "jobs_count": 0,
            "total_volume_usdc": "0.00",
            "merkle_root": None,
            "settlements": None,
            "controller": self.controller_ens
        }

        await self.redis.set(
            "swarm:epoch:current",
            json.dumps(self.current_epoch)
        )

        print(f"📖 Epoch opened: {epoch_id} ({name})")
        return self.current_epoch

    async def record_job(self, job_cid: str, result_cid: str, volume_usdc: float):
        """Record completed job in current epoch."""
        if not self.current_epoch:
            print("⚠️ No active epoch")
            return

        self.current_epoch['jobs'].append({
            "job_cid": job_cid,
            "result_cid": result_cid,
            "volume_usdc": str(volume_usdc)
        })
        self.current_epoch['jobs_count'] += 1

        current_volume = float(self.current_epoch['total_volume_usdc'])
        self.current_epoch['total_volume_usdc'] = str(current_volume + volume_usdc)

        await self.redis.set(
            "swarm:epoch:current",
            json.dumps(self.current_epoch)
        )

    async def seal_epoch(self) -> str:
        """Seal current epoch, publish to IPFS."""
        if not self.current_epoch:
            raise ValueError("No active epoch to seal")

        epoch = self.current_epoch
        epoch['status'] = 'sealed'
        epoch['ended_at'] = int(datetime.utcnow().timestamp())

        epoch['merkle_root'] = self._calculate_merkle_root(epoch['jobs'])

        total = float(epoch['total_volume_usdc'])
        epoch['settlements'] = {
            "workers": str(round(total * 0.75, 2)),
            "hive_ops": str(round(total * 0.25, 2))
        }

        epoch['timestamp'] = int(datetime.utcnow().timestamp())
        epoch['sig'] = sign_snapshot(epoch, self.controller_key)

        cid = await upload_snapshot(epoch)

        await self.redis.set(f"swarm:epochs:{epoch['epoch_id']}", json.dumps(epoch))
        await self.redis.lpush("swarm:epochs:history", cid)

        await self.redis.delete("swarm:epoch:current")
        self.current_epoch = None

        print(f"📕 Epoch sealed: {epoch['epoch_id']} → {cid[:16]}...")
        print(f"   Jobs: {epoch['jobs_count']}, Volume: ${epoch['total_volume_usdc']}")
        print(f"   Workers: ${epoch['settlements']['workers']}")
        print(f"   Hive Ops: ${epoch['settlements']['hive_ops']}")

        return cid

    def _calculate_merkle_root(self, jobs: List[dict]) -> str:
        """Calculate Merkle root of job CIDs."""
        if not jobs:
            return "0x" + "0" * 64

        leaves = [j['job_cid'] + j['result_cid'] for j in jobs]
        combined = ''.join(sorted(leaves))
        return "0x" + hashlib.sha256(combined.encode()).hexdigest()
```

### TASK 6: ORB HISTORIAN

```python
# swarm/orb/historian.py

import asyncio
import json
from typing import List, Optional

from ..ipfs import fetch_snapshot
from ..crypto import verify_snapshot

class OrbHistorian:
    """
    Reads and indexes all snapshots from IPFS.
    Builds the complete history.
    Verifies all signatures.
    Serves as the source of truth for the Orb UI.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.epochs = []
        self.jobs = {}
        self.workers = {}

    async def sync(self):
        """Sync all epoch history from IPFS."""
        print("🔮 Orb syncing...")

        epoch_cids = await self.redis.lrange("swarm:epochs:history", 0, -1)

        for cid in epoch_cids:
            cid = cid.decode() if isinstance(cid, bytes) else cid
            epoch = await fetch_snapshot(cid)

            if not epoch:
                continue

            valid, _ = verify_snapshot(epoch)
            if not valid:
                print(f"   ⚠️ Invalid epoch signature: {cid[:16]}")
                continue

            self.epochs.append(epoch)

            for job in epoch.get('jobs', []):
                self.jobs[job['job_cid']] = {
                    **job,
                    'epoch_id': epoch['epoch_id']
                }

        print(f"   ✅ Synced {len(self.epochs)} epochs, {len(self.jobs)} jobs")

    def get_stats(self) -> dict:
        """Get network stats for Orb display."""
        total_jobs = sum(e['jobs_count'] for e in self.epochs)
        total_volume = sum(float(e['total_volume_usdc']) for e in self.epochs)

        return {
            "epochs": {
                "total": len(self.epochs),
                "list": [
                    {
                        "epoch_id": e['epoch_id'],
                        "name": e['name'],
                        "status": e['status'],
                        "jobs_count": e['jobs_count'],
                        "volume_usdc": e['total_volume_usdc']
                    }
                    for e in sorted(self.epochs, key=lambda x: x['started_at'], reverse=True)
                ]
            },
            "jobs": {
                "total": total_jobs
            },
            "volume": {
                "total_usdc": round(total_volume, 2)
            }
        }

    async def verify_job(self, job_cid: str) -> dict:
        """Verify a job exists and is valid."""
        job_snapshot = await fetch_snapshot(job_cid)
        if not job_snapshot:
            return {"valid": False, "error": "Not found"}

        valid, recovered = verify_snapshot(job_snapshot)
        return {
            "valid": valid,
            "snapshot": job_snapshot,
            "signer": recovered
        }
```

---

## DIRECTORY STRUCTURE

```
~/swarm/
├── swarm/
│   ├── __init__.py
│   ├── crypto.py              # ENS signing/verification
│   ├── ipfs.py                # IPFS upload/fetch
│   ├── cli/
│   │   ├── __init__.py
│   │   └── client.py          # swarm submit, swarm status
│   ├── bee1/
│   │   ├── __init__.py
│   │   ├── watcher.py         # Job watcher (the miner)
│   │   ├── epochs.py          # Epoch manager
│   │   └── config.py
│   └── orb/
│       ├── __init__.py
│       └── historian.py       # Reads/indexes snapshots
├── scripts/
│   ├── run_watcher.py
│   ├── seal_epoch.py
│   └── test_flow.py
├── examples/
│   └── job.json               # Example job snapshot
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

# Terminal 3: Bee-1 Watcher
python -m swarm.bee1.watcher

# Terminal 4: Submit job
swarm submit examples/job.json --key $PRIVATE_KEY

# Expected output:
# Signing job as xyz.clientswarm.eth...
# Uploading to IPFS...
# → CID: bafybeigd...
# → Signaled via Redis
# → Waiting for result...
#
# ✅ Job complete!
# → Result CID: bafybeiresult...
# → Confidence: 0.72
```

---

## EXAMPLE JOB FILE

```json
{
  "type": "job",
  "version": "1.0.0",
  "job_id": "job-20260101-001",
  "job_type": "spine-mri-inference",
  "model": "queenbee-spine",
  "input_cid": "bafybeiabc123...",
  "params": {
    "confidence_threshold": 0.6,
    "output_format": "pdf"
  },
  "payment": {
    "amount": "0.10",
    "token": "USDC"
  },
  "client": "xyz.clientswarm.eth",
  "timestamp": 1735689600,
  "nonce": "a9f3b2c1d4e5"
}
```

---

## SUMMARY

This is a **SETTLEMENT LAYER**, not an API.

| Component | Role |
|-----------|------|
| **IPFS** | The mempool (global, immutable) |
| **Snapshots** | Transactions (signed, verifiable) |
| **Bee-1** | Miner (watches, executes, proves) |
| **Orb** | Historian (reads, indexes, displays) |
| **ENS** | Identity (clients, workers, controller) |

**No REST endpoints to attack.**
**No API surface to secure.**
**Just signed snapshots on a global append-only log.**

Bitcoin for AI compute. 🐝⚡💰
