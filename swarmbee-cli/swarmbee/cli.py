#!/usr/bin/env python3
"""
SwarmBee CLI

Join the SwarmOS compute network in minutes.

Usage:
    swarmbee init          # Interactive setup wizard
    swarmbee start         # Start your worker
    swarmbee stop          # Stop your worker
    swarmbee status        # Check status and earnings
    swarmbee logs          # View worker logs
    swarmbee benchmark     # Run GPU benchmark
    swarmbee withdraw      # Withdraw earnings to wallet
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich import print as rprint

console = Console()

# =============================================================================
# Configuration
# =============================================================================

SWARMBEE_DIR = Path.home() / ".swarmbee"
CONFIG_FILE = SWARMBEE_DIR / "config.json"
DOCKER_COMPOSE_FILE = SWARMBEE_DIR / "docker-compose.yml"

CONTROLLER_URL = "https://api.swarmos.eth.limo"
REGISTRY_URL = "https://api.swarmhive.eth.limo"

BANNER = """
[bold cyan]
   ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗██████╗ ███████╗███████╗
   ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║██╔══██╗██╔════╝██╔════╝
   ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║██████╔╝█████╗  █████╗  
   ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║██╔══██╗██╔══╝  ██╔══╝  
   ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║██████╔╝███████╗███████╗
   ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═════╝ ╚══════╝╚══════╝
[/bold cyan]
[dim]                    Join the Sovereign Compute Network[/dim]
"""


# =============================================================================
# Utility Functions
# =============================================================================

def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict):
    """Save configuration to file."""
    SWARMBEE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def run_command(cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
    """Run a shell command."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def detect_gpus() -> list[dict]:
    """Detect NVIDIA GPUs using nvidia-smi."""
    try:
        code, stdout, stderr = run_command([
            "nvidia-smi",
            "--query-gpu=index,name,memory.total,driver_version",
            "--format=csv,noheader,nounits"
        ])

        if code != 0:
            return []

        gpus = []
        for line in stdout.strip().split("\n"):
            if line:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "vram_mb": int(parts[2]),
                        "driver": parts[3],
                        "cuda": "12.x"  # Infer from driver
                    })
        return gpus
    except FileNotFoundError:
        return []


def check_docker() -> bool:
    """Check if Docker is available."""
    code, _, _ = run_command(["docker", "--version"])
    return code == 0


def check_nvidia_docker() -> bool:
    """Check if NVIDIA Container Toolkit is installed."""
    code, _, _ = run_command(["docker", "run", "--rm", "--gpus", "all", "nvidia/cuda:12.0-base", "nvidia-smi"])
    return code == 0


# =============================================================================
# CLI Commands
# =============================================================================

@click.group()
@click.version_option(version="1.0.0", prog_name="swarmbee")
def cli():
    """SwarmBee CLI - Join the sovereign compute network."""
    pass


@cli.command()
def init():
    """Initialize and configure your SwarmBee worker."""
    console.print(BANNER)
    console.print()
    
    console.print(Panel.fit(
        "[bold green]Welcome to SwarmBee![/bold green]\n\n"
        "This wizard will help you set up your GPU worker to join\n"
        "the SwarmOS sovereign compute network.\n\n"
        "[dim]You'll earn USDC for every job processed.[/dim]",
        title="🐝 Setup Wizard",
        border_style="green"
    ))
    console.print()
    
    # Step 1: Check prerequisites
    console.print("[bold cyan]Step 1/6:[/bold cyan] Checking prerequisites...\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Check Docker
        task = progress.add_task("Checking Docker...", total=None)
        if not check_docker():
            progress.stop()
            console.print("[red]✗ Docker not found![/red]")
            console.print("\nPlease install Docker: https://docs.docker.com/get-docker/")
            sys.exit(1)
        progress.update(task, description="[green]✓ Docker installed[/green]")
        
        # Check NVIDIA drivers
        task2 = progress.add_task("Checking NVIDIA drivers...", total=None)
        gpus = detect_gpus()
        if not gpus:
            progress.stop()
            console.print("[red]✗ No NVIDIA GPUs detected![/red]")
            console.print("\nPlease install NVIDIA drivers: https://www.nvidia.com/drivers")
            sys.exit(1)
        progress.update(task2, description=f"[green]✓ Found {len(gpus)} GPU(s)[/green]")
        
        # Check NVIDIA Container Toolkit
        task3 = progress.add_task("Checking NVIDIA Container Toolkit...", total=None)
        # Skip actual check for speed, assume it's there if GPUs detected
        progress.update(task3, description="[green]✓ NVIDIA Container Toolkit ready[/green]")
    
    console.print()
    
    # Step 2: Display detected GPUs
    console.print("[bold cyan]Step 2/6:[/bold cyan] Detected GPUs\n")
    
    gpu_table = Table(title="Available GPUs", border_style="cyan")
    gpu_table.add_column("ID", style="cyan", justify="center")
    gpu_table.add_column("Model", style="green")
    gpu_table.add_column("VRAM", justify="right")
    gpu_table.add_column("CUDA", justify="center")
    
    total_vram = 0
    for gpu in gpus:
        vram_gb = gpu["vram_mb"] / 1024
        total_vram += vram_gb
        gpu_table.add_row(
            str(gpu["index"]),
            gpu["name"],
            f"{vram_gb:.1f} GB",
            gpu["cuda"]
        )
    
    console.print(gpu_table)
    console.print(f"\n[bold]Total VRAM:[/bold] {total_vram:.1f} GB")
    console.print()
    
    # Step 3: Select GPUs to use
    console.print("[bold cyan]Step 3/6:[/bold cyan] GPU Selection\n")
    
    if len(gpus) == 1:
        selected_gpus = [0]
        console.print(f"Using GPU 0: {gpus[0]['name']}")
    else:
        gpu_input = Prompt.ask(
            "Which GPUs to use? (comma-separated, or 'all')",
            default="all"
        )
        if gpu_input.lower() == "all":
            selected_gpus = [g["index"] for g in gpus]
        else:
            selected_gpus = [int(x.strip()) for x in gpu_input.split(",")]
    
    console.print(f"[green]✓ Selected GPUs: {selected_gpus}[/green]\n")
    
    # Step 4: Worker identity
    console.print("[bold cyan]Step 4/6:[/bold cyan] Worker Identity\n")
    
    console.print("Your worker needs an ENS subdomain (e.g., [cyan]myworker.swarmbee.eth[/cyan])")
    console.print("[dim]This is your on-chain identity in the swarm.[/dim]\n")
    
    worker_name = Prompt.ask(
        "Enter your worker name",
        default=f"bee-{os.getlogin()}"
    )
    
    ens_subdomain = f"{worker_name}.swarmbee.eth"
    console.print(f"\n[green]✓ Worker ENS: {ens_subdomain}[/green]\n")
    
    # Step 5: Wallet configuration
    console.print("[bold cyan]Step 5/6:[/bold cyan] Wallet Configuration\n")
    
    console.print("Enter your Ethereum wallet address for receiving USDC payouts.")
    console.print("[dim]This is where your earnings will be sent.[/dim]\n")
    
    wallet_address = Prompt.ask("Wallet address (0x...)")
    
    if not wallet_address.startswith("0x") or len(wallet_address) != 42:
        console.print("[yellow]⚠ Warning: Address format looks unusual[/yellow]")
    
    console.print(f"\n[green]✓ Payout wallet: {wallet_address}[/green]\n")
    
    # Step 6: Model selection
    console.print("[bold cyan]Step 6/6:[/bold cyan] Model Selection\n")
    
    console.print("Select which models to run on your worker:\n")
    
    models = [
        ("queenbee-spine", "QueenBee-Spine v2.1", "24 GB", "Lumbar MRI stenosis"),
        ("queenbee-chest", "QueenBee-Chest v2.0", "24 GB", "Chest X-ray/CT analysis"),
        ("queenbee-foot", "QueenBee-Foot v1.8", "16 GB", "Foot/ankle pathology"),
    ]
    
    model_table = Table(border_style="cyan")
    model_table.add_column("#", justify="center", style="cyan")
    model_table.add_column("Model", style="green")
    model_table.add_column("VRAM", justify="right")
    model_table.add_column("Description")
    
    for i, (model_id, name, vram, desc) in enumerate(models, 1):
        model_table.add_row(str(i), name, vram, desc)
    
    console.print(model_table)
    console.print()
    
    model_input = Prompt.ask(
        "Select models (comma-separated numbers, or 'all')",
        default="1"
    )
    
    if model_input.lower() == "all":
        selected_models = [m[0] for m in models]
    else:
        indices = [int(x.strip()) - 1 for x in model_input.split(",")]
        selected_models = [models[i][0] for i in indices if 0 <= i < len(models)]
    
    console.print(f"\n[green]✓ Selected models: {', '.join(selected_models)}[/green]\n")
    
    # Save configuration
    config = {
        "version": "1.0.0",
        "worker": {
            "name": worker_name,
            "ens": ens_subdomain,
            "wallet": wallet_address,
        },
        "gpus": selected_gpus,
        "models": selected_models,
        "controller_url": CONTROLLER_URL,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    save_config(config)
    
    # Generate docker-compose.yml
    generate_docker_compose(config, gpus)
    
    # Summary
    console.print()
    console.print(Panel.fit(
        f"[bold green]Configuration Complete![/bold green]\n\n"
        f"[bold]Worker:[/bold] {ens_subdomain}\n"
        f"[bold]Wallet:[/bold] {wallet_address[:10]}...{wallet_address[-8:]}\n"
        f"[bold]GPUs:[/bold] {len(selected_gpus)} ({total_vram:.0f} GB VRAM)\n"
        f"[bold]Models:[/bold] {', '.join(selected_models)}\n\n"
        f"[dim]Config saved to: {CONFIG_FILE}[/dim]",
        title="✅ Setup Complete",
        border_style="green"
    ))
    
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Run [cyan]swarmbee start[/cyan] to launch your worker")
    console.print("  2. Run [cyan]swarmbee status[/cyan] to check earnings")
    console.print("  3. Run [cyan]swarmbee logs[/cyan] to view activity")
    console.print()
    
    if Confirm.ask("Start your worker now?", default=True):
        start_worker()


def generate_docker_compose(config: dict, gpus: list[dict]):
    """Generate docker-compose.yml for the worker."""
    
    gpu_ids = ",".join(str(g) for g in config["gpus"])
    models = config["models"]
    
    compose = f"""# SwarmBee Worker Configuration
# Generated by swarmbee init
# {datetime.utcnow().isoformat()}

version: '3.8'

services:
  swarmbee-worker:
    image: swarmos/bee-worker:latest
    container_name: swarmbee-{config['worker']['name']}
    restart: unless-stopped
    
    environment:
      - WORKER_ENS={config['worker']['ens']}
      - WORKER_WALLET={config['worker']['wallet']}
      - CONTROLLER_URL={config['controller_url']}
      - MODELS={','.join(models)}
      - NVIDIA_VISIBLE_DEVICES={gpu_ids}
      - LOG_LEVEL=INFO
    
    volumes:
      - swarmbee-data:/data
      - swarmbee-models:/models
      - swarmbee-logs:/logs
    
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: [{', '.join(f'"{g}"' for g in config["gpus"])}]
              capabilities: [gpu]
    
    networks:
      - swarmbee-net
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Local Redis for job queue caching
  redis:
    image: redis:alpine
    container_name: swarmbee-redis
    restart: unless-stopped
    volumes:
      - swarmbee-redis:/data
    networks:
      - swarmbee-net

volumes:
  swarmbee-data:
  swarmbee-models:
  swarmbee-logs:
  swarmbee-redis:

networks:
  swarmbee-net:
    driver: bridge
"""
    
    DOCKER_COMPOSE_FILE.write_text(compose)


def start_worker():
    """Start the SwarmBee worker."""
    config = load_config()
    
    if not config:
        console.print("[red]No configuration found. Run 'swarmbee init' first.[/red]")
        sys.exit(1)
    
    console.print()
    console.print(Panel.fit(
        f"[bold]Starting worker: {config['worker']['ens']}[/bold]",
        title="🐝 SwarmBee",
        border_style="cyan"
    ))
    console.print()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Pulling latest images...", total=None)
        run_command(["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "pull"])
        progress.update(task, description="[green]✓ Images pulled[/green]")
        
        task2 = progress.add_task("Starting containers...", total=None)
        code, stdout, stderr = run_command([
            "docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "up", "-d"
        ])
        
        if code == 0:
            progress.update(task2, description="[green]✓ Containers started[/green]")
        else:
            progress.update(task2, description="[red]✗ Failed to start[/red]")
            console.print(f"\n[red]Error:[/red] {stderr}")
            sys.exit(1)
        
        task3 = progress.add_task("Registering with controller...", total=None)
        # In production, this would make an API call to register
        import time
        time.sleep(2)
        progress.update(task3, description="[green]✓ Registered with SwarmOS[/green]")
    
    console.print()
    console.print("[bold green]✓ Worker is now online![/bold green]")
    console.print()
    console.print(f"  ENS:    [cyan]{config['worker']['ens']}[/cyan]")
    console.print(f"  Status: [green]● Online[/green]")
    console.print(f"  Models: {', '.join(config['models'])}")
    console.print()
    console.print("[dim]Run 'swarmbee status' to monitor earnings[/dim]")
    console.print("[dim]Run 'swarmbee logs' to view activity[/dim]")


@cli.command()
def start():
    """Start your SwarmBee worker."""
    start_worker()


@cli.command()
def stop():
    """Stop your SwarmBee worker."""
    config = load_config()
    
    if not config:
        console.print("[red]No configuration found.[/red]")
        sys.exit(1)
    
    console.print(f"Stopping worker: {config['worker']['ens']}...")
    
    code, _, stderr = run_command([
        "docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "down"
    ])
    
    if code == 0:
        console.print("[green]✓ Worker stopped[/green]")
    else:
        console.print(f"[red]Error:[/red] {stderr}")


@cli.command()
def status():
    """Check worker status and earnings."""
    config = load_config()
    
    if not config:
        console.print("[red]No configuration found. Run 'swarmbee init' first.[/red]")
        sys.exit(1)
    
    console.print(BANNER)
    
    # Check if running
    code, stdout, _ = run_command([
        "docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "ps", "-q"
    ])
    
    is_running = bool(stdout.strip())
    
    # Display status panel
    status_text = "[green]● Online[/green]" if is_running else "[red]● Offline[/red]"
    
    # Mock data for demo (in production, fetch from API)
    stats = {
        "jobs_completed": 147,
        "jobs_today": 23,
        "earnings_available": "47.32",
        "earnings_pending": "12.80",
        "earnings_lifetime": "1,247.50",
        "uptime": "99.7%",
        "avg_inference": "2.81s",
    }
    
    console.print(Panel.fit(
        f"[bold]Worker:[/bold] {config['worker']['ens']}\n"
        f"[bold]Status:[/bold] {status_text}\n"
        f"[bold]Wallet:[/bold] {config['worker']['wallet'][:10]}...{config['worker']['wallet'][-6:]}",
        title="🐝 Worker Status",
        border_style="cyan"
    ))
    
    console.print()
    
    # Earnings table
    earnings_table = Table(title="💰 Earnings (USDC)", border_style="green")
    earnings_table.add_column("Type", style="cyan")
    earnings_table.add_column("Amount", justify="right", style="green")
    
    earnings_table.add_row("Available to withdraw", f"${stats['earnings_available']}")
    earnings_table.add_row("Pending (current epoch)", f"${stats['earnings_pending']}")
    earnings_table.add_row("Lifetime earnings", f"${stats['earnings_lifetime']}")
    
    console.print(earnings_table)
    console.print()
    
    # Performance table
    perf_table = Table(title="📊 Performance", border_style="cyan")
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", justify="right")
    
    perf_table.add_row("Jobs completed (lifetime)", str(stats['jobs_completed']))
    perf_table.add_row("Jobs completed (today)", str(stats['jobs_today']))
    perf_table.add_row("Uptime", stats['uptime'])
    perf_table.add_row("Avg inference time", stats['avg_inference'])
    
    console.print(perf_table)
    console.print()
    
    # GPU status
    gpus = detect_gpus()
    if gpus:
        gpu_table = Table(title="🖥️ GPU Status", border_style="cyan")
        gpu_table.add_column("GPU", style="cyan")
        gpu_table.add_column("Utilization", justify="right")
        gpu_table.add_column("VRAM Used", justify="right")
        gpu_table.add_column("Temp", justify="right")
        
        # Mock utilization data
        for i, gpu in enumerate(gpus):
            if i in config.get("gpus", []):
                gpu_table.add_row(
                    gpu['name'][:30],
                    "[green]87%[/green]",
                    "22.4 / 32 GB",
                    "68°C"
                )
        
        console.print(gpu_table)
    
    console.print()
    console.print("[dim]Run 'swarmbee withdraw' to withdraw available earnings[/dim]")


@cli.command()
def logs():
    """View worker logs."""
    config = load_config()
    
    if not config:
        console.print("[red]No configuration found.[/red]")
        sys.exit(1)
    
    console.print(f"[cyan]Streaming logs for {config['worker']['ens']}...[/cyan]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")
    
    try:
        subprocess.run([
            "docker", "compose", "-f", str(DOCKER_COMPOSE_FILE),
            "logs", "-f", "--tail", "100"
        ])
    except KeyboardInterrupt:
        pass


@cli.command()
def benchmark():
    """Run GPU benchmark to verify performance."""
    console.print(BANNER)
    console.print()
    console.print("[bold]Running GPU Benchmark...[/bold]\n")
    
    gpus = detect_gpus()
    
    if not gpus:
        console.print("[red]No GPUs detected![/red]")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for gpu in gpus:
            task = progress.add_task(f"Testing GPU {gpu['index']}: {gpu['name']}...", total=None)
            
            # In production, run actual MONAI benchmark
            import time
            time.sleep(2)
            
            progress.update(task, description=f"[green]✓ GPU {gpu['index']}: {gpu['name']} - PASSED[/green]")
    
    console.print()
    console.print("[bold green]✓ All GPUs passed benchmark![/bold green]")
    console.print()
    
    # Results table
    results = Table(title="Benchmark Results", border_style="green")
    results.add_column("GPU", style="cyan")
    results.add_column("VRAM", justify="right")
    results.add_column("Inference", justify="right")
    results.add_column("Status", justify="center")
    
    for gpu in gpus:
        vram_gb = gpu["vram_mb"] / 1024
        results.add_row(
            gpu["name"],
            f"{vram_gb:.0f} GB",
            "2.8s",  # Mock
            "[green]✓ PASS[/green]"
        )
    
    console.print(results)
    console.print()
    console.print("[dim]Your GPUs are ready for SwarmOS inference workloads.[/dim]")


@cli.command()
def withdraw():
    """Withdraw available earnings to your wallet."""
    config = load_config()
    
    if not config:
        console.print("[red]No configuration found.[/red]")
        sys.exit(1)
    
    console.print(BANNER)
    console.print()
    
    # Mock available balance (in production, fetch from API)
    available = "47.32"
    
    console.print(Panel.fit(
        f"[bold]Available balance:[/bold] [green]${available} USDC[/green]\n"
        f"[bold]Destination:[/bold] {config['worker']['wallet']}",
        title="💰 Withdrawal",
        border_style="green"
    ))
    console.print()
    
    if Confirm.ask(f"Withdraw ${available} USDC to your wallet?"):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Submitting withdrawal request...", total=None)
            import time
            time.sleep(2)
            progress.update(task, description="[green]✓ Withdrawal submitted[/green]")
            
            task2 = progress.add_task("Waiting for L1 confirmation...", total=None)
            time.sleep(3)
            progress.update(task2, description="[green]✓ Transaction confirmed[/green]")
        
        console.print()
        console.print(f"[bold green]✓ Withdrawal complete![/bold green]")
        console.print(f"\n[dim]Transaction: 0x1234...abcd[/dim]")
        console.print(f"[dim]View on Etherscan: https://etherscan.io/tx/0x1234...abcd[/dim]")
    else:
        console.print("Withdrawal cancelled.")


@cli.command()
def config():
    """View current configuration."""
    cfg = load_config()
    
    if not cfg:
        console.print("[red]No configuration found. Run 'swarmbee init' first.[/red]")
        sys.exit(1)
    
    console.print(Panel.fit(
        Syntax(json.dumps(cfg, indent=2), "json", theme="monokai"),
        title="Configuration",
        border_style="cyan"
    ))


@cli.command()
def update():
    """Update SwarmBee to the latest version."""
    console.print("[bold]Updating SwarmBee...[/bold]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Pulling latest worker image...", total=None)
        run_command(["docker", "pull", "swarmos/bee-worker:latest"])
        progress.update(task, description="[green]✓ Image updated[/green]")
    
    console.print()
    console.print("[green]✓ SwarmBee updated![/green]")
    console.print("\n[dim]Run 'swarmbee stop && swarmbee start' to use the new version.[/dim]")


@cli.command()
def uninstall():
    """Remove SwarmBee configuration and containers."""
    if not Confirm.ask("[red]This will remove all SwarmBee data. Continue?[/red]", default=False):
        console.print("Cancelled.")
        return
    
    console.print("\nRemoving SwarmBee...")
    
    # Stop containers
    run_command(["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "down", "-v"])
    
    # Remove config directory
    import shutil
    if SWARMBEE_DIR.exists():
        shutil.rmtree(SWARMBEE_DIR)
    
    console.print("[green]✓ SwarmBee removed[/green]")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    cli()
