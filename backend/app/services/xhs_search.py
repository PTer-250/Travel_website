"""XiaoHongShu search service (text-only)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

from app.core.config import settings

SPIDER_XHS_DIR = Path(__file__).resolve().parents[2] / "Spider_XHS"
if SPIDER_XHS_DIR.exists():  # pragma: no cover - import guard
    parent_dir = SPIDER_XHS_DIR.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

try:
    # Lazy import to keep package boundary small
    from Spider_XHS.client import XhsSearchClient
except Exception as exc:  # pragma: no cover - optional dependency import
    XhsSearchClient = None  # type: ignore[misc, assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class XhsSearchService:
    """Perform keyword searches on XiaoHongShu without downloading media."""

    def __init__(self, *, cookies: Optional[str] = None, default_limit: int = 6):
        self.cookies = (cookies or settings.xhs_cookies or "").strip()
        self.default_limit = default_limit
        self._client = XhsSearchClient() if XhsSearchClient else None

    def _ensure_client(self) -> None:
        if _IMPORT_ERROR:
            raise RuntimeError(f"XHS client import failed: {_IMPORT_ERROR}")
        if not self._client:
            raise RuntimeError("XHS search client unavailable")
        if not self.cookies:
            raise RuntimeError("XHS cookies are not configured in settings.xhs_cookies")

    async def search_notes(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        sort_type: int = 0,
        note_type: int = 0,
        note_time: int = 0,
        note_range: int = 0,
        pos_distance: int = 0,
        geo: Optional[dict] = None,
    ) -> List[dict]:
        """Search notes by keyword and return text-only metadata."""

        self._ensure_client()
        take = limit or self.default_limit

        success, msg, notes = await asyncio.to_thread(
            self._client.search_some_note,  # type: ignore[union-attr]
            query,
            take,
            self.cookies,
            sort_type_choice=sort_type,
            note_type=note_type,
            note_time=note_time,
            note_range=note_range,
            pos_distance=pos_distance,
            geo=geo,
            proxies=None,
        )

        if not success:
            raise RuntimeError(f"XHS search failed: {msg}")

        filtered = [note for note in notes if note.get("model_type") == "note"][:take]
        normalized: List[dict] = []
        for item in filtered:
            detail = await self._fetch_note_detail(item)
            normalized.append(self._normalize_note(item, detail=detail))
        return normalized

    async def _fetch_note_detail(self, note_summary: dict) -> Optional[dict]:
        if not self._client:
            return None
        note_id = note_summary.get("id")
        if not note_id:
            return None
        xsec_token = note_summary.get("xsec_token")
        xsec_source = note_summary.get("xsec_source") or "pc_search"
        success, msg, detail = await asyncio.to_thread(
            self._client.get_note_detail,
            note_id,
            self.cookies,
            xsec_token=xsec_token,
            xsec_source=xsec_source,
            proxies=None,
        )
        if not success:
            return None
        return detail

    def _normalize_note(self, note: dict, *, detail: Optional[dict] = None) -> dict:
        card = note.get("note_card") or {}
        interact = card.get("interact_info") or {}
        user = card.get("user") or {}

        note_id = note.get("id") or card.get("id")
        token = note.get("xsec_token")
        token_suffix = f"?xsec_token={token}" if token else ""
        url = f"https://www.xiaohongshu.com/explore/{note_id}{token_suffix}" if note_id else None

        tags = [tag.get("name") for tag in (card.get("tag_list") or []) if tag.get("name")]

        detail_desc = self._extract_detail_desc(detail)
        desc = detail_desc or card.get("desc") or card.get("display_title") or ""

        return {
            "id": note_id,
            "title": card.get("title") or card.get("display_title") or "",
            "desc": desc,
            "liked_count": interact.get("liked_count"),
            "collected_count": interact.get("collected_count"),
            "comment_count": interact.get("comment_count"),
            "share_count": interact.get("share_count"),
            "author": user.get("nickname") or user.get("user_id"),
            "avatar": user.get("avatar"),
            "tags": tags,
            "url": url,
        }

    def _extract_detail_desc(self, detail: Optional[dict]) -> str:
        if not detail:
            return ""
        try:
            items = (detail.get("data") or {}).get("items") or []
            first = items[0] if items else None
            if not first:
                return ""
            note_card = first.get("note_card") or first.get("note") or first
            return note_card.get("desc") or note_card.get("content") or ""
        except Exception:  # pragma: no cover - defensive
            return ""
