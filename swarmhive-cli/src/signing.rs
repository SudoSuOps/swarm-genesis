//! EIP-191 / EIP-712 signing helpers
//!
//! All snapshots are signed using keccak256 payload hash.

use anyhow::Result;
use ethers::core::k256::ecdsa::SigningKey;
use ethers::signers::{LocalWallet, Signer};
use ethers::utils::keccak256;
use serde_json::Value;

/// Compute the canonical JSON representation of a snapshot payload
///
/// Rules:
/// - UTF-8 encoding
/// - Sorted object keys (lexicographic)
/// - No whitespace outside string values
/// - Remove `signing.signature` field
pub fn canonical_json(snapshot: &Value) -> Result<String> {
    let mut payload = snapshot.clone();

    // Remove signature from signing block if present
    if let Some(signing) = payload.get_mut("signing") {
        if let Some(obj) = signing.as_object_mut() {
            obj.remove("signature");
        }
    }

    // Serialize with sorted keys (serde_json does this by default with preserve_order feature off)
    let canonical = serde_json::to_string(&payload)?;
    Ok(canonical)
}

/// Compute keccak256 hash of canonical payload
pub fn payload_hash(snapshot: &Value) -> Result<String> {
    let canonical = canonical_json(snapshot)?;
    let hash = keccak256(canonical.as_bytes());
    Ok(format!("keccak256:{}", hex::encode(hash)))
}

/// Sign a payload hash using EIP-191
///
/// Message format:
/// "\x19Ethereum Signed Message:\n" + len(payload_hash) + payload_hash
pub async fn sign_eip191(payload_hash: &str, wallet: &LocalWallet) -> Result<String> {
    let signature = wallet.sign_message(payload_hash).await?;
    Ok(format!("eip191:0x{}", hex::encode(signature.to_vec())))
}

/// Verify an EIP-191 signature
pub fn verify_eip191(payload_hash: &str, signature: &str, expected_address: &str) -> Result<bool> {
    let sig_hex = signature.strip_prefix("eip191:0x").unwrap_or(signature);
    let sig_bytes = hex::decode(sig_hex)?;

    let signature = ethers::core::types::Signature::try_from(sig_bytes.as_slice())?;
    let recovered = signature.recover(payload_hash)?;

    let expected = expected_address.parse::<ethers::types::Address>()?;
    Ok(recovered == expected)
}

/// Generate a new random keypair
pub fn generate_keypair() -> LocalWallet {
    LocalWallet::new(&mut rand::thread_rng())
}

/// Load a wallet from a private key hex string
pub fn load_wallet(private_key: &str) -> Result<LocalWallet> {
    let key = private_key.strip_prefix("0x").unwrap_or(private_key);
    let wallet: LocalWallet = key.parse()?;
    Ok(wallet)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_payload_hash() {
        let snapshot = json!({
            "type": "TEST",
            "id": "test-001",
            "ts": 1735689600
        });

        let hash = payload_hash(&snapshot).unwrap();
        assert!(hash.starts_with("keccak256:"));
        assert_eq!(hash.len(), 10 + 64); // "keccak256:" + 64 hex chars
    }

    #[test]
    fn test_canonical_removes_signature() {
        let snapshot = json!({
            "type": "TEST",
            "signing": {
                "scheme": "eip191",
                "did": "ens:test.eth",
                "payload_hash": "keccak256:abc",
                "signature": "eip191:0x123"
            }
        });

        let canonical = canonical_json(&snapshot).unwrap();
        assert!(!canonical.contains("\"signature\""));
        assert!(canonical.contains("\"scheme\""));
    }
}
