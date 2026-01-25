from typing import Union

from rest_framework.exceptions import APIException


class BaseAPIException(APIException):
    """
    Base API exception.
    """

    def __init__(self, error_message: Union[str, dict], status_code: int):
        self.error_message = error_message
        self.status_code = status_code
        super().__init__(self.error_message)


class ViewException(BaseAPIException):
    """Base view exception."""


class SolanaPaymentsError(Exception):
    """Base exception for the library."""

    code: str = "solana_payments_error"
    message: str = "Solana payments error"


class PaymentError(SolanaPaymentsError):
    pass


class PaymentNotFoundError(PaymentError):
    code = "payment_not_found"

    def __init__(self, reference: str):
        super().__init__(f"Payment with reference '{reference}' was not found")
        self.reference = reference


class PaymentExpiredError(PaymentError):
    code = "payment_expired"


class PaymentPricingError(PaymentError):
    code = "payment_pricing_error"


class PaymentTokenPriceNotFoundError(PaymentPricingError):
    code = "payment_token_price_not_found"

    def __init__(self, token_mint_address: str):
        super().__init__(
            f"Payment token price not found for mint_address={token_mint_address}"
        )


class InvalidPaymentAmountError(PaymentError):
    code = "invalid_payment_amount"

    def __init__(self, expected, actual):
        super().__init__(
            f"Invalid transfer amount: expected={expected}, actual={actual}"
        )
        self.expected = expected
        self.actual = actual


class PaymentNotConfirmedError(PaymentError):
    pass
