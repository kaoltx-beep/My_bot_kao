from __future__ import annotations

import developer_mode

from tools.base import BaseTool, ToolMetadata, ToolResult


class RollbackTool(BaseTool):
    metadata = ToolMetadata(
        name="rollback",
        version="1.0.0",
        description="ย้อนการแก้ไขจาก Developer Mode proposal ที่มี backup",
        category="developer",
        risk_level="high",
        require_approval=True,
        can_rollback=False,
        parameters={"required": ["proposal_id"]},
    )

    def execute(self, **params):
        proposal_id = str(params.get("proposal_id", "")).strip()
        if not proposal_id:
            raise ValueError("proposal_id is required")
        result = developer_mode.rollback(proposal_id)
        return ToolResult(success=result.get("ok", False), data=result if result.get("ok") else None, error=result.get("error"))


def rollback_tools() -> list[BaseTool]:
    return [RollbackTool()]
