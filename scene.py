"""Pick today's scene and build the image prompt."""
from __future__ import annotations

import random

from common import load_history, load_scenes, now_utc


def current_season(month: int) -> str:
    # Northern hemisphere (Türkiye)
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


TIMES_OF_DAY = [
    "soft morning light",
    "golden hour light",
    "overcast diffused light",
    "late afternoon backlight",
    "early morning blue hour",
]


def pick_scene(settings: dict, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random()
    season = current_season(now_utc().month)
    scenes = load_scenes()
    recent = [h["scene_id"] for h in load_history()[-settings["no_repeat_window"]:]]

    candidates = [s for s in scenes if season in s.get("seasons", []) and s["id"] not in recent]
    if not candidates:
        candidates = [s for s in scenes if s["id"] not in recent] or scenes

    scene = rng.choice(candidates)
    return {
        "scene_id": scene["id"],
        "place": scene["place"],
        "pose": rng.choice(scene["poses"]),
        "light": rng.choice(TIMES_OF_DAY),
        "season": season,
    }


def build_prompt(settings: dict, scene: dict) -> str:
    return (
        f"{settings['dog_description']}, {scene['pose']}, {scene['place']}, "
        f"{scene['season']} season, {scene['light']}. {settings['style']}. "
        f"{settings['negative_hints']}."
    )
