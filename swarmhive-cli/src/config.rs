//! Configuration management for SwarmHive CLI
//!
//! Config file: ~/.swarmhive/config.toml

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// SwarmHive configuration
#[derive(Debug, Serialize, Deserialize)]
pub struct Config {
    pub identity: IdentityConfig,
    pub pool: PoolConfig,
    pub ipfs: IpfsConfig,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct IdentityConfig {
    pub ens: String,
    pub key_path: PathBuf,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PoolConfig {
    pub name: String,
    pub gateway: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct IpfsConfig {
    pub api: String,
    pub gateway: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            identity: IdentityConfig {
                ens: String::new(),
                key_path: config_dir().join("keys/node.json"),
            },
            pool: PoolConfig {
                name: "swarmpool.eth".to_string(),
                gateway: "https://w3s.link/ipfs".to_string(),
            },
            ipfs: IpfsConfig {
                api: "/ip4/127.0.0.1/tcp/5001".to_string(),
                gateway: "https://ipfs.io/ipfs".to_string(),
            },
        }
    }
}

/// Get the SwarmHive config directory (~/.swarmhive)
pub fn config_dir() -> PathBuf {
    dirs::home_dir()
        .expect("Could not find home directory")
        .join(".swarmhive")
}

/// Get the config file path (~/.swarmhive/config.toml)
pub fn config_path() -> PathBuf {
    config_dir().join("config.toml")
}

/// Load configuration from file
pub fn load() -> Result<Config> {
    let path = config_path();
    if !path.exists() {
        return Ok(Config::default());
    }
    let content = std::fs::read_to_string(&path)?;
    let config: Config = toml::from_str(&content)?;
    Ok(config)
}

/// Save configuration to file
pub fn save(config: &Config) -> Result<()> {
    let path = config_path();
    std::fs::create_dir_all(path.parent().unwrap())?;
    let content = toml::to_string_pretty(config)?;
    std::fs::write(&path, content)?;
    Ok(())
}
