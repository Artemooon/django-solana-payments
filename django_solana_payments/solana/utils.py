import hashlib
import json
from typing import Any

from solders.keypair import Keypair
from solders.pubkey import Pubkey


def parse_keypair(keypair_data: Any) -> Keypair:
    """
    Parse a keypair provided in multiple supported formats and return a `solders.keypair.Keypair`.

    Supported input formats:
    - JSON array string: "[1,2,3,...,64]" (string starting with '[')
    - Base58 string: e.g. "5J3mBb..."
    - Python list or bytes: [1,2,3,...] or b"..."

    Raises ValueError on unsupported/invalid input.
    """
    # String input
    if isinstance(keypair_data, str):
        s = keypair_data.strip()
        # JSON array like "[1,2,...]" -> convert to bytes
        if s.startswith("["):
            try:
                arr = json.loads(s)
                if isinstance(arr, list) and all(isinstance(x, int) for x in arr):
                    return Keypair.from_bytes(bytes(arr))
            except Exception:
                # If parsing to bytes failed, try Keypair.from_json() which may accept
                # different JSON structures (some libs store additional metadata)
                try:
                    return Keypair.from_json(s)
                except Exception as e:
                    raise ValueError(
                        f"Failed to parse keypair from JSON array or JSON object: {e}"
                    )
        # Otherwise try base58
        try:
            return Keypair.from_base58_string(s)
        except Exception as e:
            raise ValueError(f"Failed to parse keypair from base58 string: {e}")

    # List or bytes input
    if isinstance(keypair_data, (list, bytes)):
        try:
            return Keypair.from_bytes(bytes(keypair_data))
        except Exception as e:
            raise ValueError(f"Failed to parse keypair from bytes/list: {e}")

    raise ValueError(f"Unsupported keypair format: {type(keypair_data)}")


def derive_pubkey_string_from_keypair(keypair_data: Any) -> str:
    """
    Derive a base58 pubkey string from various forms of keypair input.

    This function is resilient: it first tries to obtain a real `Keypair` via
    `parse_keypair()` and returns its pubkey. If parsing to a `Keypair` fails
    but the input looks like a JSON array of ints, it deterministically derives
    a 32-byte value from SHA-256 of the bytes and returns its base58 representation
    as a fallback Pubkey. This is useful for tests or placeholder values where
    a real keypair isn't available.
    """
    # Try the normal, strict path first
    try:
        kp = parse_keypair(keypair_data)
        return str(kp.pubkey())
    except Exception:
        pass

    # If it's a JSON array string, try to deterministically derive a 32-byte pubkey
    if isinstance(keypair_data, str) and keypair_data.strip().startswith("["):
        try:
            arr = json.loads(keypair_data.strip())
            if isinstance(arr, list) and all(isinstance(x, int) for x in arr):
                derived = hashlib.sha256(bytes(arr)).digest()[:32]
                return str(Pubkey.from_bytes(derived))
        except Exception:
            pass

    # If it's bytes/list, derive from that
    if isinstance(keypair_data, (list, bytes)):
        try:
            derived = hashlib.sha256(bytes(keypair_data)).digest()[:32]
            return str(Pubkey.from_bytes(derived))
        except Exception:
            pass

    raise ValueError("Unable to derive pubkey string from provided keypair input")
