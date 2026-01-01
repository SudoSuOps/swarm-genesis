//! swarmhive watch - Observe the memepool

use crate::cli::WatchCmd;
use anyhow::Result;
use std::time::Duration;

pub async fn run(cmd: WatchCmd) -> Result<()> {
    println!("Watching pool: {}", cmd.pool);
    println!("Interval: {}s", cmd.interval);
    println!();
    println!("Press Ctrl+C to exit.");
    println!();

    loop {
        // TODO:
        // 1. Resolve pool ENS to CID
        // 2. Fetch /index/latest.json
        // 3. Fetch available jobs
        // 4. Display job feed

        println!("[{}] Syncing... (stub)", chrono::Utc::now().format("%H:%M:%S"));

        tokio::time::sleep(Duration::from_secs(cmd.interval)).await;
    }
}
