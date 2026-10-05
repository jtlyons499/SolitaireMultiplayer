"""Compose NPC portraits from the artist's PNG layers or player-avatar art."""
from collections import OrderedDict
from pathlib import Path
import time

import pygame

from npc_avatars import (AGE_BANDS, AVATAR_PARTS, REQUIRED_PARTS,
                         avatar_age_band, get_avatar_choices, valid_part_id)

AVATAR_CANVAS = (512, 512)
AVATAR_ART_ROOT = Path(__file__).resolve().parent / "assets" / "npcs" / "avatar"
PLAYER_PARTS = {"base": "base", "eyes": "eyes", "hair": "hair",
                "glasses": "glasses", "shirt": "top"}


def _remember(cache, key, value, maximum):
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > maximum:
        cache.popitem(last=False)
    return value


def _square_image(image, size):
    """Preserve proportions; rectangular player art receives clear padding."""
    size = int(size)
    if size <= 0:
        raise ValueError("NPC portrait size must be positive")
    width, height = image.get_size()
    scale = min(size / width, size / height)
    dimensions = (max(1, round(width * scale)), max(1, round(height * scale)))
    result = pygame.Surface((size, size), pygame.SRCALPHA)
    scaled = pygame.transform.smoothscale(image, dimensions)
    result.blit(scaled, scaled.get_rect(center=result.get_rect().center))
    return result


class NpcAvatarRenderer:
    def __init__(self, art_root=AVATAR_ART_ROOT, refresh_interval=2.0):
        self.art_root = Path(art_root)
        self.refresh_interval = max(0.0, float(refresh_interval))
        self.player_layers = {}
        self._banks = {}
        self._inventory = None
        self._revision = 0
        self._next_scan = 0.0
        self._images = OrderedDict()
        self._portraits = OrderedDict()

    def register_player_art(self, bases, eyes, hair, glasses, shirts):
        # Share already-loaded source surfaces; never draw onto them.
        self.player_layers = {"base": dict(bases), "eyes": dict(eyes),
                              "hair": dict(hair), "glasses": dict(glasses),
                              "shirt": dict(shirts)}
        self._revision += 1
        self._portraits.clear()

    def refresh(self, force=False):
        """Pick up new/edited layers within two seconds, without a restart."""
        now = time.monotonic()
        if not force and now < self._next_scan:
            return
        self._next_scan = now + self.refresh_interval
        inventory, banks = [], {}
        for band in ("", *AGE_BANDS):
            root = self.art_root if not band else self.art_root / "ages" / band
            for part, (folder, _prefix) in AVATAR_PARTS.items():
                bank = {}
                try:
                    paths = sorted((root / folder).glob("*.png"))
                    for path in paths:
                        if not valid_part_id(part, path.stem):
                            continue
                        stat = path.stat()
                        signature = (str(path), stat.st_size, stat.st_mtime_ns)
                        inventory.append(signature)
                        bank[path.stem] = (path, signature)
                except OSError:
                    # An artist may replace a file while the game is open.
                    pass
                banks[(band, part)] = bank
        inventory = tuple(inventory)
        if inventory != self._inventory:
            self._inventory = inventory
            self._banks = banks
            self._revision += 1
            self._images.clear()
            self._portraits.clear()

    def _read_image(self, path, signature):
        if signature in self._images:
            self._images.move_to_end(signature)
            return self._images[signature]
        try:
            image = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except (pygame.error, OSError):
            image = None
        return _remember(self._images, signature, image, 128)

    def _custom_part(self, part, choice, band):
        if choice is None:
            return None
        # Age-specific art overrides only the same numbered common file.
        common = self._banks.get(("", part), {})
        age_bank = self._banks.get((band, part), {})
        bank = dict(common)
        bank.update(age_bank)
        if not bank:
            return None
        ids = sorted(bank)
        start = ids.index(choice) if choice in bank else (int(choice[-2:]) - 1) % len(ids)
        for offset in range(len(ids)):
            identity = ids[(start + offset) % len(ids)]
            candidates = [bank[identity]]
            if identity in age_bank and identity in common:
                candidates.append(common[identity])
            for path, signature in candidates:
                image = self._read_image(path, signature)
                if image is not None:
                    return image
        return None

    def _player_part(self, part, choice):
        if choice is None:
            return None
        bank = self.player_layers.get(part, {})
        if not bank:
            return None
        ids = sorted(bank)
        prefix = PLAYER_PARTS[part]
        direct = f"{prefix}_{int(choice[-2:]):02d}"
        identity = direct if direct in bank else ids[(int(choice[-2:]) - 1) % len(ids)]
        return bank[identity]

    def _player_avatar(self, choices):
        # Keep the existing art's coordinates until the custom core is ready.
        base = self._player_part("base", choices["base"])
        if base is None:
            return None
        canvas = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        for part in ("base", "eyes", "hair", "glasses", "shirt"):
            image = self._player_part(part, choices[part])
            if image is not None:
                if image.get_size() != canvas.get_size():
                    image = pygame.transform.smoothscale(image, canvas.get_size())
                canvas.blit(image, (0, 0))
        return canvas

    def render(self, npc, size):
        self.refresh()
        choices = get_avatar_choices(npc)
        band = avatar_age_band(npc.get("age", 10))
        key = (tuple(choices[part] for part in AVATAR_PARTS), band, int(size), self._revision)
        if key in self._portraits:
            self._portraits.move_to_end(key)
            return self._portraits[key]
        layers = {part: self._custom_part(part, choices[part], band) for part in AVATAR_PARTS}
        if all(layers[part] is not None for part in REQUIRED_PARTS):
            canvas = pygame.Surface(AVATAR_CANVAS, pygame.SRCALPHA)
            for part in AVATAR_PARTS:
                image = layers[part]
                if image is not None:
                    if image.get_size() != AVATAR_CANVAS:
                        image = pygame.transform.smoothscale(image, AVATAR_CANVAS)
                    canvas.blit(image, (0, 0))
        else:
            canvas = self._player_avatar(choices)
        portrait = _square_image(canvas, size) if canvas is not None else None
        return _remember(self._portraits, key, portrait, 256)


_renderer = NpcAvatarRenderer()


def register_player_avatar_art(bases, eyes, hair, glasses, shirts):
    _renderer.register_player_art(bases, eyes, hair, glasses, shirts)


def draw_layered_portrait(npc, size):
    return _renderer.render(npc, size)
