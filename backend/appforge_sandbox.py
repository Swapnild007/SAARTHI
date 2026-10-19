"""Isolated AppForge build runner backed by Vercel Sandbox.

All submitted files and build commands stay inside an ephemeral microVM. The
runner never executes generated code in the FastAPI process and never grants
the sandbox access to application secrets.
"""
from __future__ import annotations

import json
import re
from datetime import timedelta
from typing import Any

MAX_FILES = 30
MAX_FILE_BYTES = 80_000
MAX_TOTAL_BYTES = 250_000
MAX_PREVIEW_BYTES = 120_000
ALLOWED_SUFFIXES = {
    ".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json",
    ".svg", ".txt", ".md", ".ts", ".tsx", ".jsx",
}
BLOCKED_NAMES = {".env", ".npmrc", ".git", "node_modules", ".vercel"}
BUILD_TIMEOUT = timedelta(seconds=45)


class BuildInputError(ValueError):
    pass


def validate_build_files(files: dict[str, str]) -> dict[str, str]:
    if not isinstance(files, dict) or not files:
        raise BuildInputError("Provide at least one project file.")
    if len(files) > MAX_FILES:
        raise BuildInputError(f"A build may contain at most {MAX_FILES} files.")

    normalized: dict[str, str] = {}
    total = 0
    for raw_path, content in files.items():
        if not isinstance(raw_path, str) or not isinstance(content, str):
            raise BuildInputError("File paths and contents must be text.")
        path = raw_path.replace("\\", "/").strip()
        parts = path.split("/")
        if (
            not path
            or path.startswith("/")
            or "\x00" in path
            or any(part in {"", ".", ".."} for part in parts)
            or any(part.lower() in BLOCKED_NAMES for part in parts)
            or any(part.startswith(".") for part in parts)
            or len(path) > 180
        ):
            raise BuildInputError(f"Unsafe project path: {raw_path[:80]}")
        suffix = "." + path.rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
        if suffix not in ALLOWED_SUFFIXES:
            raise BuildInputError(f"Unsupported file type: {path[:80]}")
        size = len(content.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            raise BuildInputError(f"File is too large: {path[:80]}")
        total += size
        normalized[path] = content
    if total > MAX_TOTAL_BYTES:
        raise BuildInputError("Project files exceed the 250 KB total limit.")
    if "index.html" not in normalized and "src/index.html" not in normalized:
        if "package.json" not in normalized:
            raise BuildInputError("Add index.html or a package.json build project.")

    if "package.json" in normalized:
        try:
            manifest = json.loads(normalized["package.json"])
        except json.JSONDecodeError as exc:
            raise BuildInputError("package.json must contain valid JSON.") from exc
        if not isinstance(manifest, dict):
            raise BuildInputError("package.json must be a JSON object.")
        scripts = manifest.get("scripts", {})
        if scripts is not None and not isinstance(scripts, dict):
            raise BuildInputError("package.json scripts must be an object.")
        # Prevent dependency lifecycle hooks from running during installation.
        # The project's build script runs only after the sandbox is network-isolated.
    return normalized


async def run_isolated_build(files: dict[str, str]) -> dict[str, Any]:
    """Run fixed validation/build commands in a short-lived, network-restricted VM."""
    from vercel import sandbox
    from vercel.api import session
    from vercel.sandbox import NetworkPolicy, SandboxResources

    normalized = validate_build_files(files)
    has_manifest = "package.json" in normalized
    install_policy = (
        NetworkPolicy.custom(allow={"registry.npmjs.org": ()})
        if has_manifest
        else NetworkPolicy.deny_all()
    )
    log_parts: list[str] = []

    async with session():
        async with sandbox.create_sandbox(
            execution_time_limit=BUILD_TIMEOUT,
            resources=SandboxResources(vcpus=1),
            network_policy=install_policy,
            persistent=False,
            region="bom1",
            tags={"app": "saarthi", "purpose": "appforge-build"},
        ) as box:
            async with box.fs.batch() as batch:
                for path, content in normalized.items():
                    batch.write_text(f"workspace/{path}", content)

            if has_manifest:
                install = await box.run_process(
                    "npm",
                    ["install", "--ignore-scripts", "--no-audit", "--no-fund", "--no-progress"],
                    cwd="workspace",
                    capture_output=True,
                    kill_after=timedelta(seconds=20),
                )
                log_parts.append((install.stdout or "")[-3000:])
                log_parts.append((install.stderr or "")[-3000:])
                if install.exit_code != 0:
                    return {
                        "ok": False,
                        "status": "dependency-install-failed",
                        "logs": "\n".join(part for part in log_parts if part)[-6000:],
                    }
                # Dependencies are installed from the registry allow-list only.
                # User build scripts must not have outbound network access.
                await box.update(network_policy=NetworkPolicy.deny_all())
                build = await box.run_process(
                    "npm",
                    ["run", "build", "--if-present"],
                    cwd="workspace",
                    capture_output=True,
                    kill_after=timedelta(seconds=20),
                )
                log_parts.append((build.stdout or "")[-3000:])
                log_parts.append((build.stderr or "")[-3000:])
                if build.exit_code != 0:
                    return {
                        "ok": False,
                        "status": "build-failed",
                        "logs": "\n".join(part for part in log_parts if part)[-6000:],
                    }
            else:
                js_files = [
                    f"workspace/{path}" for path in normalized
                    if path.lower().endswith((".js", ".mjs", ".cjs"))
                ]
                for path in js_files:
                    check = await box.run_process(
                        "node", ["--check", path],
                        capture_output=True,
                        kill_after=timedelta(seconds=8),
                    )
                    log_parts.append((check.stdout or "")[-1000:])
                    log_parts.append((check.stderr or "")[-2000:])
                    if check.exit_code != 0:
                        return {
                            "ok": False,
                            "status": "syntax-check-failed",
                            "logs": "\n".join(part for part in log_parts if part)[-6000:],
                        }

            preview_html = None
            for path in (
                "workspace/dist/index.html",
                "workspace/build/index.html",
                "workspace/index.html",
                "workspace/src/index.html",
            ):
                try:
                    candidate = await box.fs.read_text(path)
                except Exception:
                    continue
                if candidate and len(candidate.encode("utf-8")) <= MAX_PREVIEW_BYTES:
                    preview_html = candidate
                    break

            return {
                "ok": True,
                "status": "built",
                "files": len(normalized),
                "bytes": sum(len(value.encode("utf-8")) for value in normalized.values()),
                "preview_html": preview_html,
                "logs": "\n".join(part for part in log_parts if part)[-6000:],
                "isolation": "ephemeral-microvm-network-restricted",
            }
