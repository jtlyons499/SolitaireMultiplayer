"""Persistent avatar choices; independent of Pygame and installed artwork."""
import random
import re

import hashlib

def stable_seed(*parts):
    digest=hashlib.sha256('|'.join(map(str,parts)).encode('utf-8')).digest()
    return int.from_bytes(digest[:8],'big')

AVATAR_VERSION = 1
AVATAR_VARIANTS = 10
# Composition order. Every custom part uses one aligned square canvas.
AVATAR_PARTS = {
    "background": ("backgrounds", "background"),
    "base": ("bases", "base"),
    "shirt": ("shirts", "shirt"),
    "nose": ("noses", "nose"),
    "eyes": ("eyes", "eyes"),
    "smile": ("smiles", "smile"),
    "eyebrows": ("eyebrows", "eyebrows"),
    "hair": ("hair", "hair"),
    "glasses": ("glasses", "glasses"),
}
REQUIRED_PARTS = ("base", "shirt", "nose", "eyes", "smile")
OPTIONAL_PARTS = ("background", "eyebrows", "hair", "glasses")
AGE_BANDS = ("child", "teen", "adult", "veteran")


def avatar_age_band(age):
    try:
        age = max(0, int(age))
    except (ValueError, TypeError, OverflowError):
        age = 10
    return "child" if age < 13 else "teen" if age < 20 else "adult" if age < 50 else "veteran"


def valid_part_id(part, value):
    """Restrict saved art references to the named local bank, never arbitrary paths."""
    if part not in AVATAR_PARTS or not isinstance(value, str):
        return False
    prefix = AVATAR_PARTS[part][1]
    return re.fullmatch(rf"{prefix}_(0[1-9]|10)", value) is not None


def make_avatar_choices(npc):
    legacy = npc.get("portrait_style") or {}
    existing = npc.get("avatar") or {}
    if not isinstance(legacy, dict):
        legacy = {}
    if not isinstance(existing, dict):
        existing = {}
    seed = existing.get("seed", legacy.get("seed", stable_seed(npc.get("id"), "avatar")))
    try:
        seed = int(seed)
    except (ValueError, TypeError, OverflowError):
        seed = stable_seed(npc.get("id"), "avatar")
    rng = random.Random(seed)
    result = {"version": AVATAR_VERSION, "seed": seed}
    for part, (_folder, prefix) in AVATAR_PARTS.items():
        result[part] = f"{prefix}_{rng.randint(1, AVATAR_VARIANTS):02d}"
    result["background"] = None
    if not bool(legacy.get("glasses", rng.random() < 0.2)):
        result["glasses"] = None
    return result


def ensure_prospect_avatar(npc):
    """Complete once, preserving valid saved IDs even before those PNGs exist."""
    defaults = make_avatar_choices(npc)
    existing = npc.get("avatar")
    if isinstance(existing, dict):
        defaults.update({part: value for part, value in existing.items()
                         if valid_part_id(part, value)
                         or (part in OPTIONAL_PARTS and value is None)})
    npc["avatar"] = defaults
    npc.pop("portrait_style", None)
    return defaults


def get_avatar_choices(npc):
    """Pure read for renderers; save migration happens in the Career world."""
    source = dict(npc)
    return ensure_prospect_avatar(source)

