"""Wire-contract coverage for the Agent Activity frontend."""
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.agent_run import AgentRun, AgentRunStatus


def test_agent_activity_serializes_database_timestamps(client: TestClient, auth_headers):
    with SessionLocal() as db:
        run = AgentRun(
            agent_type="insight",
            status=AgentRunStatus.COMPLETED,
            trigger_event="stock_updated",
            output_action="review_inventory",
            confidence_score=0.94,
            execution_time_ms=25,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id

    response = client.get("/api/v1/agents/runs?hours=24", headers=auth_headers)
    assert response.status_code == 200
    record = next(item for item in response.json() if item["id"] == run_id)
    assert record["agent_type"] == "insight"
    assert "T" in record["created_at"]
    assert record["updated_at"]

    with SessionLocal() as db:
        db.query(AgentRun).filter(AgentRun.id == run_id).delete(synchronize_session=False)
        db.commit()
