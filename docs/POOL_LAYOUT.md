# Pool Layout Specification

IPFS directory conventions for swarmpool.eth.

## Overview

The pool state is published to IPFS as a directory tree. Each snapshot type has a dedicated path. All snapshots are append-only and immutable once published.

## Directory Structure

```
swarmpool.eth/
├── state.json                    # Current pool state (mutable root)
├── epochs/
│   ├── 0001/
│   │   ├── epoch.json           # Epoch metadata
│   │   ├── seal.json            # EPOCH_SEAL (when sealed)
│   │   ├── jobs/
│   │   │   ├── job-abc123.json
│   │   │   ├── job-def456.json
│   │   │   └── ...
│   │   ├── claims/
│   │   │   ├── claim-abc123-miner-alice.json
│   │   │   └── ...
│   │   └── proofs/
│   │       ├── proof-abc123-miner-alice.json
│   │       └── ...
│   ├── 0002/
│   │   └── ...
│   └── ...
├── miners/
│   ├── miner.alice.eth/
│   │   ├── genesis.json         # GENESIS_MINER
│   │   └── stats.json           # Aggregated stats
│   ├── miner.bob.eth/
│   │   └── ...
│   └── ...
└── manifesto.json               # Pool manifesto
```

## Path Conventions

### Epochs

| Path | Description |
|------|-------------|
| `/epochs/{epoch_num}/epoch.json` | Epoch metadata (OPEN/CLOSING/SEALED) |
| `/epochs/{epoch_num}/seal.json` | EPOCH_SEAL snapshot |
| `/epochs/{epoch_num}/jobs/{job_id}.json` | JOB snapshots |
| `/epochs/{epoch_num}/claims/{job_id}-{miner}.json` | CLAIM snapshots |
| `/epochs/{epoch_num}/proofs/{job_id}-{miner}.json` | PROOF snapshots |

Epoch numbers are zero-padded to 4 digits: `0001`, `0002`, etc.

### Miners

| Path | Description |
|------|-------------|
| `/miners/{ens}/genesis.json` | GENESIS_MINER registration |
| `/miners/{ens}/stats.json` | Aggregated performance stats |

ENS names are normalized (lowercase, no trailing dot).

### State

| Path | Description |
|------|-------------|
| `/state.json` | Current pool state (updated each publish) |
| `/manifesto.json` | Pool manifesto and terms |

## File Naming

### Jobs

```
job-{random_id}.json

Examples:
job-a1b2c3d4.json
job-spine-2025-001.json
```

Job IDs must match pattern: `^job-[a-z0-9\-]{6,64}$`

### Claims

```
claim-{job_id}-{miner_ens}.json

Examples:
claim-a1b2c3d4-miner.alice.eth.json
```

### Proofs

```
proof-{job_id}-{miner_ens}.json

Examples:
proof-a1b2c3d4-miner.alice.eth.json
```

## State.json Schema

The root `state.json` is the entry point for pool discovery:

```json
{
  "pool": "swarmpool.eth",
  "version": "bee-23@1.0",
  "current_epoch": 3,
  "epochs": {
    "active": "0003",
    "total": 3,
    "list": ["0001", "0002", "0003"]
  },
  "miners": {
    "total": 5,
    "active": 3
  },
  "stats": {
    "total_jobs": 12847,
    "total_proofs": 12847,
    "total_volume_usdc": 1284.70
  },
  "updated_at": "2025-01-01T12:00:00Z",
  "cid": "ipfs://bafy..."
}
```

## Publishing Flow

### 1. Controller Publishes Job

```bash
# Merlin publishes a new job
swarmhive publish job \
  --epoch 0003 \
  --task "queenbee-spine" \
  --reward 0.10 \
  --input ipfs://bafyinput...

# Published to:
# /epochs/0003/jobs/job-{new_id}.json
```

### 2. Miner Publishes Claim

```bash
# Miner claims a job
swarmhive claim job-abc123 \
  --miner miner.alice.eth \
  --lease 300

# Published to:
# /epochs/0003/claims/claim-job-abc123-miner.alice.eth.json
```

### 3. Miner Publishes Proof

```bash
# Miner submits proof
swarmhive prove job-abc123 \
  --miner miner.alice.eth \
  --result ipfs://bafyresult... \
  --compute-seconds 2

# Published to:
# /epochs/0003/proofs/proof-job-abc123-miner.alice.eth.json
```

### 4. Controller Seals Epoch

```bash
# Merlin seals the epoch
swarmhive seal 0003

# Published to:
# /epochs/0003/seal.json
# /epochs/0003/epoch.json (status: SEALED)
```

## IPFS Publishing

### Using IPFS CLI

```bash
# Add entire pool directory
ipfs add -r --cid-version 1 ./swarmpool/
# Returns: bafybei...root

# Pin to ensure persistence
ipfs pin add bafybei...root

# Publish to IPNS (optional)
ipfs name publish --key=swarmpool bafybei...root
```

### Using w3 (Storacha)

```bash
# Upload to web3.storage
w3 up ./swarmpool/ --name swarmpool-epoch-0003

# Returns CID for ENS update
```

### Updating ENS

After publishing, update the ENS contenthash:

```bash
# Via ENS app or CLI
ens set-content swarmpool.eth ipfs://bafybei...root
```

## Reading Pool State

### Discovery

```bash
# Resolve ENS to IPFS
ipfs resolve /ipns/swarmpool.eth
# Returns: /ipfs/bafybei...

# Or via gateway
curl https://swarmpool.eth.limo/state.json
```

### Fetching Snapshots

```bash
# Get current epoch
curl https://swarmpool.eth.limo/epochs/0003/epoch.json

# List jobs in epoch
curl https://swarmpool.eth.limo/epochs/0003/jobs/

# Get specific job
curl https://swarmpool.eth.limo/epochs/0003/jobs/job-abc123.json
```

## Indexing

Miners should index the pool for efficient job discovery:

```python
class PoolIndexer:
    def __init__(self, pool_cid: str):
        self.pool_cid = pool_cid
        self.jobs = {}
        self.claims = {}
        self.proofs = {}

    def sync_epoch(self, epoch: str):
        """Sync all snapshots for an epoch."""
        # Fetch job list
        jobs_path = f"{self.pool_cid}/epochs/{epoch}/jobs/"
        for job_file in self.list_dir(jobs_path):
            job = self.fetch_json(f"{jobs_path}/{job_file}")
            self.jobs[job['body']['job_id']] = job

        # Fetch claims
        claims_path = f"{self.pool_cid}/epochs/{epoch}/claims/"
        for claim_file in self.list_dir(claims_path):
            claim = self.fetch_json(f"{claims_path}/{claim_file}")
            job_id = claim['body']['job_id']
            self.claims[job_id] = claim

        # Fetch proofs
        proofs_path = f"{self.pool_cid}/epochs/{epoch}/proofs/"
        for proof_file in self.list_dir(proofs_path):
            proof = self.fetch_json(f"{proofs_path}/{proof_file}")
            job_id = proof['body']['job_id']
            self.proofs[job_id] = proof

    def available_jobs(self) -> list:
        """Return jobs that are not claimed or have expired claims."""
        available = []
        for job_id, job in self.jobs.items():
            if job_id not in self.claims:
                available.append(job)
            elif self.claim_expired(self.claims[job_id]):
                available.append(job)
        return available
```

## Caching

Miners SHOULD cache snapshots locally:

```
~/.swarmhive/cache/
├── swarmpool.eth/
│   ├── state.json
│   ├── epochs/
│   │   └── 0003/
│   │       ├── jobs/
│   │       ├── claims/
│   │       └── proofs/
│   └── miners/
└── cache.db              # SQLite index
```

## Garbage Collection

Old epochs can be unpinned after settlement window (e.g., 30 days):

```bash
# Unpin old epoch
ipfs pin rm bafybei...epoch0001

# Keep sealed epochs for audit
# Only unpin after payout verification complete
```

## Security Considerations

1. **Signature verification**: Always verify snapshot signatures before trusting
2. **Timestamp validation**: Reject stale snapshots
3. **Path traversal**: Sanitize ENS/job IDs to prevent directory traversal
4. **Rate limiting**: Limit fetch rate to prevent gateway abuse
5. **Pinning strategy**: Pin only verified snapshots

## Reference

- IPFS Docs: https://docs.ipfs.tech/
- ENS Contenthash: https://docs.ens.domains/contract-api-reference/publicresolver#contenthash
- w3 CLI: https://web3.storage/docs/w3cli/
