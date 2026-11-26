"""Gemini Companion plugin for Hermes Agent."""

from . import schemas, tools


def register(ctx):
    """Register Gemini tools with Hermes."""
    ctx.register_tool(name="gemini_status", toolset="gemini_companion",
                      schema=schemas.GEMINI_STATUS, handler=tools.gemini_status)
    ctx.register_tool(name="gemini_consult", toolset="gemini_companion",
                      schema=schemas.GEMINI_CONSULT, handler=tools.gemini_consult)
    ctx.register_tool(name="gemini_list_models", toolset="gemini_companion",
                      schema=schemas.GEMINI_LIST_MODELS, handler=tools.gemini_list_models)
