"""
SwarmBee Worker

GPU worker that processes jobs from the SwarmOS queue.

Responsibilities:
- Register with Bee-1 controller
- Poll job queue
- Execute MONAI inference
- Generate PDF reports
- Submit completions
"""

import os
import sys
import json
import time
import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn


# =============================================================================
# Configuration
# =============================================================================

class Config:
    # Identity
    WORKER_ENS: str = os.getenv("WORKER_ENS", "unnamed.swarmbee.eth")
    WORKER_WALLET: str = os.getenv("WORKER_WALLET", "")
    
    # Controller
    CONTROLLER_URL: str = os.getenv("CONTROLLER_URL", "https://api.swarmos.eth.limo")
    
    # Models
    MODELS: list[str] = os.getenv("MODELS", "queenbee-spine").split(",")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # Paths
    MODEL_DIR: Path = Path(os.getenv("MODEL_DIR", "/models"))
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "/data"))
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "/outputs"))
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "/logs"))
    
    # Worker settings
    HEARTBEAT_INTERVAL: int = 30  # seconds
    POLL_INTERVAL: int = 2  # seconds
    MAX_CONCURRENT_JOBS: int = 1
    
    # API
    HOST: str = "0.0.0.0"
    PORT: int = 8080


config = Config()


# =============================================================================
# Logging
# =============================================================================

def log(level: str, message: str):
    """Simple logging."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level.upper()}: {message}", flush=True)


# =============================================================================
# Model Loader
# =============================================================================

class ModelManager:
    """Manages MONAI model loading and inference."""
    
    def __init__(self):
        self.models: dict = {}
        self.device = None
    
    async def initialize(self):
        """Initialize models on startup."""
        import torch
        
        # Detect GPU
        if torch.cuda.is_available():
            self.device = torch.device("cuda:0")
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            log("info", f"GPU detected: {gpu_name} ({gpu_mem:.1f} GB)")
        else:
            log("error", "No CUDA GPU available!")
            sys.exit(1)
        
        # Load requested models
        for model_name in config.MODELS:
            await self.load_model(model_name)
    
    async def load_model(self, model_name: str):
        """Load a MONAI model."""
        log("info", f"Loading model: {model_name}")
        
        model_path = config.MODEL_DIR / model_name / "model.pt"
        
        if not model_path.exists():
            # Download model weights if not present
            await self.download_model(model_name)
        
        try:
            import torch
            from monai.networks.nets import SwinUNETR
            
            # Model architecture depends on model type
            if "spine" in model_name:
                model = SwinUNETR(
                    img_size=(96, 96, 96),
                    in_channels=1,
                    out_channels=5,  # L1-L5 stenosis grades
                    feature_size=48,
                )
            elif "chest" in model_name:
                from monai.networks.nets import ViT
                model = ViT(
                    in_channels=1,
                    img_size=(224, 224),
                    patch_size=16,
                    num_classes=14,  # Multiple findings
                )
            else:
                # Default architecture
                from monai.networks.nets import DenseNet121
                model = DenseNet121(
                    spatial_dims=2,
                    in_channels=1,
                    out_channels=10,
                )
            
            # Load weights
            if model_path.exists():
                state_dict = torch.load(model_path, map_location=self.device)
                model.load_state_dict(state_dict)
            
            model = model.to(self.device)
            model.eval()
            
            self.models[model_name] = model
            log("info", f"Model loaded: {model_name}")
            
        except Exception as e:
            log("error", f"Failed to load model {model_name}: {e}")
    
    async def download_model(self, model_name: str):
        """Download model weights from registry."""
        log("info", f"Downloading model weights: {model_name}")
        
        model_dir = config.MODEL_DIR / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # In production, download from SwarmHive registry
        # For now, create placeholder
        log("warning", f"Model weights not found, using random initialization")
    
    async def infer(self, model_name: str, input_path: Path) -> dict:
        """Run inference on input."""
        import torch
        import nibabel as nib
        import numpy as np
        from monai.transforms import (
            Compose,
            LoadImage,
            EnsureChannelFirst,
            ScaleIntensity,
            Resize,
            ToTensor,
        )
        
        if model_name not in self.models:
            raise ValueError(f"Model not loaded: {model_name}")
        
        model = self.models[model_name]
        
        # Load and preprocess
        start_time = time.time()
        
        transforms = Compose([
            LoadImage(image_only=True),
            EnsureChannelFirst(),
            ScaleIntensity(),
            Resize((96, 96, 96)),
            ToTensor(),
        ])
        
        try:
            input_tensor = transforms(str(input_path))
            input_tensor = input_tensor.unsqueeze(0).to(self.device)
        except Exception as e:
            log("error", f"Failed to load input: {e}")
            raise
        
        # Run inference
        with torch.no_grad():
            output = model(input_tensor)
            predictions = torch.softmax(output, dim=1)
        
        inference_time = time.time() - start_time
        
        # Convert to findings
        findings = self._predictions_to_findings(model_name, predictions.cpu().numpy())
        
        return {
            "model": model_name,
            "inference_time_seconds": round(inference_time, 3),
            "findings": findings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def _predictions_to_findings(self, model_name: str, predictions: 'np.ndarray') -> dict:
        """Convert model predictions to clinical findings."""
        import numpy as np
        
        if "spine" in model_name:
            levels = ["L1-L2", "L2-L3", "L3-L4", "L4-L5", "L5-S1"]
            grades = ["Normal", "Mild", "Moderate", "Severe"]
            
            findings = {}
            probs = predictions[0]
            
            for i, level in enumerate(levels):
                if i < len(probs):
                    grade_idx = int(np.clip(probs[i] * 4, 0, 3))
                    findings[level] = {
                        "grade": grades[grade_idx],
                        "confidence": float(probs[i]),
                    }
            
            return findings
        
        return {"raw_predictions": predictions.tolist()}


# =============================================================================
# PDF Report Generator
# =============================================================================

class ReportGenerator:
    """Generates PDF reports from findings."""
    
    def generate(self, job_id: str, findings: dict, output_path: Path) -> Path:
        """Generate a PDF report."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        pdf_path = output_path / f"{job_id}_report.pdf"
        
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Header
        story.append(Paragraph("SwarmOS Medical AI Report", styles["Title"]))
        story.append(Spacer(1, 12))
        
        # Metadata
        story.append(Paragraph(f"<b>Job ID:</b> {job_id}", styles["Normal"]))
        story.append(Paragraph(f"<b>Model:</b> {findings.get('model', 'Unknown')}", styles["Normal"]))
        story.append(Paragraph(f"<b>Generated:</b> {findings.get('timestamp', 'Unknown')}", styles["Normal"]))
        story.append(Paragraph(f"<b>Inference Time:</b> {findings.get('inference_time_seconds', 0):.2f}s", styles["Normal"]))
        story.append(Spacer(1, 24))
        
        # Findings
        story.append(Paragraph("Findings", styles["Heading2"]))
        story.append(Spacer(1, 12))
        
        findings_data = findings.get("findings", {})
        
        if isinstance(findings_data, dict):
            table_data = [["Level", "Grade", "Confidence"]]
            for level, data in findings_data.items():
                if isinstance(data, dict):
                    table_data.append([
                        level,
                        data.get("grade", "N/A"),
                        f"{data.get('confidence', 0):.1%}"
                    ])
            
            if len(table_data) > 1:
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                story.append(table)
        
        story.append(Spacer(1, 24))
        
        # Footer
        story.append(Paragraph("─" * 60, styles["Normal"]))
        story.append(Paragraph(
            "<i>This report was generated by SwarmOS sovereign compute infrastructure. "
            "Results should be reviewed by a qualified healthcare professional.</i>",
            styles["Normal"]
        ))
        
        # Verification hash
        content_hash = hashlib.sha256(json.dumps(findings, sort_keys=True).encode()).hexdigest()[:16]
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>Verification Hash:</b> {content_hash}", styles["Normal"]))
        
        # Build PDF
        doc.build(story)
        
        return pdf_path


# =============================================================================
# Worker
# =============================================================================

class Worker:
    """Main worker class."""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.report_generator = ReportGenerator()
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False
        self.current_job: Optional[str] = None
        self.stats = {
            "jobs_completed": 0,
            "jobs_failed": 0,
            "total_inference_time": 0.0,
            "started_at": None,
        }
    
    async def start(self):
        """Start the worker."""
        log("info", f"Starting worker: {config.WORKER_ENS}")
        
        # Initialize connections
        self.redis_client = redis.from_url(config.REDIS_URL)
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize models
        await self.model_manager.initialize()
        
        # Register with controller
        await self.register()
        
        # Start background tasks
        self.running = True
        self.stats["started_at"] = datetime.now(timezone.utc).isoformat()
        
        asyncio.create_task(self.heartbeat_loop())
        asyncio.create_task(self.job_loop())
        
        log("info", "Worker started successfully")
    
    async def stop(self):
        """Stop the worker."""
        log("info", "Stopping worker...")
        self.running = False
        
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()
    
    async def register(self):
        """Register with the controller."""
        log("info", f"Registering with controller: {config.CONTROLLER_URL}")
        
        try:
            response = await self.http_client.post(
                f"{config.CONTROLLER_URL}/v1/workers/register",
                json={
                    "ens": config.WORKER_ENS,
                    "wallet": config.WORKER_WALLET,
                    "models": config.MODELS,
                    "capabilities": {
                        "gpu": True,
                        "models": config.MODELS,
                    },
                },
            )
            
            if response.status_code == 200:
                log("info", "Registered successfully")
            else:
                log("warning", f"Registration returned {response.status_code}")
                
        except Exception as e:
            log("warning", f"Failed to register (will retry): {e}")
    
    async def heartbeat_loop(self):
        """Send periodic heartbeats to controller."""
        while self.running:
            try:
                await self.http_client.post(
                    f"{config.CONTROLLER_URL}/v1/workers/heartbeat",
                    json={
                        "ens": config.WORKER_ENS,
                        "status": "busy" if self.current_job else "online",
                        "current_job": self.current_job,
                        "stats": self.stats,
                    },
                )
            except Exception as e:
                log("warning", f"Heartbeat failed: {e}")
            
            await asyncio.sleep(config.HEARTBEAT_INTERVAL)
    
    async def job_loop(self):
        """Poll for and process jobs."""
        while self.running:
            try:
                # Check queue for jobs we can handle
                for model in config.MODELS:
                    queue_key = f"jobs:{model}:pending"
                    
                    job_data = await self.redis_client.lpop(queue_key)
                    
                    if job_data:
                        job = json.loads(job_data)
                        await self.process_job(job)
                        break
                
            except Exception as e:
                log("error", f"Job loop error: {e}")
            
            await asyncio.sleep(config.POLL_INTERVAL)
    
    async def process_job(self, job: dict):
        """Process a single job."""
        job_id = job.get("job_id", "unknown")
        
        log("info", f"Processing job: {job_id}")
        self.current_job = job_id
        
        try:
            # Get job details
            model = job.get("model", config.MODELS[0])
            input_path = Path(job.get("input_path", ""))
            
            # Run inference
            start_time = time.time()
            findings = await self.model_manager.infer(model, input_path)
            inference_time = time.time() - start_time
            
            # Generate PDF report
            output_dir = config.OUTPUT_DIR / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            pdf_path = self.report_generator.generate(job_id, findings, output_dir)
            
            # Save findings JSON
            findings_path = output_dir / f"{job_id}_findings.json"
            findings_path.write_text(json.dumps(findings, indent=2))
            
            # Generate proof hash
            proof_hash = hashlib.sha256(
                json.dumps(findings, sort_keys=True).encode()
            ).hexdigest()
            
            # Submit completion
            await self.submit_completion(job_id, {
                "status": "completed",
                "findings_path": str(findings_path),
                "report_path": str(pdf_path),
                "proof_hash": proof_hash,
                "inference_time": inference_time,
            })
            
            # Update stats
            self.stats["jobs_completed"] += 1
            self.stats["total_inference_time"] += inference_time
            
            log("info", f"Job completed: {job_id} ({inference_time:.2f}s)")
            
        except Exception as e:
            log("error", f"Job failed: {job_id} - {e}")
            self.stats["jobs_failed"] += 1
            
            await self.submit_completion(job_id, {
                "status": "failed",
                "error": str(e),
            })
        
        finally:
            self.current_job = None
    
    async def submit_completion(self, job_id: str, result: dict):
        """Submit job completion to controller."""
        try:
            await self.http_client.post(
                f"{config.CONTROLLER_URL}/v1/jobs/{job_id}/complete",
                json={
                    "worker_ens": config.WORKER_ENS,
                    **result,
                },
            )
        except Exception as e:
            log("error", f"Failed to submit completion: {e}")


# =============================================================================
# FastAPI App
# =============================================================================

worker = Worker()

app = FastAPI(
    title="SwarmBee Worker",
    version="1.0.0",
)


@app.on_event("startup")
async def startup():
    await worker.start()


@app.on_event("shutdown")
async def shutdown():
    await worker.stop()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "worker_ens": config.WORKER_ENS,
        "models": config.MODELS,
        "current_job": worker.current_job,
    }


@app.get("/status")
async def status():
    return {
        "worker_ens": config.WORKER_ENS,
        "wallet": config.WORKER_WALLET,
        "models": config.MODELS,
        "running": worker.running,
        "current_job": worker.current_job,
        "stats": worker.stats,
    }


@app.get("/stats")
async def stats():
    return worker.stats


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "worker.main:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info",
    )
