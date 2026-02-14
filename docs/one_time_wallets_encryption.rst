.. _one_time_wallets_encryption:

One-Time Wallets Encryption
===========================

`django-solana-payments` can encrypt one-time wallet keypair payloads before storing them in your database.
This reduces exposure risk if database records are leaked.

Enable the feature
------------------

Set these values in `SOLANA_PAYMENTS`:

.. code-block:: python

    SOLANA_PAYMENTS = {
        # ... other settings
        "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": True,
        "ONE_TIME_WALLETS_ENCRYPTION_KEY": "ONE_TIME_WALLETS_ENCRYPTION_KEY",
    }

When encryption is enabled, `ONE_TIME_WALLETS_ENCRYPTION_KEY` is required.

How to generate `ONE_TIME_WALLETS_ENCRYPTION_KEY`
-------------------------------------------------

Generate a valid Fernet key with Python:

.. code-block:: python

    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode("utf-8"))

The output is a URL-safe base64 string. Put that full value into:

- `SOLANA_PAYMENTS["ONE_TIME_WALLETS_ENCRYPTION_KEY"]`

Recommended practice:

- Generate a different key per environment (dev/stage/prod).
- Store keys in a secret manager or protected environment variables, not in source control.
- Plan key rotation carefully (old encrypted records require old key compatibility or migration).

How encryption works
--------------------

Encryption is implemented in `django_solana_payments/services/wallet_encryption_service.py` using `cryptography.fernet.Fernet`.

Behavior:

1. Before storing one-time wallet keypair JSON, the plaintext is encrypted with Fernet.
2. Encrypted ciphertext is stored in the wallet record (`keypair_json`).
3. On wallet usage, ciphertext is decrypted back to the original keypair JSON and parsed into a `Keypair`.

About Fernet:

- Fernet provides authenticated symmetric encryption (confidentiality + integrity checks).
- If ciphertext is modified, decryption fails validation.

Notes
-----

- This feature protects wallet keypair material at rest in your database.
- You are still responsible for broader key management, secret storage, access control, and infrastructure security.
