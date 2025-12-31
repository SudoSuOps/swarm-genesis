"""
Alert System for Bumble70B Worker
Discord + Telegram webhook notifications.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

import httpx


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure."""
    level: AlertLevel
    title: str
    message: str
    worker_ens: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def to_discord_embed(self) -> dict:
        """Convert to Discord embed format."""
        colors = {
            AlertLevel.INFO: 0x3498db,      # Blue
            AlertLevel.WARNING: 0xf39c12,   # Orange
            AlertLevel.ERROR: 0xe74c3c,     # Red
            AlertLevel.CRITICAL: 0x9b59b6,  # Purple
        }

        fields = [
            {"name": "Worker", "value": self.worker_ens, "inline": True},
            {"name": "Level", "value": self.level.value.upper(), "inline": True},
        ]

        for key, value in self.metadata.items():
            fields.append({"name": key, "value": str(value), "inline": True})

        return {
            "embeds": [{
                "title": f"{'🔴' if self.level == AlertLevel.CRITICAL else '🟡' if self.level == AlertLevel.WARNING else '🔵'} {self.title}",
                "description": self.message,
                "color": colors.get(self.level, 0x95a5a6),
                "fields": fields,
                "timestamp": self.timestamp.isoformat(),
                "footer": {"text": "SwarmOS Alert System"}
            }]
        }

    def to_telegram_message(self) -> str:
        """Convert to Telegram message format."""
        emoji = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨",
        }

        meta_str = "\n".join(f"• {k}: {v}" for k, v in self.metadata.items())

        return f"""{emoji.get(self.level, '📢')} *{self.title}*

{self.message}

*Worker:* `{self.worker_ens}`
*Level:* {self.level.value.upper()}
*Time:* {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

{meta_str if meta_str else ''}"""


class AlertManager:
    """
    Manages alerts and notifications.

    Supports:
    - Discord webhooks
    - Telegram bot API
    - Generic webhooks
    - Rate limiting to prevent spam
    """

    def __init__(
        self,
        worker_ens: str,
        discord_webhook_url: str = "",
        telegram_bot_token: str = "",
        telegram_chat_id: str = "",
        generic_webhook_url: str = "",
        rate_limit_seconds: int = 60,  # Min time between same alerts
    ):
        self.worker_ens = worker_ens
        self.discord_webhook_url = discord_webhook_url
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.generic_webhook_url = generic_webhook_url
        self.rate_limit_seconds = rate_limit_seconds

        self._last_alerts: dict[str, float] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self):
        """Start the alert manager."""
        self._client = httpx.AsyncClient(timeout=30.0)

    async def stop(self):
        """Stop the alert manager."""
        if self._client:
            await self._client.aclose()

    def _should_send(self, alert_key: str) -> bool:
        """Check if alert should be sent (rate limiting)."""
        now = time.time()
        last_sent = self._last_alerts.get(alert_key, 0)

        if now - last_sent < self.rate_limit_seconds:
            return False

        self._last_alerts[alert_key] = now
        return True

    async def send_alert(self, alert: Alert):
        """Send alert to all configured channels."""
        alert_key = f"{alert.level.value}:{alert.title}"

        if not self._should_send(alert_key):
            return  # Rate limited

        tasks = []

        if self.discord_webhook_url:
            tasks.append(self._send_discord(alert))

        if self.telegram_bot_token and self.telegram_chat_id:
            tasks.append(self._send_telegram(alert))

        if self.generic_webhook_url:
            tasks.append(self._send_generic(alert))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_discord(self, alert: Alert):
        """Send alert to Discord."""
        try:
            response = await self._client.post(
                self.discord_webhook_url,
                json=alert.to_discord_embed(),
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[ALERT] Discord send failed: {e}")

    async def _send_telegram(self, alert: Alert):
        """Send alert to Telegram."""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            response = await self._client.post(
                url,
                json={
                    "chat_id": self.telegram_chat_id,
                    "text": alert.to_telegram_message(),
                    "parse_mode": "Markdown",
                },
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[ALERT] Telegram send failed: {e}")

    async def _send_generic(self, alert: Alert):
        """Send alert to generic webhook."""
        try:
            response = await self._client.post(
                self.generic_webhook_url,
                json={
                    "level": alert.level.value,
                    "title": alert.title,
                    "message": alert.message,
                    "worker_ens": alert.worker_ens,
                    "timestamp": alert.timestamp.isoformat(),
                    "metadata": alert.metadata,
                },
            )
            response.raise_for_status()
        except Exception as e:
            print(f"[ALERT] Generic webhook send failed: {e}")

    # =============================================================================
    # Convenience Methods
    # =============================================================================

    async def worker_started(self, models: list[str], gpus: list[int]):
        """Alert: Worker started."""
        await self.send_alert(Alert(
            level=AlertLevel.INFO,
            title="Worker Started",
            message=f"Bumble70B worker is now online and ready to process jobs.",
            worker_ens=self.worker_ens,
            metadata={
                "Models": ", ".join(models),
                "GPUs": ", ".join(str(g) for g in gpus),
            }
        ))

    async def worker_stopped(self, reason: str = "Graceful shutdown"):
        """Alert: Worker stopped."""
        await self.send_alert(Alert(
            level=AlertLevel.WARNING,
            title="Worker Stopped",
            message=f"Worker has stopped: {reason}",
            worker_ens=self.worker_ens,
        ))

    async def worker_error(self, error: str, job_id: Optional[str] = None):
        """Alert: Worker error."""
        metadata = {}
        if job_id:
            metadata["Job ID"] = job_id

        await self.send_alert(Alert(
            level=AlertLevel.ERROR,
            title="Worker Error",
            message=error,
            worker_ens=self.worker_ens,
            metadata=metadata,
        ))

    async def high_error_rate(self, error_rate: float, window_jobs: int):
        """Alert: High error rate detected."""
        await self.send_alert(Alert(
            level=AlertLevel.CRITICAL,
            title="High Error Rate",
            message=f"Error rate is {error_rate:.1%} over last {window_jobs} jobs.",
            worker_ens=self.worker_ens,
            metadata={
                "Error Rate": f"{error_rate:.1%}",
                "Window": f"{window_jobs} jobs",
            }
        ))

    async def low_confidence_streak(self, streak: int, threshold: int):
        """Alert: Low confidence streak."""
        await self.send_alert(Alert(
            level=AlertLevel.WARNING,
            title="Low Confidence Streak",
            message=f"Last {streak} consecutive jobs had confidence below {threshold}%.",
            worker_ens=self.worker_ens,
            metadata={
                "Streak": streak,
                "Threshold": f"{threshold}%",
            }
        ))

    async def gpu_high_temperature(self, gpu_id: int, temperature: float):
        """Alert: GPU high temperature."""
        await self.send_alert(Alert(
            level=AlertLevel.WARNING,
            title="GPU High Temperature",
            message=f"GPU {gpu_id} is running hot at {temperature:.0f}°C.",
            worker_ens=self.worker_ens,
            metadata={
                "GPU": gpu_id,
                "Temperature": f"{temperature:.0f}°C",
            }
        ))

    async def job_timeout(self, job_id: str, timeout_seconds: int):
        """Alert: Job timeout."""
        await self.send_alert(Alert(
            level=AlertLevel.ERROR,
            title="Job Timeout",
            message=f"Job {job_id} exceeded timeout of {timeout_seconds}s.",
            worker_ens=self.worker_ens,
            metadata={
                "Job ID": job_id,
                "Timeout": f"{timeout_seconds}s",
            }
        ))

    async def queue_backlog(self, model: str, queue_length: int):
        """Alert: Queue backlog."""
        await self.send_alert(Alert(
            level=AlertLevel.WARNING,
            title="Queue Backlog",
            message=f"Model {model} has {queue_length} jobs waiting.",
            worker_ens=self.worker_ens,
            metadata={
                "Model": model,
                "Queue Length": queue_length,
            }
        ))
