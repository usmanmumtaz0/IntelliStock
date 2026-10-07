# Phase 9: Implementation Order

**Purpose:** Step-by-step implementation sequence with clear dependencies  
**Duration:** 4 weeks  
**Resource:** 1-2 backend engineers  

---

## Week 1: Foundation

### Day 1: Database Schema

**Tasks:**
1. Design final schema (inventory_history, alert_lifecycle, audit_logs enhancements)
2. Create migration scripts
3. Deploy to staging PostgreSQL
4. Create indexes
5. Verify performance with test data

**Deliverable:** Production-ready database schema

**Verification:**
```bash
psql -h localhost -U postgres -d intellistock
SELECT count(*) FROM inventory_history;  # Should exist
```

### Days 2-3: Inventory History Model & Service

**Tasks:**
1. Create SQLAlchemy model for inventory_history
2. Implement InventoryHistoryService with all query methods
3. Unit tests (10+ tests)
4. Integration tests with ReconciliationEngine

**Files:**
- `backend/app/models/inventory_history.py` (NEW)
- `backend/app/services/inventory_history_service.py` (NEW)
- `backend/tests/test_inventory_history.py` (NEW)

**Verification:**
```bash
pytest backend/tests/test_inventory_history.py -v
```

### Days 4-5: Inventory History API

**Tasks:**
1. Implement REST endpoints (GET history, GET trends, etc.)
2. Pydantic schemas
3. Integrate with reconciliation engine (log changes)
4. API documentation

**Files:**
- Add endpoints to `backend/app/api/inventory.py`
- Pydantic schemas in `backend/app/schemas/inventory.py`

**Verification:**
```bash
curl http://localhost:8000/api/v1/inventory/zone-A/prod-X/history
# Should return historical records
```

**Deliverable:** Full inventory history working end-to-end

---

## Week 2: Intelligence

### Day 6: Alert Lifecycle Model & Service

**Tasks:**
1. Create alert_lifecycle table migration
2. Create SQLAlchemy model
3. Implement AlertLifecycleService with deduplication
4. Implement cooldown and escalation logic
5. Unit tests (15+ tests)

**Files:**
- `backend/app/models/alert_lifecycle.py` (NEW)
- `backend/app/services/alert_lifecycle_service.py` (NEW)

**Verification:**
```bash
pytest backend/tests/test_alert_lifecycle.py -v
```

### Day 7: Alert Lifecycle API

**Tasks:**
1. Implement lifecycle endpoints (acknowledge, resolve, reopen)
2. Deduplication logic in alert creation
3. Cooldown period enforcement
4. Auto-escalation job

**Files:**
- Enhance `backend/app/api/alerts.py`

**Deliverable:** Alerts with full lifecycle management

### Days 8-9: Analytics Service & API

**Tasks:**
1. Implement AnalyticsService (trends, depletion, stockouts, product perf, zone perf)
2. Implement 8 analytics endpoints
3. Add caching (Redis) for analytics results
4. Performance testing

**Files:**
- `backend/app/services/analytics_service.py` (NEW)
- Add endpoints to `backend/app/api/analytics.py` (NEW)

**Verification:**
```bash
curl http://localhost:8000/api/v1/analytics/inventory/trends
curl http://localhost:8000/api/v1/analytics/products/performance
# All should return <500ms
```

**Deliverable:** Full analytics platform operational

---

## Week 3: Observability

### Day 10: Agent Execution Enhancement

**Tasks:**
1. Enhance agent_runs table with tracing columns
2. Enhance AgentTelemetryService
3. Integrate with all 4 agents (supervisor, insight, anomaly, notification)
4. Unit and integration tests

**Files:**
- Enhance `backend/app/services/agent_telemetry.py`
- Update all agent files to record execution details

**Verification:**
```bash
curl http://localhost:8000/api/v1/agents/insight_agent/stats
# Should show execution stats with confidence, time, etc.
```

### Days 11-12: Audit Trail Enhancement

**Tasks:**
1. Extend AuditService to cover application events
2. Wire audit logging to: login, inventory updates, alerts, settings
3. Verify non-repudiation (no modification of old records)
4. Query endpoints

**Files:**
- Enhance `backend/app/core/audit.py`
- Wire logging to endpoints

**Deliverable:** Complete application audit trail

### Days 13-14: System Health Enhancement

**Tasks:**
1. Enhance health check endpoints
2. Add component-level health (database, agents, comms)
3. Add structured responses
4. Liveness and readiness probes

**Files:**
- Enhance `backend/app/core/health.py`

**Verification:**
```bash
curl http://localhost:8000/api/v1/health/detailed
# Should show all components
```

**Deliverable:** Enhanced system observability

---

## Week 4: Polish & Integration

### Day 15: Performance Optimization

**Tasks:**
1. Query profiling and optimization
2. Index verification
3. N+1 query prevention
4. Pagination implementation
5. Load testing (10x MVP volume)

**Deliverable:** Production-optimized queries

### Day 16: Data Retention & Cleanup

**Tasks:**
1. Implement retention policies
2. Cleanup job (runs daily)
3. Soft-delete support
4. Archiving strategy

**Files:**
- `backend/app/jobs/cleanup_job.py` (NEW)

**Deliverable:** Data governance implemented

### Days 17-18: Comprehensive Testing

**Tasks:**
1. Unit test all new services (>90% coverage)
2. Integration tests across components
3. API contract tests
4. Performance tests
5. Security tests (auth, validation, etc.)

**Verification:**
```bash
pytest backend/tests/ -v --cov
# Should show >90% coverage on new code
```

**Deliverable:** Comprehensive test suite passing

### Day 19: Frontend Integration

**Tasks:**
1. API documentation update (OpenAPI/Swagger)
2. Provide frontend requirements document
3. Example requests and responses
4. Integration support for frontend team

**Files:**
- Update API reference docs

**Deliverable:** Frontend team can build against APIs

### Day 20: Buffer & Final Verification

**Tasks:**
1. Address any issues from Week 3-4
2. Final integration testing
3. Production readiness checklist
4. Documentation finalization

**Deliverable:** Production-ready Phase 9

---

## Implementation Checklist

### Week 1
- [ ] Database schema finalized
- [ ] Inventory history table created
- [ ] InventoryHistoryService implemented
- [ ] Inventory history API working
- [ ] Tests passing (>90% coverage)

### Week 2
- [ ] Alert lifecycle implemented
- [ ] Deduplication working
- [ ] Analytics service completed
- [ ] All 8 analytics endpoints operational
- [ ] Cache strategy implemented

### Week 3
- [ ] Agent execution tracing added
- [ ] Audit trail enhanced
- [ ] System health upgraded
- [ ] All tests passing
- [ ] Performance baseline established

### Week 4
- [ ] Queries optimized
- [ ] Retention policies active
- [ ] Load testing passed (10x)
- [ ] Full test coverage (>90%)
- [ ] Frontend integration ready
- [ ] All documentation updated

---

## Dependencies Between Features

```
┌─────────────────────────────────┐
│ 1. Database Schema              │ (Foundation)
└──────────────┬──────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
  ┌──────────┐  ┌─────────────────┐
  │ Inventory│  │Alert Lifecycle  │
  │ History  │  │Deduplication    │
  └────┬─────┘  └────┬────────────┘
       │             │
       └─────┬───────┘
             ▼
      ┌──────────────┐
      │ Analytics    │
      │ (uses both)  │
      └──────────────┘
             │
        ┌────┼────┐
        ▼    ▼    ▼
      Agent Audit System
      Tracing Trail Health
```

---

## Resource Allocation

**Backend Engineer 1:**
- Week 1: Database, Inventory History
- Week 2: Analytics
- Week 3-4: Testing, optimization

**Backend Engineer 2 (if available):**
- Week 2: Alert Lifecycle (parallel with Eng1 on Analytics)
- Week 3: Agent Tracing, Audit Trail (parallel)
- Week 4: Testing, frontend integration

**Database Architect:**
- Day 1: Schema review
- Week 1: Migration strategy
- Week 4: Performance verification

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Database migration fails | Rollback plan, test on staging first |
| Analytics queries slow | Early performance profiling and caching |
| Breaking existing APIs | Only add new endpoints, don't modify existing |
| Scope creep | Stick to documented spec, no new features |
| Testing falls behind | Automated tests throughout, not at end |

---

## Success Criteria (Daily)

- Code compiles without errors
- Tests passing (new + existing)
- No regression on existing APIs
- Documentation updated
- Changes reviewed and committed

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

