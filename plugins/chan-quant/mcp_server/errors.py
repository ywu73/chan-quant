from __future__ import annotations


class ChanQuantError(Exception):
    """A stable, user-facing failure from the local Chan Quant adapter."""

    def __init__(self, code: str, message: str, *, status: str = "UNAVAILABLE") -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)

