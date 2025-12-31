"""
Prometheus Metrics for Bumble70B Worker
Production monitoring with full observability.
"""

import time
from typing import Optional
from dataclasses import dataclass, field
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry


# Create a custom registry
REGISTRY = CollectorRegistry()


# =============================================================================
# Metrics Definitions
# =============================================================================

# Job Metrics
JOBS_TOTAL = Counter(
    'swarmos_jobs_total',
    'Total number of jobs processed',
    ['model', 'status', 'worker'],
    registry=REGISTRY
)

JOBS_IN_PROGRESS = Gauge(
    'swarmos_jobs_in_progress',
    'Number of jobs currently being processed',
    ['model', 'worker'],
    registry=REGISTRY
)

JOB_DURATION_SECONDS = Histogram(
    'swarmos_job_duration_seconds',
    'Job processing duration in seconds',
    ['model', 'worker'],
    buckets=[10, 30, 60, 90, 120, 150, 180, 240, 300, 600],
    registry=REGISTRY
)

INFERENCE_DURATION_SECONDS = Histogram(
    'swarmos_inference_duration_seconds',
    'Pure inference duration in seconds (excluding PDF generation)',
    ['model', 'worker'],
    buckets=[5, 15, 30, 60, 90, 120, 180],
    registry=REGISTRY
)

# Confidence Metrics
CONFIDENCE_SCORE = Histogram(
    'swarmos_confidence_score',
    'Confidence score distribution (0-100)',
    ['model', 'worker'],
    buckets=[30, 40, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100],
    registry=REGISTRY
)

LOW_CONFIDENCE_TOTAL = Counter(
    'swarmos_low_confidence_total',
    'Number of jobs with low confidence (routed to human review)',
    ['model', 'worker'],
    registry=REGISTRY
)

# GPU Metrics
GPU_UTILIZATION = Gauge(
    'swarmos_gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id', 'worker'],
    registry=REGISTRY
)

GPU_MEMORY_USED_GB = Gauge(
    'swarmos_gpu_memory_used_gb',
    'GPU memory used in GB',
    ['gpu_id', 'worker'],
    registry=REGISTRY
)

GPU_MEMORY_TOTAL_GB = Gauge(
    'swarmos_gpu_memory_total_gb',
    'GPU total memory in GB',
    ['gpu_id', 'worker'],
    registry=REGISTRY
)

GPU_TEMPERATURE = Gauge(
    'swarmos_gpu_temperature_celsius',
    'GPU temperature in Celsius',
    ['gpu_id', 'worker'],
    registry=REGISTRY
)

GPU_POWER_WATTS = Gauge(
    'swarmos_gpu_power_watts',
    'GPU power draw in Watts',
    ['gpu_id', 'worker'],
    registry=REGISTRY
)

# Queue Metrics
QUEUE_LENGTH = Gauge(
    'swarmos_queue_length',
    'Number of jobs in queue',
    ['model', 'queue_type'],
    registry=REGISTRY
)

# Worker Metrics
WORKER_UP = Gauge(
    'swarmos_worker_up',
    'Worker is up and running (1=up, 0=down)',
    ['worker', 'model'],
    registry=REGISTRY
)

WORKER_UPTIME_SECONDS = Gauge(
    'swarmos_worker_uptime_seconds',
    'Worker uptime in seconds',
    ['worker'],
    registry=REGISTRY
)

WORKER_INFO = Info(
    'swarmos_worker',
    'Worker information',
    ['worker'],
    registry=REGISTRY
)

# K-Samples Metrics (for dynamic K)
K_SAMPLES_USED = Histogram(
    'swarmos_k_samples_used',
    'Number of K samples used per inference',
    ['model', 'worker'],
    buckets=[3, 4, 5, 6, 7, 8, 9, 10],
    registry=REGISTRY
)

# Error Metrics
ERRORS_TOTAL = Counter(
    'swarmos_errors_total',
    'Total number of errors',
    ['error_type', 'model', 'worker'],
    registry=REGISTRY
)


# =============================================================================
# Metrics Tracker
# =============================================================================

@dataclass
class MetricsTracker:
    """Track and expose metrics for Prometheus."""

    worker_ens: str
    start_time: float = field(default_factory=time.time)
    _low_confidence_streak: int = 0

    def record_job_start(self, model: str):
        """Record job start."""
        JOBS_IN_PROGRESS.labels(model=model, worker=self.worker_ens).inc()

    def record_job_complete(
        self,
        model: str,
        duration_seconds: float,
        inference_seconds: float,
        confidence_score: int,
        k_samples: int,
    ):
        """Record successful job completion."""
        JOBS_IN_PROGRESS.labels(model=model, worker=self.worker_ens).dec()
        JOBS_TOTAL.labels(model=model, status="success", worker=self.worker_ens).inc()
        JOB_DURATION_SECONDS.labels(model=model, worker=self.worker_ens).observe(duration_seconds)
        INFERENCE_DURATION_SECONDS.labels(model=model, worker=self.worker_ens).observe(inference_seconds)
        CONFIDENCE_SCORE.labels(model=model, worker=self.worker_ens).observe(confidence_score)
        K_SAMPLES_USED.labels(model=model, worker=self.worker_ens).observe(k_samples)

        # Track low confidence streak
        if confidence_score < 55:
            self._low_confidence_streak += 1
            LOW_CONFIDENCE_TOTAL.labels(model=model, worker=self.worker_ens).inc()
        else:
            self._low_confidence_streak = 0

    def record_job_failed(self, model: str, error_type: str):
        """Record job failure."""
        JOBS_IN_PROGRESS.labels(model=model, worker=self.worker_ens).dec()
        JOBS_TOTAL.labels(model=model, status="failed", worker=self.worker_ens).inc()
        ERRORS_TOTAL.labels(error_type=error_type, model=model, worker=self.worker_ens).inc()
        self._low_confidence_streak = 0

    def record_gpu_stats(self, gpu_id: int, util: float, mem_used: float, mem_total: float, temp: float, power: float):
        """Record GPU statistics."""
        GPU_UTILIZATION.labels(gpu_id=str(gpu_id), worker=self.worker_ens).set(util)
        GPU_MEMORY_USED_GB.labels(gpu_id=str(gpu_id), worker=self.worker_ens).set(mem_used)
        GPU_MEMORY_TOTAL_GB.labels(gpu_id=str(gpu_id), worker=self.worker_ens).set(mem_total)
        GPU_TEMPERATURE.labels(gpu_id=str(gpu_id), worker=self.worker_ens).set(temp)
        GPU_POWER_WATTS.labels(gpu_id=str(gpu_id), worker=self.worker_ens).set(power)

    def record_queue_length(self, model: str, queue_type: str, length: int):
        """Record queue length."""
        QUEUE_LENGTH.labels(model=model, queue_type=queue_type).set(length)

    def set_worker_up(self, model: str, is_up: bool):
        """Set worker up status."""
        WORKER_UP.labels(worker=self.worker_ens, model=model).set(1 if is_up else 0)

    def update_uptime(self):
        """Update worker uptime."""
        WORKER_UPTIME_SECONDS.labels(worker=self.worker_ens).set(time.time() - self.start_time)

    def set_worker_info(self, gpu_model: str, models: list[str], version: str):
        """Set worker info labels."""
        WORKER_INFO.labels(worker=self.worker_ens).info({
            'gpu_model': gpu_model,
            'models': ','.join(models),
            'version': version,
        })

    @property
    def low_confidence_streak(self) -> int:
        """Get current low confidence streak."""
        return self._low_confidence_streak

    def get_metrics(self) -> bytes:
        """Generate Prometheus metrics output."""
        self.update_uptime()
        return generate_latest(REGISTRY)

    def get_content_type(self) -> str:
        """Get Prometheus content type."""
        return CONTENT_TYPE_LATEST
