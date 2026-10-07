# Alert Intelligence Specification

**Purpose:** Transform alerts from notifications into managed lifecycle items  
**Component:** Backend alert system  
**Priority:** HIGH (Phase 9.2)  
**Complexity:** Medium  
**Estimated Effort:** 4 days

---

## Overview

Current alert system (Phase 8) generates alerts but doesn't manage them. Phase 9 adds:
- Alert deduplication (prevent spam)
- Lifecycle management (CREATED → ACKNOWLEDGED → RESOLVED)
- Cooldown periods (rate limit alert notifications)
- Escalation (auto-escalate old unresolved alerts)
- History tracking (full audit of alert state changes)

---

## Alert Lifecycle

```
CREATED
   ↓
ACTIVE (user sees it)
   ↓
ACKNOWLEDGED (user marked as seen)
   ↓
RESOLVED (issue fixed)
   ↓
(Can reopen if issue recurs)
```

---

## Database Schema

### New Table: `alert_lifecycle`

```sql
CREATE TABLE alert_lifecycle (
    id UUID PRIMARY KEY,
    
    -- Alert identification
    alert_type VARCHAR(50) NOT NULL,  -- low_stock, camera_offline, anomaly
    severity VARCHAR(20) NOT NULL,    -- critical, warning, info
    
    -- Resource reference
    zone_id VARCHAR(36),
    product_id VARCHAR(36),
    camera_id VARCHAR(36),
    
    -- Deduplication
    dedup_group_id VARCHAR(255),      -- Group for duplicate detection
    dedup_count INTEGER DEFAULT 1,    -- How many duplicates suppressed
    
    -- Lifecycle state
    status VARCHAR(20) NOT NULL,      -- CREATED, ACTIVE, ACKNOWLEDGED, RESOLVED
    
    -- Cooldown
    last_notified_at TIMESTAMP,
    next_notification_time TIMESTAMP,
    notification_count INTEGER DEFAULT 0,
    
    -- Escalation
    created_at TIMESTAMP NOT NULL,
    last_state_change TIMESTAMP,
    escalated BOOLEAN DEFAULT FALSE,
    escalated_at TIMESTAMP,
    
    -- Actor tracking
    acknowledged_by VARCHAR(36),
    acknowledged_at TIMESTAMP,
    resolved_by VARCHAR(36),
    resolved_at TIMESTAMP,
    resolution_reason TEXT,
    
    -- Content
    title VARCHAR(255),
    description TEXT,
    
    -- Foreign keys
    FOREIGN KEY (zone_id) REFERENCES shelf_zones(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (camera_id) REFERENCES cameras(id),
    
    -- Indexes
    INDEX idx_status_severity (status, severity),
    INDEX idx_created_time (created_at DESC),
    INDEX idx_dedup_group (dedup_group_id),
    INDEX idx_zone_product (zone_id, product_id),
    INDEX idx_needs_notification (status, next_notification_time IS NOT NULL)
);

-- Track state changes
CREATE TABLE alert_state_history (
    id UUID PRIMARY KEY,
    alert_id UUID NOT NULL,
    from_status VARCHAR(20),
    to_status VARCHAR(20),
    actor_user_id VARCHAR(36),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (alert_id) REFERENCES alert_lifecycle(id)
);
```

---

## Service Layer

### `AlertLifecycleService` (New)

```python
class AlertLifecycleService:
    """Manage alert lifecycle and deduplication."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Creation
    def create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
        zone_id: Optional[str] = None,
        product_id: Optional[str] = None,
        camera_id: Optional[str] = None
    ) -> Alert:
        """Create new alert with deduplication check."""
        
        # Check for duplicate
        dedup_group = self._get_dedup_group(
            alert_type, severity, zone_id, product_id
        )
        
        # Find existing active alert
        existing = self.db.query(Alert).filter(
            Alert.dedup_group_id == dedup_group,
            Alert.status.in_(["CREATED", "ACTIVE"])
        ).first()
        
        if existing:
            # Increment duplicate count, don't create new
            existing.dedup_count += 1
            self.db.commit()
            return existing
        
        # Create new alert
        alert = Alert(...)
        self.db.add(alert)
        self.db.commit()
        return alert
    
    # Deduplication
    def _get_dedup_group(
        self,
        alert_type: str,
        severity: str,
        zone_id: Optional[str],
        product_id: Optional[str]
    ) -> str:
        """Generate dedup group ID for alert."""
        return hashlib.md5(
            f"{alert_type}:{severity}:{zone_id}:{product_id}".encode()
        ).hexdigest()
    
    # Lifecycle
    def acknowledge_alert(
        self,
        alert_id: str,
        user_id: str
    ) -> Alert:
        """Mark alert as acknowledged."""
        alert = self.db.query(Alert).get(alert_id)
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()
        
        self._record_state_change(
            alert_id, "ACTIVE", "ACKNOWLEDGED", user_id
        )
        self.db.commit()
        return alert
    
    def resolve_alert(
        self,
        alert_id: str,
        user_id: str,
        reason: str
    ) -> Alert:
        """Mark alert as resolved."""
        alert = self.db.query(Alert).get(alert_id)
        alert.status = "RESOLVED"
        alert.resolved_by = user_id
        alert.resolved_at = datetime.utcnow()
        alert.resolution_reason = reason
        
        self._record_state_change(
            alert_id, alert.status, "RESOLVED", user_id, reason
        )
        self.db.commit()
        return alert
    
    def reopen_alert(
        self,
        alert_id: str,
        user_id: str,
        reason: str
    ) -> Alert:
        """Reopen a resolved alert."""
        alert = self.db.query(Alert).get(alert_id)
        alert.status = "ACTIVE"
        alert.resolved_by = None
        alert.resolved_at = None
        
        self._record_state_change(
            alert_id, "RESOLVED", "ACTIVE", user_id, reason
        )
        self.db.commit()
        return alert
    
    # Cooldown
    def apply_cooldown(
        self,
        alert_id: str,
        cooldown_minutes: int = 30
    ):
        """Set next notification time."""
        alert = self.db.query(Alert).get(alert_id)
        alert.last_notified_at = datetime.utcnow()
        alert.next_notification_time = (
            datetime.utcnow() + timedelta(minutes=cooldown_minutes)
        )
        alert.notification_count += 1
        self.db.commit()
    
    # Escalation
    def escalate_old_alerts(
        self,
        hours_old: int = 24
    ) -> int:
        """Auto-escalate unresolved alerts older than threshold."""
        cutoff = datetime.utcnow() - timedelta(hours=hours_old)
        
        alerts = self.db.query(Alert).filter(
            Alert.status.in_(["ACTIVE", "ACKNOWLEDGED"]),
            Alert.created_at < cutoff,
            Alert.escalated == False
        ).all()
        
        count = 0
        for alert in alerts:
            alert.escalated = True
            alert.escalated_at = datetime.utcnow()
            alert.severity = self._escalate_severity(alert.severity)
            count += 1
        
        self.db.commit()
        return count
    
    def _escalate_severity(self, current: str) -> str:
        """Escalate severity level."""
        mapping = {"info": "warning", "warning": "critical"}
        return mapping.get(current, current)
    
    # Querying
    def get_active_alerts(
        self,
        severity: Optional[str] = None
    ) -> List[Alert]:
        """Get all active/unresolved alerts."""
        query = self.db.query(Alert).filter(
            Alert.status.in_(["CREATED", "ACTIVE", "ACKNOWLEDGED"])
        )
        if severity:
            query = query.filter(Alert.severity == severity)
        return query.all()
    
    def get_alert_state_history(
        self,
        alert_id: str
    ) -> List[AlertStateChange]:
        """Get full lifecycle history for alert."""
        return self.db.query(AlertStateHistory).filter(
            AlertStateHistory.alert_id == alert_id
        ).order_by(AlertStateHistory.created_at.desc()).all()
    
    def _record_state_change(
        self,
        alert_id: str,
        from_status: str,
        to_status: str,
        user_id: str,
        reason: Optional[str] = None
    ):
        """Record state transition."""
        change = AlertStateHistory(
            alert_id=alert_id,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=user_id,
            reason=reason
        )
        self.db.add(change)
```

---

## API Endpoints

### Alert Lifecycle Endpoints

```
GET  /api/v1/alerts                              # List all alerts
GET  /api/v1/alerts/{alert_id}                   # Get single alert
POST /api/v1/alerts/{alert_id}/acknowledge       # Mark acknowledged
POST /api/v1/alerts/{alert_id}/resolve           # Mark resolved
POST /api/v1/alerts/{alert_id}/reopen            # Reopen resolved
GET  /api/v1/alerts/{alert_id}/history           # Lifecycle history
```

### Example Request: Acknowledge Alert

```
POST /api/v1/alerts/alert-123/acknowledge
Content-Type: application/json

{
  "reason": "Already addressing this issue"
}

Response 200:
{
  "id": "alert-123",
  "status": "ACKNOWLEDGED",
  "acknowledged_by": "user-001",
  "acknowledged_at": "2026-10-07T14:05:00Z"
}
```

### Example Request: Resolve Alert

```
POST /api/v1/alerts/alert-123/resolve
Content-Type: application/json

{
  "reason": "Issue fixed - restocked product"
}

Response 200:
{
  "id": "alert-123",
  "status": "RESOLVED",
  "resolved_by": "user-001",
  "resolved_at": "2026-10-07T14:15:00Z"
}
```

---

## Deduplication Logic

### How it Works

1. **On alert creation:**
   - Generate dedup group from: type + severity + zone + product
   - Check if active alert exists in that group
   - If yes: increment `dedup_count`, don't create new
   - If no: create new alert

2. **Example:**
   ```
   Low stock alert for Zone A / Product X
   
   First detection: Create alert (dedup_count = 1)
   Second detection (1 min later): Same group → dedup_count = 2
   Third detection (2 min later): Same group → dedup_count = 3
   
   User sees ONE alert: "Low stock - Product X (3 occurrences)"
   ```

### Threshold Configuration

```python
# Alert dedup rules
DEDUP_RULES = {
    "low_stock": {
        "group_by": ["zone_id", "product_id", "severity"],
        "merge_within_minutes": 60,
        "max_duplicates_before_escalate": 10
    },
    "camera_offline": {
        "group_by": ["camera_id"],
        "merge_within_minutes": 30,
        "max_duplicates": float("inf")
    },
    "anomaly": {
        "group_by": ["zone_id", "product_id"],
        "merge_within_minutes": 120,
        "max_duplicates": 5
    }
}
```

---

## Cooldown Strategy

```python
# Cooldown periods
COOLDOWN_PERIODS = {
    "low_stock": {"critical": 5, "warning": 30, "info": 60},
    "camera_offline": {"critical": 1, "warning": 10},
    "anomaly": {"critical": 10, "warning": 60}
}

# Don't spam user with same alert
# After notifying, set next_notification_time
```

---

## Escalation Rules

```python
ESCALATION_RULES = {
    "created_to_active": "immediately",
    "auto_escalate_hours": 24,
    "escalate_severity": {"info": "warning", "warning": "critical"},
    "max_escalations": 3
}

# Example:
# Created: 2026-10-06 14:00 (severity: warning)
# Still unresolved after 24h: Auto-escalate to critical
# Still unresolved after 48h: Re-escalate (severity stays critical)
```

---

## Pydantic Schemas

```python
class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    status: str  # CREATED, ACTIVE, ACKNOWLEDGED, RESOLVED
    title: str
    description: str
    zone_id: Optional[str]
    product_id: Optional[str]
    dedup_count: int
    escalated: bool
    created_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]

class AlertStateChangeResponse(BaseModel):
    from_status: str
    to_status: str
    actor_user_id: str
    reason: Optional[str]
    created_at: datetime

class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    active_count: int
    critical_count: int
    acknowledged_count: int
    resolved_count: int
```

---

## Testing

```python
def test_deduplication():
    """Duplicate alerts don't create new records."""

def test_lifecycle_transitions():
    """Verify valid state transitions."""

def test_escalation():
    """Alerts escalate after threshold time."""

def test_cooldown():
    """Notification cooldown working."""

def test_reopen():
    """Can reopen resolved alerts."""
```

---

## Success Criteria

✅ Deduplication >95% effective  
✅ No duplicate alert spam  
✅ Lifecycle transitions working  
✅ Escalation automatic and correct  
✅ Cooldown preventing notification spam  
✅ API fully documented  
✅ >90% test coverage  

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

