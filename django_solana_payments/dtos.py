from dataclasses import dataclass

from django.contrib.auth import get_user_model

User = get_user_model()

@dataclass(frozen=True, slots=True)
class CreateSolanaPaymentDTO:
    user: User | None
    label: str | None
    message: str | None
    meta_data: dict | None
    email: str | None = None
