"""
Notification Agent — Sends alerts and messages to stakeholders.
Formats and routes notifications based on severity and context.
"""
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    DASHBOARD = "dashboard"


class NotificationAgent:
    """
    Formats and routes notifications based on event severity.
    Placeholder for Phase 7 actual delivery implementation.
    """
    
    def notify(self, event_type: str, severity: str, context: dict) -> dict:
        """
        Send a notification about an event.
        
        Args:
            event_type: Type of event (e.g., "low_stock", "camera_offline")
            severity: Severity level (critical, warning, info)
            context: Event context and metadata
        
        Returns:
            dict with notification sent, channels, timestamp
        """
        logger.info(f"Notification Agent handling {event_type} (severity: {severity})")
        
        channels = self._select_channels(severity)
        message = self._format_message(event_type, severity, context)
        
        # Placeholder: actual delivery would go here
        logger.info(f"Would send notification via {channels}: {message['title']}")
        
        return {
            "agent": "notification",
            "event": event_type,
            "severity": severity,
            "channels": channels,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "delivery_status": "queued",  # In Phase 7, actually send
            "confidence": 1.0,
        }
    
    def _select_channels(self, severity: str) -> list:
        """
        Select notification channels based on severity.
        
        Args:
            severity: Event severity level
        
        Returns:
            List of channels to use
        """
        if severity == "critical":
            return [
                NotificationChannel.DASHBOARD,
                NotificationChannel.IN_APP,
                # In Phase 7: add NotificationChannel.EMAIL, NotificationChannel.SMS
            ]
        elif severity == "warning":
            return [
                NotificationChannel.DASHBOARD,
                NotificationChannel.IN_APP,
            ]
        else:  # info
            return [NotificationChannel.DASHBOARD]
    
    def _format_message(self, event_type: str, severity: str, context: dict) -> dict:
        """
        Format a notification message.
        
        Args:
            event_type: Type of event
            severity: Severity level
            context: Event metadata
        
        Returns:
            Formatted message with title, body, action
        """
        zone = context.get("zone", "Unknown")
        product = context.get("product", "Unknown")
        
        templates = {
            "low_stock": {
                "critical": {
                    "title": f"❌ Out of Stock: {product}",
                    "body": f"Product {product} in zone {zone} is out of stock. Restock immediately.",
                    "action": "view_inventory",
                },
                "warning": {
                    "title": f"⚠️ Low Stock: {product}",
                    "body": f"Product {product} in zone {zone} is below threshold. Plan restock.",
                    "action": "view_inventory",
                },
            },
            "camera_offline": {
                "critical": {
                    "title": f"🔴 Camera Offline: {zone}",
                    "body": f"Camera monitoring zone {zone} is offline. Check connection.",
                    "action": "view_cameras",
                },
                "warning": {
                    "title": f"⚠️ Camera Issue: {zone}",
                    "body": f"Camera in zone {zone} frame rate degraded.",
                    "action": "view_cameras",
                },
            },
            "anomaly_detected": {
                "warning": {
                    "title": f"🔍 Anomaly: {product}",
                    "body": f"Unusual pattern detected for {product} in {zone}. Review manually.",
                    "action": "view_alerts",
                },
            },
        }
        
        msg_template = templates.get(event_type, {}).get(severity, {
            "title": f"{event_type.title()} - {severity.title()}",
            "body": f"Event: {event_type} in {zone}",
            "action": "view_dashboard",
        })
        
        return msg_template
