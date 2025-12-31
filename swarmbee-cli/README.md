# 🐝 SwarmBee CLI

**Join the SwarmOS sovereign compute network in minutes.**

```
   ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗██████╗ ███████╗███████╗
   ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║██╔══██╗██╔════╝██╔════╝
   ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║██████╔╝█████╗  █████╗  
   ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║██╔══██╗██╔══╝  ██╔══╝  
   ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║██████╔╝███████╗███████╗
   ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═════╝ ╚══════╝╚══════╝
```

SwarmBee CLI lets GPU operators join the SwarmOS decentralized compute network. Run medical AI inference on your hardware, earn USDC for every job processed.

## 🚀 Quick Start

```bash
# Install
pip install swarmbee

# Initialize (interactive wizard)
swarmbee init

# Start earning
swarmbee start
```

That's it. You're now part of the swarm. 🐝

## 📋 Requirements

- **OS**: Linux (Ubuntu 22.04+ recommended)
- **GPU**: NVIDIA GPU with 16GB+ VRAM
  - RTX 3090, 4090, 5090
  - RTX 6000 Ada
  - A100, H100
- **CUDA**: 12.0+
- **Docker**: 24.0+ with NVIDIA Container Toolkit
- **Python**: 3.10+

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install swarmbee
```

### From Source

```bash
git clone https://github.com/sudohash/swarmbee-cli
cd swarmbee-cli
pip install -e .
```

### Verify Installation

```bash
swarmbee --version
# swarmbee, version 1.0.0
```

## 🛠️ Commands

### `swarmbee init`

Interactive setup wizard that:
- Detects your NVIDIA GPUs
- Configures your worker identity (ENS subdomain)
- Sets your payout wallet address
- Selects which AI models to run
- Generates Docker configuration

```bash
$ swarmbee init

🐝 Setup Wizard

Step 1/6: Checking prerequisites...
✓ Docker installed
✓ Found 2 GPU(s)
✓ NVIDIA Container Toolkit ready

Step 2/6: Detected GPUs
┌────┬─────────────────────┬──────────┬──────┐
│ ID │ Model               │ VRAM     │ CUDA │
├────┼─────────────────────┼──────────┼──────┤
│ 0  │ NVIDIA RTX 5090     │ 32.0 GB  │ 12.4 │
│ 1  │ NVIDIA RTX 5090     │ 32.0 GB  │ 12.4 │
└────┴─────────────────────┴──────────┴──────┘

...
```

### `swarmbee start`

Start your worker and begin processing jobs.

```bash
$ swarmbee start

🐝 SwarmBee
Starting worker: myworker.swarmbee.eth

✓ Images pulled
✓ Containers started
✓ Registered with SwarmOS

✓ Worker is now online!

  ENS:    myworker.swarmbee.eth
  Status: ● Online
  Models: queenbee-spine, queenbee-chest
```

### `swarmbee stop`

Gracefully stop your worker.

```bash
$ swarmbee stop
Stopping worker: myworker.swarmbee.eth...
✓ Worker stopped
```

### `swarmbee status`

Check your worker status and earnings.

```bash
$ swarmbee status

🐝 Worker Status
Worker: myworker.swarmbee.eth
Status: ● Online
Wallet: 0x742d35...f7e3e0

💰 Earnings (USDC)
┌─────────────────────────┬──────────┐
│ Type                    │ Amount   │
├─────────────────────────┼──────────┤
│ Available to withdraw   │ $47.32   │
│ Pending (current epoch) │ $12.80   │
│ Lifetime earnings       │ $1,247.50│
└─────────────────────────┴──────────┘

📊 Performance
┌─────────────────────────┬──────────┐
│ Metric                  │ Value    │
├─────────────────────────┼──────────┤
│ Jobs completed (lifetime)│ 147     │
│ Jobs completed (today)  │ 23       │
│ Uptime                  │ 99.7%    │
│ Avg inference time      │ 2.81s    │
└─────────────────────────┴──────────┘
```

### `swarmbee logs`

Stream worker logs in real-time.

```bash
$ swarmbee logs
Streaming logs for myworker.swarmbee.eth...

[2025-01-01 10:23:45] INFO: Job job-00148 claimed
[2025-01-01 10:23:45] INFO: Loading input: spine_148.nii.gz
[2025-01-01 10:23:47] INFO: Inference complete: 2.31s
[2025-01-01 10:23:48] INFO: Report generated: report_148.pdf
[2025-01-01 10:23:48] INFO: Job job-00148 completed
```

### `swarmbee benchmark`

Test your GPU performance before going live.

```bash
$ swarmbee benchmark

Running GPU Benchmark...

✓ GPU 0: NVIDIA RTX 5090 - PASSED
✓ GPU 1: NVIDIA RTX 5090 - PASSED

Benchmark Results
┌─────────────────────┬─────────┬───────────┬────────┐
│ GPU                 │ VRAM    │ Inference │ Status │
├─────────────────────┼─────────┼───────────┼────────┤
│ NVIDIA RTX 5090     │ 32 GB   │ 2.8s      │ ✓ PASS │
│ NVIDIA RTX 5090     │ 32 GB   │ 2.9s      │ ✓ PASS │
└─────────────────────┴─────────┴───────────┴────────┘
```

### `swarmbee withdraw`

Withdraw available earnings to your wallet.

```bash
$ swarmbee withdraw

💰 Withdrawal
Available balance: $47.32 USDC
Destination: 0x742d35Cc6634C0532925a3b844Bc9e7595f7e3e0

Withdraw $47.32 USDC to your wallet? [Y/n]: Y

✓ Withdrawal submitted
✓ Transaction confirmed

✓ Withdrawal complete!
Transaction: 0x1234...abcd
```

### `swarmbee config`

View current configuration.

```bash
$ swarmbee config
```

### `swarmbee update`

Update to the latest worker image.

```bash
$ swarmbee update
```

## 💰 Economics

### Earnings Per Job

| Model | Job Price | Worker Earnings (70%) |
|-------|-----------|----------------------|
| QueenBee-Spine | $0.10 | $0.07 |
| QueenBee-Chest | $0.10 | $0.07 |
| QueenBee-Foot | $0.08 | $0.056 |

### Additional Earnings

- **Readiness Pool (23%)**: Distributed based on uptime
- Workers with 99%+ uptime earn bonus USDC

### Payout Schedule

- Epochs settle every 24 hours at 00:00 UTC
- Earnings become available after epoch settlement
- Withdraw anytime to your Ethereum wallet

## 🖥️ Supported Models

| Model | VRAM Required | Description |
|-------|---------------|-------------|
| `queenbee-spine` | 24 GB | Lumbar MRI stenosis classification |
| `queenbee-chest` | 24 GB | Chest X-ray and CT analysis |
| `queenbee-foot` | 16 GB | Foot/ankle pathology detection |
| `queenbee-brain` | 32 GB | Brain MRI segmentation (Beta) |
| `queenbee-knee` | 24 GB | Knee MRI analysis (Beta) |

## 🔧 Configuration

Configuration is stored in `~/.swarmbee/config.json`:

```json
{
  "version": "1.0.0",
  "worker": {
    "name": "myworker",
    "ens": "myworker.swarmbee.eth",
    "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f7e3e0"
  },
  "gpus": [0, 1],
  "models": ["queenbee-spine", "queenbee-chest"],
  "controller_url": "https://api.swarmos.eth.limo",
  "created_at": "2025-01-01T00:00:00Z"
}
```

## 🐳 Docker Architecture

SwarmBee runs as Docker containers:

```
┌─────────────────────────────────────────┐
│            Your Machine                  │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │     swarmbee-worker container      │ │
│  │                                    │ │
│  │  ┌──────────────────────────────┐ │ │
│  │  │    MONAI + PyTorch + CUDA    │ │ │
│  │  │    QueenBee Model Weights    │ │ │
│  │  │    FastAPI Worker Server     │ │ │
│  │  └──────────────────────────────┘ │ │
│  │              │ GPU                 │ │
│  └──────────────┼─────────────────────┘ │
│                 ▼                        │
│  ┌────────────────────────────────────┐ │
│  │         NVIDIA GPU(s)              │ │
│  │      RTX 5090 / 6000 Ada           │ │
│  └────────────────────────────────────┘ │
│                                          │
└─────────────────────────────────────────┘
```

## 🛡️ Security

- **No private keys**: Your wallet address is only used for receiving payouts
- **Local inference**: Patient data is processed locally, never leaves your machine
- **ENS identity**: Your worker is identified by an ENS subdomain, not IP address
- **HTTPS only**: All communication with SwarmOS is encrypted

## 🔍 Troubleshooting

### GPU not detected

```bash
# Check NVIDIA drivers
nvidia-smi

# Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Container won't start

```bash
# Check logs
docker logs swarmbee-myworker

# Verify NVIDIA Container Toolkit
sudo apt install nvidia-container-toolkit
sudo systemctl restart docker
```

### Network issues

```bash
# Test connectivity to controller
curl https://api.swarmos.eth.limo/health
```

## 📚 Resources

- **Website**: [swarmbee.eth.limo](https://swarmbee.eth.limo)
- **Explorer**: [swarmorb.eth.limo](https://swarmorb.eth.limo)
- **Model Registry**: [swarmhive.eth.limo](https://swarmhive.eth.limo)
- **Documentation**: [docs.swarmos.eth.limo](https://docs.swarmos.eth.limo)
- **Discord**: [discord.gg/sudohash](https://discord.gg/sudohash)
- **Twitter**: [@sudohash](https://twitter.com/sudohash)

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🙏 Credits

Built by [SudoHash LLC](https://sudohash.eth.limo) in Florida 🌴☀️

Powered by:
- [MONAI](https://monai.io/) - Medical Open Network for AI
- [PyTorch](https://pytorch.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Docker](https://www.docker.com/)
- [ENS](https://ens.domains/)

---

**Local. Sovereign. Trusted.** 🐝⚡💰
