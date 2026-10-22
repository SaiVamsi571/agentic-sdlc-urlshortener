"""
Base62 Encoding and MurmurHash3 Hashing with Collision Resolution Probing.
Produces deterministic, uniformly distributed 7-character alphanumeric short codes.
"""
import hashlib
from typing import Callable, Optional

from src.constants import (
    BASE62_ALPHABET,
    BASE62_RADIX,
    DEFAULT_CODE_LENGTH,
    DEFAULT_ENCODER_SALT,
)


def encode_base62(num: int, length: int = DEFAULT_CODE_LENGTH) -> str:
    """Encodes a positive integer into a Base62 string with fixed minimum length."""
    if num == 0:
        return BASE62_ALPHABET[0] * length

    chars: list[str] = []
    while num > 0:
        num, rem = divmod(num, BASE62_RADIX)
        chars.append(BASE62_ALPHABET[rem])

    result = "".join(reversed(chars))
    # Pad to target length if shorter
    if len(result) < length:
        result = result.rjust(length, BASE62_ALPHABET[0])
    elif len(result) > length:
        result = result[:length]
    return result


def hash_64bit(data: str) -> int:
    """
    Computes a 64-bit integer hash of the input string.
    Uses MurmurHash3 if available, falling back to truncated SHA-256.
    """
    try:
        import murmurhash  # installed in environment
        # murmurhash.m3h64 returns 64-bit integer
        h = murmurhash.m3h64(data)
        return abs(h)
    except (ImportError, AttributeError):
        import struct
        sha = hashlib.sha256(data.encode("utf-8")).digest()
        # Take first 8 bytes as 64-bit unsigned integer
        return struct.unpack(">Q", sha[:8])[0]


class Base62Encoder:
    """
    Generates deterministic Base62 short codes from original URLs with collision resolution.
    """
    def __init__(
        self,
        salt: str = DEFAULT_ENCODER_SALT,
        code_length: int = DEFAULT_CODE_LENGTH,
    ):
        self.salt = salt
        self.code_length = code_length

    def generate_code(self, original_url: str, collision_attempt: int = 0) -> str:
        """
        Generates a 7-character Base62 short code.
        If collision_attempt > 0, adds attempt nonce to resolve collision deterministically.
        """
        seed = f"{original_url}:{self.salt}"
        if collision_attempt > 0:
            seed = f"{seed}:probe_{collision_attempt}"

        val = hash_64bit(seed)
        return encode_base62(val, length=self.code_length)
