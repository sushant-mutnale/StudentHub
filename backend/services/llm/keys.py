import hashlib
from dataclasses import dataclass, field
from typing import Iterator, Optional, Sequence


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ApiKey:
    index: int
    value: str = field(repr=False)
    keyhash: str


class ApiKeyPool:
    def __init__(self, keys: Sequence[Optional[str]]):
        cleaned = [key.strip() for key in keys if key and key.strip()]
        self._keys = tuple(
            ApiKey(index=index, value=value, keyhash=fingerprint(value))
            for index, value in enumerate(cleaned)
        )

    def __len__(self) -> int:
        return len(self._keys)

    def __iter__(self) -> Iterator[ApiKey]:
        return iter(self._keys)

    @property
    def empty(self) -> bool:
        return not self._keys
