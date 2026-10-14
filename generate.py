"""Image generation via Replicate (Joy's Flux LoRA)."""
from __future__ import annotations

import replicate
import requests

from common import log, require_env


def generate_image(settings: dict, prompt: str) -> bytes:
    require_env("REPLICATE_API_TOKEN")
    model = settings.get("replicate_model")
    if not model:
        raise SystemExit(
            "replicate_model boş. LoRA eğitimi bitince settings.yaml'a ya da "
            "REPLICATE_MODEL secret'ına 'kullanici/model:versiyon' yaz."
        )

    log(f"Görsel üretiliyor: {model}")
    output = replicate.run(
        model,
        input={
            "prompt": prompt,
            "aspect_ratio": settings.get("aspect_ratio", "4:5"),
            "num_outputs": 1,
            "output_format": "jpg",
            "output_quality": 95,
            "lora_scale": settings.get("lora_scale", 1.0),
            "num_inference_steps": 28,
        },
    )
    item = output[0] if isinstance(output, list) else output
    # Newer replicate clients return FileOutput objects with .read()
    if hasattr(item, "read"):
        return item.read()
    resp = requests.get(str(item), timeout=120)
    resp.raise_for_status()
    return resp.content
