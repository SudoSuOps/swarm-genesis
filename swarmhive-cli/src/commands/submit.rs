//! swarmhive submit - Submit a job snapshot

use crate::cli::SubmitCmd;
use anyhow::Result;

pub async fn run(cmd: SubmitCmd) -> Result<()> {
    println!("Submitting job: {}", cmd.file);

    // TODO:
    // 1. Read JSON file
    // 2. Validate against job.schema.json
    // 3. Verify signature
    // 4. Check epoch is OPEN
    // 5. Publish to IPFS under /jobs/epoch-{N}/

    println!("Validation... (stub)");
    println!("Publishing... (stub)");

    Ok(())
}
