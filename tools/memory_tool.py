from __future__ import annotations

import memory_manager_v2

from tools.base import BaseTool, ToolMetadata, ToolResult


class MemorySearchTool(BaseTool):
    metadata = ToolMetadata(
        name="memory_search",
        version="1.0.0",
        description="ค้นหาความทรงจำล่าสุดของ Jarvis",
        category="memory",
        risk_level="low",
        parameters={"required": []},
    )

    def execute(self, **params):
        limit = int(params.get("limit", 5))
        limit = max(1, min(limit, 50))
        return ToolResult(success=True, data=memory_manager_v2.get_memory(limit))


class MemoryStoreTool(BaseTool):
    metadata = ToolMetadata(
        name="memory_store",
        version="1.0.0",
        description="บันทึกข้อเท็จจริงลง Memory ของ Jarvis",
        category="memory",
        risk_level="medium",
        parameters={"required": ["key", "value"]},
    )

    def execute(self, **params):
        key = str(params.get("key", "")).strip()
        value = str(params.get("value", "")).strip()
        if not key or not value:
            raise ValueError("key และ value ต้องไม่ว่าง")
        memory_manager_v2.save_fact(key, value)
        return ToolResult(success=True, data=f"บันทึก memory: {key}")


def memory_tools() -> list[BaseTool]:
    return [MemorySearchTool(), MemoryStoreTool()]
