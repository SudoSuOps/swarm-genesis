"""
SwarmOrb Indexer - Core Logic

Scans audit/epoch-* directories, extracts summaries, and builds index.json
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EpochRef(BaseModel):
    """Reference to a finalized epoch in the index"""
    epoch_id: str
    start_time: str
    end_time: str
    status: str = "finalized"
    bundle_ref: str
    summary_hash: str
    jobs_completed: int = 0
    total_distributed: str = "0.00"
    agents_active: int = 0


class AgentSummary(BaseModel):
    """Aggregate stats for a top agent"""
    ens: str
    jobs_completed: int = 0
    total_earned: str = "0.00"
    uptime_hours: float = 0.0


class AggregateStats(BaseModel):
    """Aggregate stats across all epochs"""
    total_epochs: int = 0
    total_jobs: int = 0
    total_distributed: str = "0.00"
    unique_agents: int = 0
    unique_clients: int = 0
    top_agents: list[AgentSummary] = Field(default_factory=list)


class OrbIndex(BaseModel):
    """The main index.json structure"""
    version: str = "1.0.0"
    generated_at: str
    coordinator: str = "swarmos.eth"
    epochs: list[EpochRef] = Field(default_factory=list)
    stats: AggregateStats = Field(default_factory=AggregateStats)


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def parse_epoch_id(dir_name: str) -> str | None:
    """Extract epoch ID from directory name (e.g., epoch-001)"""
    match = re.match(r"^(epoch-\d{3,})$", dir_name)
    return match.group(1) if match else None


def load_json(file_path: Path) -> dict[str, Any] | None:
    """Load JSON file, return None if not found or invalid"""
    try:
        with open(file_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def scan_epoch_directory(epoch_dir: Path) -> EpochRef | None:
    """
    Scan a single epoch directory and extract summary info.
    Returns None if the epoch is invalid or incomplete.
    """
    epoch_id = parse_epoch_id(epoch_dir.name)
    if not epoch_id:
        return None
    
    summary_path = epoch_dir / "SUMMARY.json"
    signature_path = epoch_dir / "SIGNATURE.txt"
    
    # Must have SUMMARY.json
    summary = load_json(summary_path)
    if not summary:
        print(f"  [SKIP] {epoch_id}: Missing or invalid SUMMARY.json")
        return None
    
    # Compute summary hash
    summary_hash = compute_sha256(summary_path) if summary_path.exists() else ""
    
    # Check for signature file (optional but noted)
    has_signature = signature_path.exists()
    if not has_signature:
        print(f"  [WARN] {epoch_id}: Missing SIGNATURE.txt")
    
    # Extract key fields
    jobs = summary.get("jobs", {})
    treasury = summary.get("treasury", {})
    agents = summary.get("agents", {})
    
    return EpochRef(
        epoch_id=epoch_id,
        start_time=summary.get("start_time", ""),
        end_time=summary.get("end_time", ""),
        status="finalized",
        bundle_ref=f"./audit/{epoch_id}",
        summary_hash=summary_hash,
        jobs_completed=jobs.get("total_completed", 0),
        total_distributed=treasury.get("distributed", "0.00"),
        agents_active=agents.get("total_active", 0),
    )


def aggregate_stats(epochs: list[EpochRef], audit_dir: Path) -> AggregateStats:
    """
    Compute aggregate statistics across all epochs.
    Requires re-reading some epoch data for agent/client aggregation.
    """
    total_jobs = 0
    total_distributed = 0.0
    all_agents: dict[str, AgentSummary] = {}
    all_clients: set[str] = set()
    
    for epoch_ref in epochs:
        total_jobs += epoch_ref.jobs_completed
        try:
            total_distributed += float(epoch_ref.total_distributed)
        except ValueError:
            pass
        
        # Load full summary for agent/client details
        epoch_dir = audit_dir / epoch_ref.epoch_id
        summary = load_json(epoch_dir / "SUMMARY.json")
        if not summary:
            continue
        
        # Aggregate agent earnings
        agents_data = summary.get("agents", {})
        for payout in agents_data.get("payouts", []):
            ens = payout.get("ens", "")
            if not ens:
                continue
            
            if ens not in all_agents:
                all_agents[ens] = AgentSummary(ens=ens)
            
            agent = all_agents[ens]
            agent.jobs_completed += payout.get("jobs_completed", 0)
            try:
                current = float(agent.total_earned)
                additional = float(payout.get("total_payout", "0"))
                agent.total_earned = f"{current + additional:.2f}"
            except ValueError:
                pass
            
            uptime_secs = payout.get("uptime_seconds", 0)
            agent.uptime_hours += uptime_secs / 3600
        
        # Aggregate clients
        clients_data = summary.get("clients", {})
        for client in clients_data.get("top_clients", []):
            ens = client.get("ens", "")
            if ens:
                all_clients.add(ens)
    
    # Sort agents by earnings (desc) and take top 10
    sorted_agents = sorted(
        all_agents.values(),
        key=lambda a: float(a.total_earned),
        reverse=True
    )[:10]
    
    return AggregateStats(
        total_epochs=len(epochs),
        total_jobs=total_jobs,
        total_distributed=f"{total_distributed:.2f}",
        unique_agents=len(all_agents),
        unique_clients=len(all_clients),
        top_agents=sorted_agents,
    )


def build_index(audit_dir: Path, coordinator: str = "swarmos.eth") -> OrbIndex:
    """
    Scan audit directory and build the complete index.
    
    Args:
        audit_dir: Path to audit directory containing epoch-* folders
        coordinator: ENS name of the coordinator
    
    Returns:
        OrbIndex object ready to serialize
    """
    print(f"Scanning: {audit_dir}")
    
    if not audit_dir.exists():
        raise FileNotFoundError(f"Audit directory not found: {audit_dir}")
    
    # Find all epoch directories
    epoch_dirs = sorted(
        [d for d in audit_dir.iterdir() if d.is_dir() and parse_epoch_id(d.name)],
        key=lambda d: d.name,
        reverse=True  # Newest first
    )
    
    print(f"Found {len(epoch_dirs)} epoch directories")
    
    # Process each epoch
    epochs: list[EpochRef] = []
    for epoch_dir in epoch_dirs:
        print(f"  Processing: {epoch_dir.name}")
        epoch_ref = scan_epoch_directory(epoch_dir)
        if epoch_ref:
            epochs.append(epoch_ref)
            print(f"    ✓ {epoch_ref.jobs_completed} jobs, ${epoch_ref.total_distributed} distributed")
    
    # Compute aggregates
    stats = aggregate_stats(epochs, audit_dir)
    
    # Build final index
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return OrbIndex(
        version="1.0.0",
        generated_at=now,
        coordinator=coordinator,
        epochs=epochs,
        stats=stats,
    )


def write_index(index: OrbIndex, output_path: Path) -> None:
    """Write index to JSON file"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(index.model_dump(), f, indent=2)
    
    print(f"\nWrote: {output_path}")
    print(f"  Epochs: {len(index.epochs)}")
    print(f"  Total jobs: {index.stats.total_jobs}")
    print(f"  Total distributed: ${index.stats.total_distributed}")
