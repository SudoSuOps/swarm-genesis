# Signing Specification

Canonical hashing and signature rules for Bee-23 snapshots.

## Overview

All snapshots MUST be signed by the issuer. Signatures are verified against ENS-resolved addresses.

## Supported Schemes

| Scheme | Use Case | Spec |
|--------|----------|------|
| `eip191` | Personal signatures | [EIP-191](https://eips.ethereum.org/EIPS/eip-191) |
| `eip712` | Typed data (future) | [EIP-712](https://eips.ethereum.org/EIPS/eip-712) |

## Payload Hashing

### Step 1: Canonical JSON

Before hashing, the payload MUST be serialized to canonical JSON:

1. Remove `signing` block from payload
2. Sort all object keys alphabetically (recursive)
3. No whitespace (compact)
4. UTF-8 encoding

```python
import json

def canonical_json(obj):
    """Serialize to canonical JSON (sorted keys, compact)."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))
```

### Step 2: Hash

Compute SHA-256 or Keccak-256 of the canonical JSON bytes:

```python
import hashlib

def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def payload_hash(snapshot: dict) -> str:
    # Remove signing block
    payload = {k: v for k, v in snapshot.items() if k != 'signing'}
    canonical = canonical_json(payload).encode('utf-8')
    return f"sha256:{sha256_hash(canonical)}"
```

### Hash Format

```
sha256:a1b2c3d4e5f6...  (64 hex chars)
keccak256:a1b2c3d4...   (64 hex chars)
```

## EIP-191 Signing

### Message Format

The signed message is the payload hash prefixed with context:

```
swarmpool.eth snapshot v1
{payload_hash}
```

Example:
```
swarmpool.eth snapshot v1
sha256:7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b
```

### Signing

```python
from eth_account import Account
from eth_account.messages import encode_defunct

def sign_snapshot(snapshot: dict, private_key: str) -> str:
    """Sign snapshot with EIP-191."""
    hash_value = payload_hash(snapshot)
    message = f"swarmpool.eth snapshot v1\n{hash_value}"
    signable = encode_defunct(text=message)
    signed = Account.sign_message(signable, private_key)
    return f"eip191:{signed.signature.hex()}"
```

### Signature Format

```
eip191:0x{r}{s}{v}  (65 bytes = 130 hex chars)
```

## Verification

### Step 1: Resolve ENS

```python
from web3 import Web3

def resolve_ens(ens_name: str, provider: str) -> str:
    """Resolve ENS name to address."""
    w3 = Web3(Web3.HTTPProvider(provider))
    return w3.ens.address(ens_name)
```

### Step 2: Recover Signer

```python
from eth_account.messages import encode_defunct
from eth_account import Account

def verify_signature(snapshot: dict) -> bool:
    """Verify snapshot signature."""
    signing = snapshot['signing']

    # Extract components
    did = signing['did']  # "ens:miner.alice.eth"
    ens_name = did.replace('ens:', '')
    payload_hash_value = signing['payload_hash']
    signature = signing['signature'].replace('eip191:', '')

    # Reconstruct message
    message = f"swarmpool.eth snapshot v1\n{payload_hash_value}"
    signable = encode_defunct(text=message)

    # Recover signer
    recovered = Account.recover_message(signable, signature=bytes.fromhex(signature[2:]))

    # Resolve ENS and compare
    expected = resolve_ens(ens_name, "https://eth.llamarpc.com")

    return recovered.lower() == expected.lower()
```

## Signing Block Schema

```json
{
  "signing": {
    "scheme": "eip191",
    "did": "ens:miner.alice.eth",
    "payload_hash": "sha256:7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b",
    "signature": "eip191:0x1234...abcd"
  }
}
```

## DID Format

All identities use ENS-based DIDs:

```
ens:{name}.eth
ens:{name}.swarmos.eth
ens:{name}.swarmhive.eth
```

Examples:
- `ens:merlin.swarmos.eth` (controller)
- `ens:miner.alice.eth` (miner)
- `ens:swarmpool.eth` (pool)

## Security Rules

1. **Hash before sign**: Never sign raw JSON
2. **Canonical form**: Always sort keys, no whitespace
3. **Prefix context**: Include `swarmpool.eth snapshot v1` to prevent cross-protocol replay
4. **ENS verification**: Always resolve ENS on-chain, never trust cached addresses
5. **Timestamp checks**: Reject snapshots with `ts` too far in future (>60s) or past (>24h for claims)

## CLI Examples

```bash
# Sign a snapshot
swarmhive sign snapshot.json --key ~/.swarmhive/keys/node.json

# Verify a snapshot
swarmhive verify snapshot.json

# Extract payload hash
swarmhive hash snapshot.json
```

## Reference Implementation

See: `swarmhive-cli/src/signing.py`
