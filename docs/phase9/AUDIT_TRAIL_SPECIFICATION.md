# Audit Trail Specification

**Purpose:** Complete application-level audit logging for compliance and accountability  
**Component:** Backend audit system  
**Priority:** HIGH (Phase 9.3)  
**Complexity:** Low  
**Estimated Effort:** 2 days

---

## Overview

Phase 8 created `AuditLog` model for security events. Phase 9 extends to all application events: inventory updates, alerts, settings changes.

---

## What Gets Audited

```
LOGIN                 User authentication
LOGOUT                User session termination
INVENTORY_UPDATE      Quantity change
ALERT_ACKNOWLEDGED    Alert status change
ALERT_RESOLVED        Alert resolution
SETTING_CHANGED       Configuration update
ADMIN_ACTION          Admin operations
RESTOCK_RECORDED      Restock event
CAMERA_UPDATE         Camera configuration
ZONE_UPDATE           Zone configuration
```

---

## Database Schema

Existing `audit_logs` table (Phase 8) supports this. Just ensure:

```sql
ALTER TABLE audit_logs ADD COLUMN (
    resource_type VARCHAR(50),       -- product, inventory, alert, etc.
    resource_id VARCHAR(255),
    action VARCHAR(50),
    user_id VARCHAR(36),
    ip_address VARCHAR(45),
    old_values JSONB,
    new_values JSONB,
    status VARCHAR(20),              -- success, failure
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_action_time 
ON audit_logs (action, timestamp DESC);

CREATE INDEX idx_audit_user_time 
ON audit_logs (user_id, timestamp DESC);

CREATE INDEX idx_audit_resource 
ON audit_logs (resource_type, resource_id);
```

---

## Service Layer

### `AuditService` (Enhancement)

```python
class AuditService:
    """Application-level audit logging."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        ip_address: str,
        old_values: dict = None,
        new_values: dict = None,
        success: bool = True,
        error_message: str = None
    ) -> AuditLog:
        """Log application event."""
        
        audit = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address=ip_address,
            old_values=old_values,
            new_values=new_values,
            status="success" if success else "failure",
            error_message=error_message
        )
        self.db.add(audit)
        self.db.commit()
        return audit
    
    # Common logging methods
    def log_inventory_update(
        self,
        inventory_id: str,
        previous_qty: int,
        new_qty: int,
        user_id: str,
        ip_address: str
    ):
        """Log inventory change."""
        self.log_event(
            action="INVENTORY_UPDATE",
            resource_type="inventory",
            resource_id=inventory_id,
            user_id=user_id,
            ip_address=ip_address,
            old_values={"quantity": previous_qty},
            new_values={"quantity": new_qty}
        )
    
    def log_alert_acknowledged(
        self,
        alert_id: str,
        user_id: str,
        ip_address: str
    ):
        """Log alert acknowledgment."""
        self.log_event(
            action="ALERT_ACKNOWLEDGED",
            resource_type="alert",
            resource_id=alert_id,
            user_id=user_id,
            ip_address=ip_address,
            old_values={"status": "active"},
            new_values={"status": "acknowledged"}
        )
    
    def log_login(self, user_id: str, ip_address: str):
        """Log user login."""
        self.log_event(
            action="LOGIN",
            resource_type="user",
            resource_id=user_id,
            user_id=user_id,
            ip_address=ip_address
        )
    
    # Querying
    def get_audit_trail(
        self,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[str] = None,
        days: int = 30,
        limit: int = 100
    ) -> List[AuditLog]:
        """Query audit logs."""
        query = self.db.query(AuditLog).filter(
            AuditLog.timestamp > datetime.utcnow() - timedelta(days=days)
        )
        
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
```

---

## Integration Points

### Inventory Update

```python
@router.post("/api/v1/inventory/{inventory_id}/update-manual")
async def update_inventory(
    inventory_id: str,
    update: InventoryUpdate,
    user: TokenData = Depends(get_current_user),
    request: Request,
    db: Session = Depends(get_db)
):
    inventory = db.query(Inventory).get(inventory_id)
    old_qty = inventory.quantity_estimate
    
    # Update
    inventory.quantity_estimate = update.new_quantity
    db.commit()
    
    # Audit
    audit_service.log_inventory_update(
        inventory_id=inventory_id,
        previous_qty=old_qty,
        new_qty=update.new_quantity,
        user_id=user.user_id,
        ip_address=request.client.host
    )
    
    return {"success": True}
```

---

## API Endpoints

```
GET /api/v1/audit/logs                    # Query audit trail
GET /api/v1/audit/logs/user/{user_id}     # User activity
GET /api/v1/audit/logs/resource/{resource_type}/{resource_id}  # Resource changes
```

---

## Retention

- Keep audit logs for 12 months
- Archive after 90 days to cold storage
- Retention policy configurable

---

## Success Criteria

✅ All application events logged  
✅ Non-repudiation enforced  
✅ Query performance fast  
✅ Retention working  
✅ API documented  

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

