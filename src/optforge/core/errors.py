"""Exception hierarchy for expected, user-facing failures.

Anything raised from this module is safe to show to a human: the message is
written for a terminal, not for a stack trace. Unexpected exceptions are left
alone so they keep their traceback.
"""

from __future__ import annotations


class OptForgeError(Exception):
    """Base class for every expected OptForge failure."""


class PermissionDenied(OptForgeError):
    """The operating system refused access to the requested resource."""


class InvalidInput(OptForgeError):
    """The caller supplied a value that cannot be used."""


class NotFound(OptForgeError):
    """The requested resource does not exist."""


class OperationFailed(OptForgeError):
    """An operation was attempted but could not be completed."""
