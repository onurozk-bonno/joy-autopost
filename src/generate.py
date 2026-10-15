"""Image generation.

Backends (IMAGE_BACKEND variable):
  - "pollinations": free, no API key. Joy is described in text only (no trained model),
    so she will look similar but not identical.
  - "replicate": Joy's trained Flux LoRA (most accurate). Needs REPLICATE_API_TOKEN + REPLICATE_MODEL.
"""
from __future__ import annotations

import os
import random
import time
import urllib.parse

import requests

from common import log, require_env


def _backend(settings: dict) -> str:
    return os.getenv("IMAGE_BACKEND") or settings.get("image_backend", "pollinations")


def _pollinations(settings: dict, prompt: str) -> bytes:
    w, h = 1080, 1350  # 4:5 Instagram portrait
    seed = random.randint(1, 10_000_000)
    url = (
        "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt, safe="")
        + f"?width={w}&height={h}&model=flux&nologo=true&enhance=false&seed={seed}"
    )
    headers = {}
    if os.getenv("POLLINATIONS_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['POLLINATIONS_TOKEN']}"
    last_err = None
    for attempt in range(4):
        try:
            log(f"Pollinations ile görsel üretiliyor (seed {seed}, deneme {attempt + 1})")
            resp = requests.get(url, headers=headers, timeout=180)
            ctype = resp.headers.get("content-type", "")
            if resp.status_code == 200 and ctype.startswith("image/"):
                return resp.content
            last_err = f"HTTP {resp.status_code} {ctype} {resp.text[:200]}"
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"Pollinations görsel üretemedi: {last_err}")


def _replicate(settings: dict, prompt: str) -> bytes:
    import replicate  # only needed for this backend

    require_env("REPLICATE_API_TOKEN")
    model = settings.get("replicate_model")
    if not model:
        raise SystemExit("REPLICATE_MODEL boş. LoRA eğitimi bitince 'kullanici/model:versiyon' yaz.")
    log(f"Replicate ile görsel üretiliyor: {model}")
    output = replicate.run(model, input={
        "prompt": prompt,
        "aspect_ratio": settings.get("aspect_ratio", "4:5"),
        "num_outputs": 1,
        "output_format": "jpg",
        "output_quality": 95,
        "lora_scale": settings.get("lora_scale", 1.0),
        "num_inference_steps": 28,
    })
    item = output[0] if isinstance(output, list) else output
    if hasattr(item, "read"):
        return item.read()
    resp = requests.get(str(item), timeout=120)
    resp.raise_for_status()
    return resp.content


# ---------------- Gemini (reference photos, no training) ----------------
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _reference_images(max_refs: int = 4) -> list[bytes]:
    """Joy reference photos: files in refs/ first, then recent Instagram posts."""
    from common import ROOT

    refs: list[bytes] = []
    ref_dir = ROOT / "refs"
    if ref_dir.is_dir():
        for f in sorted(ref_dir.iterdir()):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png") and len(refs) < max_refs:
                refs.append(f.read_bytes())
    if len(refs) < max_refs and os.getenv("IG_ACCESS_TOKEN"):
        try:
            data = requests.get(
                "https://graph.instagram.com/me/media",
                params={"fields": "media_type,media_url,children{media_type,media_url}",
                        "limit": 20, "access_token": os.environ["IG_ACCESS_TOKEN"]},
                timeout=30,
            ).json().get("data", [])
            urls = []
            for m in data:
                if m.get("media_type") == "IMAGE":
                    urls.append(m["media_url"])
                elif m.get("media_type") == "CAROUSEL_ALBUM":
                    urls += [c["media_url"] for c in m.get("children", {}).get("data", [])
                             if c.get("media_type") == "IMAGE"][:1]
            for u in urls:
                if len(refs) >= max_refs:
                    break
                r = requests.get(u, timeout=60)
                if r.ok:
                    refs.append(r.content)
        except Exception as e:  # references are best-effort
            log(f"Instagram referansları alınamadı: {e}")
    log(f"{len(refs)} referans fotoğraf kullanılıyor")
    return refs


GEMINI_INSTRUCTION = (
    "The reference photos show Joy, a real Afghan hound. Create ONE new photorealistic photo of "
    "this exact same dog: same face, same muzzle color and markings, same coat color, curly/wavy "
    "coat texture and length, same long feathered ears. Ignore any people or other animals in the "
    "references. Scene: {scene}. Natural light, shot on a phone/35mm camera, shallow depth of field, "
    "candid and real-looking, not illustrated. Vertical 4:5 composition with the whole dog in frame. "
    "No people, no leash, no text, no watermark, correct anatomy with four legs."
)


def _gemini(settings: dict, scene_text: str) -> bytes:
    import base64

    key = require_env("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL") or settings.get("gemini_model", "gemini-2.5-flash-image")
    parts = [{"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(img).decode()}}
             for img in _reference_images()]
    parts.append({"text": GEMINI_INSTRUCTION.format(scene=scene_text)})
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "4:5"}},
    }
    log(f"Gemini ile görsel üretiliyor: {model}")
    last = None
    for attempt in range(3):
        resp = requests.post(GEMINI_URL.format(model=model), json=body,
                             headers={"x-goog-api-key": key}, timeout=180)
        data = resp.json()
        if resp.ok:
            for cand in data.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    blob = part.get("inlineData") or part.get("inline_data")
                    if blob and blob.get("data"):
                        return base64.b64decode(blob["data"])
            last = f"görsel dönmedi: {str(data)[:300]}"
        else:
            last = f"HTTP {resp.status_code}: {str(data)[:300]}"
        log(f"Gemini denemesi başarısız ({last}), tekrar deneniyor")
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Gemini görsel üretemedi: {last}")


def generate_image(settings: dict, prompt: str, scene: dict | None = None) -> bytes:
    if _backend(settings) == "gemini":
        scene_text = (f"{scene['pose']}, {scene['place']}, {scene['season']}, {scene['light']}"
                      if scene else prompt)
        return _gemini(settings, scene_text)
    if _backend(settings) == "replicate":
        return _replicate(settings, prompt)
    # Pollinations has no LoRA: drop the trigger word so it isn't drawn as text
    return _pollinations(settings, prompt.replace(settings.get("trigger_word", "JOYDOG") + ", ", ""))
