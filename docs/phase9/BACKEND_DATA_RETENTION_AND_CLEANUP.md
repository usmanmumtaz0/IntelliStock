# Backend Data Retention and Cleanup

**Purpose:** Data lifecycle governance and retention policies  
**Component:** Backend data management  
**Priority:** MEDIUM (Phase 9.4)  
**Complexity:** Low  
**Estimated Effort:** 2 days

---

## Retention Policies

### By Data Type

| Data Type | Retention | Archive | Hard Delete |
|-----------|-----------|---------|------------|
| Inventory History | 90 days | Optional | 180 days |
| Alerts | 365 days | N/A | 365+ days |
| Audit Logs | 365 days | Yes | 18+ months |
| Agent Runs | 90 days | N/A | 180 days |
| Events | 30 days | N/A | 60 days |

---

## Configuration

```python
# In config.py
RETENTION_POLICIES = {
    "inventory_history": 90,      # days
    "alerts": 365,
    "audit_logs": 365,
    "agent_runs": 90,
    "events": 30,
}

ARCHIVE_ENABLED = True
ARCHIVE_AFTER_DAYS = 90
HARD_DELETE_AFTER_DAYS = 180
```

---

## Cleanup Job

```python
# In jobs/cleanup_job.py

@scheduler.scheduled_job('cron', hour=3, minute=0)  # 3 AM daily
def daily_cleanup():
    """Run data cleanup job."""
    
    # Soft-delete old records
    for table_name, retention_days in RETENTION_POLICIES.items():
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        # Archive old records
        if ARCHIVE_ENABLED and table_name in ARCHIVABLE_TABLES:
            archive_old_records(table_name, cutoff)
        
        # Hard-delete very old records
        hard_cutoff = cutoff - timedelta(days=HARD_DELETE_AFTER_DAYS)
        hard_delete_records(table_name, hard_cutoff)
    
    log_cleanup_job()
```

---

## Archival Strategy

```python
def archive_old_records(table_name, cutoff):
    """Archive records older than cutoff."""
    
    if table_name == "inventory_history":
        records = db.query(InventoryHistory)\
            .filter(InventoryHistory.created_at < cutoff)\
            .all()
        
        # Option 1: Copy to archive table
        for record in records:
            archive_table.insert(record)
        
        # Option 2: Export to S3/cold storage
        export_to_s3(records, f"archive/inventory_history/{cutoff.year}/{cutoff.month}")
        
        # Mark as archived
        for record in records:
            record.is_archived = True
        db.commit()
```

---

## Soft Delete Pattern

```python
# Add to tables
ALTER TABLE inventory_history ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;

# When querying, exclude archived
db.query(InventoryHistory)\
    .filter(InventoryHistory.is_archived == False)\
    .all()

# To delete: Mark as archived
record.is_archived = True
db.commit()

# Never hard-delete, allows recovery if needed
```

---

## Hard Delete Strategy

```python
def hard_delete_records(table_name, cutoff):
    """Permanently delete records older than cutoff."""
    
    if table_name == "inventory_history":
        db.query(InventoryHistory)\
            .filter(InventoryHistory.created_at < cutoff)\
            .delete(synchronize_session=False)
        db.commit()
        log_event(f"Hard deleted old {table_name} records")
```

---

## Retention Rationale

### Inventory History (90 days)

```
Why 90 days?
- Covers typical business cycles
- Annual trends not needed (use aggregate table)
- Storage efficient (~10 MB/month)
- Still supports 3-month rolling analysis
```

### Audit Logs (365 days)

```
Why 1 year?
- Compliance requirement
- Legal holds often 12 months
- Storage manageable (<5 MB/month)
```

### Alerts (365 days)

```
Why 1 year?
- Historical alert context
- Pattern analysis over year
```

---

## Privacy Compliance (GDPR)

```python
def delete_user_data(user_id):
    """GDPR right-to-be-forgotten."""
    
    # Anonymize or delete user references
    db.query(AuditLog)\
        .filter(AuditLog.user_id == user_id)\
        .delete()
    
    db.query(AlertStateHistory)\
        .filter(AlertStateHistory.actor_user_id == user_id)\
        .delete()
    
    db.commit()
    log_event(f"Deleted user data for {user_id}")
```

---

## Monitoring

```python
def monitor_storage():
    """Check storage usage."""
    
    # Get table sizes
    table_sizes = get_table_sizes()
    
    # Alert if growing too fast
    if table_sizes['inventory_history'] > 1000:  # MB
        alert("Inventory history table >1GB")
    
    # Report to monitoring system
    send_metric("database.inventory_history_mb", table_sizes['inventory_history'])
```

---

## Backup Strategy

```
Daily Backups:
- Full backup: Weekly
- Incremental: Daily
- Retention: 30 days

Before any cleanup: Full backup taken
After any hard-delete: Verify backup exists
```

---

## Success Criteria

✅ Retention policies active  
✅ Cleanup job runs daily  
✅ Storage remains manageable  
✅ Recovery possible (backups verified)  
✅ GDPR compliant  

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

