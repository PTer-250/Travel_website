"""Minimal XiaoHongShu search client used by the backend agent."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import requests

from .signature import generate_request_params, generate_x_b3_traceid


class XhsSearchClient:
    """Wrapper around the XiaoHongShu web search endpoints."""

    def __init__(self, base_url: str = "https://edith.xiaohongshu.com", *, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search_note(
        self,
        query: str,
        cookies_str: str,
        *,
        page: int = 1,
        sort_type_choice: int = 0,
        note_type: int = 0,
        note_time: int = 0,
        note_range: int = 0,
        pos_distance: int = 0,
        geo: Optional[Dict[str, Any]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        payload = self._build_search_payload(
            query,
            page=page,
            sort_type_choice=sort_type_choice,
            note_type=note_type,
            note_time=note_time,
            note_range=note_range,
            pos_distance=pos_distance,
            geo=geo,
        )
        try:
            api = "/api/sns/web/v1/search/notes"
            headers, cookies, data = generate_request_params(cookies_str, api, payload, "POST")
            response = requests.post(
                f"{self.base_url}{api}",
                headers=headers,
                data=data.encode("utf-8"),
                cookies=cookies,
                proxies=proxies,
                timeout=self.timeout,
            )
            res_json: Dict[str, Any] = response.json()
            success = bool(res_json.get("success"))
            msg = res_json.get("msg", "")
            return success, msg, res_json
        except Exception as exc:  # pragma: no cover - network failures
            return False, str(exc), None

    def search_some_note(
        self,
        query: str,
        require_num: int,
        cookies_str: str,
        *,
        sort_type_choice: int = 0,
        note_type: int = 0,
        note_time: int = 0,
        note_range: int = 0,
        pos_distance: int = 0,
        geo: Optional[Dict[str, Any]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, list]:
        page = 1
        collected = []
        try:
            while True:
                success, msg, res_json = self.search_note(
                    query,
                    cookies_str,
                    page=page,
                    sort_type_choice=sort_type_choice,
                    note_type=note_type,
                    note_time=note_time,
                    note_range=note_range,
                    pos_distance=pos_distance,
                    geo=geo,
                    proxies=proxies,
                )
                if not success or not res_json:
                    raise RuntimeError(msg or "search_note failed")
                data = res_json.get("data") or {}
                items = data.get("items")
                if not items:
                    break
                collected.extend(items)
                page += 1
                if len(collected) >= require_num or not data.get("has_more"):
                    break
        except Exception as exc:  # pragma: no cover - network failures
            return False, str(exc), []
        return True, "成功", collected[:require_num]

    def _build_search_payload(
        self,
        query: str,
        *,
        page: int,
        sort_type_choice: int,
        note_type: int,
        note_time: int,
        note_range: int,
        pos_distance: int,
        geo: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        sort_tag = {
            1: "time_descending",
            2: "popularity_descending",
            3: "comment_descending",
            4: "collect_descending",
        }.get(sort_type_choice, "general")

        note_type_tag = {1: "视频笔记", 2: "普通笔记"}.get(note_type, "不限")
        note_time_tag = {1: "一天内", 2: "一周内", 3: "半年内"}.get(note_time, "不限")
        note_range_tag = {1: "已看过", 2: "未看过", 3: "已关注"}.get(note_range, "不限")
        pos_distance_tag = {1: "同城", 2: "附近"}.get(pos_distance, "不限")

        geo_payload = json.dumps(geo, separators=(",", ":")) if geo else ""

        return {
            "keyword": query,
            "page": page,
            "page_size": 20,
            "search_id": generate_x_b3_traceid(21),
            "sort": "general",
            "note_type": 0,
            "ext_flags": [],
            "filters": [
                {"tags": [sort_tag], "type": "sort_type"},
                {"tags": [note_type_tag], "type": "filter_note_type"},
                {"tags": [note_time_tag], "type": "filter_note_time"},
                {"tags": [note_range_tag], "type": "filter_note_range"},
                {"tags": [pos_distance_tag], "type": "filter_pos_distance"},
            ],
            "geo": geo_payload,
            "image_formats": ["jpg", "webp", "avif"],
        }

    def get_note_detail(
        self,
        note_id: str,
        cookies_str: str,
        *,
        xsec_token: Optional[str] = None,
        xsec_source: str = "pc_search",
        proxies: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        try:
            api = "/api/sns/web/v1/feed"
            data = {
                "source_note_id": note_id,
                "image_formats": ["jpg", "webp", "avif"],
                "extra": {"need_body_topic": "1"},
                "xsec_source": xsec_source,
            }
            if xsec_token:
                data["xsec_token"] = xsec_token
            headers, cookies, payload = generate_request_params(cookies_str, api, data, "POST")
            response = requests.post(
                f"{self.base_url}{api}",
                headers=headers,
                data=payload.encode("utf-8"),
                cookies=cookies,
                proxies=proxies,
                timeout=self.timeout,
            )
            res_json: Dict[str, Any] = response.json()
            success = bool(res_json.get("success"))
            msg = res_json.get("msg", "")
            return success, msg, res_json
        except Exception as exc:  # pragma: no cover - network failures
            return False, str(exc), None


__all__ = ["XhsSearchClient"]
