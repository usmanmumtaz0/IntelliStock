"""
Reconciliation Logic Service (INV-002)
Validates observations and reconciles them into trusted inventory state.
Core rule: YOLO output is observation, not truth. Reconciliation engine decides what's real.
"""
import logging
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from app.models.inventory import Inventory, InventoryStatus
from app.models.product import Product
from app.models.camera import Camera
from app.services.observation_window import (
    Observation,
    ObservationWindow,
    get_observation_window,
)

logger = logging.getLogger(__name__)

# Reconciliation thresholds (from CLAUDE.md Section 5.2)
MIN_CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence to trust an observation
MIN_WINDOW_AGREEMENT = 0.5  # 50% of observations must agree on quantity
MIN_CONSECUTIVE_FRAMES = 2  # Must see same quantity in at least 2 consecutive frames


class ReconciliationEngine:
    """
    Reconciliation engine: converts observations to trusted state.
    Implements the rules from architecture Section 5.2.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def reconcile_observation(
        self,
        camera_id: str,
        zone_id: str,
        product_id: str,
        observed_quantity: int,
        confidence: float,
    ) -> Tuple[bool, Optional[str]]:
        """
        Reconcile a single observation.
        
        Args:
            camera_id: Camera UUID
            zone_id: Zone UUID
            product_id: Product UUID
            observed_quantity: YOLO-detected quantity
            confidence: Detection confidence 0.0-1.0
        
        Returns:
            Tuple[accepted: bool, reason: str | None]
        """
        # Step 1: Check confidence threshold
        if confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.debug(
                f"Observation rejected: confidence {confidence} < {MIN_CONFIDENCE_THRESHOLD}"
            )
            return False, f"Low confidence: {confidence:.2f}"
        
        # Step 2: Add to observation window
        obs_window = get_observation_window(camera_id, zone_id, product_id)
        observations = obs_window.add_observation(
            Observation(
                zone_id=zone_id,
                product_id=product_id,
                quantity=observed_quantity,
                confidence=confidence,
                camera_id=camera_id,
            )
        )
        
        # Step 3: Check window size (need at least 2 observations for consensus)
        if len(observations) < MIN_CONSECUTIVE_FRAMES:
            logger.debug(
                f"Window not full: {len(observations)}/{MIN_CONSECUTIVE_FRAMES} observations"
            )
            return False, f"Insufficient observations: {len(observations)}/{MIN_CONSECUTIVE_FRAMES}"
        
        # Step 4: Calculate consensus quantity
        consensus_qty = obs_window.get_quantity_consensus()
        avg_confidence = obs_window.get_average_confidence()
        
        if consensus_qty is None:
            return False, "Failed to calculate consensus"
        
        # Step 5: Check variance tolerance (all observations within tolerance)
        qtys = [o.quantity for o in observations]
        variance = max(qtys) - min(qtys)
        
        if variance > 2:  # Tolerance: ±2 units
            logger.debug(f"High variance rejected: {variance} > 2")
            return False, f"High variance in observations: {variance} units"
        
        # Step 6: Check average confidence sufficient
        if avg_confidence < MIN_CONFIDENCE_THRESHOLD:
            logger.debug(f"Average confidence too low: {avg_confidence:.2f}")
            return False, f"Average confidence too low: {avg_confidence:.2f}"
        
        # ✅ ACCEPTED: Update inventory state
        success = self._update_inventory_state(
            zone_id=zone_id,
            product_id=product_id,
            quantity_estimate=consensus_qty,
            confidence=avg_confidence,
            observations_count=len(observations),
        )
        
        if success:
            logger.info(
                f"Reconciliation ACCEPTED: {zone_id}/{product_id} = {consensus_qty} "
                f"(confidence={avg_confidence:.2f}, variance={variance})"
            )
            return True, f"Consensus: qty={consensus_qty}, conf={avg_confidence:.2f}"
        else:
            return False, "Failed to update inventory state"
    
    def _update_inventory_state(
        self,
        zone_id: str,
        product_id: str,
        quantity_estimate: int,
        confidence: float,
        observations_count: int,
    ) -> bool:
        """Update inventory record with reconciled state."""
        try:
            # Get or create inventory record
            inv = self.db.query(Inventory).filter(
                (Inventory.zone_id == zone_id)
                & (Inventory.product_id == product_id)
            ).first()
            
            if not inv:
                inv = Inventory(
                    zone_id=zone_id,
                    product_id=product_id,
                )
                self.db.add(inv)
            
            # Update state
            prev_qty = inv.quantity_estimate
            inv.quantity_estimate = quantity_estimate
            inv.confidence = confidence
            inv.observations_count = observations_count
            inv.last_observation_time = datetime.utcnow().isoformat()
            
            # Apply state machine logic
            self._apply_state_transition(inv)
            
            self.db.commit()
            
            if prev_qty != quantity_estimate:
                logger.info(
                    f"Inventory updated: {zone_id}/{product_id} "
                    f"{prev_qty} → {quantity_estimate}, status={inv.status.value}"
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to update inventory: {e}")
            self.db.rollback()
            return False
    
    def _apply_state_transition(self, inv: Inventory):
        """Apply state machine logic (from Section 5.3)."""
        prev_status = inv.status
        qty = inv.quantity_estimate
        conf = inv.confidence
        
        # Get product thresholds
        product = self.db.query(Product).filter(
            Product.id == inv.product_id
        ).first()
        
        if not product:
            inv.status = InventoryStatus.UNKNOWN
            return
        
        low_threshold = product.low_stock_threshold
        
        # State machine transitions
        if conf < 0.5:
            inv.status = InventoryStatus.DETECTION_UNCERTAIN
        elif qty == 0:
            inv.status = InventoryStatus.OUT_OF_STOCK
        elif qty <= low_threshold:
            inv.status = InventoryStatus.LOW_STOCK
        else:
            inv.status = InventoryStatus.ADEQUATE
        
        if prev_status != inv.status:
            logger.info(
                f"State transition: {prev_status.value} → {inv.status.value} "
                f"(qty={qty}, conf={conf:.2f})"
            )
