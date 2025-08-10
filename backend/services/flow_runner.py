from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging
from backend.config import settings

logger = logging.getLogger(__name__)
cfg = settings()

@dataclass
class FlowRunner:
    """
    Thin facade to trigger Smallest.ai flows/agents (Atoms).
    """
    smallest_client: Any
    default_flows: Dict[str, str] | None = None

    def trigger(self, flow_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a prebuilt/custom flow by name and return an execution handle.
        Swap this with real SDK calls to your Atoms/Flows.
        """
        flow_id = (self.default_flows or {}).get(flow_name)
        if not flow_id:
            logger.info("Flow '%s' not registered; running stub.", flow_name)
            return {"ok": True, "flow": flow_name, "stub": True, "payload": payload}
        # Example stub for a real call:
        try:
            # resp = self.smallest_client.atoms.run_flow(flow_id=flow_id, input=payload)
            # return {"ok": True, "id": resp.id}
            return {"ok": True, "flow_id": flow_id, "payload": payload, "note": "TODO wire SDK"}
        except Exception as e:
            logger.warning("Flow trigger failed: %s", e)
            return {"ok": False, "error": str(e)}

    def status(self, execution_id: str) -> Dict[str, Any]:
        """
        Poll flow run status. Replace with SDK polling.
        """
        return {"ok": True, "id": execution_id, "status": "completed (stub)"}
