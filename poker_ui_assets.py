import os
import pygame

POKER_LOGO_SOURCE_SIZE = (900, 240)
POKER_LOGO_DRAW_SIZE = (280, 75)

POKER_LOGO_PATHS = {
    "texas_holdem": "assets/poker/logos/texas_holdem.png",
    "five_card_draw": "assets/poker/logos/five_card_draw.png",
    "seven_card_stud": "assets/poker/logos/seven_card_stud.png",
}

_logo_cache = {}


def get_poker_logo(game_id, size=POKER_LOGO_DRAW_SIZE):
    path = POKER_LOGO_PATHS.get(game_id)
    if not path:
        return None
    cache_key = (game_id, tuple(size))
    if cache_key in _logo_cache:
        return _logo_cache[cache_key]
    try:
        image = pygame.image.load(path).convert_alpha()
        image = pygame.transform.smoothscale(image, size)
    except (pygame.error, FileNotFoundError):
        image = None
    _logo_cache[cache_key] = image
    return image


def draw_poker_logo(surface, game_id, rect):
    image = get_poker_logo(game_id, rect.size)
    if image is None:
        return False
    surface.blit(image, image.get_rect(center=rect.center))
    return True
