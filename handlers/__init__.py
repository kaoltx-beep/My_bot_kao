"""Jarvis request handlers.

The package keeps FastAPI and Telegram transport handlers out of run.py.
"""

from .telegram import register_handlers

__all__ = ["register_handlers"]
