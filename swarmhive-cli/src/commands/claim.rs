//! swarmhive claim - Claim a SOLO job

use crate::cli::ClaimCmd;
use crate::config;
use anyhow::Result;
use chrono::Utc;
use serde_json::json;

pub async fn run(cmd: ClaimCmd) -> Result<()> {
    let config = config::load()?;

    println!("Claiming job: {}", cmd.job_id);
    println!("Miner: {}", config.identity.ens);
    println!("Lease: {}s", cmd.lease);

    // Build CLAIM snapshot
    let ts = Utc::now().timestamp();
    let claim = json!({
        "type": "CLAIM",
        "version": "bee-23@1.0",
        "id": format!("claim-{}-{}", cmd.job_id, ts),
        "ts": ts,
        "issuer": config.identity.ens,
        "pool": config.pool.name,
        "body": {
            "job_id": cmd.job_id,
            "miner": config.identity.ens,
            "claim_ts": ts,
            "lease_seconds": cmd.lease
        },
        "signing": {
            "scheme": "eip191",
            "did": format!("ens:{}", config.identity.ens),
            "payload_hash": "",
            "signature": ""
        }
    });

    // TODO:
    // 1. Compute payload hash
    // 2. Sign with miner key
    // 3. Publish to IPFS under /claims/{job_id}/

    println!();
    println!("Claim snapshot: (stub)");
    println!("{}", serde_json::to_string_pretty(&claim)?);

    Ok(())
}
