# Bumble70B Worker - Level Up Edition

Production-ready SwarmOS worker with speed optimizations, multi-GPU support, and full observability.

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   BUMBLE70B LEVEL UP                                                     ║
║                                                                          ║
║   Worker:    bumble70b.swarmbee.eth                                      ║
║   GPUs:      2x RTX 5090 (63.7 GB VRAM total)                            ║
║   Models:    GPU 0: QueenBee-Spine | GPU 1: QueenBee-Chest               ║
║   Speed:     ~60-80 seconds/job (2x throughput)                          ║
║   Power:     Solar (Florida, USA)                                        ║
║                                                                          ║
║   sovereign.compute.no-cloud                                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## Features

### Speed Optimizations
- **Dynamic K-Samples**: Automatically adjusts K based on confidence
  - High confidence (>75%): K=3 (faster)
  - Low confidence (<55%): K=7 (more accurate)
  - Default: K=5
- **INT8 Quantization**: Enabled for RTX 5090
- **Flash Attention**: Optimized attention mechanism
- **Target**: ~60-80 seconds/job (2x throughput from Epoch 0)

### Multi-GPU Support
- GPU 0: QueenBee-Spine (lumbar stenosis analysis)
- GPU 1: QueenBee-Chest (pulmonary findings)
- Independent job queues per model
- Parallel processing

### Production Hardening
- **Prometheus Metrics**: Full observability at `/metrics`
- **Grafana Dashboard**: Pre-configured dashboard
- **Alert System**: Discord + Telegram webhooks
- **Systemd Service**: Auto-restart on crash
- **Health Checks**: Proper timeouts
- **Structured Logging**: JSON format for log aggregation

### Job Receipts & Proofs
- **Merkle Trees**: Batch receipts into provable trees
- **SSH Signatures**: ED25519 signed with bee_key
- **IPFS Upload**: Decentralized storage for reports
- **SwarmLedger Compatible**: Ready for settlement layer

## Quick Start

### 1. Start Infrastructure

```bash
cd /home/ai/swarm-genesis/bee/bumble70b

# Start Redis, Prometheus, Grafana, IPFS
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Install Worker Dependencies

```bash
# Using existing venv
source /home/ai/swarm-genesis/swarmos-backend/venv/bin/activate

# Install additional deps
pip install prometheus-client redis httpx

# Verify
python -c "from worker import app; print('Worker OK')"
```

### 3. Run Worker

```bash
# Development mode
cd /home/ai/swarm-genesis/bee/bumble70b/worker
python -m uvicorn worker:app --host 0.0.0.0 --port 8080 --reload

# Production mode (systemd)
sudo cp systemd/swarmbee-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable swarmbee-worker
sudo systemctl start swarmbee-worker
```

### 4. Access Dashboards

- **Worker Health**: http://localhost:8080/health
- **Prometheus Metrics**: http://localhost:8080/metrics
- **Grafana Dashboard**: http://localhost:3000 (admin/swarmos2025)
- **Prometheus UI**: http://localhost:9091

## Configuration

### Environment Variables

```bash
# Identity
WORKER_ENS=bumble70b.swarmbee.eth
WORKER_KEY_PATH=/home/ai/swarmos/bee/bumble70b/bee_key

# Services
REDIS_URL=redis://localhost:6379
QUEENBEE_URL=http://localhost:8000
CONTROLLER_URL=http://localhost:8001

# Paths
OUTPUT_DIR=/home/ai/swarm-genesis/data/outputs
LOG_DIR=/home/ai/swarm-genesis/logs
RECEIPTS_DIR=/home/ai/swarm-genesis/receipts

# Alerts (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Speed Tuning

Edit `worker/config.py`:

```python
# Reduce K for faster inference
default_k_samples: int = 5

# Enable dynamic K
dynamic_k_enabled: bool = True
dynamic_k_config: dict = {
    "min_k": 3,           # Fast for high confidence
    "max_k": 7,           # Accurate for low confidence
    "confidence_threshold_high": 0.75,
    "confidence_threshold_low": 0.55,
}

# Enable optimizations
use_int8: bool = True
use_flash_attention: bool = True
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Detailed status |
| `/metrics` | GET | Prometheus metrics |
| `/stats` | GET | Quick stats |
| `/submit` | POST | Submit job directly |

## Job Queue Structure

Redis queues per model:
- `jobs:queenbee-spine:pending` - Spine jobs waiting
- `jobs:queenbee-chest:pending` - Chest jobs waiting
- `jobs:human_review:pending` - Low confidence jobs

Submit job to queue:
```python
import redis
import json

r = redis.Redis()
job = {
    "job_id": "job_001",
    "model": "queenbee-spine",
    "findings": "L4-L5: Moderate stenosis..."
}
r.rpush("jobs:queenbee-spine:pending", json.dumps(job))
```

## Metrics

Key Prometheus metrics:
- `swarmos_jobs_total{status, model}` - Total jobs
- `swarmos_inference_duration_seconds` - Inference latency
- `swarmos_confidence_score` - Confidence distribution
- `swarmos_gpu_utilization_percent` - GPU usage
- `swarmos_gpu_temperature_celsius` - GPU temp
- `swarmos_queue_length{model}` - Queue depth
- `swarmos_k_samples_used` - Dynamic K tracking

## Alerts

Automatic alerts for:
- Worker started/stopped
- High error rate (>10%)
- Low confidence streak (5+ consecutive)
- GPU high temperature (>85°C)
- Job timeout (>5 minutes)
- Queue backlog (>100 jobs)

## Receipt Format

```json
{
  "job_id": "job_001",
  "worker_ens": "bumble70b.swarmbee.eth",
  "model": "queenbee-spine",
  "input_hash": "sha256:...",
  "output_hash": "sha256:...",
  "report_hash": "sha256:...",
  "inference_time_ms": 75000,
  "confidence_score": 68,
  "k_samples": 5,
  "timestamp": "2025-12-31T21:30:00Z",
  "epoch": 0,
  "ipfs_cid": "Qm..."
}
```

Merkle proofs are generated every 100 receipts and signed with the bee key.

## File Structure

```
bee/bumble70b/
├── worker/
│   ├── __init__.py
│   ├── config.py        # Configuration
│   ├── worker.py        # Main worker
│   ├── metrics.py       # Prometheus metrics
│   ├── alerts.py        # Webhook alerts
│   └── receipts.py      # Merkle proofs
├── grafana/
│   ├── dashboard.json   # Grafana dashboard
│   └── provisioning/    # Auto-load configs
├── systemd/
│   └── swarmbee-worker.service
├── docker-compose.yml   # Infrastructure stack
├── prometheus.yml       # Prometheus config
├── card.html            # Bee identity card
└── README.md            # This file
```

## Scaling

To add more GPUs:

1. Update `config.py`:
```python
gpu_model_assignments: dict = {
    0: "queenbee-spine",
    1: "queenbee-chest",
    2: "queenbee-brain",
    3: "queenbee-cardiac",
}
```

2. Add Redis queues for new models

3. Restart worker

## Troubleshooting

### Worker won't start
```bash
# Check logs
journalctl -u swarmbee-worker -f

# Check Redis
redis-cli ping

# Check QueenBee
curl http://localhost:8000/health
```

### High latency
- Check GPU utilization in Grafana
- Reduce K-samples if confidence is consistently high
- Check for memory leaks

### Low confidence
- Enable dynamic K with max_k=7
- Consider adding RAG for clinical literature
- Route to human review queue

## License

SwarmOS - Sovereign Compute Infrastructure
NYE 2025 | Epoch 0

---

*Built with Claude Code | bumble70b.swarmbee.eth*
