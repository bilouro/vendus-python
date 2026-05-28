"""URLs, prefixes, defaults. No magic — all constants."""

from __future__ import annotations

# Base URLs
PRODUCTION_BASE_URL = "https://www.vendus.pt/ws"
SPAIN_BASE_URL = "https://www.vendus.es/ws"

# Sandbox URL — TBD. Investigate during v0.1 dev.
SANDBOX_BASE_URL: str | None = None

# Per-resource API versions (Vendus does not use a single version)
API_VERSION_DOCUMENTS = "v1.1"
API_VERSION_CLIENTS = "v1.0"
API_VERSION_PRODUCTS = "v1.0"
API_VERSION_RECEIPTS = "v1.1"

# Paths (prefix with /{API_VERSION_...})
PATH_DOCUMENTS = "/documents"
PATH_CLIENTS = "/clients"

# HTTP defaults
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.5

# Reserved fiscal_id values
FINAL_CONSUMER_FORBIDDEN_NIF = "999999990"

# User-Agent
USER_AGENT_PREFIX = "vendus-python"
