"""Process isolation for the existing synchronous assistant engine."""
from __future__ import annotations

import asyncio
import contextvars
import json
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager

timings: contextvars.ContextVar[dict[str, float] | None] = contextvars.ContextVar(
    "stage_timings", default=None
)


@contextmanager
def stage(name: str) -> Iterator[None]:
    started = time.monotonic()
    try:
        yield
    finally:
        report = timings.get()
        if report is not None:
            report[name] = round(report.get(name, 0) + (time.monotonic() - started) * 1000, 2)


async def run_turn(payload: dict, budget: float) -> dict:
    started = time.monotonic()
    worker = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "backend.turn_worker",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        async with asyncio.timeout(max(0, budget - (time.monotonic() - started))):
            output, _ = await worker.communicate(json.dumps(payload).encode())
        if worker.returncode:
            raise RuntimeError("Chat worker failed")
        return json.loads(output)
    finally:
        if worker.returncode is None:
            try:
                worker.kill()
            except ProcessLookupError:
                pass
            await worker.wait()
