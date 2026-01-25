from dataclasses import dataclass

from solders.signature import Signature
from solders.transaction_status import TransactionConfirmationStatus


@dataclass(frozen=True, slots=True)
class ConfirmTransactionDTO:
    tx_signature: Signature
    confirmation_status: TransactionConfirmationStatus | None = None
