//! swarmhive prove - Submit proof of compute

use crate::cli::ProveCmd;
use crate::config;
use anyhow::Result;
use chrono::Utc;
use serde_json::json;

pub async fn run(cmd: ProveCmd) -> Result<()> {
    let config = config::load()?;

    println!("Proving job: {}", cmd.job_id);
    println!("Miner: {}", config.identity.ens);
    println!("Result: {}", cmd.result);
    println!("Compute: {}s", cmd.compute_seconds);

    // Build PROOF snapshot
    let ts = Utc::now().timestamp();
    let proof = json!({
        "type": "PROOF",
        "version": "bee-23@1.0",
        "id": format!("proof-{}-{}", cmd.job_id, ts),
        "ts": ts,
        "issuer": config.identity.ens,
        "pool": config.pool.name,
        "body": {
            "job_id": cmd.job_id,
            "miner": config.identity.ens,
            "compute_seconds": cmd.compute_seconds,
            "outputs": {
                "result_cid": cmd.result
            }
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
    // 3. Publish to IPFS under /proofs/epoch-{N}/{job_id}/

    println!();
    println!("Proof snapshot: (stub)");
    println!("{}", serde_json::to_string_pretty(&proof)?);

    Ok(())
}
