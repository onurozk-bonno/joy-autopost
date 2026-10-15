"""Haftalık Instagram insights raporu (Instagram API with Instagram Login).

Gerekli izin: instagram_business_manage_insights. İzin yoksa çökmez; Türkçe uyarı verir.
Ortam: IG_ACCESS_TOKEN, IG_USER_ID. Opsiyonel: INSIGHTS_OUT_DIR (rapor klasörü),
HISTORY_FILE (history.json yolu), GRAPH_VERSION.

Metrik notları (Meta dokümanı, 2026):
- impressions/plays kaldırıldı -> `views` kullanılır.
- Hesap: reach, views, profile_views (total_value), follower_count (time_series, son 30 gün).
- Medya: reach, views, likes, comments, saved, shares, total_interactions
  (+ Reels: ig_reels_avg_watch_time). Her metrik ayrı istenir; desteklenmeyen metrik raporu bozmaz.
- Hashtag kaynaklı görüntülenme için Graph API'de hashtag kırılımı YOK; "Hashtag'lerden" sayısı
  sadece Instagram uygulamasındaki post istatistiklerinde görünür. Rapor bunu not olarak belirtir.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = "https://graph.instagram.com"
ROOT = Path(__file__).resolve().parent
if ROOT.name == "src":
    ROOT = ROOT.parent

ACCOUNT_TOTAL = ["reach", "views", "profile_views"]
MEDIA_METRICS = ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions"]
REEL_EXTRA = ["ig_reels_avg_watch_time"]

PERMISSION_CODES = {10, 200}


class PermissionMissing(Exception):
    pass


class ApiError(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
        self.code = (payload.get("error") or {}).get("code")
        super().__init__(str(payload))


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {msg}", flush=True)


def _get(path: str, params: dict, token: str, version: str) -> dict:
    resp = requests.get(f"{BASE}/{version}/{path}", params={**params, "access_token": token}, timeout=30)
    try:
        data = resp.json()
    except ValueError:
        data = {"error": {"message": resp.text[:200], "code": resp.status_code}}
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        msg = str(err.get("message", "")).lower()
        if err.get("code") in PERMISSION_CODES and ("permission" in msg or "insights" in msg or err.get("code") == 10):
            raise PermissionMissing(msg)
        raise ApiError(data)
    return data


def _value(item: dict):
    if "total_value" in item:
        return item["total_value"].get("value")
    vals = item.get("values") or []
    return vals[-1].get("value") if vals else None


def fetch_account(token: str, user_id: str, version: str, now: datetime) -> dict:
    since = int((now - timedelta(days=7)).timestamp())
    until = int(now.timestamp())
    out: dict = {}
    for m in ACCOUNT_TOTAL:
        try:
            d = _get(f"{user_id}/insights", {"metric": m, "period": "day", "metric_type": "total_value",
                                             "since": since, "until": until}, token, version)
            out[m] = _value(d["data"][0]) if d.get("data") else None
        except ApiError as e:
            log(f"Hesap metriği alınamadı ({m}): {e}")
            out[m] = None
    try:  # follower_count: son 30 gün sınırı, günlük seri
        d = _get(f"{user_id}/insights", {"metric": "follower_count", "period": "day",
                                         "since": since, "until": until}, token, version)
        vals = [v.get("value", 0) for v in d["data"][0].get("values", [])] if d.get("data") else []
        out["follower_gain_7d"] = sum(vals) if vals else None
    except ApiError as e:
        log(f"follower_count alınamadı: {e}")
        out["follower_gain_7d"] = None
    try:
        out["followers_count"] = _get("me", {"fields": "followers_count,media_count"}, token, version).get("followers_count")
    except ApiError:
        out["followers_count"] = None
    return out


def shortcode(permalink: str | None) -> str | None:
    m = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([^/?#]+)", permalink or "")
    return m.group(1) if m else None


def list_media(token: str, version: str, limit: int = 50) -> list[dict]:
    d = _get("me/media", {"fields": "id,permalink,media_product_type,media_type,timestamp,caption",
                          "limit": limit}, token, version)
    return d.get("data", [])


def fetch_media_insights(token: str, media: dict, version: str) -> dict:
    metrics = list(MEDIA_METRICS)
    if media.get("media_product_type") == "REELS":
        metrics += REEL_EXTRA
    out = {}
    for m in metrics:
        try:
            d = _get(f"{media['id']}/insights", {"metric": m}, token, version)
            out[m] = _value(d["data"][0]) if d.get("data") else None
        except ApiError as e:
            log(f"{media['id']} {m} alınamadı: {(e.payload.get('error') or {}).get('message', e)}")
            out[m] = None
    return out


def load_history() -> list[dict]:
    cands = [Path(os.environ["HISTORY_FILE"])] if os.getenv("HISTORY_FILE") else []
    cands += [ROOT / "state" / "history.json", ROOT / "history.json"]
    for p in cands:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return []


def collect(token: str, user_id: str, version: str, history: list[dict], now: datetime) -> dict:
    account = fetch_account(token, user_id, version, now)
    by_code = {shortcode(m.get("permalink")): m for m in list_media(token, version)}
    posts = []
    for h in history:
        media = by_code.get(shortcode(h.get("permalink")))
        if not media:
            continue
        posts.append({"draft_id": h.get("draft_id"), "scene_id": h.get("scene_id"),
                      "permalink": h.get("permalink"), "type": media.get("media_product_type"),
                      "caption": media.get("caption") or "",
                      "metrics": fetch_media_insights(token, media, version)})
    return {"account": account, "posts": posts}


def _n(v) -> str:
    return "-" if v is None else str(v)


def _score(p: dict) -> int:
    m = p["metrics"]
    return (m.get("reach") or 0) + 5 * (m.get("saved") or 0) + 3 * (m.get("shares") or 0)


def render_report(data: dict, now: datetime) -> str:
    a, posts = data["account"], data["posts"]
    L = [f"# Joy Insights haftalık rapor - {now:%Y-%m-%d}", "",
         "## Hesap (son 7 gün)", "",
         "| Metrik | Değer |", "|---|---|",
         f"| Erişim (reach) | {_n(a.get('reach'))} |",
         f"| Görüntülenme (views) | {_n(a.get('views'))} |",
         f"| Profil ziyareti | {_n(a.get('profile_views'))} |",
         f"| Takipçi değişimi (7 gün) | {_n(a.get('follower_gain_7d'))} |",
         f"| Toplam takipçi | {_n(a.get('followers_count'))} |", "",
         "## Postlar", ""]
    if not posts:
        L.append("Eşleşen post yok.")
    else:
        L += ["| Post | Tür | Erişim | Görüntülenme | Kaydetme | Beğeni | Yorum | Paylaşım |", "|---|---|---|---|---|---|---|---|"]
        for p in posts:
            m = p["metrics"]
            L.append(f"| [{p['draft_id']}]({p['permalink']}) ({p['scene_id']}) | {p['type']} | {_n(m.get('reach'))} | "
                     f"{_n(m.get('views'))} | {_n(m.get('saved'))} | {_n(m.get('likes'))} | "
                     f"{_n(m.get('comments'))} | {_n(m.get('shares'))} |")
        ranked = sorted(posts, key=_score, reverse=True)
        L += ["", "## En iyi 3 (skor = erişim + 5*kaydetme + 3*paylaşım)", ""]
        L += [f"- {p['draft_id']} ({p['scene_id']}): skor {_score(p)}" for p in ranked[:3]]
        L += ["", "## En zayıf 3", ""]
        L += [f"- {p['draft_id']} ({p['scene_id']}): skor {_score(p)}" for p in ranked[::-1][:3]]
        if len(posts) < 5:
            L += ["", f"Not: Yalnızca {len(posts)} post var; sıralama istatistiksel olarak anlamlı değil (varsayım, veri değil)."]
    L += ["", "## Notlar", "",
          "- Veri: Meta Graph API, 48 saate kadar gecikebilir. `impressions`/`plays` kaldırıldı; `views` kullanılır.",
          "- Hashtag kaynaklı görüntülenme API'de sunulmuyor; Instagram uygulamasında post istatistiklerinden elle bakılmalı.",
          "- En iyi paylaşım saati için en az ~10 post gerekir; şimdilik öneri yok."]
    return "\n".join(L) + "\n"


def main() -> int:
    token, user_id = os.getenv("IG_ACCESS_TOKEN"), os.getenv("IG_USER_ID")
    if not token or not user_id:
        print("Eksik ortam değişkeni: IG_ACCESS_TOKEN ve IG_USER_ID gerekli.")
        return 1
    version = os.getenv("GRAPH_VERSION", "v23.0")
    now = datetime.now(timezone.utc)
    try:
        data = collect(token, user_id, version, load_history(), now)
    except PermissionMissing:
        msg = ("instagram_business_manage_insights izni yok. Meta panelinde (app joytry) izni ekleyip "
               "bu kapsamla yeni bir IG_ACCESS_TOKEN üretin; rapor bu hafta atlandı.")
        print(f"::notice title=Insights izni eksik::{msg}" if os.getenv("GITHUB_ACTIONS") else msg)
        return 0
    except ApiError as e:
        print(f"Instagram API hatası: {e}")
        return 1
    out_dir = Path(os.getenv("INSIGHTS_OUT_DIR") or ROOT / "reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"insights-{now:%Y-%m-%d}.md"
    path.write_text(render_report(data, now), encoding="utf-8")
    log(f"Rapor yazıldı: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
