import datetime
from itertools import islice
from typing import Iterable, Iterator, List, TypeVar

from django.utils import timezone

from django_solana_payments.settings import solana_payments_settings

T = TypeVar("T")


def set_default_expiration_date():
    """
    Calculates the expiration date based on the user-defined
    SOLANA_PAYMENTS['EXPIRATION_MINUTES'] setting.
    """
    minutes = solana_payments_settings.EXPIRATION_MINUTES
    return timezone.now() + datetime.timedelta(minutes=minutes)


def chunked(iterable: Iterable[T], size: int) -> Iterator[List[T]]:
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk
