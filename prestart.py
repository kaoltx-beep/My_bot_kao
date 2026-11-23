"""Restore the sanitized Termux source bundle before the web service starts."""
from __future__ import annotations

import base64
import io
from pathlib import Path, PurePosixPath
import tarfile


ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "deploy" / "termux_source_bundle.tar.gz.b64"


def main() -> None:
    encoded = BUNDLE.read_text(encoding="ascii").strip()
    archive = base64.b64decode(encoded, validate=True)

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as source:
        members = source.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise RuntimeError("Unsafe path in source bundle")
            if member.issym() or member.islnk():
                raise RuntimeError("Links are not allowed in source bundle")
        source.extractall(ROOT, members=members, filter="data")

    # Keep the extraction step active on every restart/redeploy.
    (ROOT / "Procfile").write_text(
        "web: python prestart.py && uvicorn run:app --host 0.0.0.0 --port $PORT\n",
        encoding="utf-8",
    )
    print(f"Jarvis source bundle restored: {len(members)} files")


if __name__ == "__main__":
    main()
