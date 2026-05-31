# Examples

Runnable examples for the `vendus` SDK. Each file is a standalone script.

## Running

The examples read your API key from the environment (`VendusClient.from_env()`):

```bash
export VENDUS_API_KEY=...        # from your Vendus account
python examples/01_invoice.py
```

Most examples use `register_id=1` — change it to your register's id (find it in the
Vendus backoffice or via `GET /v1.1/registers/`). A Fatura-Recibo also needs a
payment-method id; the FR examples look one up with `list_payment_methods()`.

> **Test vs real.** `mode` inherits your register's mode — **test** on new accounts, so
> these scripts issue non-fiscal test documents by default. To issue **real** documents,
> construct the client with `VendusClient(api_key=..., default_mode=DocumentMode.NORMAL)`
> or pass `mode=` per call. Real documents are permanent fiscal records — reverse an
> invoice with a credit note (FT/FR/NC cannot be cancelled).

## Index

| File | Shows |
|---|---|
| `00_all_scenarios.py` | Every issuing scenario side by side (FT, FR, NC) |
| `01_invoice.py` | Issue an invoice (FT) |
| `02_credit_note.py` | Credit a previous invoice (NC) |
| `03_invoice_receipt.py` | Issue a Fatura-Recibo (FR) with a payment |
| `04_invoice_without_nif.py` | Invoice a client by name only (no NIF) |
| `05_final_consumer.py` | Invoice a final consumer (anonymous) |
| `06_async_usage.py` | The `_async` variants |
| `07_get_list_cancel.py` | Fetch, list, and reverse (the cancel restriction) |
| `08_error_handling.py` | Catching the exception hierarchy |
| `09_fastapi_integration.py` | A FastAPI endpoint issuing invoices |

See the [docs site](https://bilouro.github.io/vendus-python/) for the full guide.
