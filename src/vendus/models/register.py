"""Register (caixa) model — the POS register documents are issued from."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Register(BaseModel):
    """A Vendus register (caixa).

    Read-only via the API — registers are created and configured in the Vendus
    backoffice. Use ``id`` as ``register_id`` when issuing documents.

    ``mode`` is the register's working mode (``"normal"`` / ``"tests"``); documents
    issued from it inherit it unless a per-call or client ``mode`` overrides it.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    mode: str = Field(default="", description='Working mode: "normal" or "tests".')
    type: str = ""
    status: Optional[str] = None
    situation: Optional[str] = None
    store_id: Optional[int] = None
