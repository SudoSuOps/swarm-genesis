# SwarmPool Manifesto

## Sovereignty Over Allocation

We reject the "dark room" model of centralized compute allocation.

In traditional cloud infrastructure, a coordinator assigns work to workers in a black box. Workers have no visibility into the job queue. They cannot make intelligent decisions about capacity. They are reduced to fungible execution units.

SwarmPool inverts this. Jobs are published to an open mempool. Miners see all available work. They choose what to compute based on their capabilities, availability, and economic incentives. They can scale up when demand is high, scale down when it's not.

**The miner has agency.**

## Append-Only Truth

All state is published to IPFS as signed snapshots:

- Jobs are published by the controller
- Claims are published by miners
- Proofs are published by miners
- Epoch seals are published by the controller

Nothing is hidden. Everything is verifiable. The pool cannot lie about payouts because all inputs are public.

## No Inbound APIs

The controller (Merlin) has no inbound public API.

- It does not accept job submissions from external parties
- It does not assign jobs to workers
- It does not manage a job queue

Merlin's role is limited:
1. Publish jobs to the mempool
2. Open and close epochs
3. Verify proofs
4. Seal payouts

This constraint eliminates an entire class of attacks: there is no API to spam, no endpoint to DDoS, no authentication to bypass.

## Proof or Nothing

Miners are paid for completed work, not promised work.

A valid payout requires:
1. A signed JOB snapshot from the controller
2. A signed PROOF snapshot from the miner
3. Matching job_id across both
4. Valid cryptographic signatures

No proof = no pay. There are no exceptions.

## ENS Identity

All actors in the system have ENS identity:

- `swarmpool.eth` - The job mempool
- `merlin.swarmos.eth` - The controller
- `miner.*.eth` - Compute providers

Identity is not a database entry. It's a cryptographic commitment. Signatures are verified against ENS-resolved addresses.

## Economics

The split is simple:

- **75%** to miners who completed proofs
- **25%** to hive operations (maintenance, infrastructure, development)

This is not a governance token. This is not yield farming. This is payment for work.

## Two Modes

**SOLO**: First miner to claim wins the job. Higher variance, full reward. For miners who want to compete.

**PPL (Pay Per Last)**: Pool smoothing. Lower variance, shared rewards. For miners who want stability.

Both modes coexist. Miners choose per-job.

## What We Don't Do

- No staking requirements
- No slashing
- No governance tokens
- No yield farming
- No NFTs
- No "decentralized" with admin keys
- No Cloudflare dependencies
- No centralized job assignment

## The Stack

- **IPFS**: Append-only mempool
- **ENS**: Identity layer
- **EIP-191/712**: Signatures
- **USDC/USDT/DAI**: Settlement
- **GPU**: Compute

That's it. No chain-specific dependencies. No smart contracts required for core operation (optional for on-chain settlement).

## Genesis

Epoch 0001 opens January 1, 2025.

The pool is `swarmpool.eth`.
The controller is `merlin.swarmos.eth`.
The first miner is `bumble70b.swarmbee.eth`.

Let's mine.

---

*swarmpool.eth*
