# SAARTHI AppForge Alpha

## Purpose
An additive workspace inside SAARTHI for prompt-driven creation and iterative refinement of HTML applications, with a first isolated cloud-build path.

## Architecture
- Frontend: standalone responsive HTML/CSS/JavaScript at `/appforge`.
- API: FastAPI router under `/api/appforge`.
- Intelligence: delegates to the existing `SaarthiEngine` with the `coding` assistant profile.
- Preview: HTML is rendered in a browser iframe with the `sandbox="allow-scripts"` attribute and a restrictive Content Security Policy. Generated code is not executed inside the trusted FastAPI process.
- Local state: project metadata and version checkpoints live in browser localStorage for Alpha.
- Export: downloads the current HTML as a portable file.
- Cloud build: `backend/appforge_sandbox.py` writes submitted files to an ephemeral Vercel Sandbox microVM. The sandbox uses one vCPU, a short execution timeout, and no persistence. Package downloads are restricted to the npm registry; package lifecycle scripts are disabled during installation, then network access is denied before project build scripts run. The sandbox is always cleaned up by its async context manager.

## API
- `GET /api/appforge/health`: reports Alpha boundaries and whether isolated builds are configured.
- `POST /api/appforge/generate`: accepts `prompt`, `project_name`, and optional `current_html` / `change_request`. It returns a complete HTML document when the coding engine provides one; otherwise it returns a safe starter document.
- `POST /api/appforge/build`: accepts a bounded file map and requires `X-AppForge-Build-Key`. It validates paths and file sizes, then runs the build in the isolated sandbox. Configure `APPFORGE_BUILD_TOKEN` only on the private `feat/appforge-alpha` Vercel Preview environment. The endpoint is disabled when that variable is absent.

## Build limits and safety
- Maximum 30 files, 80 KB per file, 250 KB total, and a 45-second sandbox execution limit.
- Rejects absolute paths, traversal, dotfiles, environment files, package-manager configuration, and dependency directories.
- No application secrets or production environment variables are passed to the sandbox.
- No build runs in the FastAPI process. User code may execute only inside the isolated microVM after outbound network access has been denied.
- The preview remains an untrusted document and is constrained by iframe sandboxing and CSP.

## Security boundaries
- The preview is not a production runtime.
- No model credentials are sent to the browser.
- The private build key is entered in the UI and is not persisted in localStorage.
- Production deployment, privileged MCP access, and database credentials are not exposed to generated projects.
- The private build key is a temporary single-user gate, not a replacement for full account authentication. Do not enable the endpoint on production or expose the key publicly.

## Known Alpha limitations
- Projects and checkpoints are browser-local, not synchronized across devices.
- The current UI sends its single HTML file to the build endpoint; the API accepts multi-file projects for future editor integration.
- The current cloud build validates JavaScript syntax or runs an existing `npm run build` script; it does not deploy or publish the result.
- Durable Git-backed persistence, account authentication, distributed quotas, deployment approvals, and public publishing remain release gates.
- The fallback template is not a substitute for a configured coding model.

## Validation
Run `python -m compileall -q backend app.py tests` and `python -m pytest -q`.
