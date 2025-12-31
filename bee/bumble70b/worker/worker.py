"""
Bumble70B Production Worker
Level Up: Speed + Multi-GPU + Full Observability

Features:
- Dynamic K-samples based on confidence
- Multi-GPU support (Spine on GPU0, Chest on GPU1)
- Redis job queues per model type
- Prometheus metrics
- Discord/Telegram alerts
- Merkle proof receipts
- Health checks with proper timeouts
- Structured JSON logging
"""

import os
import sys
import json
import time
import asyncio
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, Response
from fastapi.responses import PlainTextResponse
import uvicorn

from config import config, WorkerConfig
from metrics import MetricsTracker
from alerts import AlertManager, AlertLevel, Alert
from receipts import ReceiptManager, JobReceipt


# =============================================================================
# Structured Logging
# =============================================================================

def log(level: str, message: str, **kwargs):
    """Structured JSON logging."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "worker": config.worker_ens,
        "message": message,
        **kwargs
    }
    print(json.dumps(entry), flush=True)


# =============================================================================
# GPU Utilities
# =============================================================================

async def get_gpu_stats() -> list[dict]:
    """Get GPU statistics via nvidia-smi."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        stats = []
        for line in stdout.decode().strip().split("\n"):
            if line:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    stats.append({
                        "gpu_id": int(parts[0]),
                        "utilization": float(parts[1]),
                        "memory_used_mb": float(parts[2]),
                        "memory_total_mb": float(parts[3]),
                        "temperature": float(parts[4]),
                        "power_watts": float(parts[5]) if parts[5] != "[N/A]" else 0,
                    })
        return stats
    except Exception as e:
        log("error", f"Failed to get GPU stats: {e}")
        return []


# =============================================================================
# Inference Engine
# =============================================================================

class InferenceEngine:
    """
    Handles inference with dynamic K-samples.
    Optimized for RTX 5090 with INT8 quantization.
    """

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.http_client: Optional[httpx.AsyncClient] = None

    async def start(self):
        """Initialize the inference engine."""
        self.http_client = httpx.AsyncClient(timeout=180.0)
        log("info", "Inference engine started")

    async def stop(self):
        """Shutdown the inference engine."""
        if self.http_client:
            await self.http_client.aclose()

    def compute_dynamic_k(self, initial_confidence: float = None) -> int:
        """
        Compute K samples dynamically based on confidence.
        Higher confidence -> fewer samples needed.
        """
        if not self.config.dynamic_k_enabled:
            return self.config.default_k_samples

        dk = self.config.dynamic_k_config

        if initial_confidence is None:
            # No prior, use default
            return self.config.default_k_samples

        if initial_confidence >= dk["confidence_threshold_high"]:
            return dk["min_k"]
        elif initial_confidence <= dk["confidence_threshold_low"]:
            return dk["max_k"]
        else:
            # Linear interpolation
            range_conf = dk["confidence_threshold_high"] - dk["confidence_threshold_low"]
            range_k = dk["max_k"] - dk["min_k"]
            ratio = (initial_confidence - dk["confidence_threshold_low"]) / range_conf
            return int(dk["max_k"] - (ratio * range_k))

    async def run_inference(
        self,
        model: str,
        findings: str,
        job_id: str,
        k_samples: int = None,
    ) -> dict:
        """
        Run inference via QueenBee API.
        Returns result with timing and confidence.
        """
        if k_samples is None:
            k_samples = self.config.default_k_samples

        start_time = time.time()

        try:
            # Determine endpoint based on model
            if "spine" in model:
                endpoint = f"{self.config.queenbee_url}/spine-report"
            elif "chest" in model:
                endpoint = f"{self.config.queenbee_url}/chest-report"
            else:
                endpoint = f"{self.config.queenbee_url}/inference"

            response = await self.http_client.post(
                endpoint,
                json={
                    "findings": findings,
                    "k_samples": k_samples,
                    "max_new_tokens": 512,
                    "use_int8": self.config.use_int8,
                    "use_flash_attention": self.config.use_flash_attention,
                },
            )
            response.raise_for_status()
            result = response.json()

            inference_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "job_id": job_id,
                "model": model,
                "inference_ms": inference_ms,
                "k_samples": k_samples,
                "result": result,
                "confidence": result.get("confidence", {}).get("score_0_100", 0),
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "job_id": job_id,
                "model": model,
                "error": "Timeout",
                "error_type": "timeout",
            }
        except Exception as e:
            return {
                "success": False,
                "job_id": job_id,
                "model": model,
                "error": str(e),
                "error_type": "exception",
            }


# =============================================================================
# Report Generator
# =============================================================================

class ReportGenerator:
    """Generate HTML/PDF reports from inference results."""

    def __init__(self, output_dir: Path, worker_ens: str):
        self.output_dir = Path(output_dir)
        self.worker_ens = worker_ens
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html(self, job_id: str, model: str, result: dict) -> tuple[Path, str]:
        """Generate HTML report and return path + content."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Extract data
        impression = result.get("impression", ["No impression available"])
        stenosis = result.get("stenosis_grades", {})
        confidence = result.get("confidence", {})
        recommendations = result.get("recommendation", [])

        # Verification hash
        content_hash = hashlib.sha256(
            json.dumps(result, sort_keys=True).encode()
        ).hexdigest()[:16]

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Medical AI Report - {job_id}</title>
    <style>
        body {{ font-family: 'Helvetica', sans-serif; margin: 40px; color: #1a1a1a; }}
        .header {{ border-bottom: 3px solid #10b981; padding-bottom: 20px; margin-bottom: 30px; }}
        .logo {{ font-size: 24px; font-weight: bold; color: #10b981; }}
        .job-id {{ color: #666; font-size: 14px; }}
        h2 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f8f8; }}
        .confidence {{ background: #f0fdf4; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .verification {{ background: #f8f8f8; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
        ul {{ line-height: 1.8; }}
        .normal {{ color: #10b981; font-weight: bold; }}
        .mild {{ color: #84cc16; font-weight: bold; }}
        .moderate {{ color: #f97316; font-weight: bold; }}
        .severe {{ color: #ef4444; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">SwarmOS Medical AI</div>
        <div class="job-id">Report ID: {job_id} | Model: {model} | Generated: {timestamp}</div>
    </div>
"""

        if stenosis:
            html += """    <h2>Findings by Level</h2>
    <table>
        <tr><th>Level</th><th>Grade</th></tr>
"""
            for level, grade in stenosis.items():
                grade_class = grade.lower() if grade in ["Normal", "Mild", "Moderate", "Severe"] else ""
                html += f'        <tr><td>{level}</td><td class="{grade_class}">{grade}</td></tr>\n'
            html += "    </table>\n"

        html += """    <h2>Clinical Impression</h2>
    <ul>
"""
        for imp in (impression if isinstance(impression, list) else [impression]):
            html += f"        <li>{imp}</li>\n"

        html += """    </ul>

    <h2>Recommendations</h2>
    <ul>
"""
        for rec in (recommendations if isinstance(recommendations, list) else [recommendations]):
            html += f"        <li>{rec}</li>\n"

        conf_score = confidence.get("score_0_100", 0) if isinstance(confidence, dict) else confidence
        conf_method = confidence.get("method", "k-self-consistency") if isinstance(confidence, dict) else "unknown"

        html += f"""    </ul>

    <div class="confidence">
        <strong>AI Confidence:</strong> {conf_score}%
        (Method: {conf_method})
    </div>

    <div class="verification">
        <strong>Verification Hash:</strong> {content_hash}
    </div>

    <div class="footer">
        <p><strong>Model:</strong> {model}</p>
        <p><strong>Worker:</strong> {self.worker_ens}</p>
        <p style="margin-top:20px"><em>This report was generated by SwarmOS sovereign compute infrastructure.
        Results should be validated by a qualified healthcare professional.</em></p>
    </div>
</body>
</html>
"""

        report_path = self.output_dir / f"{job_id}_report.html"
        report_path.write_text(html)

        return report_path, html


# =============================================================================
# Worker
# =============================================================================

class Bumble70BWorker:
    """
    Production-ready Bumble70B worker.
    Multi-GPU, multi-model, fully monitored.
    """

    def __init__(self, config: WorkerConfig):
        self.config = config

        # Components
        self.inference_engine = InferenceEngine(config)
        self.report_generator = ReportGenerator(config.output_dir, config.worker_ens)
        self.metrics = MetricsTracker(config.worker_ens)
        self.alerts = AlertManager(
            worker_ens=config.worker_ens,
            discord_webhook_url=config.alert_discord_webhook,
            telegram_bot_token=config.alert_telegram_bot_token,
            telegram_chat_id=config.alert_telegram_chat_id,
            generic_webhook_url=config.alert_webhook_url,
        )
        self.receipt_manager = ReceiptManager(
            worker_ens=config.worker_ens,
            receipts_dir=config.receipts_dir,
            private_key_path=config.worker_key_path,
            batch_size=config.merkle_batch_size,
        )

        # Redis
        self.redis: Optional[redis.Redis] = None

        # State
        self.running = False
        self.current_jobs: dict[int, str] = {}  # gpu_id -> job_id
        self.stats = {
            "jobs_completed": 0,
            "jobs_failed": 0,
            "total_inference_ms": 0,
            "started_at": None,
        }

    async def start(self):
        """Start the worker."""
        log("info", "Starting Bumble70B worker", models=list(self.config.gpu_model_assignments.values()))

        # Initialize components
        await self.inference_engine.start()
        await self.alerts.start()

        self.redis = redis.from_url(self.config.redis_url)

        self.running = True
        self.stats["started_at"] = datetime.now(timezone.utc).isoformat()

        # Set metrics
        self.metrics.set_worker_info(
            gpu_model=self.config.gpu_model,
            models=list(self.config.gpu_model_assignments.values()),
            version="2.0.0",
        )
        for model in self.config.gpu_model_assignments.values():
            self.metrics.set_worker_up(model, True)

        # Start background tasks
        asyncio.create_task(self.heartbeat_loop())
        asyncio.create_task(self.job_loop())
        asyncio.create_task(self.gpu_monitor_loop())
        asyncio.create_task(self.queue_monitor_loop())

        # Send startup alert
        await self.alerts.worker_started(
            models=list(self.config.gpu_model_assignments.values()),
            gpus=list(self.config.gpu_model_assignments.keys()),
        )

        log("info", "Worker started successfully")

    async def stop(self):
        """Stop the worker gracefully."""
        log("info", "Stopping worker")
        self.running = False

        # Flush receipts
        self.receipt_manager.flush()

        # Close connections
        await self.inference_engine.stop()
        await self.alerts.worker_stopped()
        await self.alerts.stop()

        if self.redis:
            await self.redis.close()

        log("info", "Worker stopped")

    async def heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self.running:
            try:
                # TODO: Send heartbeat to controller
                pass
            except Exception as e:
                log("warning", f"Heartbeat failed: {e}")

            await asyncio.sleep(self.config.heartbeat_interval)

    async def gpu_monitor_loop(self):
        """Monitor GPU stats and record metrics."""
        while self.running:
            try:
                stats = await get_gpu_stats()
                for gpu in stats:
                    self.metrics.record_gpu_stats(
                        gpu_id=gpu["gpu_id"],
                        util=gpu["utilization"],
                        mem_used=gpu["memory_used_mb"] / 1024,
                        mem_total=gpu["memory_total_mb"] / 1024,
                        temp=gpu["temperature"],
                        power=gpu["power_watts"],
                    )

                    # Alert on high temperature
                    if gpu["temperature"] > 85:
                        await self.alerts.gpu_high_temperature(
                            gpu["gpu_id"],
                            gpu["temperature"]
                        )

            except Exception as e:
                log("warning", f"GPU monitoring failed: {e}")

            await asyncio.sleep(10)

    async def queue_monitor_loop(self):
        """Monitor queue lengths."""
        while self.running:
            try:
                for model in self.config.gpu_model_assignments.values():
                    queue_name = self.config.get_queue_name(model, "pending")
                    length = await self.redis.llen(queue_name)
                    self.metrics.record_queue_length(model, "pending", length)

                    if length > 100:
                        await self.alerts.queue_backlog(model, length)

            except Exception as e:
                log("warning", f"Queue monitoring failed: {e}")

            await asyncio.sleep(30)

    async def job_loop(self):
        """Main job processing loop."""
        while self.running:
            try:
                # Check each model queue
                for gpu_id, model in self.config.gpu_model_assignments.items():
                    # Skip if GPU is busy
                    if gpu_id in self.current_jobs:
                        continue

                    # Try to claim a job
                    queue_name = self.config.get_queue_name(model, "pending")
                    job_data = await self.redis.lpop(queue_name)

                    if job_data:
                        job = json.loads(job_data)
                        # Process in background
                        asyncio.create_task(
                            self.process_job(job, gpu_id, model)
                        )

            except Exception as e:
                log("error", f"Job loop error: {e}")

            await asyncio.sleep(self.config.poll_interval)

    async def process_job(self, job: dict, gpu_id: int, model: str):
        """Process a single job."""
        job_id = job.get("job_id", f"job_{int(time.time())}")
        findings = job.get("findings", "")

        self.current_jobs[gpu_id] = job_id
        self.metrics.record_job_start(model)

        log("info", f"Processing job", job_id=job_id, model=model, gpu=gpu_id)
        start_time = time.time()

        try:
            # Compute dynamic K
            k_samples = self.inference_engine.compute_dynamic_k()

            # Run inference
            result = await self.inference_engine.run_inference(
                model=model,
                findings=findings,
                job_id=job_id,
                k_samples=k_samples,
            )

            if not result["success"]:
                raise RuntimeError(result.get("error", "Unknown error"))

            # Check confidence for dynamic K adjustment
            confidence = result.get("confidence", 0)

            # If low confidence and we didn't use max K, retry with more samples
            if (
                confidence < self.config.low_confidence_threshold
                and k_samples < self.config.dynamic_k_config["max_k"]
            ):
                new_k = self.config.dynamic_k_config["max_k"]
                log("info", f"Low confidence {confidence}%, retrying with K={new_k}", job_id=job_id)

                result = await self.inference_engine.run_inference(
                    model=model,
                    findings=findings,
                    job_id=job_id,
                    k_samples=new_k,
                )

                if not result["success"]:
                    raise RuntimeError(result.get("error", "Unknown error"))

                k_samples = new_k
                confidence = result.get("confidence", 0)

            # Generate report
            report_path, report_content = self.report_generator.generate_html(
                job_id=job_id,
                model=model,
                result=result["result"],
            )

            # Calculate durations
            total_duration = time.time() - start_time
            inference_seconds = result["inference_ms"] / 1000

            # Record metrics
            self.metrics.record_job_complete(
                model=model,
                duration_seconds=total_duration,
                inference_seconds=inference_seconds,
                confidence_score=confidence,
                k_samples=k_samples,
            )

            # Create receipt
            self.receipt_manager.create_receipt(
                job_id=job_id,
                model=model,
                input_data=findings,
                output_data=json.dumps(result["result"]),
                report_content=report_content,
                inference_time_ms=result["inference_ms"],
                confidence_score=confidence,
                k_samples=k_samples,
            )

            # Update stats
            self.stats["jobs_completed"] += 1
            self.stats["total_inference_ms"] += result["inference_ms"]

            # Route low confidence to human review
            if confidence < self.config.low_confidence_threshold:
                await self.redis.rpush(
                    self.config.human_review_queue,
                    json.dumps({
                        "job_id": job_id,
                        "model": model,
                        "confidence": confidence,
                        "report_path": str(report_path),
                    })
                )
                log("info", f"Routed to human review", job_id=job_id, confidence=confidence)

            # Check for low confidence streak
            if self.metrics.low_confidence_streak >= self.config.alert_low_confidence_streak:
                await self.alerts.low_confidence_streak(
                    self.metrics.low_confidence_streak,
                    self.config.low_confidence_threshold,
                )

            log(
                "info",
                f"Job completed",
                job_id=job_id,
                inference_ms=result["inference_ms"],
                confidence=confidence,
                k_samples=k_samples,
            )

        except Exception as e:
            self.stats["jobs_failed"] += 1
            self.metrics.record_job_failed(model, type(e).__name__)

            log("error", f"Job failed", job_id=job_id, error=str(e))
            await self.alerts.worker_error(str(e), job_id)

        finally:
            del self.current_jobs[gpu_id]


# =============================================================================
# FastAPI Application
# =============================================================================

worker = Bumble70BWorker(config)
app = FastAPI(
    title="Bumble70B Worker",
    description="SwarmOS Production Worker - Level Up Edition",
    version="2.0.0",
)


@app.on_event("startup")
async def startup():
    await worker.start()


@app.on_event("shutdown")
async def shutdown():
    await worker.stop()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy" if worker.running else "unhealthy",
        "worker_ens": config.worker_ens,
        "models": list(config.gpu_model_assignments.values()),
        "gpus": list(config.gpu_model_assignments.keys()),
        "current_jobs": worker.current_jobs,
    }


@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "worker_ens": config.worker_ens,
        "running": worker.running,
        "models": config.gpu_model_assignments,
        "current_jobs": worker.current_jobs,
        "stats": worker.stats,
        "config": {
            "dynamic_k_enabled": config.dynamic_k_enabled,
            "default_k_samples": config.default_k_samples,
            "use_int8": config.use_int8,
            "use_flash_attention": config.use_flash_attention,
        },
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=worker.metrics.get_metrics(),
        media_type=worker.metrics.get_content_type(),
    )


@app.get("/stats")
async def stats():
    """Quick stats endpoint."""
    return worker.stats


@app.post("/submit")
async def submit_job(job: dict):
    """Submit a job directly (bypassing Redis queue)."""
    model = job.get("model", "queenbee-spine")
    gpu_id = config.get_gpu_for_model(model)

    if gpu_id is None:
        return {"error": f"Model {model} not available on this worker"}

    if gpu_id in worker.current_jobs:
        return {"error": f"GPU {gpu_id} is busy"}

    # Process immediately
    asyncio.create_task(worker.process_job(job, gpu_id, model))

    return {"status": "accepted", "job_id": job.get("job_id")}


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "worker:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )
