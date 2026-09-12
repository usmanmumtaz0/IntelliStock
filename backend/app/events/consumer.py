"""
Event consumer and deterministic rule engine.
Processes inventory events and applies business logic.
"""
import json
import logging
import threading
from typing import Callable, Dict, List
import redis

from app.core.config import settings
from app.models.event import EventType

logger = logging.getLogger(__name__)

INVENTORY_CHANNEL = "inventory.events"


class RuleEngine:
    """Deterministic rule engine for inventory events."""
    
    def __init__(self):
        """Initialize rule engine."""
        self.handlers: Dict[EventType, List[Callable]] = {}
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default business logic rules."""
        # Low stock rule: if quantity < threshold, trigger alert
        self.register(
            EventType.STOCK_UPDATED,
            self._rule_low_stock_check,
        )
        
        # Out of stock rule: if quantity = 0, escalate alert
        self.register(
            EventType.STOCK_UPDATED,
            self._rule_out_of_stock_check,
        )
        
        # Camera offline rule: suppress inventory updates
        self.register(
            EventType.CAMERA_OFFLINE,
            self._rule_camera_offline_mark,
        )
    
    def register(self, event_type: EventType, handler: Callable):
        """Register a handler for an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")
    
    def process_event(self, event: Dict) -> List[Dict]:
        """
        Process an event through registered rules.
        
        Args:
            event: Event payload dict
        
        Returns:
            List of action dicts to execute
        """
        event_type = EventType(event.get("event_type"))
        actions = []
        
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    result = handler(event)
                    if result:
                        actions.extend(result if isinstance(result, list) else [result])
                except Exception as e:
                    logger.error(f"Error in handler for {event_type.value}: {e}")
        
        return actions
    
    def _rule_low_stock_check(self, event: Dict) -> List[Dict] | None:
        """Rule: Check if quantity is below threshold."""
        # This is a placeholder — real implementation would check database
        # For now, just log the check
        state = event.get("new_state", "")
        if "qty=" in state:
            try:
                qty = int(state.split("=")[1])
                if qty < 10:  # Hardcoded threshold for demo
                    logger.warning(f"Low stock detected: {event.get('product_id')} qty={qty}")
                    return [{
                        "type": "alert",
                        "severity": "warning",
                        "message": f"Low stock: product {event.get('product_id')} qty={qty}",
                    }]
            except (ValueError, IndexError):
                pass
        return None
    
    def _rule_out_of_stock_check(self, event: Dict) -> List[Dict] | None:
        """Rule: Check if out of stock."""
        state = event.get("new_state", "")
        if state == "qty=0":
            logger.warning(f"Out of stock: {event.get('product_id')}")
            return [{
                "type": "alert",
                "severity": "critical",
                "message": f"Out of stock: product {event.get('product_id')}",
            }]
        return None
    
    def _rule_camera_offline_mark(self, event: Dict) -> List[Dict] | None:
        """Rule: Mark all zones from this camera as uncertain."""
        logger.warning(f"Camera offline: {event.get('camera_id')}")
        return [{
            "type": "status_update",
            "camera_id": event.get("camera_id"),
            "status": "offline",
            "message": f"Camera {event.get('camera_id')} is offline",
        }]


# Global rule engine instance
rule_engine = RuleEngine()


class EventConsumer:
    """Consumes events from Redis pub/sub and applies rules."""
    
    def __init__(self, rule_engine: RuleEngine):
        """Initialize consumer."""
        self.rule_engine = rule_engine
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        self.running = False
    
    def start(self):
        """Start consuming events in a background thread."""
        if self.running:
            logger.warning("Event consumer already running")
            return
        
        self.running = True
        self.pubsub.subscribe(INVENTORY_CHANNEL)
        
        # Start consumer thread
        thread = threading.Thread(target=self._consume_loop, daemon=True)
        thread.start()
        logger.info("Event consumer started")
    
    def stop(self):
        """Stop consuming events."""
        self.running = False
        self.pubsub.unsubscribe()
        self.pubsub.close()
        logger.info("Event consumer stopped")
    
    def _consume_loop(self):
        """Main event consumption loop."""
        try:
            for message in self.pubsub.listen():
                if not self.running:
                    break
                
                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        actions = self.rule_engine.process_event(event)
                        
                        if actions:
                            logger.debug(f"Event processed, {len(actions)} actions generated")
                            for action in actions:
                                logger.info(f"Action: {action.get('type')} - {action.get('message')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse event: {e}")
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
        except Exception as e:
            logger.error(f"Event consumer error: {e}")
            self.running = False


# Global consumer instance
event_consumer = EventConsumer(rule_engine)
