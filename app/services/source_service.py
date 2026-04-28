"""Source collection service.

Phase 1 only handles user-supplied source material. External web/API search is
deferred to Phase 2 (it would require provider keys, rate limits, and crawl
policy that don't fit the MVP).
"""

from __future__ import annotations

from typing import Optional


class SourceService:
    def collect(self, agenda: str, conditions: Optional[str] = None) -> str:
        """Return any pre-fetched source material as a single string blob.

        For Phase 1 there is no external collection — this returns an empty
        string and the juniors rely on the LLM's own knowledge plus the
        agenda. This is a deliberate seam for Phase 2.
        """
        return ""
