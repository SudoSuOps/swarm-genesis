# SwarmPool Genesis

**Sovereign Compute Pool** settled via IPFS.

> Jobs are visible. Miners choose. Proof settles.

## Architecture

```
                      ┌───────────────────────────────┐
                      │           swarmpool.eth        │
                      │   IPFS-backed JOB MEMEPOOL     │
                      │  (append-only signed snapshots)│
                      └───────────────┬───────────────┘
                                      │
                 publishes JOB / EPOCH│open/close / seals
                                      │
                           ┌──────────▼──────────┐
                           │  MERLIN (Controller)│
                           │  merlin.swarmos.eth  │
                           │  - authors jobs      │
                           │  - opens epochs      │
                           │  - verifies proofs   │
                           │  - seals payouts     │
                           │  (NO compute, NO assign,
                           │   NO inbound API)    │
                           └──────────┬──────────┘
                                      │
                    reads JOBS         │         publishes PROOF/RESULT
               ┌───────────────────────┼───────────────────────────────┐
               │                       │                               │
     ┌─────────▼─────────┐    ┌────────▼─────────┐           ┌─────────▼─────────┐
     │ SwarmHive Miner A  │    │ SwarmHive Miner B │   ...     │ SwarmHive Miner N  │
     │ miner.*.eth        │    │ miner.*.eth       │           │ miner.*.eth        │
     │ - watch pool       │    │ - watch pool      │           │ - watch pool       │
     │ - SOLO or PPL      │    │ - SOLO or PPL     │           │ - SOLO or PPL      │
     │ - compute local    │    │ - compute local   │           │ - compute local    │
     └─────────┬─────────┘    └────────┬─────────┘           └─────────┬─────────┘
               │                        │                               │
               │ optional: executes      │                               │
               │ heavy tasks via         │                               │
               │ worker bee              │                               │
         ┌─────▼─────┐           ┌──────▼──────┐                 ┌──────▼──────┐
         │ Bumble70B  │           │ Bumble70B    │                 │ Bumble70B    │
         │ (Worker)   │           │ (Worker)     │                 │ (Worker)     │
         └───────────┘           └──────────────┘                 └──────────────┘

                 Settlement:
                 - PROOF snapshots → payout calculation
                 - EPOCH_SEAL snapshot → final truth
                 - 75% miners / 25% hive ops
                 - No proof, no pay
```

## Actors

| Actor | ENS | Role |
|-------|-----|------|
| SwarmPool | swarmpool.eth | IPFS job mempool (append-only) |
| Merlin | merlin.swarmos.eth | Controller: authors jobs, seals epochs |
| Miners | miner.*.eth | Sovereign compute providers |
| Bumble70B | bumble70b.swarmbee.eth | Worker bee (GPU inference) |

## Snapshot Types

| Type | Schema | Publisher |
|------|--------|-----------|
| `GENESIS_MINER` | genesis.miner.schema.json | Miner |
| `JOB` | job.schema.json | Controller (Merlin) |
| `CLAIM` | claim.schema.json | Miner |
| `PROOF` | proof.schema.json | Miner |
| `EPOCH_SEAL` | epoch.seal.schema.json | Controller (Merlin) |

## Directory Structure

```
swarm-genesis/
├── epochs/
│   └── 0001/
│       └── epoch.json          # Genesis epoch
├── schemas/
│   └── bee-23/
│       ├── base.snapshot.schema.json
│       ├── genesis.miner.schema.json
│       ├── job.schema.json
│       ├── claim.schema.json
│       ├── proof.schema.json
│       └── epoch.seal.schema.json
├── orb/
│   └── prompts/
│       └── ingest_swarmpool_genesis.txt
├── swarmpool-landing/          # Dashboard UI
├── MANIFESTO.md
├── SWARMPOOL_ARCHITECTURE.md
└── COMPUTE_SETTLEMENT_LAYER.md
```

## Quick Start (Miner)

```bash
curl -fsSL https://swarmhive.eth.limo/install.sh | bash
swarmhive init --ens miner --pool swarmpool.eth
```

Output:
```
Miner: miner.alice.eth
Genesis CID: ipfs://bafy...
Config: ~/.swarmhive/config.toml
Next: swarmhive watch --pool swarmpool.eth
```

## Economics

- **75%** → Miners (proportional to completed proofs)
- **25%** → Hive Operations (pool maintenance, infra)
- **Currency**: USDC / USDT / DAI
- **Settlement**: Per-epoch Merkle proofs
- **Rule**: No proof = no pay

## Modes

- **SOLO**: First-claim wins, higher variance, full job reward
- **PPL**: Pool smoothing, lower variance, shared rewards

## Links

- **Dashboard**: [swarmpool.eth.limo](https://swarmpool.eth.limo)
- **Architecture**: [SWARMPOOL_ARCHITECTURE.md](./SWARMPOOL_ARCHITECTURE.md)
- **Settlement**: [COMPUTE_SETTLEMENT_LAYER.md](./COMPUTE_SETTLEMENT_LAYER.md)

## License

MIT
