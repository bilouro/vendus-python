# Security Policy

## Supported Versions

Only the latest minor version receives security updates while the project is in alpha.

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue.

Email the maintainer at the address listed in `pyproject.toml` with:

- A description of the issue
- Steps to reproduce
- Affected versions
- Your suggested fix (if any)

You will receive an acknowledgement within 72 hours. Coordinated disclosure preferred.

## Scope

In scope:
- Credential leakage via logs or exception messages
- PII leakage (NIF, email, address) outside redacted channels
- Auth bypass or request tampering
- Insecure defaults in `HttpTransport`

Out of scope:
- Vendus API itself (report to Vendus)
- AT communication (handled by Vendus, not this SDK)
- Misconfiguration in user applications
