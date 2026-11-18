"""Authenticated Vercel setup and recovery. Run from the repository root."""
import getpass
import secrets
import sys

import httpx

from backend.passwords import hash_password


def configure(client, project, team, branch, owner, password):
    """Scope all writes to this preview branch; the API authorizes ownership."""
    params = {"teamId": team}
    response = client.get(f"/v9/projects/{project}", params=params)
    if response.status_code != 200:
        raise RuntimeError("Vercel did not authorize access to this project.")
    values = {
        "SAARTHI_PREVIEW_OWNER_ID": owner,
        "SAARTHI_PREVIEW_OWNER_PASSWORD_HASH": hash_password(password),
        "SAARTHI_PREVIEW_SESSION_KEY": secrets.token_hex(32),
    }
    existing = client.get(f"/v9/projects/{project}/env", params=params).raise_for_status().json()["envs"]
    # Owner ID must remain stable to preserve access to existing conversations.
    matches = [v for v in existing if v["key"] == "SAARTHI_PREVIEW_OWNER_ID"
               and v.get("gitBranch") == branch]
    if matches:
        raise RuntimeError("Owner already exists. Use rotate mode to retain the existing identity.")
    for key, value in values.items():
        result = client.post(f"/v10/projects/{project}/env", params={**params, "upsert": "true"},
                             json={"key": key, "value": value, "type": "encrypted",
                                   "target": ["preview"], "gitBranch": branch})
        if not result.is_success:
            raise RuntimeError("Vercel rejected setup. Re-run setup after checking project access.")


def main():
    mode = input("First setup or password recovery? [setup/rotate] ").strip()
    if mode not in {"setup", "rotate"}:
        raise ValueError("Choose setup or rotate.")
    token = getpass.getpass("Vercel access token (hidden): ")
    project = input("Vercel project ID: ").strip()
    team = input("Vercel team ID: ").strip()
    branch = "codex/saarthi-production-recovery"
    password = getpass.getpass("Create your owner password (24+ characters, hidden): ")
    if password != getpass.getpass("Repeat password (hidden): "):
        raise ValueError("Passwords do not match.")
    encoded = hash_password(password)
    with httpx.Client(base_url="https://api.vercel.com", headers={"Authorization": f"Bearer {token}"},
                      timeout=15, follow_redirects=False) as client:
        if mode == "setup":
            owner = input("Stable owner ID (letters, digits, underscore or hyphen): ").strip()
            import re
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", owner):
                raise ValueError("Invalid owner ID.")
            configure(client, project, team, branch, owner, password)
        else:
            client.get(f"/v9/projects/{project}", params={"teamId": team}).raise_for_status()
            for key, value in {"SAARTHI_PREVIEW_OWNER_PASSWORD_HASH": encoded,
                               "SAARTHI_PREVIEW_SESSION_KEY": secrets.token_hex(32)}.items():
                result = client.post(f"/v10/projects/{project}/env",
                    params={"teamId": team, "upsert": "true"},
                    json={"key": key, "value": value, "type": "encrypted",
                          "target": ["preview"], "gitBranch": branch})
                if not result.is_success:
                    raise RuntimeError("Vercel rejected rotation. Check access and retry.")
    print("Owner settings saved. Redeploy this preview branch to activate them.")
    print("Use your chosen password in Chrome. Existing sessions expire on the new deployment.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, httpx.HTTPError):
        print("Setup did not complete. Check inputs and Vercel project access, then retry.", file=sys.stderr)
        sys.exit(1)
