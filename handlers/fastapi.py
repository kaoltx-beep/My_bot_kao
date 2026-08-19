"""FastAPI route handlers for Jarvis."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.api_route("/health", methods=["GET", "HEAD"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.api_route("/", methods=["GET", "HEAD"])
def root() -> dict[str, str]:
    return {"status": "ok"}
