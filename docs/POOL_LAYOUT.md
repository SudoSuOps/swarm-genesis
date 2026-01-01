# Swarmpool.eth — IPFS Directory Conventions

## Purpose

Swarmpool is not a server.
It is a content-addressed ledger of opportunity.

**Structure creates discoverability.**

## 1. Root Layout

```
/swarmpool
├── /genesis
├── /epochs
├── /jobs
├── /claims
├── /proofs
└── /index
```

Each directory contains immutable snapshots only.

## 2. /genesis/

Genesis anchors.

```
/genesis
├── pool.json
├── manifesto.json
└── protocol.json
```

These never change.

## 3. /epochs/

Epoch lifecycle records.

```
/epochs
├── 0001
│   ├── epoch.json
│   └── seal.json
├── 0002
└── 0003
```

**Rules:**

- `epoch.json` published at OPEN
- `seal.json` published once at CLOSE
- epochs are append-only

## 4. /jobs/

Job offers.

```
/jobs
├── epoch-0003
│   ├── job-abc123.json
│   ├── job-def456.json
```

Jobs reference:

- epoch
- reward terms
- input CIDs

## 5. /claims/

Optional SOLO claims.

```
/claims
├── job-abc123
│   └── miner.alice.eth.json
```

Claims are advisory, not authoritative.

## 6. /proofs/

Proof of Compute submissions.

```
/proofs
├── epoch-0003
│   ├── job-abc123
│   │   ├── miner.alice.eth.json
│   │   └── miner.bob.eth.json
```

Multiple proofs allowed (PPL).

## 7. /index/

Read-optimized mirrors (optional).

```
/index
├── latest.json
├── epochs.json
├── miners.json
```

Indexes:

- are derived
- can be regenerated
- are never authoritative

## 8. Canon Rule

> Authority lives in snapshots, not indexes.
