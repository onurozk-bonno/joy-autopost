"""Claude API: image quality check and caption writing."""
from __future__ import annotations

import base64
import json
import os
import re

import anthropic

from common import log, require_env

# Model adı GitHub'da CLAUDE_MODEL değişkeniyle değiştirilebilir.
DEFAULT_MODEL = "claude-sonnet-4-5"


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=require_env("ANTHROPIC_API_KEY"))


def _model() -> str:
    return os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"JSON bulunamadı: {text[:200]}")
    return json.loads(match.group(0))


QC_PROMPT = """You are the quality checker for an Instagram account featuring Joy, an Afghan hound.
Reference look: blue-grey curly textured coat with cream/beige tones, brindle speckles on face
and muzzle, black nose, long grey-cream tasseled ears, cream chest, tail curled into a ring,
NO collar.

Inspect the image and reply ONLY with JSON:
{"pass": true/false, "score": 1-10, "issues": ["..."]}

Fail it if ANY of these: wrong number of legs/paws, deformed face or eyes, merged or melted
limbs, a collar/leash, people, text/watermark, the dog clearly not matching the reference
(e.g. smooth silky long coat, wrong colors), or obvious AI artifacts. Pass only if score >= 7."""


def quality_check(image: bytes) -> dict:
    log("Kalite kontrolü (Claude)...")
    msg = _client().messages.create(
        model=_model(),
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg",
                    "data": base64.standard_b64encode(image).decode()}},
                {"type": "text", "text": QC_PROMPT},
            ],
        }],
    )
    result = _extract_json(msg.content[0].text)
    log(f"QC sonucu: {result}")
    return result


CAPTION_PROMPT = """Write an Instagram caption for @joytheafghanhound, an account of AI-generated
images of Joy, a free-spirited, shy and noble Afghan hound who loves nature.

Scene: {scene}
Language: {language}  ("tr+en" = Turkish first, then a blank line, then English)

Rules:
- Voice: Joy's gentle inner world, poetic but short (1-3 sentences per language). No cheesy puns.
- Mention naturally that this is one of "Joy's dream scenes" / "Joy'un hayal sahneleri" so readers
  know the image is AI-made.
- Then 8-12 relevant hashtags on one line, mixing Turkish and English, and ALWAYS include
  #aiart #yapayzeka #afghanhound.
- No emojis except at most one nature emoji.

Reply ONLY with JSON: {{"caption": "..."}}"""


def write_caption(scene: dict, language: str) -> str:
    log("Caption yazılıyor (Claude)...")
    scene_text = f"{scene['pose']}, {scene['place']}, {scene['light']}, {scene['season']}"
    msg = _client().messages.create(
        model=_model(),
        max_tokens=700,
        messages=[{"role": "user", "content": CAPTION_PROMPT.format(scene=scene_text, language=language)}],
    )
    caption = _extract_json(msg.content[0].text)["caption"].strip()
    if len(caption) > 2200:  # Instagram limit
        caption = caption[:2190].rstrip() + "…"
    return caption
