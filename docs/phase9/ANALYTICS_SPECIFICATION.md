# Analytics Specification

**Purpose:** Extract business intelligence from inventory and system data  
**Component:** Backend analytics layer  
**Priority:** HIGH (Phase 9.2)  
**Complexity:** Medium  
**Estimated Effort:** 5 days

---

## Overview

Phase 9 Analytics provides real-time insights into inventory performance, product movement, zone efficiency, and system health through dedicated API endpoints. Data is sourced from `inventory_history`, current `inventory` state, `events`, and `alerts`.

---

## Analytics Categories

### 1. Inventory Trends

```
GET /api/v1/analytics/inventory/trends
```

**Purpose:** Show quantity trends over time  
**Query Parameters:**
- `zone_id` (optional)
- `product_id` (optional)
- `days` (default: 30)
- `aggregation` (hourly|daily|weekly)

**Response:**
```json
{
  "period": "30_days",
  "zone": "Zone A",
  "product": "Product X",
  "aggregation": "daily",
  "data": [
    {
      "date": "2026-10-07",
      "avg_quantity": 8.5,
      "min_quantity": 7,
      "max_quantity": 10,
      "changes": 3,
      "confidence": 0.94
    }
  ],
  "summary": {
    "avg_quantity": 8.3,
    "depletion_rate_per_day": 0.5,
    "restocking_frequency": "every 3 days",
    "trend": "declining"
  }
}
```

**Database Query:**
```sql
SELECT 
  DATE(created_at) as date,
  AVG(new_quantity) as avg_quantity,
  MIN(new_quantity) as min_quantity,
  MAX(new_quantity) as max_quantity,
  COUNT(*) as changes,
  AVG(confidence) as confidence
FROM inventory_history
WHERE zone_id = ? AND product_id = ?
  AND created_at > DATE_SUB(NOW(), INTERVAL ? DAY)
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### 2. Depletion Analysis

```
GET /api/v1/analytics/inventory/depletion
```

**Purpose:** Identify fast-moving products  
**Query Parameters:**
- `zone_id` (optional)
- `days` (default: 30)
- `threshold` (minimum changes to consider)

**Response:**
```json
{
  "period": "30_days",
  "analysis": [
    {
      "zone": "Zone A",
      "product": "Product X",
      "depletion_rate": 0.5,  // units per day
      "unit": "per_day",
      "total_depleted": 15,
      "events": 30,
      "trend": "stable|increasing|decreasing",
      "next_stockout_eta": "2026-10-15T08:00:00Z"
    }
  ],
  "highest_depletion": "Product X",
  "total_depleted_all": 450
}
```

### 3. Stockout Analysis

```
GET /api/v1/analytics/inventory/stockouts
```

**Purpose:** Identify and predict stockouts  
**Query Parameters:**
- `days` (default: 30)
- `threshold` (qty ≤ threshold = stockout)

**Response:**
```json
{
  "period": "30_days",
  "threshold": 2,
  "stockouts": [
    {
      "zone": "Zone A",
      "product": "Product X",
      "stockout_date": "2026-10-06",
      "duration_hours": 4,
      "frequency": "2x in past 30 days",
      "severity": "high",
      "impact": "likely_lost_sales"
    }
  ],
  "total_stockout_hours": 48,
  "most_at_risk": "Product X (Zone A)"
}
```

### 4. Product Performance

```
GET /api/v1/analytics/products/performance
```

**Purpose:** Rank products by movement and performance  
**Query Parameters:**
- `days` (default: 30)
- `sort_by` (depletion|frequency|volatility)
- `limit` (top N products)

**Response:**
```json
{
  "period": "30_days",
  "products": [
    {
      "id": "prod-001",
      "sku": "X-123",
      "name": "Product X",
      "total_movements": 150,
      "avg_quantity_across_zones": 8.2,
      "total_depleted": 30,
      "depletion_rate": 1.0,  // per day
      "volatility": "low",
      "confidence_avg": 0.94,
      "stockouts": 2,
      "zones_selling": 5,
      "trend": "high_velocity"
    }
  ],
  "summary": {
    "fastest_mover": "Product X",
    "most_stable": "Product Y",
    "highest_volatility": "Product Z"
  }
}
```

### 5. Zone Performance

```
GET /api/v1/analytics/zones/performance
```

**Purpose:** Evaluate zone efficiency and activity  
**Query Parameters:**
- `days` (default: 30)
- `sort_by` (activity|stability)

**Response:**
```json
{
  "period": "30_days",
  "zones": [
    {
      "id": "zone-001",
      "name": "Zone A",
      "products_count": 20,
      "total_changes": 350,
      "avg_confidence": 0.93,
      "stockout_incidents": 3,
      "activity_level": "high",
      "health": "healthy",
      "most_volatile_product": "Product X",
      "detection_accuracy": 0.95
    }
  ],
  "summary": {
    "most_active_zone": "Zone A",
    "most_reliable_zone": "Zone C",
    "average_confidence": 0.92
  }
}
```

### 6. Alert Analytics

```
GET /api/v1/analytics/alerts/summary
```

**Purpose:** Alert statistics and patterns  
**Query Parameters:**
- `days` (default: 30)
- `severity` (optional filter)

**Response:**
```json
{
  "period": "30_days",
  "total_alerts": 145,
  "by_severity": {
    "critical": 12,
    "warning": 85,
    "info": 48
  },
  "by_type": {
    "low_stock": 95,
    "camera_offline": 28,
    "anomaly": 15,
    "other": 7
  },
  "avg_resolution_time_hours": 2.5,
  "unresolved_count": 12,
  "most_frequent_zone": "Zone A",
  "most_frequent_product": "Product X",
  "trends": {
    "increasing|stable|decreasing": "stable"
  }
}
```

### 7. System Performance

```
GET /api/v1/analytics/system/performance
```

**Purpose:** System health and efficiency metrics  
**Query Parameters:**
- `days` (default: 7)

**Response:**
```json
{
  "period": "7_days",
  "metrics": {
    "total_events_processed": 50000,
    "avg_event_latency_ms": 125,
    "detection_accuracy": 0.94,
    "reconciliation_success_rate": 0.98,
    "api_availability": 0.9995,
    "camera_uptime": 0.9987
  },
  "ai_agents": {
    "supervisor": {
      "executions": 1200,
      "avg_duration_ms": 45,
      "success_rate": 0.99
    },
    "insight": {
      "executions": 800,
      "avg_duration_ms": 120,
      "success_rate": 0.97
    },
    "anomaly": {
      "executions": 1000,
      "avg_duration_ms": 90,
      "success_rate": 0.96
    }
  },
  "database": {
    "query_avg_ms": 25,
    "slow_query_count": 3,
    "connections_avg": 15
  }
}
```

### 8. Comparison Analytics

```
GET /api/v1/analytics/compare
```

**Purpose:** Compare performance between periods or regions  
**Query Parameters:**
- `compare_type` (zone|product|period)
- `dimension1_id`
- `dimension2_id`
- `metric` (depletion|activity|accuracy)

**Response:**
```json
{
  "comparison": {
    "type": "zone",
    "dimension1": {
      "id": "zone-001",
      "name": "Zone A",
      "metric_value": 0.8
    },
    "dimension2": {
      "id": "zone-002",
      "name": "Zone B",
      "metric_value": 0.6
    },
    "difference": 0.2,
    "difference_percent": 33,
    "dimension1_winning": true
  }
}
```

---

## Service Layer

### `AnalyticsService` (New)

```python
class AnalyticsService:
    """Analytics calculations and aggregations."""
    
    def __init__(self, db: Session, history_service: InventoryHistoryService):
        self.db = db
        self.history_service = history_service
    
    # Trends
    def get_inventory_trends(
        self,
        zone_id: Optional[str] = None,
        product_id: Optional[str] = None,
        days: int = 30,
        aggregation: str = "daily"
    ) -> TrendResponse:
        """Get inventory quantity trends."""
    
    # Depletion
    def get_depletion_analysis(
        self,
        zone_id: Optional[str] = None,
        days: int = 30
    ) -> DepletionAnalysisResponse:
        """Analyze product depletion rates."""
    
    def calculate_depletion_rate(
        self,
        zone_id: str,
        product_id: str,
        days: int = 30
    ) -> float:
        """Calculate units depleted per day."""
    
    # Stockouts
    def get_stockout_analysis(
        self,
        days: int = 30,
        threshold: int = 2
    ) -> StockoutAnalysisResponse:
        """Analyze stockout incidents."""
    
    def predict_next_stockout(
        self,
        zone_id: str,
        product_id: str
    ) -> Optional[datetime]:
        """Predict when stockout will occur."""
    
    # Products
    def get_product_performance(
        self,
        days: int = 30,
        sort_by: str = "depletion",
        limit: int = 20
    ) -> ProductPerformanceResponse:
        """Rank products by performance."""
    
    # Zones
    def get_zone_performance(
        self,
        days: int = 30,
        sort_by: str = "activity"
    ) -> ZonePerformanceResponse:
        """Evaluate zone efficiency."""
    
    # Alerts
    def get_alert_analytics(
        self,
        days: int = 30
    ) -> AlertAnalyticsResponse:
        """Alert statistics and trends."""
    
    # System
    def get_system_performance(
        self,
        days: int = 7
    ) -> SystemPerformanceResponse:
        """System health and efficiency."""
    
    # Comparison
    def compare_analytics(
        self,
        compare_type: str,  # "zone", "product", "period"
        dimension1_id: str,
        dimension2_id: str,
        metric: str
    ) -> ComparisonResponse:
        """Compare two dimensions."""
```

---

## API Endpoints

All analytics endpoints:

| Endpoint | Method | Purpose | Cache |
|----------|--------|---------|-------|
| `/api/v1/analytics/inventory/trends` | GET | Quantity trends | 5 min |
| `/api/v1/analytics/inventory/depletion` | GET | Depletion analysis | 10 min |
| `/api/v1/analytics/inventory/stockouts` | GET | Stockout analysis | 10 min |
| `/api/v1/analytics/products/performance` | GET | Product rankings | 10 min |
| `/api/v1/analytics/zones/performance` | GET | Zone efficiency | 10 min |
| `/api/v1/analytics/alerts/summary` | GET | Alert statistics | 5 min |
| `/api/v1/analytics/system/performance` | GET | System metrics | 1 min |
| `/api/v1/analytics/compare` | GET | Comparative analysis | 10 min |

---

## Pydantic Schemas

```python
class TrendDataPoint(BaseModel):
    timestamp: datetime
    value: float
    confidence: Optional[float]

class DepletionMetric(BaseModel):
    zone: str
    product: str
    rate: float  # units per day
    trend: str  # stable|increasing|decreasing

class StockoutEvent(BaseModel):
    zone: str
    product: str
    date: datetime
    duration_hours: int
    frequency: str

class ProductPerformance(BaseModel):
    sku: str
    name: str
    movements: int
    depletion_rate: float
    volatility: str
    trend: str

class ZonePerformance(BaseModel):
    name: str
    activity_level: str
    confidence: float
    health: str

class AlertSummary(BaseModel):
    total: int
    by_severity: dict
    by_type: dict
    avg_resolution_hours: float
    trend: str

class SystemPerformance(BaseModel):
    events_processed: int
    avg_latency_ms: float
    accuracy: float
    uptime: float
```

---

## Performance Optimization

### Query Strategy

1. **Aggregate on write:** Calculate trends during history recording
2. **Cache results:** Redis cache for analytics (TTL: 5-10 min)
3. **Pre-compute daily:** Store daily aggregates for historical queries
4. **Index heavily:** On zone_id, product_id, created_at

### Database Queries

```sql
-- Depletion rate (most important)
SELECT 
  product_id,
  zone_id,
  COUNT(CASE WHEN quantity_delta < 0 THEN 1 END) as depletion_events,
  SUM(CASE WHEN quantity_delta < 0 THEN ABS(quantity_delta) ELSE 0 END) as total_depleted,
  DATEDIFF(MAX(created_at), MIN(created_at)) as days,
  ROUND(SUM(CASE WHEN quantity_delta < 0 THEN ABS(quantity_delta) ELSE 0 END) / 
        DATEDIFF(MAX(created_at), MIN(created_at)), 2) as rate_per_day
FROM inventory_history
WHERE created_at > DATE_SUB(NOW(), INTERVAL ? DAY)
GROUP BY product_id, zone_id;
```

### Caching Strategy

```python
# Cache key: analytics:{endpoint}:{params_hash}
# TTL: 5-10 minutes
# Invalidate on new inventory_history record

redis_key = f"analytics:trends:{zone_id}:{product_id}:{days}"
cached = redis_client.get(redis_key)
if cached:
    return json.loads(cached)

# Calculate...
result = calculate_trends(...)

# Cache
redis_client.setex(redis_key, 600, json.dumps(result))
return result
```

---

## Testing

### Unit Tests

```python
def test_depletion_calculation():
def test_stockout_detection():
def test_product_ranking():
def test_zone_performance():
def test_cache_invalidation():
```

### Integration Tests

```python
def test_analytics_with_history():
def test_comparison_accuracy():
def test_performance_under_load():
```

---

## Success Criteria

✅ All 8 analytics endpoints operational  
✅ Queries respond in <500ms (with caching)  
✅ Accuracy verified against raw data  
✅ API fully documented  
✅ Cache invalidation working  
✅ >90% test coverage  

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026  
**Next Document:** ALERT_INTELLIGENCE_SPECIFICATION.md

