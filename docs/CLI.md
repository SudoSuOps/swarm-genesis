# SwarmHive CLI Specification

Command reference for `swarmhive` CLI.

## Installation

```bash
# From PyPI
pip install swarmhive-cli

# From source
git clone https://github.com/SudoSuOps/swarm-genesis
cd swarm-genesis/swarmhive-cli
pip install -e .
```

## Configuration

Config file: `~/.swarmhive/config.toml`

```toml
[identity]
ens = "miner.alice.eth"
key_path = "~/.swarmhive/keys/node.json"

[pool]
name = "swarmpool.eth"
gateway = "https://w3s.link/ipfs"

[ipfs]
api = "/ip4/127.0.0.1/tcp/5001"
gateway = "https://ipfs.io/ipfs"

[models]
dir = "~/.swarmhive/models"
```

## Commands

### init

Initialize a new miner identity.

```bash
swarmhive init --ens miner.alice.eth --pool swarmpool.eth
```

**Flow:**
1. Check environment (OS, IPFS, dependencies)
2. Generate keypair → `~/.swarmhive/keys/node.json`
3. Prompt for wallet signature
4. Create GENESIS_MINER snapshot
5. Publish to IPFS
6. Write config

**Output:**
```
Miner: miner.alice.eth
Genesis CID: ipfs://bafy...
Config: ~/.swarmhive/config.toml
Next: swarmhive watch --pool swarmpool.eth
```

**Options:**
| Flag | Description |
|------|-------------|
| `--ens` | ENS identity (required) |
| `--pool` | Pool to join (default: swarmpool.eth) |
| `--gpu` | GPU devices to use (default: auto-detect) |
| `--skip-signature` | Skip wallet signature (dev only) |

---

### keygen

Generate a new keypair.

```bash
swarmhive keygen
```

**Output:**
```
Generated keypair:
  Private: ~/.swarmhive/keys/node.json
  Public:  0x1234...abcd
```

---

### watch

Watch pool for available jobs.

```bash
swarmhive watch --pool swarmpool.eth
```

**Flow:**
1. Sync pool state from IPFS
2. Index available jobs
3. Filter by capabilities
4. Display job feed
5. Auto-claim in SOLO mode (optional)

**Options:**
| Flag | Description |
|------|-------------|
| `--pool` | Pool to watch (default: config) |
| `--epoch` | Specific epoch (default: current) |
| `--mode` | SOLO or PPL (default: SOLO) |
| `--auto-claim` | Auto-claim matching jobs |
| `--interval` | Sync interval in seconds (default: 10) |

**Output:**
```
Watching swarmpool.eth (epoch 0003)
Mode: SOLO | Auto-claim: ON

[12:00:01] JOB job-abc123 | queenbee-spine | $0.10 | AVAILABLE
[12:00:02] JOB job-def456 | queenbee-chest | $0.10 | CLAIMED by miner.bob.eth
[12:00:05] CLAIMING job-abc123...
[12:00:05] CLAIMED job-abc123 | lease: 300s
```

---

### claim

Claim a specific job.

```bash
swarmhive claim job-abc123 --lease 300
```

**Flow:**
1. Fetch job snapshot
2. Verify job is available
3. Create CLAIM snapshot
4. Sign with miner key
5. Publish to IPFS

**Options:**
| Flag | Description |
|------|-------------|
| `--lease` | Lease duration in seconds (default: 300) |
| `--miner` | Miner identity (default: config) |

**Output:**
```
Claimed: job-abc123
Lease: 300s (expires 12:05:00)
Claim CID: ipfs://bafy...
```

---

### prove

Submit proof of completed work.

```bash
swarmhive prove job-abc123 \
  --result ipfs://bafyresult... \
  --compute-seconds 2
```

**Flow:**
1. Verify claim exists for miner
2. Create PROOF snapshot
3. Sign with miner key
4. Publish to IPFS

**Options:**
| Flag | Description |
|------|-------------|
| `--result` | Result CID (required) |
| `--compute-seconds` | Compute time (required) |
| `--log` | Optional log CID |
| `--miner` | Miner identity (default: config) |

**Output:**
```
Proof submitted: job-abc123
Result: ipfs://bafyresult...
Compute: 2s
Proof CID: ipfs://bafy...
```

---

### mine

Full mining loop (watch + claim + compute + prove).

```bash
swarmhive mine --gpu 0,1
```

**Flow:**
1. Start watcher
2. Auto-claim available jobs
3. Run inference
4. Submit proof
5. Repeat

**Options:**
| Flag | Description |
|------|-------------|
| `--gpu` | GPU devices (default: all) |
| `--mode` | SOLO or PPL (default: SOLO) |
| `--models` | Model filter (default: all) |
| `--max-concurrent` | Max concurrent jobs (default: 1) |

**Output:**
```
Mining on swarmpool.eth
GPUs: 0 (RTX 4090), 1 (RTX 4090)
Mode: SOLO

[12:00:01] CLAIMED job-abc123 | queenbee-spine
[12:00:03] COMPLETED job-abc123 | 1.8s | $0.075 earned
[12:00:04] CLAIMED job-def456 | queenbee-chest
[12:00:05] COMPLETED job-def456 | 1.2s | $0.075 earned
...
```

---

### seal (Controller only)

Seal an epoch.

```bash
swarmhive seal 0003
```

**Flow:**
1. Aggregate all proofs for epoch
2. Calculate payouts (75% miners / 25% hive)
3. Build Merkle tree
4. Create EPOCH_SEAL snapshot
5. Sign with controller key
6. Publish to IPFS

**Options:**
| Flag | Description |
|------|-------------|
| `--dry-run` | Preview without publishing |
| `--force` | Seal even with pending jobs |

**Output:**
```
Sealing epoch 0003

Jobs: 1,234
Proofs: 1,234
Volume: $123.40

Payouts:
  miner.alice.eth: $45.00
  miner.bob.eth:   $32.25
  miner.carol.eth: $15.30
  (hive):          $30.85

Merkle root: 0x7a8b...
Seal CID: ipfs://bafy...
```

---

### earnings

Check earnings for an epoch.

```bash
swarmhive earnings --epoch 0003
```

**Options:**
| Flag | Description |
|------|-------------|
| `--epoch` | Epoch number (default: current) |
| `--miner` | Miner identity (default: config) |

**Output:**
```
Epoch 0003 Earnings

Jobs completed: 47
Compute time: 82s
Gross: $4.70
Net (75%): $3.53

Status: PENDING (epoch not sealed)
```

---

### verify

Verify a snapshot signature.

```bash
swarmhive verify snapshot.json
```

**Output:**
```
Snapshot: PROOF
Issuer: ens:miner.alice.eth
Payload hash: sha256:7a8b...
Signature: VALID
ENS resolved: 0x1234...abcd
Signer: 0x1234...abcd
```

---

### models

Manage AI models.

```bash
# List available models
swarmhive models list

# Download a model
swarmhive models download queenbee-spine

# Download all models
swarmhive models download --all

# Check model status
swarmhive models status
```

**Output (list):**
```
Available models:

  queenbee-spine    v1.0.0    2.1GB    INSTALLED
  queenbee-chest    v1.0.0    1.8GB    NOT INSTALLED
  queenbee-cardiac  v1.0.0    2.4GB    NOT INSTALLED
```

---

### status

Show current mining status.

```bash
swarmhive status
```

**Output:**
```
SwarmHive Miner Status

Identity: miner.alice.eth
Pool: swarmpool.eth
Epoch: 0003 (OPEN)

GPU 0: RTX 4090 (24GB) - IDLE
GPU 1: RTX 4090 (24GB) - COMPUTING job-abc123

Session:
  Jobs: 47
  Earnings: $3.53
  Uptime: 4h 23m
```

---

### epoch

Epoch operations.

```bash
# Fetch epoch data
swarmhive epoch fetch 0003

# Verify epoch seal
swarmhive epoch verify 0003

# List jobs in epoch
swarmhive epoch jobs 0003

# Generate payout proof
swarmhive epoch proof 0003 --miner miner.alice.eth
```

---

### publish

Publish a snapshot to IPFS.

```bash
swarmhive publish snapshot.json
```

---

### sign

Sign a snapshot.

```bash
swarmhive sign snapshot.json --key ~/.swarmhive/keys/node.json
```

---

### hash

Compute payload hash.

```bash
swarmhive hash snapshot.json
```

**Output:**
```
sha256:7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SWARMHIVE_CONFIG` | Config file path |
| `SWARMHIVE_KEY` | Private key path |
| `SWARMHIVE_POOL` | Default pool |
| `IPFS_API` | IPFS API endpoint |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Config error |
| 3 | Network error |
| 4 | Signature error |
| 5 | Validation error |
