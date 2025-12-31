"""
Bumble70B Worker Configuration
Level Up: Speed + Multi-GPU + Production Ready
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WorkerConfig:
    """Production worker configuration."""

    # Identity
    worker_ens: str = os.getenv("WORKER_ENS", "bumble70b.swarmbee.eth")
    worker_wallet: str = os.getenv("WORKER_WALLET", "")
    worker_key_path: str = os.getenv("WORKER_KEY_PATH", "/home/ai/swarmos/bee/bumble70b/bee_key")

    # GPUs - Multi-GPU Support
    gpu_ids: list[int] = field(default_factory=lambda: [0, 1])
    gpu_model: str = "RTX 5090"
    vram_per_gpu_gb: int = 32

    # Models per GPU
    gpu_model_assignments: dict = field(default_factory=lambda: {
        0: "queenbee-spine",
        1: "queenbee-chest",
    })

    # Speed Optimizations
    default_k_samples: int = 5  # Reduced from 7 for speed
    dynamic_k_enabled: bool = True
    dynamic_k_config: dict = field(default_factory=lambda: {
        "min_k": 3,           # Minimum K for high-confidence cases
        "max_k": 7,           # Maximum K for low-confidence cases
        "confidence_threshold_high": 0.75,  # Above this: use min_k
        "confidence_threshold_low": 0.55,   # Below this: use max_k
    })

    # INT8 Quantization
    use_int8: bool = True
    use_flash_attention: bool = True

    # Batch Processing
    max_batch_size: int = 2  # For RTX 5090 with 70B model
    prefetch_enabled: bool = True

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Queue Names (per model type)
    queue_prefix: str = "jobs"

    # Controller
    controller_url: str = os.getenv("CONTROLLER_URL", "http://localhost:8001")
    queenbee_url: str = os.getenv("QUEENBEE_URL", "http://localhost:8000")

    # Paths
    model_dir: Path = Path(os.getenv("MODEL_DIR", "/home/ai/models"))
    data_dir: Path = Path(os.getenv("DATA_DIR", "/home/ai/swarm-genesis/data"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "/home/ai/swarm-genesis/data/outputs"))
    log_dir: Path = Path(os.getenv("LOG_DIR", "/home/ai/swarm-genesis/logs"))
    receipts_dir: Path = Path(os.getenv("RECEIPTS_DIR", "/home/ai/swarm-genesis/receipts"))

    # Worker Behavior
    heartbeat_interval: int = 30
    poll_interval: float = 0.5  # Faster polling
    max_concurrent_jobs: int = 2  # One per GPU
    job_timeout: int = 300  # 5 minutes max per job

    # Confidence Routing
    low_confidence_threshold: int = 55  # Below this -> human review
    human_review_queue: str = "jobs:human_review:pending"

    # Monitoring
    metrics_port: int = 9090
    metrics_enabled: bool = True

    # Alerts
    alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "")
    alert_discord_webhook: str = os.getenv("DISCORD_WEBHOOK_URL", "")
    alert_telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    alert_telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Alert Thresholds
    alert_error_rate_threshold: float = 0.1  # 10% error rate triggers alert
    alert_low_confidence_streak: int = 5  # 5 consecutive low confidence jobs

    # IPFS
    ipfs_enabled: bool = True
    ipfs_api_url: str = os.getenv("IPFS_API_URL", "http://localhost:5001")

    # Receipts & Proofs
    merkle_batch_size: int = 100  # Batch receipts into Merkle trees

    def get_queue_name(self, model: str, status: str = "pending") -> str:
        """Get Redis queue name for a model type."""
        return f"{self.queue_prefix}:{model}:{status}"

    def get_gpu_for_model(self, model: str) -> Optional[int]:
        """Get GPU ID assigned to a model."""
        for gpu_id, assigned_model in self.gpu_model_assignments.items():
            if assigned_model == model:
                return gpu_id
        return None


# Global config instance
config = WorkerConfig()
