mod cli;
mod commands;
mod config;
mod ipfs;
mod signing;

use cli::Cli;
use clap::Parser;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        cli::Commands::Init(cmd) => commands::init::run(cmd).await,
        cli::Commands::Watch(cmd) => commands::watch::run(cmd).await,
        cli::Commands::Submit(cmd) => commands::submit::run(cmd).await,
        cli::Commands::Claim(cmd) => commands::claim::run(cmd).await,
        cli::Commands::Prove(cmd) => commands::prove::run(cmd).await,
        cli::Commands::Seal(cmd) => commands::seal::run(cmd).await,
    }
}
