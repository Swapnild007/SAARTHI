"""Mobile owner verification through the deployment management API."""
import hashlib
import re
import secrets

import httpx

from .deployment import setting

GRANT_COOKIE = "saarthi_owner_setup"
GRANT_TTL = 600
BRANCH = "codex/saarthi-production-recovery"


def authorization_digest(environment: str, origin: str, token: str) -> str:
    return hashlib.sha256(f"{environment}|{origin}|{token}".encode()).hexdigest()


def database_auth() -> bool:
    return setting("OWNER_AUTH_STORE") == "database"


async def verify_deployment_access(token: str) -> bool:
    """A branch-scoped create/delete proves management write authorization."""
    project = setting("DEPLOYMENT_PROJECT_ID")
    team = setting("DEPLOYMENT_TEAM_ID")
    if not re.fullmatch(r"prj_[A-Za-z0-9]+", project) or not re.fullmatch(r"team_[A-Za-z0-9]+", team):
        return False
    # The token is used only on Vercel's fixed origin and is never persisted.
    async with httpx.AsyncClient(base_url="https://api.vercel.com", timeout=5,
                                 follow_redirects=False,
                                 headers={"Authorization": f"Bearer {token}"}) as client:
        response = await client.post(f"/v10/projects/{project}/env", params={"teamId": team}, json={
            "key": "SAARTHI_SETUP_PROOF_" + secrets.token_hex(8).upper(),
            "value": "temporary-management-permission-check",
            "type": "encrypted", "target": ["preview"], "gitBranch": BRANCH,
        })
        if not response.is_success:
            return False
        record = response.json().get("created", response.json())
        if isinstance(record, list):
            record = record[0] if len(record) == 1 else {}
        identifier = record.get("id") if isinstance(record, dict) else None
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
            return False
        removed = await client.delete(f"/v9/projects/{project}/env/{identifier}", params={"teamId": team})
        return removed.is_success
