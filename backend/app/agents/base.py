from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json
from sqlalchemy.orm import Session
from backend.app.models.entities import AgentRun
from backend.app.core.logging import logger

def make_json_serializable(obj: Any) -> Any:
    """Recursively converts non-serializable objects (like datetime) to ISO strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    return obj

class BaseAgent(ABC):
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    def execute(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the agent logic, records performance telemetry and persists the execution in agent_runs.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        logger.info(f"[{self.name}] Starting execution for workflow {workflow_id}")

        try:
            output_data, reasoning_summary = self._run(db, workflow_id, state)
            status = "SUCCESS"
        except Exception as e:
            logger.error(f"[{self.name}] Error during execution: {e}", exc_info=True)
            status = "FAILED"
            output_data = {"error": str(e)}
            reasoning_summary = f"Agent failed with error: {str(e)}"

        completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Sanitize input data summary to prevent circular or oversized JSON
        safe_input_summary = {
            k: len(v) if isinstance(v, (list, dict)) else v
            for k, v in state.items()
            if k not in ["db", "_db"]
        }

        # Persist agent run record with JSON-safe structures
        agent_run = AgentRun(
            workflow_id=workflow_id,
            agent_name=self.name,
            input_data=make_json_serializable(safe_input_summary),
            output_data=make_json_serializable(output_data),
            status=status,
            started_at=now,
            completed_at=completed_at,
            reasoning_summary=reasoning_summary
        )
        db.add(agent_run)
        db.commit()

        # Return updated state slice
        return output_data

    @abstractmethod
    def _run(self, db: Session, workflow_id: str, state: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        """Subclasses must implement actual agent logic returning (output_dict, reasoning_summary)."""
        pass
