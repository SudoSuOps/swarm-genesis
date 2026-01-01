//! IPFS add / cat helpers
//!
//! Uses local IPFS daemon via CLI or HTTP API.

use anyhow::{Context, Result};
use std::process::Command;

/// Add content to IPFS and return the CID
pub fn add(content: &str) -> Result<String> {
    let output = Command::new("ipfs")
        .args(["add", "-Q", "--cid-version=1", "-"])
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .spawn()
        .context("Failed to spawn ipfs command")?
        .wait_with_output()?;

    if !output.status.success() {
        anyhow::bail!("ipfs add failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    let cid = String::from_utf8(output.stdout)?
        .trim()
        .to_string();

    Ok(format!("ipfs://{}", cid))
}

/// Add a file to IPFS
pub fn add_file(path: &str) -> Result<String> {
    let output = Command::new("ipfs")
        .args(["add", "-Q", "--cid-version=1", path])
        .output()
        .context("Failed to run ipfs add")?;

    if !output.status.success() {
        anyhow::bail!("ipfs add failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    let cid = String::from_utf8(output.stdout)?
        .trim()
        .to_string();

    Ok(format!("ipfs://{}", cid))
}

/// Fetch content from IPFS by CID
pub fn cat(cid: &str) -> Result<String> {
    let cid = cid.strip_prefix("ipfs://").unwrap_or(cid);

    let output = Command::new("ipfs")
        .args(["cat", cid])
        .output()
        .context("Failed to run ipfs cat")?;

    if !output.status.success() {
        anyhow::bail!("ipfs cat failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    Ok(String::from_utf8(output.stdout)?)
}

/// Check if IPFS daemon is running
pub fn is_daemon_running() -> bool {
    Command::new("ipfs")
        .args(["id"])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

/// Resolve an IPNS or DNSLink name to a CID
pub fn resolve(name: &str) -> Result<String> {
    let output = Command::new("ipfs")
        .args(["resolve", "-r", name])
        .output()
        .context("Failed to run ipfs resolve")?;

    if !output.status.success() {
        anyhow::bail!("ipfs resolve failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    Ok(String::from_utf8(output.stdout)?.trim().to_string())
}

/// List directory contents at CID
pub fn ls(cid: &str) -> Result<Vec<String>> {
    let cid = cid.strip_prefix("ipfs://").unwrap_or(cid);

    let output = Command::new("ipfs")
        .args(["ls", cid])
        .output()
        .context("Failed to run ipfs ls")?;

    if !output.status.success() {
        anyhow::bail!("ipfs ls failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    let files: Vec<String> = String::from_utf8(output.stdout)?
        .lines()
        .filter_map(|line| line.split_whitespace().nth(2).map(String::from))
        .collect();

    Ok(files)
}
