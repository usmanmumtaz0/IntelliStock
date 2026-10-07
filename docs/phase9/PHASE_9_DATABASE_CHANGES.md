# Phase 9: Database Changes

**Purpose:** Document all schema modifications for Phase 9  
**Status:** Specification  

---

## New Tables (3)

### 1. inventory_history

```sql
CREATE TABLE inventory_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    previous_quantity INTEGER NOT NULL,
    new_quantity INTEGER NOT NULL,
    quantity_delta INTEGER NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    source_system VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    related_detection_id VARCHAR(255),
    related_event_id VARCHAR(255),
    actor_user_id VARCHAR(36),
    actor_system VARCHAR(100),
    reason VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (zone_id) REFERENCES shelf_zones(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    
    INDEX idx_zone_product_time (zone_id, product_id, created_at DESC),
    INDEX idx_change_type_time (change_type, created_at DESC),
    INDEX idx_created_time (created_at DESC),
    INDEX idx_source_system (source_system)
);
```

### 2. alert_lifecycle

```sql
CREATE TABLE alert_lifecycle (
    id UUID PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    zone_id VARCHAR(36),
    product_id VARCHAR(36),
    camera_id VARCHAR(36),
    dedup_group_id VARCHAR(255),
    dedup_count INTEGER DEFAULT 1,
    status VARCHAR(20) NOT NULL,
    last_notified_at TIMESTAMP,
    next_notification_time TIMESTAMP,
    notification_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    last_state_change TIMESTAMP,
    escalated BOOLEAN DEFAULT FALSE,
    escalated_at TIMESTAMP,
    acknowledged_by VARCHAR(36),
    acknowledged_at TIMESTAMP,
    resolved_by VARCHAR(36),
    resolved_at TIMESTAMP,
    resolution_reason TEXT,
    title VARCHAR(255),
    description TEXT,
    
    FOREIGN KEY (zone_id) REFERENCES shelf_zones(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (camera_id) REFERENCES cameras(id),
    
    INDEX idx_status_severity (status, severity),
    INDEX idx_created_time (created_at DESC),
    INDEX idx_dedup_group (dedup_group_id),
    INDEX idx_zone_product (zone_id, product_id),
    INDEX idx_needs_notification (status, next_notification_time IS NOT NULL)
);
```

### 3. alert_state_history

```sql
CREATE TABLE alert_state_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL,
    from_status VARCHAR(20),
    to_status VARCHAR(20),
    actor_user_id VARCHAR(36),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (alert_id) REFERENCES alert_lifecycle(id),
    INDEX idx_alert_id (alert_id)
);
```

---

## Table Modifications (2)

### 1. audit_logs (Phase 8 Enhancement)

```sql
ALTER TABLE audit_logs ADD COLUMN (
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    action VARCHAR(50),
    ip_address VARCHAR(45),
    old_values JSONB,
    new_values JSONB,
    status VARCHAR(20),
    error_message TEXT
);

CREATE INDEX idx_audit_action_time ON audit_logs (action, timestamp DESC);
CREATE INDEX idx_audit_user_time ON audit_logs (user_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_logs (resource_type, resource_id);
```

### 2. agent_runs (Phase 8 Enhancement)

```sql
ALTER TABLE agent_runs ADD COLUMN (
    input_data JSON,
    input_zone_id VARCHAR(36),
    input_product_id VARCHAR(36),
    input_confidence FLOAT,
    output_data JSON,
    output_recommendation VARCHAR(255),
    output_confidence FLOAT,
    reasoning_steps JSON,
    reasoning_summary TEXT,
    execution_time_ms INTEGER,
    error_occurred BOOLEAN DEFAULT FALSE,
    error_type VARCHAR(100),
    error_message TEXT,
    error_trace TEXT,
    llm_model VARCHAR(100),
    llm_tokens_input INTEGER,
    llm_tokens_output INTEGER,
    llm_cost_cents DECIMAL(8, 2)
);

CREATE INDEX idx_agent_confidence ON agent_runs (agent_type, output_confidence DESC);
CREATE INDEX idx_failed ON agent_runs (error_occurred, created_at DESC);
CREATE INDEX idx_recommendation ON agent_runs (output_recommendation);
```

---

## Indexes Summary

| Table | Index | Columns | Purpose |
|-------|-------|---------|---------|
| inventory_history | idx_zone_product_time | (zone_id, product_id, created_at DESC) | Query by zone/product |
| inventory_history | idx_change_type_time | (change_type, created_at DESC) | Filter by type |
| inventory_history | idx_created_time | (created_at DESC) | Date range queries |
| alert_lifecycle | idx_status_severity | (status, severity) | Active alerts |
| alert_lifecycle | idx_dedup_group | (dedup_group_id) | Deduplication |
| alert_lifecycle | idx_needs_notification | (status, next_notification_time) | Notification scheduler |
| agent_runs | idx_agent_confidence | (agent_type, output_confidence DESC) | Agent performance |
| agent_runs | idx_failed | (error_occurred, created_at DESC) | Failure analysis |
| audit_logs | idx_audit_action_time | (action, timestamp DESC) | Audit queries |

---

## Migration Strategy

### Step 1: Create new tables
```bash
# Create inventory_history, alert_lifecycle, alert_state_history
# Test on staging first
```

### Step 2: Modify existing tables
```bash
# Add columns to audit_logs, agent_runs
# Backfill existing audit_logs with resource info
```

### Step 3: Update services
```bash
# Wire InventoryHistoryService to reconciliation engine
# Wire AlertLifecycleService to alert generation
# Wire AuditService to endpoints
```

### Step 4: Verify data integrity
```bash
# All new columns nullable (backwards compatible)
# No data loss
# Queries optimized and tested
```

---

## Data Volume Estimates

| Table | Est. Monthly Records | Est. Storage (30 days) |
|-------|---------------------|----------------------|
| inventory_history | 50K | 10 MB |
| alert_lifecycle | 5K | 1 MB |
| alert_state_history | 20K | 2 MB |
| audit_logs (extended) | 30K | 5 MB |
| agent_runs (extended) | 10K | 2 MB |

**Total:** ~20 MB per month (easily manageable)

---

## Retention Configuration

```python
RETENTION_POLICIES = {
    "inventory_history": 90,          # days
    "alert_lifecycle": 365,
    "audit_logs": 365,
    "agent_runs": 90
}

# Cleanup job runs daily
def cleanup_expired_records():
    for table, days in RETENTION_POLICIES.items():
        cutoff = datetime.utcnow() - timedelta(days=days)
        # Soft delete or hard delete based on config
```

---

## Success Criteria

✅ All tables created successfully  
✅ Indexes optimized  
✅ Migration zero-downtime  
✅ Existing data preserved  
✅ Query performance validated  
✅ Retention policies working  

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

