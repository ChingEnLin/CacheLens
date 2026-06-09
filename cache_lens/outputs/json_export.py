"""JSON export of SessionReport to a file or stdout."""

from __future__ import annotations

import dataclasses
import json
import sys
from datetime import datetime

from ..models import SessionReport


def _default(obj: object) -> object:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Not JSON serialisable: {type(obj)}")


def to_dict(report: SessionReport) -> dict:
    return dataclasses.asdict(report)


def to_json(report: SessionReport) -> str:
    return json.dumps(to_dict(report), default=_default, indent=2)


def export(report: SessionReport, target: str) -> None:
    """Write the report. `target` may be a path template or "-" for stdout.

    Path tokens: {timestamp}, {session_id}, {model}.
    """
    payload = to_json(report)
    if target == "-":
        sys.stdout.write(payload + "\n")
        return

    path = target.format(
        timestamp=report.ended_at.strftime("%Y%m%dT%H%M%S"),
        session_id=report.session_id,
        model=report.model.replace("/", "_"),
    )
    import os

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(payload)
