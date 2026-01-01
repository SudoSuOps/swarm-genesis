use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "swarmhive")]
#[command(about = "SwarmHive sovereign compute CLI", long_about = None)]
#[command(version)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize a new miner identity
    Init(InitCmd),
    /// Watch the pool for available jobs
    Watch(WatchCmd),
    /// Submit a job snapshot
    Submit(SubmitCmd),
    /// Claim a SOLO job
    Claim(ClaimCmd),
    /// Submit proof of compute
    Prove(ProveCmd),
    /// Seal an epoch (controller only)
    Seal(SealCmd),
}

#[derive(Parser)]
pub struct InitCmd {
    /// ENS identity (e.g., miner.alice.eth)
    #[arg(long)]
    pub ens: String,

    /// Pool to join
    #[arg(long, default_value = "swarmpool.eth")]
    pub pool: String,
}

#[derive(Parser)]
pub struct WatchCmd {
    /// Pool to watch
    #[arg(long, default_value = "swarmpool.eth")]
    pub pool: String,

    /// Sync interval in seconds
    #[arg(long, default_value_t = 10)]
    pub interval: u64,
}

#[derive(Parser)]
pub struct SubmitCmd {
    /// Path to job snapshot JSON
    pub file: String,
}

#[derive(Parser)]
pub struct ClaimCmd {
    /// Job ID to claim
    pub job_id: String,

    /// Lease duration in seconds
    #[arg(long, default_value_t = 900)]
    pub lease: u64,
}

#[derive(Parser)]
pub struct ProveCmd {
    /// Job ID
    pub job_id: String,

    /// Result CID (ipfs://...)
    #[arg(long)]
    pub result: String,

    /// Compute time in seconds
    #[arg(long)]
    pub compute_seconds: u64,
}

#[derive(Parser)]
pub struct SealCmd {
    /// Epoch number to seal
    #[arg(long)]
    pub epoch: u64,
}
