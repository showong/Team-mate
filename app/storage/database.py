"""Storage entry point.

Phase 1 ships an in-memory implementation. We expose a single accessor so the
API layer (and tests) can grab the same `Repositories` instance per process.

Phase 2 plan: replace `_singleton` with a SQLAlchemy session factory and have
each repository wrap a session, while keeping the same public methods.
"""

from __future__ import annotations

from threading import Lock
from typing import Optional

from app.storage.repositories import Repositories


_singleton: Optional[Repositories] = None
_lock = Lock()


def get_repositories() -> Repositories:
    global _singleton
    if _singleton is None:
        with _lock:
            if _singleton is None:
                _singleton = Repositories()
    return _singleton


def reset_repositories() -> None:
    """Test helper. Drops the in-memory state."""
    global _singleton
    with _lock:
        _singleton = None
