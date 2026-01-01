//! swarmhive init - Register as a compute provider

use crate::cli::InitCmd;
use crate::config::{self, Config, IdentityConfig, IpfsConfig, PoolConfig};
use crate::signing;
use anyhow::Result;
use chrono::Utc;
use serde_json::json;

pub async fn run(cmd: InitCmd) -> Result<()> {
    println!("Initializing SwarmHive miner...");
    println!("ENS: {}", cmd.ens);
    println!("Pool: {}", cmd.pool);
    println!();

    // 1. Check IPFS daemon
    if !crate::ipfs::is_daemon_running() {
        println!("Warning: IPFS daemon not running. Publishing will fail.");
    }

    // 2. Generate keypair
    println!("Generating keypair...");
    let wallet = signing::generate_keypair();
    let address = format!("{:?}", wallet.address());
    println!("Address: {}", address);

    // 3. Build GENESIS_MINER snapshot
    let ts = Utc::now().timestamp();
    let snapshot_id = format!("genesis-{}-{}", cmd.ens.replace('.', "-"), ts);

    let snapshot = json!({
        "type": "GENESIS_MINER",
        "version": "bee-23@1.0",
        "id": snapshot_id,
        "ts": ts,
        "issuer": cmd.ens,
        "pool": cmd.pool,
        "body": {
            "miner": cmd.ens,
            "capabilities": {
                "gpu_model": "unknown",
                "gpu_count": 1,
                "gpu_vram_gb": 8,
                "cpu_model": "unknown",
                "cpu_cores": 4,
                "ram_gb": 16,
                "storage_gb": 100,
                "frameworks": ["pytorch", "onnx"]
            },
            "availability": {
                "uptime_class": "best_effort",
                "power_profile": "balanced"
            }
        },
        "signing": {
            "scheme": "eip191",
            "did": format!("ens:{}", cmd.ens),
            "payload_hash": "",
            "signature": ""
        }
    });

    // 4. Compute payload hash
    let hash = signing::payload_hash(&snapshot)?;
    println!("Payload hash: {}", hash);

    // 5. Sign (stub - would need wallet signature)
    println!("Signing... (stub - manual signature required)");
    // let signature = signing::sign_eip191(&hash, &wallet).await?;

    // 6. Publish to IPFS (stub)
    println!("Publishing to IPFS... (stub)");
    // let cid = crate::ipfs::add(&serde_json::to_string_pretty(&snapshot)?)?;
    // println!("Genesis CID: {}", cid);

    // 7. Write config
    let config = Config {
        identity: IdentityConfig {
            ens: cmd.ens.clone(),
            key_path: config::config_dir().join("keys/node.json"),
        },
        pool: PoolConfig {
            name: cmd.pool.clone(),
            gateway: "https://w3s.link/ipfs".to_string(),
        },
        ipfs: IpfsConfig {
            api: "/ip4/127.0.0.1/tcp/5001".to_string(),
            gateway: "https://ipfs.io/ipfs".to_string(),
        },
    };
    config::save(&config)?;

    println!();
    println!("=== Genesis Summary ===");
    println!("Miner: {}", cmd.ens);
    println!("Pool: {}", cmd.pool);
    println!("Config: {:?}", config::config_path());
    println!();
    println!("Next: swarmhive watch --pool {}", cmd.pool);

    Ok(())
}
