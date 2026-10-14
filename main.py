"""Joy Autopost CLI.

  python src/main.py check                 -> token ve hesabı test eder
  python src/main.py draft                 -> sahne seçer, görsel + caption üretir, drafts/ altına kaydeder
  python src/main.py publish --draft ID    -> taslağı Instagram'da paylaşır
  python src/main.py refresh-token         -> 60 günlük token'ı yeniler (yeni token'ı yazdırmaz)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from claude_tasks import quality_check, write_caption
from common import DRAFTS_DIR, load_history, load_settings, log, now_utc, save_history
from generate import generate_image
from instagram import publish_image, refresh_token, whoami
from scene import build_prompt, pick_scene


def set_output(key: str, value: str) -> None:
    """Expose a value to later GitHub Actions steps."""
    path = os.getenv("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def cmd_check(settings: dict) -> None:
    info = whoami(settings)
    log(f"Bağlı hesap: @{info.get('username')} ({info.get('account_type')}), gönderi: {info.get('media_count')}")


def cmd_draft(settings: dict) -> str:
    scene = pick_scene(settings)
    prompt = build_prompt(settings, scene)
    log(f"Sahne: {scene['scene_id']} / {scene['pose']}")

    image, qc = None, None
    for attempt in range(1, settings["max_attempts"] + 1):
        log(f"Deneme {attempt}/{settings['max_attempts']}")
        candidate = generate_image(settings, prompt)
        qc = quality_check(candidate)
        if qc.get("pass"):
            image = candidate
            break
    if image is None:
        raise SystemExit(f"{settings['max_attempts']} denemede kaliteli görsel çıkmadı. Son QC: {qc}")

    caption = write_caption(scene, settings["caption_language"])

    draft_id = now_utc().strftime("%Y%m%d-%H%M")
    DRAFTS_DIR.mkdir(exist_ok=True)
    (DRAFTS_DIR / f"{draft_id}.jpg").write_bytes(image)
    (DRAFTS_DIR / f"{draft_id}.json").write_text(json.dumps({
        "id": draft_id, "scene": scene, "prompt": prompt, "caption": caption,
        "qc": qc, "status": "draft",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"Taslak hazır: drafts/{draft_id}.jpg")
    set_output("draft_id", draft_id)
    return draft_id


def image_url_for(draft_id: str) -> str:
    base = os.getenv("IMAGE_BASE_URL")
    if not base:
        repo = os.getenv("GITHUB_REPOSITORY")
        branch = os.getenv("GITHUB_REF_NAME", "main")
        if not repo:
            raise SystemExit("IMAGE_BASE_URL veya GITHUB_REPOSITORY gerekli.")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}/drafts"
    return f"{base.rstrip('/')}/{draft_id}.jpg"


def cmd_publish(settings: dict, draft_id: str) -> None:
    meta_path = DRAFTS_DIR / f"{draft_id}.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("status") == "published":
        log("Bu taslak zaten paylaşılmış, atlanıyor.")
        return

    result = publish_image(settings, image_url_for(draft_id), meta["caption"])

    meta.update(status="published", published_at=now_utc().isoformat(), **result)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    history = load_history()
    history.append({"draft_id": draft_id, "scene_id": meta["scene"]["scene_id"],
                    "published_at": meta["published_at"], "permalink": result.get("permalink")})
    save_history(history)
    set_output("permalink", result.get("permalink") or "")


def cmd_refresh(settings: dict) -> None:
    data = refresh_token(settings)
    days = int(data.get("expires_in", 0)) // 86400
    log(f"Token yenilendi, {days} gün geçerli. Yeni token'ı GitHub secret'ına yaz.")
    new_token = data.get("access_token")
    if new_token and os.getenv("GITHUB_OUTPUT"):
        # Mask in logs and hand to the workflow step that updates the secret
        print(f"::add-mask::{new_token}")
        set_output("new_token", new_token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check", "draft", "publish", "refresh-token"])
    parser.add_argument("--draft", help="publish için taslak ID")
    args = parser.parse_args()
    settings = load_settings()

    if args.command == "check":
        cmd_check(settings)
    elif args.command == "draft":
        cmd_draft(settings)
    elif args.command == "publish":
        if not args.draft:
            sys.exit("--draft gerekli")
        cmd_publish(settings, args.draft)
    elif args.command == "refresh-token":
        cmd_refresh(settings)


if __name__ == "__main__":
    main()
