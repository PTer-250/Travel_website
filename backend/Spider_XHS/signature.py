"""Request signing utilities for XiaoHongShu web APIs."""

from __future__ import annotations

import importlib.resources as importlib_resources
import json
import random
from pathlib import Path
from typing import Any, Dict, Tuple

import execjs

PACKAGE_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_ROOT / "static"


def _patch_xray_source(source: str) -> str:
    """Ensure webpack chunks are required via absolute paths."""

    static_dir = STATIC_DIR
    replacements = {
        "require('./xhs_xray_pack1.js');": static_dir / "xhs_xray_pack1.js",
        "require('../static/xhs_xray_pack1.js');": static_dir / "xhs_xray_pack1.js",
        "require('./static/xhs_xray_pack1.js');": static_dir / "xhs_xray_pack1.js",
        "require('./xhs_xray_pack2.js');": static_dir / "xhs_xray_pack2.js",
        "require('../static/xhs_xray_pack2.js');": static_dir / "xhs_xray_pack2.js",
        "require('./static/xhs_xray_pack2.js');": static_dir / "xhs_xray_pack2.js",
    }

    for placeholder, path in replacements.items():
        absolute = path.as_posix()
        source = source.replace(placeholder, f"require('{absolute}');")
    return source


def _load_static_source(filename: str) -> str:
    """Load a helper JavaScript file regardless of package location."""

    package = __package__ or "Spider_XHS"
    attempts = []

    try:
        resource = importlib_resources.files(package).joinpath("static", filename)
        attempts.append(str(resource))
        text = resource.read_text(encoding="utf-8")
        if filename == "xhs_xray.js":
            text = _patch_xray_source(text)
        return text
    except (FileNotFoundError, ModuleNotFoundError):
        pass

    path = STATIC_DIR / filename
    attempts.append(str(path))
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if filename == "xhs_xray.js":
            text = _patch_xray_source(text)
        return text

    searched = ", ".join(attempts)
    raise FileNotFoundError(f"Missing XiaoHongShu helper script: {filename} (checked: {searched})")


def _compile_js(filename: str) -> Any:
    return execjs.compile(_load_static_source(filename))


_XS_JS = _compile_js("xhs_xs_xsc_56.js")
_XRAY_JS = _compile_js("xhs_xray.js")


def trans_cookies(cookies_str: str) -> Dict[str, str]:
    """Convert the raw cookie string into a dict understood by requests."""

    if not cookies_str:
        raise ValueError("XHS cookies string is empty")
    pairs = [part.strip() for part in cookies_str.split(";") if part.strip()]
    cookies: Dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        cookies[key] = value
    if "a1" not in cookies:
        raise ValueError("XHS cookies must contain the 'a1' token")
    return cookies


def generate_x_b3_traceid(length: int = 16) -> str:
    alphabet = "abcdef0123456789"
    return "".join(random.choice(alphabet) for _ in range(length))


def generate_xray_traceid() -> str:
    return _XRAY_JS.call("traceId")


def get_request_headers_template() -> Dict[str, str]:
    return {
        "authority": "edith.xiaohongshu.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.xiaohongshu.com",
        "pragma": "no-cache",
        "referer": "https://www.xiaohongshu.com/",
        "sec-ch-ua": '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
        ),
        "x-b3-traceid": "",
        "x-mns": "unload",
        "x-s": "",
        "x-s-common": "",
        "x-t": "",
        "x-xray-traceid": generate_xray_traceid(),
    }


def _generate_xs_xs_common(a1: str, api: str, data: Any, method: str) -> Tuple[str, int, str]:
    payload = data if data else ""
    ret = _XS_JS.call("get_request_headers_params", api, payload, a1, method)
    return ret["xs"], ret["xt"], ret["xs_common"]


def generate_headers(a1: str, api: str, data: Any = None, method: str = "POST") -> Tuple[Dict[str, str], str]:
    xs, xt, xs_common = _generate_xs_xs_common(a1, api, data, method)
    x_b3_traceid = generate_x_b3_traceid()
    headers = get_request_headers_template()
    headers["x-s"] = xs
    headers["x-t"] = str(xt)
    headers["x-s-common"] = xs_common
    headers["x-b3-traceid"] = x_b3_traceid
    serialized = json.dumps(data, separators=(",", ":"), ensure_ascii=False) if data else ""
    return headers, serialized


def generate_request_params(
    cookies_str: str,
    api: str,
    data: Any = None,
    method: str = "POST",
) -> Tuple[Dict[str, str], Dict[str, str], str]:
    cookies = trans_cookies(cookies_str)
    headers, serialized = generate_headers(cookies["a1"], api, data, method)
    return headers, cookies, serialized


__all__ = [
    "generate_request_params",
    "generate_x_b3_traceid",
    "trans_cookies",
]
