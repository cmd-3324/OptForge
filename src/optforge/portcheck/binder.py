"""Bind probes that answer "can this host:port be bound right now?"."""

from __future__ import annotations

import os
import socket

from optforge.core.errors import OperationFailed
from optforge.core.net import Endpoint, resolve_endpoints

_WILDCARD_HOSTS = frozenset({"", "*", "any", "all"})
_WILDCARD_ADDRESSES = frozenset({"0.0.0.0", "::"})


class PortBinder:
    """Test bindability without leaving a socket behind.

    Notes:
        * POSIX sets ``SO_REUSEADDR`` so a socket in ``TIME_WAIT`` does not make
          a genuinely free port look busy.
        * Windows sets ``SO_EXCLUSIVEADDRUSE`` instead; ``SO_REUSEADDR`` on
          Windows lets two processes bind the same port, which is exactly the
          bug this tool exists to detect.
        * A successful probe is inherently racy: another process may take the
          port after the probe closes. Callers must treat the answer as a
          snapshot.

    A host the caller named explicitly is never silently assumed free: an
    unresolvable name is an error, because answering "free" for a typo is worse
    than refusing to answer.
    """

    def __init__(self, default_host: str = "0.0.0.0") -> None:
        self._default_host = default_host

    def is_free(self, port: int, host: str | None = None) -> bool:
        """Return ``True`` only if every resolved address for the host binds.

        Raises:
            OperationFailed: if an explicit ``host`` cannot be resolved.
        """
        endpoints = self._endpoints(port, host or self._default_host)
        return all(self._can_bind(endpoint) for endpoint in endpoints)

    def is_free_on_all_interfaces(self, port: int) -> bool:
        """Return ``True`` if both the IPv4 and IPv6 wildcard addresses bind."""
        return self.is_free(port, "0.0.0.0") and self.is_free(port, "::")

    def _endpoints(self, port: int, host: str) -> list[Endpoint]:
        """Return the addresses that should be probed for ``host``.

        A wildcard request that resolves to nothing means the machine has no
        address of that family (IPv6 disabled, for example). There is nothing
        to bind, so the port cannot be occupied there. An explicit host is a
        different question: its failure to resolve is information the caller
        needs, not a free port.
        """
        lowered = host.lower()
        target = None if lowered in _WILDCARD_HOSTS else host
        try:
            return resolve_endpoints(target or "", port, passive=True)
        except OperationFailed:
            if lowered in _WILDCARD_HOSTS or lowered in _WILDCARD_ADDRESSES:
                return []
            raise

    def _can_bind(self, endpoint: Endpoint) -> bool:
        try:
            sock = socket.socket(endpoint.family, socket.SOCK_STREAM)
        except OSError:
            return False
        try:
            self._configure(sock)
            sock.bind(endpoint.sockaddr)
            return True
        except OSError:
            return False
        finally:
            sock.close()

    @staticmethod
    def _configure(sock: socket.socket) -> None:
        if os.name == "nt":
            exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
            if exclusive is not None:
                sock.setsockopt(socket.SOL_SOCKET, exclusive, 1)
            return
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
