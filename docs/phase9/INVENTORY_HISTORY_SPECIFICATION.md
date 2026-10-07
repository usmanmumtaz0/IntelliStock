# Inventory History Specification

**Purpose:** Track every meaningful inventory state change for historical analysis, compliance, and audit trail  
**Component:** Backend core capability  
**Priority:** CRITICAL (Phase 9.1)  
**Complexity:** Medium  
**Estimated Effort:** 3 days

---

## Overview

The Inventory History system provides an immutable, append-only record of every inventory quantity change. Unlike the current `Inventory` table (which stores only current state), inventory history preserves the complete record of changes for analytics, debugging, and compliance.

### Current Gap

```
Current: Inventory table stores ONLY current state
─────────────────────────────────────────────────
Zone A / Product X : quantity = 5, confidence = 0.95
(How did it become 5? When? Why? Lost.)

After Phase 9:
─────────────────────────────────────────────────
inventory_history records:
  2026-10-07 14:00 : 10 → 8  (detection)
  2026-10-07 14:05 : 8  → 7  (reconciliation)
  2026-10-07 14:10 : 7  → 5  (reconciliation)
(Full traceability)
```

---

## Functional Requirements

### 1. What Gets Tracked

Every inventory change must record:

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `id` | UUID | Unique record | uuid4() |
| `zone_id` | String | Which shelf zone | "zone-001" |
| `product_id` | String | Which product | "prod-X123" |
| `previous_quantity` | Integer | Quantity before | 10 |
| `new_quantity` | Integer | Quantity after | 8 |
| `quantity_delta` | Integer | Change amount | -2 |
| `change_type` | Enum | Reason for change | "DETECTION" |
| `confidence` | Float | Certainty of change | 0.95 |
| `source_system` | String | Where change originated | "reconciliation" |
| `source_id` | String | Reference ID | "event-123" |
| `related_detection_id` | String | CV detection ID | "det-456" |
| `actor_user_id` | String | Who caused it | "user-001" |
| `actor_system` | String | System component | "reconciliation_engine" |
| `reason` | String | Human-readable why | "Detection in ROI zone-A" |
| `notes` | Text | Additional context | "3 products detected..." |
| `created_at` | Timestamp | When recorded | 2026-10-07 14:05 |
| `processed_at` | Timestamp | When written to DB | 2026-10-07 14:05 |

### 2. Change Types

```
INITIALIZATION       Product first added to zone (initial count)
DETECTION           CV detection observed quantity
RECONCILIATION      Reconciliation engine verified
MANUAL_UPDATE       User manually updated count
RESTOCK             Replenishment event
SALE                Point-of-sale update
ADJUSTMENT          Correction/discrepancy fix
CORRECTION          Admin corrected error
SYSTEM_UPDATE       Automated system adjustment
MIGRATION           Data migration or transfer
```

### 3. Data Retention

```
Active Data:         Last 90 days (hot, queryable)
Archival:            Beyond 90 days (cold storage optional)
Hard Delete:         After 12 months (regulatory, GDPR)
Configuration:       Via environment variable
```

### 4. Immutability

```
✅ Record created → NEVER modified
✅ Record created → NEVER deleted
✅ Append-only design
✅ Historical queries return consistent results
✅ Audit-safe (no modification of past records)
```

---

## Database Schema

### New Table: `inventory_history`

```sql
CREATE TABLE inventory_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Inventory coordinates
    zone_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    
    -- Quantity change
    previous_quantity INTEGER NOT NULL,
    new_quantity INTEGER NOT NULL,
    quantity_delta INTEGER NOT NULL,
    
    -- Change metadata
    change_type VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    
    -- Source tracking
    source_system VARCHAR(50) NOT NULL,  -- "reconciliation", "manual", "cv", etc.
    source_id VARCHAR(255),
    related_detection_id VARCHAR(255),
    related_event_id VARCHAR(255),
    
    -- Actor tracking
    actor_user_id VARCHAR(36),
    actor_system VARCHAR(100),
    
    -- Context
    reason VARCHAR(255),
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (zone_id) REFERENCES shelf_zones(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    
    -- Indexes for common queries
    INDEX idx_zone_product_time (zone_id, product_id, created_at DESC),
    INDEX idx_change_type_time (change_type, created_at DESC),
    INDEX idx_created_time (created_at DESC),
    INDEX idx_source_system (source_system),
    
    -- Partitioning (optional for very large deployments)
    -- PARTITION BY RANGE (YEAR(created_at))
);

-- Index for analytics
CREATE INDEX idx_inventory_history_compound 
ON inventory_history (zone_id, product_id, change_type, created_at DESC);

-- Index for audit queries
CREATE INDEX idx_inventory_history_actor 
ON inventory_history (actor_user_id, created_at DESC);
```

### Retention Policy Configuration

```sql
-- Soft-delete support (optional)
ALTER TABLE inventory_history ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;
CREATE INDEX idx_not_archived ON inventory_history (is_archived) 
WHERE is_archived = FALSE;
```

---

## Service Layer

### `InventoryHistoryService` (New)

```python
class InventoryHistoryService:
    """Manages inventory history tracking and querying."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Recording changes
    def record_detection(
        self,
        zone_id: str,
        product_id: str,
        previous_qty: int,
        detected_qty: int,
        confidence: float,
        detection_id: str
    ) -> InventoryHistory:
        """Record a CV detection."""
        
    def record_reconciliation(
        self,
        zone_id: str,
        product_id: str,
        previous_qty: int,
        reconciled_qty: int,
        event_id: str
    ) -> InventoryHistory:
        """Record reconciliation engine update."""
        
    def record_manual_update(
        self,
        zone_id: str,
        product_id: str,
        previous_qty: int,
        new_qty: int,
        user_id: str,
        reason: str
    ) -> InventoryHistory:
        """Record manual user update."""
        
    def record_restock(
        self,
        zone_id: str,
        product_id: str,
        new_qty: int,
        previous_qty: int,
        actor: str
    ) -> InventoryHistory:
        """Record restock event."""
    
    # Querying
    def get_history_by_zone_product(
        self,
        zone_id: str,
        product_id: str,
        days: int = 30,
        limit: int = 100,
        offset: int = 0
    ) -> List[InventoryHistory]:
        """Get all changes for a zone/product."""
        
    def get_trend_data(
        self,
        zone_id: str,
        product_id: str,
        days: int = 30,
        aggregation: str = "hourly"  # "hourly", "daily", "weekly"
    ) -> List[TrendPoint]:
        """Get aggregated trend data."""
        
    def get_changes_by_type(
        self,
        change_type: str,
        days: int = 30,
        limit: int = 100
    ) -> List[InventoryHistory]:
        """Get all changes of specific type."""
        
    def get_recent_changes(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[InventoryHistory]:
        """Get most recent changes across all products."""
        
    def get_zone_history(
        self,
        zone_id: str,
        days: int = 30
    ) -> List[InventoryHistory]:
        """Get all changes in a zone."""
        
    def get_product_history(
        self,
        product_id: str,
        days: int = 30
    ) -> List[InventoryHistory]:
        """Get all changes for a product across zones."""
        
    # Analytics
    def get_depletion_rate(
        self,
        zone_id: str,
        product_id: str,
        days: int = 30
    ) -> Depletion RateMetric:
        """Calculate how fast inventory decreases."""
        
    def get_stockout_frequency(
        self,
        zone_id: str,
        product_id: str,
        days: int = 30
    ) -> StockoutMetric:
        """How often does product stock out."""
        
    def get_restocking_frequency(
        self,
        zone_id: str,
        product_id: str,
        days: int = 30
    ) -> RestockingMetric:
        """How often is product restocked."""
        
    def archive_old_records(self, days_old: int = 90):
        """Move old records to archive (if implemented)."""
        
    def cleanup_expired_records(self, retention_days: int = 365):
        """Delete records older than retention period."""
```

---

## API Endpoints

### New Inventory History Endpoints

#### 1. Get History for Zone/Product

```
GET /api/v1/inventory/{zone_id}/{product_id}/history
```

**Parameters:**
```
days: int = 30                    # Last N days
limit: int = 50                   # Page size
offset: int = 0                   # Page offset
change_type: str (optional)       # Filter by type
source_system: str (optional)     # Filter by source
```

**Response:**
```json
{
  "data": [
    {
      "id": "hist-001",
      "zone_id": "zone-A",
      "product_id": "prod-X",
      "previous_quantity": 10,
      "new_quantity": 8,
      "quantity_delta": -2,
      "change_type": "DETECTION",
      "confidence": 0.95,
      "source_system": "reconciliation",
      "reason": "Detected reduction in ROI",
      "created_at": "2026-10-07T14:05:00Z"
    },
    ...
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "pages": 3
  }
}
```

#### 2. Get Trend Data

```
GET /api/v1/inventory/{zone_id}/{product_id}/trend
```

**Parameters:**
```
days: int = 30
aggregation: str = "hourly"       # hourly, daily, weekly
```

**Response:**
```json
{
  "product": "Product X",
  "zone": "Zone A",
  "period": "30_days",
  "aggregation": "daily",
  "data": [
    {
      "timestamp": "2026-10-07T00:00:00Z",
      "quantity": 10,
      "changes_count": 3,
      "avg_confidence": 0.92,
      "min_qty": 7,
      "max_qty": 12
    },
    ...
  ]
}
```

#### 3. Get Changes by Type

```
GET /api/v1/inventory/history/by-type/{change_type}
```

**Parameters:**
```
days: int = 30
limit: int = 50
offset: int = 0
zone_id: str (optional)
product_id: str (optional)
```

**Response:** List of InventoryHistory records

#### 4. Get Recent Changes

```
GET /api/v1/inventory/history/recent
```

**Parameters:**
```
limit: int = 50
offset: int = 0
```

**Response:** List of most recent InventoryHistory records

---

## Pydantic Schemas

```python
class InventoryHistoryBase(BaseModel):
    """Base history schema."""
    zone_id: str
    product_id: str
    previous_quantity: int
    new_quantity: int
    change_type: str
    confidence: float = 0.0
    source_system: str
    reason: Optional[str] = None

class InventoryHistoryCreate(InventoryHistoryBase):
    """Create new history record."""
    actor_user_id: Optional[str] = None
    actor_system: Optional[str] = None
    related_detection_id: Optional[str] = None
    related_event_id: Optional[str] = None
    notes: Optional[str] = None

class InventoryHistoryResponse(InventoryHistoryBase):
    """Return history record."""
    id: str
    quantity_delta: int
    created_at: datetime
    processed_at: datetime
    actor_user_id: Optional[str]
    actor_system: Optional[str]
    
    class Config:
        from_attributes = True

class TrendDataPoint(BaseModel):
    """Single point in trend data."""
    timestamp: datetime
    quantity: int
    changes_count: int
    avg_confidence: float
    min_qty: int
    max_qty: int

class TrendResponse(BaseModel):
    """Trend query response."""
    product: str
    zone: str
    period: str
    aggregation: str
    data: List[TrendDataPoint]
```

---

## Integration Points

### ReconciliationEngine

When reconciliation happens, record history:

```python
# Current (Phase 8)
inventory.quantity_estimate = reconciled_qty
db.commit()

# Enhanced (Phase 9)
inventory.quantity_estimate = reconciled_qty
db.commit()

# ADD: Record history
history_service.record_reconciliation(
    zone_id=inventory.zone_id,
    product_id=inventory.product_id,
    previous_qty=old_qty,
    reconciled_qty=reconciled_qty,
    event_id=event.id
)
```

### CV Detection

When detection updates inventory:

```python
history_service.record_detection(
    zone_id=zone.id,
    product_id=product.id,
    previous_qty=current_qty,
    detected_qty=new_qty,
    confidence=detection.confidence,
    detection_id=detection.id
)
```

### Manual Updates

When user updates inventory:

```python
@router.post("/api/v1/inventory/{inventory_id}/update-manual")
def update_inventory_manual(
    inventory_id: str,
    update: InventoryManualUpdate,
    user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inventory = db.query(Inventory).get(inventory_id)
    old_qty = inventory.quantity_estimate
    
    history_service.record_manual_update(
        zone_id=inventory.zone_id,
        product_id=inventory.product_id,
        previous_qty=old_qty,
        new_qty=update.new_quantity,
        user_id=user.user_id,
        reason=update.reason
    )
    
    inventory.quantity_estimate = update.new_quantity
    db.commit()
```

---

## Query Performance Considerations

### Indexes Required

```sql
-- Primary query pattern: zone + product + recent
CREATE INDEX idx_zone_product_time 
ON inventory_history (zone_id, product_id, created_at DESC);

-- Analytics pattern: change type + time
CREATE INDEX idx_change_type_time 
ON inventory_history (change_type, created_at DESC);

-- Audit pattern: actor + time
CREATE INDEX idx_actor_time 
ON inventory_history (actor_user_id, created_at DESC);

-- Date range queries
CREATE INDEX idx_created_time 
ON inventory_history (created_at DESC);
```

### Query Optimization

```python
# ❌ SLOW: Fetch all, filter in Python
records = db.query(InventoryHistory).filter(
    InventoryHistory.zone_id == zone_id,
    InventoryHistory.product_id == product_id
).all()
records = [r for r in records if r.created_at > cutoff]

# ✅ FAST: Filter in database
records = db.query(InventoryHistory).filter(
    InventoryHistory.zone_id == zone_id,
    InventoryHistory.product_id == product_id,
    InventoryHistory.created_at > cutoff
).order_by(InventoryHistory.created_at.desc()).limit(limit).all()
```

### Aggregation Optimization

```python
# Trend data should be pre-aggregated, not computed on query
# Store daily aggregates in separate table or cache

class InventoryHistoryAggregate:
    """Pre-computed daily aggregates for fast trending."""
    zone_id: str
    product_id: str
    date: Date
    avg_quantity: Float
    min_quantity: Integer
    max_quantity: Integer
    changes_count: Integer
```

---

## Testing Requirements

### Unit Tests

```python
def test_record_detection():
    """Test detection recording."""
    
def test_record_reconciliation():
    """Test reconciliation recording."""
    
def test_immutability():
    """Verify records cannot be modified."""
    
def test_date_filtering():
    """Test historical queries with date filters."""
    
def test_aggregation():
    """Test trend data aggregation."""
```

### Integration Tests

```python
def test_history_with_reconciliation():
    """Test history integration with reconciliation engine."""
    
def test_api_endpoints():
    """Test all history APIs."""
```

---

## Rollout Plan

### Phase 9.1a: Database

1. Create `inventory_history` table
2. Add indexes
3. Deploy to staging
4. Verify performance

### Phase 9.1b: Service

1. Implement `InventoryHistoryService`
2. Wire to reconciliation engine
3. Wire to detection handling
4. Unit test coverage

### Phase 9.1c: API

1. Implement REST endpoints
2. Add Pydantic schemas
3. Integration testing
4. API documentation

### Phase 9.1d: Verification

1. Manual testing with real data
2. Performance testing (1M+ records)
3. Retention job verification
4. Production readiness

---

## Success Criteria

✅ All inventory changes recorded (100% capture)  
✅ History queries respond in <200ms  
✅ Retention working (old records deleted)  
✅ Immutability enforced (no modifications)  
✅ API fully documented  
✅ Tests passing (>90% coverage)  
✅ Zero data loss  
✅ Database query plans optimized  

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026  
**Next Document:** ANALYTICS_SPECIFICATION.md

