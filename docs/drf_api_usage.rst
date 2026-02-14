.. _api_usage:

DRF API Usage
=========

This page describes the HTTP endpoints provided by `django-solana-payments` when you install the DRF extra and include the package URLs.

Base routing
------------

If your project uses:

.. code-block:: python

    urlpatterns = [
        path("solana-payments/", include("django_solana_payments.urls")),
    ]

Then the endpoints below are available under the `/solana-payments/` prefix.

Integration flow
-------

Typical API flow:

1. Call `POST /solana-payments/initiate/` to create a payment and receive `payment_address`.
2. Show that address/QR code to the payer, then the payer sends funds to the `payment_address`.

   Common UI examples:

   - Connect crypto wallet -> show payment summary in the wallet extension -> user signs and sends transaction -> app checks payment status.
   - Open wallet app (Phantom/Solflare/mobile wallet) -> scan the QR code -> send expected amount -> return to your app -> app payment checks status.


3. Poll `GET /solana-payments/verify-transfer/{payment_address}?token_type=...` until status becomes `confirmed` or `finalized`.
4. Optionally call `GET /solana-payments/payments/{payment_address}/` for details.

.. note::

   The library author plans to add a long-polling payment status endpoint in the near future.
   Until then, use short-interval polling from your backend or frontend.

1. Create Payment
-----------------

**Endpoint:** `POST /solana-payments/initiate/`

Creates a payment record and returns a one-time Solana payment address.

Example request:

.. code-block:: bash

    curl -X POST "http://localhost:8000/solana-payments/initiate/" \
      -H "Content-Type: application/json" \
      -d '{
        "label": "Premium Plan",
        "message": "Monthly subscription",
        "meta_data": {"order_id": "sub-1001"}
      }'

Example response (`201`):

.. code-block:: json

    {
      "payment_address": "GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS"
    }

Notes:

- If the request is authenticated, the payment is linked to `request.user`.
- Active payment tokens are converted into price entries and attached automatically.

2. Verify Payment Transfer
--------------------------

**Endpoint:** `GET /solana-payments/verify-transfer/{payment_address}`

Verifies the on-chain transfer and updates payment status when successful.

Required query params:

- `token_type`: `NATIVE` or `SPL`

Optional query params:

- `mint_address`: required when `token_type=SPL`
- `meta_data`: JSON metadata to store on successful verification

Example request (native SOL):

.. code-block:: bash

    curl "http://localhost:8000/solana-payments/verify-transfer/GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS?token_type=NATIVE"

Example request (SPL token):

.. code-block:: bash

    curl "http://localhost:8000/solana-payments/verify-transfer/GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS?token_type=SPL&mint_address=Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr"

Example response (`200`):

.. code-block:: json

    {
      "status": "confirmed",
      "payment_address": "GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS"
    }

Common error responses:

- `400`: invalid query params (for example, unsupported `token_type` or wrong `mint_address` usage)
- `404`: payment not found or payment expired
- `409`: payment amount mismatch or payment not confirmed at required commitment level

3. Get Payment Details
----------------------

**Endpoint:** `GET /solana-payments/payments/{payment_address}/`

Returns payment details including related crypto prices.

Example request:

.. code-block:: bash

    curl "http://localhost:8000/solana-payments/payments/GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS/"

4. List Allowed Tokens
----------------------

**Endpoint:** `GET /solana-payments/payments-tokens/`

Returns allowed payment token records (for example SOL/USDC configurations).

Example request:

.. code-block:: bash

    curl "http://localhost:8000/solana-payments/payments-tokens/"
