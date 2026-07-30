from __future__ import annotations

import expense_manager

from tools.base import BaseTool, ToolMetadata, ToolResult


class ExpenseAddTool(BaseTool):
    metadata = ToolMetadata(
        name="expense_add",
        version="1.0.0",
        description="บันทึกรายจ่ายใหม่ เช่น น้ำมัน 500",
        category="expense",
        risk_level="medium",
        require_approval=False,
        parameters={"required": ["item", "amount"]},
    )

    def execute(self, **params):
        item = str(params.get("item", "")).strip()
        amount = float(params.get("amount", 0))
        if not item or amount <= 0:
            raise ValueError("item และ amount ต้องถูกต้อง")
        return ToolResult(success=True, data=expense_manager.add_expense(item, amount))


class ExpenseListTool(BaseTool):
    metadata = ToolMetadata(
        name="expense_list",
        version="1.0.0",
        description="ดูรายการค่าใช้จ่ายทั้งหมด",
        category="expense",
        risk_level="low",
        parameters={"required": []},
    )

    def execute(self, **params):
        return ToolResult(success=True, data=expense_manager.list_expenses())


class ExpenseMonthlyTool(BaseTool):
    metadata = ToolMetadata(
        name="expense_monthly",
        version="1.0.0",
        description="ดูสรุปค่าใช้จ่ายเดือนปัจจุบัน",
        category="expense",
        risk_level="low",
        parameters={"required": []},
    )

    def execute(self, **params):
        return ToolResult(success=True, data=expense_manager.monthly_summary())


def expense_tools() -> list[BaseTool]:
    return [ExpenseAddTool(), ExpenseListTool(), ExpenseMonthlyTool()]
