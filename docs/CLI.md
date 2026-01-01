# SwarmHive CLI Reference

## Philosophy

The CLI is:

- local
- deterministic
- sovereign
- boring (by design)

**No background magic. No silent mutation.**

## 1. swarmhive init

Register as a compute provider.

```bash
swarmhive init --ens miner.alice.eth --pool swarmpool.eth
```

Creates:

- local keys
- GENESIS_MINER snapshot
- publishes to IPFS
- writes `~/.swarmhive/config.toml`

## 2. swarmhive watch

Observe the memepool.

```bash
swarmhive watch --pool swarmpool.eth
```

Shows:

- open epochs
- available jobs
- SOLO / PPL modes
- reward terms

Read-only. Safe.

## 3. swarmhive submit

Submit a job (controller / client).

```bash
swarmhive submit job.json
```

Validates:

- schema
- signature
- epoch state

Publishes to `/jobs`.

## 4. swarmhive claim

Claim a SOLO job (optional).

```bash
swarmhive claim job-abc123 --lease 900
```

Publishes a CLAIM snapshot.
Does not block others from computing.

## 5. swarmhive prove

Submit Proof of Compute.

```bash
swarmhive prove \
  --job job-abc123 \
  --result ipfs://bafy... \
  --compute-seconds 1834
```

Publishes a PROOF snapshot.

## 6. swarmhive seal

Epoch close (Merlin only).

```bash
swarmhive seal --epoch 3
```

- aggregates proofs
- computes payouts
- publishes EPOCH_SEAL

## 7. Exit Is Always Allowed

```
Ctrl+C
```

No penalties. No locks. No state loss.

## 8. Canon Rule

> If you don't want to compute, you don't.
> If you compute, you prove.
> If you prove, you earn.
