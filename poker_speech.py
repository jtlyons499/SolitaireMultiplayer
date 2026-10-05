import pygame


POKER_CHAT_POPUPS_ENABLED = True


def set_poker_chat_popups_enabled(enabled):
    global POKER_CHAT_POPUPS_ENABLED
    POKER_CHAT_POPUPS_ENABLED = bool(enabled)


def is_poker_chat_popups_enabled():
    return bool(POKER_CHAT_POPUPS_ENABLED)


class PokerSpeechOverlay:
    """Short-lived NPC table chatter drawn beside a player's name plate."""

    def __init__(
            self,
            duration_ms=2600,
            fade_ms=450,
            max_width=235,
            height=36
    ):
        self.duration_ms = int(duration_ms)
        self.fade_ms = int(fade_ms)
        self.max_width = int(max_width)
        self.height = int(height)
        self.entries = {}

    @staticmethod
    def _key(speaker):
        return str(speaker or "").strip().casefold()

    def clear(self):
        self.entries.clear()

    def post(self, speaker, message):
        speaker_key = self._key(speaker)
        message = str(message or "").strip()

        if not speaker_key or not message:
            return

        self.entries[speaker_key] = {
            "message": message,
            "started_at": pygame.time.get_ticks(),
        }

    @staticmethod
    def _ellipsize(text, font, max_width):
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text

        suffix = "..."
        if font.size(suffix)[0] > max_width:
            return ""

        trimmed = text
        while trimmed:
            trimmed = trimmed[:-1].rstrip()
            candidate = trimmed + suffix
            if font.size(candidate)[0] <= max_width:
                return candidate

        return suffix

    def draw(
            self,
            surface,
            speaker,
            anchor_rect,
            font,
            text_color=(245, 245, 245),
            fill=(18, 20, 24, 238),
            border=(235, 190, 70)
    ):
        key = self._key(speaker)
        entry = self.entries.get(key)
        if entry is None:
            return False

        now = pygame.time.get_ticks()
        elapsed = now - int(entry.get("started_at", now))

        if elapsed >= self.duration_ms:
            self.entries.pop(key, None)
            return False

        max_text_width = max(40, self.max_width - 24)
        display_text = self._ellipsize(
            entry.get("message", ""),
            font,
            max_text_width,
        )

        if not display_text:
            return False

        text_surface = font.render(
            display_text,
            True,
            text_color,
        )

        width = min(
            self.max_width,
            max(92, text_surface.get_width() + 24),
        )

        rect = pygame.Rect(
            0,
            0,
            width,
            self.height,
        )

        # NPC seats on the left speak to the right; seats on the right speak
        # to the left. This keeps bubbles near names without covering portraits.
        if anchor_rect.centerx <= surface.get_width() // 2:
            rect.left = anchor_rect.right + 8
        else:
            rect.right = anchor_rect.left - 8

        rect.centery = anchor_rect.centery
        rect.left = max(6, min(rect.left, surface.get_width() - rect.width - 6))
        rect.top = max(6, min(rect.top, surface.get_height() - rect.height - 6))

        alpha = 255
        fade_start = max(0, self.duration_ms - self.fade_ms)
        if elapsed > fade_start and self.fade_ms > 0:
            alpha = max(
                0,
                int(255 * (self.duration_ms - elapsed) / self.fade_ms),
            )

        bubble = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            bubble,
            (*fill[:3], min(alpha, fill[3] if len(fill) > 3 else alpha)),
            bubble.get_rect(),
            border_radius=9,
        )
        pygame.draw.rect(
            bubble,
            (*border[:3], alpha),
            bubble.get_rect(),
            2,
            border_radius=9,
        )

        text_surface.set_alpha(alpha)
        bubble.blit(
            text_surface,
            text_surface.get_rect(center=bubble.get_rect().center),
        )

        surface.blit(bubble, rect.topleft)
        return True
