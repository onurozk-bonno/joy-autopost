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

import io

from claude_tasks import quality_check, write_caption
from common import DRAFTS_DIR, load_history, load_settings, log, now_utc, save_history
from generate import generate_image
from instagram import publish_image, publish_reel, refresh_token, whoami
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

    has_claude = bool(os.getenv("ANTHROPIC_API_KEY"))
    image, qc = None, None
    for attempt in range(1, settings["max_attempts"] + 1):
        log(f"Deneme {attempt}/{settings['max_attempts']}")
        candidate = to_jpeg(generate_image(settings, prompt, scene))
        if not has_claude:
            # No Claude key: skip automatic QC, the human approves in the GitHub Issue
            image, qc = candidate, {"pass": None, "note": "Claude anahtarı yok, kalite kontrolü onay modunda sende"}
            break
        qc = quality_check(candidate)
        if qc.get("pass"):
            image = candidate
            break
    if image is None:
        raise SystemExit(f"{settings['max_attempts']} denemede kaliteli görsel çıkmadı. Son QC: {qc}")

    if has_claude:
        caption = write_caption(scene, settings["caption_language"])
    else:
        caption = fallback_caption(scene)

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


def to_jpeg(data: bytes) -> bytes:
    """Instagram only accepts JPEG."""
    from PIL import Image

    img = Image.open(io.BytesIO(data)).convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92)
    return out.getvalue()


FALLBACK_LINES = {
    "lake_mist": ("Sis kalkarken göl de, ben de sessizce uyanıyoruz.", "The mist lifts, and the lake and I wake up quietly."),
    "waterfall": ("Suyun sesi, düşüncelerimden daha yüksek.", "The water is louder than my thoughts."),
    "mountain_meadow": ("Rüzgâr kulaklarıma yolu anlatıyor.", "The wind tells my ears which way to go."),
    "river_bed": ("Akıntıya karşı değil, akıntıyla birlikte.", "Not against the current, but with it."),
    "forest_fog": ("Sisli ormanda her ağaç bir sır saklıyor.", "In the foggy forest, every tree keeps a secret."),
    "steppe_sunset": ("Güneş batarken bozkır altına dönüyor.", "At sunset the steppe turns to gold."),
    "beach_dunes": ("Dalgalar gelip gidiyor, ben kalıyorum.", "The waves come and go; I stay."),
    "autumn_lake": ("Sonbahar göle düşünce iki kez güzel.", "Autumn is twice as beautiful when it falls on a lake."),
    "snowy_forest": ("Kar, adımlarımı tek tek saklıyor.", "The snow keeps my footsteps one by one."),
    "canyon_stream": ("Taşların arasından turkuaz bir şarkı akıyor.", "A turquoise song runs between the stones."),
    "lavender_hill": ("Ege ışığında lavanta kokulu bir öğleden sonra.", "A lavender-scented afternoon in Aegean light."),
    "rainy_marsh": ("Yağmurdan sonra dünya yeniden yıkanmış gibi.", "After the rain, the world feels newly washed."),
}


# Instagram allows at most 5 hashtags per post (since Dec 2025): 2 niche + 1 scene + #aiart + 1 rotating
SCENE_TAGS = {
    "lake_mist": "#mistymorning", "waterfall": "#waterfall", "mountain_meadow": "#mountaindog",
    "river_bed": "#riverdog", "forest_fog": "#forestwalk", "steppe_sunset": "#goldenhour",
    "beach_dunes": "#beachdog", "autumn_lake": "#autumnvibes", "snowy_forest": "#snowdog",
    "canyon_stream": "#adventuredog", "lavender_hill": "#lavenderfields", "rainy_marsh": "#rainyday",
}


def fallback_caption(scene: dict) -> str:
    tr, en = FALLBACK_LINES.get(scene["scene_id"], ("Doğada özgür bir ruh.", "A free spirit in the wild."))
    return (
        f"{tr}\nJoy'un hayal sahnelerinden biri 🌿\n\n"
        f"{en}\nOne of Joy's dream scenes.\n\n"
        f"#afghanhound #joytheafghanhound {SCENE_TAGS.get(scene['scene_id'], '#naturedog')} #aiart "
        f"{'#afgantazısı' if hash(scene['scene_id']) % 2 else '#sighthound'}"
    )


def image_url_for(draft_id: str, ext: str = "jpg") -> str:
    base = os.getenv("IMAGE_BASE_URL")
    if not base:
        repo = os.getenv("GITHUB_REPOSITORY")
        branch = os.getenv("GITHUB_REF_NAME", "main")
        if not repo:
            raise SystemExit("IMAGE_BASE_URL veya GITHUB_REPOSITORY gerekli.")
        base = f"https://raw.githubusercontent.com/{repo}/{branch}/drafts"
    return f"{base.rstrip('/')}/{draft_id}.{ext}"


def cmd_publish(settings: dict, draft_id: str) -> None:
    meta_path = DRAFTS_DIR / f"{draft_id}.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("status") == "published":
        log("Bu taslak zaten paylaşılmış, atlanıyor.")
        return

    if meta.get("media_type") == "reel":
        result = publish_reel(settings, image_url_for(draft_id, "mp4"), meta["caption"])
    else:
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
