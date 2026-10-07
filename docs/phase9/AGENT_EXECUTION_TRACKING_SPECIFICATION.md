# Agent Execution Tracking Specification

**Purpose:** Full observability into AI agent behavior and decision-making  
**Component:** Backend agent telemetry  
**Priority:** HIGH (Phase 9.3)  
**Complexity:** Low-Medium  
**Estimated Effort:** 3 days

---

## Overview

Phase 8 logs agent runs. Phase 9 enhances with full execution tracing: inputs, outputs, confidence scores, reasoning, and error tracking. Every AI agent decision becomes debuggable and explainable.

---

## Existing vs. Enhanced

**Currently (Phase 8):**
```python
AgentRun model tracks:
- id, agent_type, status, created_at

Missing:
- What was the input?
- What was the decision/output?
- How confident was the agent?
- Why did it make that decision?
- What went wrong if it failed?
```

**After Phase 9:**
```python
Enhanced AgentRun tracks:
- id, agent_type, status
- input (what triggered it)
- decision/output (what it decided)
- confidence (how sure)
- reasoning (why)
- error (if failed)
- execution trace (step-by-step)
```

---

## Database Schema

### Enhanced: `agent_runs` table

```sql
ALTER TABLE agent_runs ADD COLUMN (
    -- Input
    input_data JSON,                          -- What triggered execution
    input_zone_id VARCHAR(36),
    input_product_id VARCHAR(36),
    input_confidence FLOAT,
    
    -- Output
    output_data JSON,                         -- Decision/recommendation
    output_recommendation VARCHAR(255),       -- e.g., "RESTOCK", "INVESTIGATE"
    output_confidence FLOAT,                  -- 0.0-1.0
    
    -- Reasoning
    reasoning_steps JSON,                     -- Step-by-step trace
    reasoning_summary TEXT,
    
    -- Performance
    execution_time_ms INTEGER,
    
    -- Error handling
    error_occurred BOOLEAN DEFAULT FALSE,
    error_type VARCHAR(100),
    error_message TEXT,
    error_trace TEXT,
    
    -- Metadata
    llm_model VARCHAR(100),                   -- e.g., "gpt-4", "claude-3"
    llm_tokens_input INTEGER,
    llm_tokens_output INTEGER,
    llm_cost_cents DECIMAL(8, 2),
    
    -- Indexes
    INDEX idx_agent_confidence (agent_type, output_confidence DESC),
    INDEX idx_failed (error_occurred, created_at DESC),
    INDEX idx_recommendation (output_recommendation)
);
```

---

## Service Enhancement

### Enhanced `AgentTelemetryService`

```python
class AgentTelemetryService:
    """Track and query agent executions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Recording executions
    def start_execution(
        self,
        agent_type: str,
        input_data: dict
    ) -> AgentRun:
        """Record execution start."""
        run = AgentRun(
            agent_type=agent_type,
            status="RUNNING",
            input_data=input_data,
            started_at=datetime.utcnow()
        )
        self.db.add(run)
        self.db.commit()
        return run
    
    def complete_execution(
        self,
        run_id: str,
        output_data: dict,
        output_confidence: float,
        reasoning_steps: list,
        execution_time_ms: int,
        llm_data: dict = None
    ) -> AgentRun:
        """Record successful execution."""
        run = self.db.query(AgentRun).get(run_id)
        run.status = "COMPLETED"
        run.output_data = output_data
        run.output_confidence = output_confidence
        run.reasoning_steps = reasoning_steps
        run.execution_time_ms = execution_time_ms
        run.completed_at = datetime.utcnow()
        
        if llm_data:
            run.llm_model = llm_data.get("model")
            run.llm_tokens_input = llm_data.get("tokens_input")
            run.llm_tokens_output = llm_data.get("tokens_output")
            run.llm_cost_cents = llm_data.get("cost_cents")
        
        self.db.commit()
        return run
    
    def fail_execution(
        self,
        run_id: str,
        error_type: str,
        error_message: str,
        error_trace: str = None
    ) -> AgentRun:
        """Record failed execution."""
        run = self.db.query(AgentRun).get(run_id)
        run.status = "FAILED"
        run.error_occurred = True
        run.error_type = error_type
        run.error_message = error_message
        run.error_trace = error_trace
        run.completed_at = datetime.utcnow()
        
        self.db.commit()
        return run
    
    # Querying
    def get_execution(self, run_id: str) -> AgentRun:
        """Get full execution details."""
        return self.db.query(AgentRun).get(run_id)
    
    def get_agent_history(
        self,
        agent_type: str,
        days: int = 30,
        limit: int = 100
    ) -> List[AgentRun]:
        """Get execution history for agent."""
        return self.db.query(AgentRun).filter(
            AgentRun.agent_type == agent_type,
            AgentRun.created_at > datetime.utcnow() - timedelta(days=days)
        ).order_by(AgentRun.created_at.desc()).limit(limit).all()
    
    def get_failed_executions(
        self,
        agent_type: Optional[str] = None,
        days: int = 7
    ) -> List[AgentRun]:
        """Get failed executions for debugging."""
        query = self.db.query(AgentRun).filter(
            AgentRun.status == "FAILED",
            AgentRun.created_at > datetime.utcnow() - timedelta(days=days)
        )
        if agent_type:
            query = query.filter(AgentRun.agent_type == agent_type)
        return query.order_by(AgentRun.created_at.desc()).all()
    
    # Statistics
    def get_agent_statistics(
        self,
        agent_type: str,
        days: int = 30
    ) -> AgentStatistics:
        """Get performance statistics for agent."""
        runs = self.get_agent_history(agent_type, days=days, limit=10000)
        
        total = len(runs)
        succeeded = len([r for r in runs if r.status == "COMPLETED"])
        failed = len([r for r in runs if r.status == "FAILED"])
        
        success_rate = succeeded / total if total > 0 else 0
        avg_confidence = sum(r.output_confidence or 0 for r in runs) / total if total > 0 else 0
        avg_time_ms = sum(r.execution_time_ms or 0 for r in runs) / succeeded if succeeded > 0 else 0
        
        recommendations = {}
        for run in runs:
            if run.output_recommendation:
                recommendations[run.output_recommendation] = recommendations.get(run.output_recommendation, 0) + 1
        
        return AgentStatistics(
            agent_type=agent_type,
            total_executions=total,
            success_count=succeeded,
            failure_count=failed,
            success_rate=success_rate,
            avg_confidence=avg_confidence,
            avg_execution_time_ms=avg_time_ms,
            most_common_recommendation=max(recommendations, key=recommendations.get),
            error_breakdown=self._get_error_breakdown(runs)
        )
    
    def _get_error_breakdown(self, runs: List[AgentRun]) -> dict:
        """Categorize errors."""
        errors = {}
        for run in runs:
            if run.error_type:
                errors[run.error_type] = errors.get(run.error_type, 0) + 1
        return errors
    
    # Debugging
    def get_reasoning_trace(self, run_id: str) -> dict:
        """Get detailed reasoning for execution."""
        run = self.get_execution(run_id)
        return {
            "agent": run.agent_type,
            "status": run.status,
            "input": run.input_data,
            "reasoning_steps": run.reasoning_steps,
            "output": run.output_data,
            "confidence": run.output_confidence,
            "error": run.error_message if run.error_occurred else None
        }
```

---

## API Endpoints

```
GET  /api/v1/agents/runs/{run_id}              # Get execution
GET  /api/v1/agents/{agent_type}/history       # Execution history
GET  /api/v1/agents/{agent_type}/stats         # Performance stats
GET  /api/v1/agents/{agent_type}/failures      # Failed executions
GET  /api/v1/agents/{agent_type}/trace/{run_id} # Detailed trace
```

### Example: Get Agent Statistics

```
GET /api/v1/agents/insight_agent/stats?days=30

Response 200:
{
  "agent_type": "insight_agent",
  "period_days": 30,
  "total_executions": 1200,
  "success_count": 1164,
  "failure_count": 36,
  "success_rate": 0.97,
  "avg_confidence": 0.92,
  "avg_execution_time_ms": 120,
  "most_common_recommendation": "RESTOCK",
  "error_breakdown": {
    "timeout": 20,
    "invalid_data": 12,
    "llm_error": 4
  }
}
```

### Example: Get Reasoning Trace

```
GET /api/v1/agents/anomaly_agent/trace/run-12345

Response 200:
{
  "agent": "anomaly_agent",
  "status": "COMPLETED",
  "input": {
    "zone_id": "zone-A",
    "product_id": "prod-X",
    "current_quantity": 2,
    "historical_avg": 8.5
  },
  "reasoning_steps": [
    "Step 1: Fetch historical data (30 days)",
    "Step 2: Calculate average: 8.5 units",
    "Step 3: Calculate deviation: -6.5 units (-76%)",
    "Step 4: Check if anomalous: YES (>50% deviation)",
    "Step 5: Determine severity: CRITICAL",
    "Step 6: Formulate recommendation: INVESTIGATE_IMMEDIATELY"
  ],
  "output": {
    "is_anomaly": true,
    "severity": "critical",
    "recommendation": "INVESTIGATE_IMMEDIATELY",
    "details": "Sudden 76% drop from historical average"
  },
  "confidence": 0.98,
  "error": null
}
```

---

## Integration Example

### How Agents Record Execution

```python
# In supervisor_agent.py

class SupervisorAgent:
    def __init__(self, db: Session, telemetry: AgentTelemetryService):
        self.db = db
        self.telemetry = telemetry
    
    def route(self, event_type: str, event_data: dict) -> dict:
        """Route event to appropriate agent."""
        
        # Start recording execution
        run = self.telemetry.start_execution(
            agent_type="supervisor",
            input_data={"event_type": event_type, "data": event_data}
        )
        
        try:
            # Determine which agent to call
            if event_type == "low_stock":
                reasoning = ["Detected low stock event", "Routing to insight agent"]
                recommendation = "ANALYZE_INVENTORY"
            elif event_type == "anomaly":
                reasoning = ["Detected anomaly event", "Routing to anomaly agent"]
                recommendation = "INVESTIGATE"
            else:
                recommendation = "NOTIFY"
                reasoning = ["Unknown event type", "Routing to notification agent"]
            
            # Record successful execution
            self.telemetry.complete_execution(
                run_id=run.id,
                output_data={
                    "routed_to_agent": recommended_agent,
                    "recommendation": recommendation
                },
                output_confidence=0.95,
                reasoning_steps=reasoning,
                execution_time_ms=45
            )
            
            return recommendation
            
        except Exception as e:
            # Record failure
            self.telemetry.fail_execution(
                run_id=run.id,
                error_type=type(e).__name__,
                error_message=str(e),
                error_trace=traceback.format_exc()
            )
            raise
```

---

## Pydantic Schemas

```python
class AgentRunResponse(BaseModel):
    id: str
    agent_type: str
    status: str  # RUNNING, COMPLETED, FAILED
    input_data: dict
    output_data: Optional[dict]
    output_confidence: Optional[float]
    reasoning_steps: Optional[list]
    error_occurred: bool
    error_type: Optional[str]
    execution_time_ms: Optional[int]
    created_at: datetime

class AgentStatistics(BaseModel):
    agent_type: str
    total_executions: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_confidence: float
    avg_execution_time_ms: float
    most_common_recommendation: str
    error_breakdown: dict

class ReasoningTrace(BaseModel):
    agent: str
    status: str
    input: dict
    reasoning_steps: list
    output: dict
    confidence: float
    error: Optional[str]
```

---

## Testing

```python
def test_execution_recording():
    """Verify execution details recorded."""

def test_failure_tracking():
    """Errors properly tracked."""

def test_statistics_accuracy():
    """Stats computed correctly."""

def test_reasoning_trace():
    """Full trace available for debugging."""
```

---

## Success Criteria

✅ All agent executions traced  
✅ Inputs and outputs captured  
✅ Confidence scores recorded  
✅ Failures tracked with error details  
✅ Statistics accurate and useful  
✅ Reasoning traces available  
✅ API fully documented  
✅ >90% test coverage  

---

**Document Version:** 1.0  
**Last Updated:** October 7, 2026

