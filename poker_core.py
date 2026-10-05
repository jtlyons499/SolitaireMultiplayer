# ==================================================
# SHARED POKER CORE HELPERS
#
# This module is intentionally game-agnostic so
# Texas Hold'em, Five-Card Draw, and Seven-Card Stud
# can share the same hand-history/event infrastructure.
# ==================================================

SUIT_SYMBOLS = {
    "Clubs": "C",
    "Diamonds": "D",
    "Hearts": "H",
    "Spades": "S",
}


def format_poker_card(card):

    if not card:
        return "?"

    rank = str(
        card.get(
            "rank",
            "?"
        )
    )

    suit = SUIT_SYMBOLS.get(
        card.get("suit"),
        "?"
    )

    return f"{rank}{suit}"


def format_poker_cards(cards):

    return " ".join(
        format_poker_card(card)
        for card in cards
        if card
    )


class PokerHandHistory:

    def __init__(
            self,
            max_lines=500,
            max_events=1000
    ):

        self.max_lines = max(
            50,
            int(max_lines)
        )

        self.max_events = max(
            100,
            int(max_events)
        )

        self.lines = []
        self.events = []

    def clear(self):

        self.lines.clear()
        self.events.clear()

    def start_hand(
            self,
            hand_number,
            game_name="Poker",
            stage="start"
    ):

        if self.lines:
            self.lines.append("")

        self.add(
            "hand_start",
            f"--- {game_name} Hand {hand_number} ---",
            hand_number=hand_number,
            stage=stage
        )

    def add(
            self,
            event_type,
            text,
            hand_number=None,
            stage=None,
            actor_index=None,
            amount=None,
            **data
    ):

        if not text:
            return

        text = str(text)

        event = {
            "type": str(event_type),
            "text": text,
            "hand_number": hand_number,
            "stage": stage,
            "actor_index": actor_index,
            "amount": amount,
        }

        if data:
            event.update(data)

        self.events.append(event)
        self.lines.append(text)

        if len(self.events) > self.max_events:
            del self.events[
                :-self.max_events
            ]

        if len(self.lines) > self.max_lines:
            del self.lines[
                :-self.max_lines
            ]

    def get_lines(self):

        return list(self.lines)

    def get_events(self):

        return [
            dict(event)
            for event in self.events
        ]

    def get_current_hand_events(
            self,
            hand_number
    ):

        return [
            dict(event)
            for event in self.events
            if event.get("hand_number")
            == hand_number
        ]


# ==================================================
# POKER DISPLAY HELPERS
# ==================================================

POKER_RANK_NAMES = {
    14: "Ace",
    13: "King",
    12: "Queen",
    11: "Jack",
    10: "Ten",
    9: "Nine",
    8: "Eight",
    7: "Seven",
    6: "Six",
    5: "Five",
    4: "Four",
    3: "Three",
    2: "Two",
    1: "Ace",
}

POKER_RANK_PLURALS = {
    14: "Aces",
    13: "Kings",
    12: "Queens",
    11: "Jacks",
    10: "Tens",
    9: "Nines",
    8: "Eights",
    7: "Sevens",
    6: "Sixes",
    5: "Fives",
    4: "Fours",
    3: "Threes",
    2: "Twos",
    1: "Aces",
}

POKER_RANK_SHORT = {
    14: "A",
    13: "K",
    12: "Q",
    11: "J",
    10: "10",
    9: "9",
    8: "8",
    7: "7",
    6: "6",
    5: "5",
    4: "4",
    3: "3",
    2: "2",
    1: "A",
}


def format_poker_display_name(name):
    """Return the compact table name used by every poker variant.

    Most NPCs use only their first name to keep HUDs, chat, and history tidy.
    Memphis van Dijk intentionally keeps the distinctive ``van Dijk`` label.
    """
    raw = str(name or "Opponent").strip()

    if not raw:
        return "Opponent"

    lowered = raw.casefold()

    if "van dijk" in lowered:
        return "van Dijk"

    return raw.split()[0]


def _poker_rank_name(value, plural=False, compact=False):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return str(value)

    if compact:
        return POKER_RANK_SHORT.get(value, str(value))

    mapping = (
        POKER_RANK_PLURALS
        if plural
        else POKER_RANK_NAMES
    )

    return mapping.get(value, str(value))


def describe_poker_score(score, compact=True):
    """Explain a five-card comparison tuple, including kicker information."""
    if not score:
        return "Unknown hand"

    score = tuple(score)
    category = score[0]
    values = list(score[1:])

    if category == 8:
        high = values[0] if values else 0

        if high == 14:
            return "Royal Flush"

        return (
            f"{_poker_rank_name(high, compact=compact)}-high "
            f"Straight Flush"
        )

    if category == 7:
        quad = values[0] if values else 0
        kicker = values[1] if len(values) > 1 else None

        text = (
            f"Four of a Kind, "
            f"{_poker_rank_name(quad, plural=True, compact=False)}"
        )

        if kicker is not None:
            text += (
                f", {_poker_rank_name(kicker, compact=compact)} kicker"
            )

        return text

    if category == 6:
        trips = values[0] if values else 0
        pair = values[1] if len(values) > 1 else 0

        return (
            f"Full House, "
            f"{_poker_rank_name(trips, plural=True, compact=False)} over "
            f"{_poker_rank_name(pair, plural=True, compact=False)}"
        )

    if category == 5:
        if not values:
            return "Flush"

        if compact:
            ranks = "-".join(
                _poker_rank_name(value, compact=True)
                for value in values
            )
            return f"Flush, {ranks}"

        return (
            f"Flush, "
            f"{_poker_rank_name(values[0], compact=False)}-high"
        )

    if category == 4:
        high = values[0] if values else 0
        return (
            f"{_poker_rank_name(high, compact=compact)}-high Straight"
        )

    if category == 3:
        trips = values[0] if values else 0
        kickers = values[1:]

        text = (
            f"Three of a Kind, "
            f"{_poker_rank_name(trips, plural=True, compact=False)}"
        )

        if kickers:
            kicker_text = "-".join(
                _poker_rank_name(value, compact=True)
                for value in kickers
            )
            text += (
                f", {kicker_text} "
                f"{'kicker' if len(kickers) == 1 else 'kickers'}"
            )

        return text

    if category == 2:
        high_pair = values[0] if values else 0
        low_pair = values[1] if len(values) > 1 else 0
        kicker = values[2] if len(values) > 2 else None

        text = (
            f"Two Pair, "
            f"{_poker_rank_name(high_pair, plural=True, compact=False)} "
            f"and {_poker_rank_name(low_pair, plural=True, compact=False)}"
        )

        if kicker is not None:
            text += (
                f", {_poker_rank_name(kicker, compact=compact)} kicker"
            )

        return text

    if category == 1:
        pair = values[0] if values else 0
        kickers = values[1:]

        text = (
            f"Pair of "
            f"{_poker_rank_name(pair, plural=True, compact=False)}"
        )

        if kickers:
            kicker_text = "-".join(
                _poker_rank_name(value, compact=True)
                for value in kickers
            )
            text += (
                f", {kicker_text} "
                f"{'kicker' if len(kickers) == 1 else 'kickers'}"
            )

        return text

    if category == 0:
        if not values:
            return "High Card"

        high = values[0]
        kickers = values[1:]

        text = (
            f"{_poker_rank_name(high, compact=compact)}-high"
        )

        if kickers:
            kicker_text = "-".join(
                _poker_rank_name(value, compact=True)
                for value in kickers
            )
            text += (
                f", {kicker_text} "
                f"{'kicker' if len(kickers) == 1 else 'kickers'}"
            )

        return text

    return "Poker hand"
