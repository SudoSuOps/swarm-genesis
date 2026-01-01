# Bee-23 Snapshot Signing Rules (EIP-191 / EIP-712)

## Purpose

All SwarmHive snapshots MUST be:

- tamper-evident
- content-addressable
- independently verifiable
- ENS-bound

**There is no trust without signatures.**

## 1. Signing Overview

Every snapshot:

- is canonical JSON
- is hashed
- is signed by an ENS-controlled key
- is published to IPFS

Signatures prove:

- who authored the snapshot
- what exact content was authored
- when it was authored (via timestamp)

## 2. Canonical Payload Rules

Before hashing or signing:

**Serialize JSON using:**
- UTF-8
- sorted object keys (lexicographic)
- no whitespace outside string values

**Remove:**
- `signing.signature`

**Keep:**
- `signing.scheme`
- `signing.did`
- `signing.payload_hash` (optional at pre-hash stage)

This canonical serialization is the **signing payload**.

## 3. Payload Hash

### Default (REQUIRED)

```
keccak256(canonical_json_bytes)
```

Encoded as:

```
keccak256:<64-hex>
```

This hash:

- is stored in `signing.payload_hash`
- is what gets signed

## 4. EIP-191 (Default, Simple)

Used for:

- CLI signing
- hardware wallets
- fast miner onboarding

### Message Format

```
"\x19Ethereum Signed Message:\n" + len(payload_hash) + payload_hash
```

### Snapshot Field

```json
"signing": {
  "scheme": "eip191",
  "did": "ens:miner.alice.eth",
  "payload_hash": "keccak256:abc123...",
  "signature": "eip191:0x..."
}
```

## 5. EIP-712 (Optional, Structured)

Used for:

- advanced tooling
- multi-sig controllers
- future DAO-less governance

### Domain

```json
{
  "name": "SwarmHive",
  "version": "bee-23@1.0",
  "chainId": <current>,
  "verifyingContract": "0x0000000000000000000000000000000000000000"
}
```

### Typed Message

```json
{
  "Snapshot": [
    { "name": "type", "type": "string" },
    { "name": "id", "type": "string" },
    { "name": "payload_hash", "type": "bytes32" }
  ]
}
```

## 6. Verification Rules (Hard Invariants)

A snapshot is **INVALID** if:

- signature does not recover to ENS owner
- payload hash mismatch
- timestamp is in the future (>5 min drift)
- signature reused with different payload

Invalid snapshots are ignored by:

- miners
- Merlin
- SwarmHive indexers

## 7. Nonce & Replay Protection

Replay protection is achieved by:

- unique snapshot `id`
- monotonic timestamps
- epoch scoping

No global nonce registry is required.

## 8. Canon Rule

> If a snapshot cannot be independently verified from ENS → hash → signature, it does not exist.
