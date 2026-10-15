"""Instagram API with Instagram Login: publish a single image post."""
from __future__ import annotations

import time

import requests

from common import log, require_env

BASE = "https://graph.instagram.com"


def _api(settings: dict) -> str:
    return f"{BASE}/{settings.get('graph_version', 'v23.0')}"


def _check(resp: requests.Response) -> dict:
    data = resp.json()
    if resp.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Instagram API hatası: {data}")
    return data


def publish_image(settings: dict, image_url: str, caption: str) -> dict:
    token = require_env("IG_ACCESS_TOKEN")
    user_id = require_env("IG_USER_ID")
    api = _api(settings)

    log("Medya konteyneri oluşturuluyor...")
    container = _check(requests.post(
        f"{api}/{user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=60,
    ))
    creation_id = container["id"]

    # Wait until Instagram has fetched and processed the image
    for _ in range(20):
        status = _check(requests.get(
            f"{api}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ))
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram görseli işleyemedi: {status}")
        time.sleep(5)

    log("Yayınlanıyor...")
    published = _check(requests.post(
        f"{api}/{user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    ))
    media_id = published["id"]
    info = _check(requests.get(
        f"{api}/{media_id}",
        params={"fields": "permalink", "access_token": token},
        timeout=30,
    ))
    log(f"Paylaşıldı: {info.get('permalink')}")
    return {"media_id": media_id, "permalink": info.get("permalink")}


def publish_reel(settings: dict, video_url: str, caption: str) -> dict:
    token = require_env("IG_ACCESS_TOKEN")
    user_id = require_env("IG_USER_ID")
    api = _api(settings)

    log("Reels konteyneri oluşturuluyor...")
    container = _check(requests.post(
        f"{api}/{user_id}/media",
        data={"media_type": "REELS", "video_url": video_url, "caption": caption,
              "share_to_feed": "true", "access_token": token},
        timeout=60,
    ))
    creation_id = container["id"]

    # Videos take longer to process: wait up to ~10 minutes
    for _ in range(60):
        status = _check(requests.get(
            f"{api}/{creation_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        ))
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram videoyu işleyemedi: {status}")
        time.sleep(10)
    else:
        raise RuntimeError("Video işleme zaman aşımına uğradı")

    log("Reels yayınlanıyor...")
    published = _check(requests.post(
        f"{api}/{user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    ))
    media_id = published["id"]
    info = _check(requests.get(
        f"{api}/{media_id}",
        params={"fields": "permalink", "access_token": token},
        timeout=30,
    ))
    log(f"Reels paylaşıldı: {info.get('permalink')}")
    return {"media_id": media_id, "permalink": info.get("permalink")}


def refresh_token(settings: dict) -> dict:
    """Long-lived tokens last 60 days; refreshing returns a token valid for another 60 days."""
    token = require_env("IG_ACCESS_TOKEN")
    return _check(requests.get(
        f"{BASE}/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=30,
    ))


def whoami(settings: dict) -> dict:
    token = require_env("IG_ACCESS_TOKEN")
    return _check(requests.get(
        f"{_api(settings)}/me",
        params={"fields": "user_id,username,account_type,media_count", "access_token": token},
        timeout=30,
    ))
