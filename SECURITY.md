# Security Policy

## Supported versions

The current main branch is the supported development line.

## Reporting a vulnerability

Please do not disclose security vulnerabilities in public GitHub issues.

Use GitHub's private vulnerability reporting for this repository when available. Include:
- affected endpoint, feature, or component
- reproduction steps
- security impact
- relevant logs or screenshots with secrets and personal data removed

SAARTHI uses OWASP ASVS/API Security guidance for the web/API surface and OWASP MASVS/MASTG for the future Android client.

## Security expectations

- Never commit API keys, provider credentials, signing keys, or user secrets.
- Production secrets must remain server-side.
- Research URL fetching must reject private/internal destinations and unsafe redirects.
- API payloads and attachments must remain bounded.
- Security regressions should add a reproducible automated test where practical.
