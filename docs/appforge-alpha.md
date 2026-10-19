# SAARTHI AppForge Alpha

## Purpose
An additive workspace inside SAARTHI for prompt-driven creation and iterative refinement of single-file HTML applications.

## Architecture
- Frontend: standalone responsive HTML/CSS/JavaScript at `/appforge`.
- API: FastAPI router under `/api/appforge`.
- Intelligence: delegates to the existing `SaarthiEngine` with the `coding` assistant profile.
- Preview: HTML is rendered in a browser iframe with the `sandbox="allow-scripts"` attribute and a restrictive Content Security Policy. Generated code is not executed inside the trusted FastAPI process.
- Local state: project metadata and version checkpoints live in browser localStorage for Alpha.
- Export: downloads the current HTML as a portable file.

## API
- `GET /api/appforge/health`: reports Alpha feature boundaries.
- `POST /api/appforge/generate`: accepts `prompt`, `project_name`, and optional `current_html` / `change_request`. It returns a complete HTML document when the coding engine provides one; otherwise it returns a safe starter document and reports that mode explicitly.

## Security boundaries
- The preview is not a production runtime.
- Network access from preview documents is blocked by CSP; the iframe has no same-origin permission.
- Payload lengths are bounded by Pydantic validation.
- No model credentials are sent to the browser.
- Production deployment, privileged MCP access, and database credentials are not exposed to generated projects.

## Known Alpha limitations
- Projects and checkpoints are browser-local, not synchronized across devices.
- This version does not run managed cloud sandbox builds, install arbitrary dependencies, support multi-file frameworks, connect generated applications to databases, or publish production deployments.
- The fallback template is not a substitute for a configured coding model.
- Before broader release, add authenticated project ownership, durable Git-backed persistence, managed isolated execution, dependency/network policy, quota enforcement, and deployment approvals.

## Validation
Run `python -m compileall -q backend app.py tests` and `python -m pytest -q`.
