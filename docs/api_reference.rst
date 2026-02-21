.. _api_reference:

API Reference
=============

This section provides auto-generated references for public modules, classes, and helper functions in `django-solana-payments`.

Core Services
-------------

VerifyTransactionService
^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: django_solana_payments.services.verify_transaction_service.VerifyTransactionService
   :members:
   :show-inheritance:
   :member-order: bysource

SolanaPaymentsService
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: django_solana_payments.services.solana_payments_service.SolanaPaymentsService
   :members:
   :show-inheritance:
   :member-order: bysource

OneTimeWalletService
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: django_solana_payments.services.one_time_wallet_service.OneTimeWalletService
   :members:
   :show-inheritance:
   :member-order: bysource

Main wallet service functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: django_solana_payments.services.main_wallet_service
   :members:
   :member-order: bysource

Additional Service Modules
--------------------------

.. automodule:: django_solana_payments.services.verify_transaction_service
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.services.one_time_wallet_service
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.services.solana_payments_service
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.services.wallet_encryption_service
   :members:
   :member-order: bysource

Models
------

AbstractPaymentToken
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: django_solana_payments.models.AbstractPaymentToken
   :members:
   :show-inheritance:
   :member-order: bysource

AbstractSolanaPayment
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: django_solana_payments.models.AbstractSolanaPayment
   :members:
   :show-inheritance:
   :member-order: bysource

Concrete models
^^^^^^^^^^^^^^^

.. automodule:: django_solana_payments.models
   :members:
   :exclude-members: AbstractPaymentToken, AbstractSolanaPayment
   :member-order: bysource

API Layer
---------

Views
^^^^^

.. automodule:: django_solana_payments.api.views.initiate_solana_payment
   :members:

.. automodule:: django_solana_payments.api.views.solana_pay_payment
   :members:

.. automodule:: django_solana_payments.api.views.verify_transfer
   :members:

.. automodule:: django_solana_payments.api.views.allowed_payment_crypto_token
   :members:

Serializers
^^^^^^^^^^^

.. automodule:: django_solana_payments.api.serializers
   :members:
   :member-order: bysource

Helpers
-------

.. automodule:: django_solana_payments.helpers
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.api.helpers
   :members:
   :member-order: bysource

Signals
-------

.. automodule:: django_solana_payments.signals
   :members:
   :member-order: bysource

Core Types and Exceptions
-------------------------

.. automodule:: django_solana_payments.choices
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.exceptions
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.solana.exceptions
   :members:
   :member-order: bysource

Solana Clients
--------------

.. automodule:: django_solana_payments.solana.base_solana_client
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.solana.solana_balance_client
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.solana.solana_token_client
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.solana.solana_transaction_query_client
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.solana.solana_transaction_sender_client
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.solana.solana_transaction_builder
   :members:
   :member-order: bysource

.. automodule:: django_solana_payments.solana.utils
   :members:
   :member-order: bysource

Admin
-----

Admin classes are registered in `django_solana_payments.admin` and require `django.contrib.admin`
to be present in `INSTALLED_APPS`.
