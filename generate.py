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


def generate_image(settings: dict, prompt: str) -> bytes:
    if _backend(settings) == "replicate":
        return _replicate(settings, prompt)
    # Pollinations has no LoRA: drop the trigger word so it isn't drawn as text
    return _pollinations(settings, prompt.replace(settings.get("trigger_word", "JOYDOG") + ", ", ""))
