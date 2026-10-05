"""Stable NPC traits and session-local, opponent-specific poker grudges.

Skill remains separate from personality. Explicit trait values are independent:
caution means exposure control, aggression means initiating pressure, selectivity
means waiting for value, and pessimism means giving up on weak early streets.
Legacy archetypes are used only to migrate old/custom NPC records.
"""
import hashlib
import random

TRAIT_NAMES = (
    "caution", "aggressiveness", "unpredictability", "escalation",
    "selectivity", "tenacity", "pessimism", "bitterness",
)
TRAIT_LABELS = {key: key.title() for key in TRAIT_NAMES}
LEGACY_TRAITS = {
    "balanced": (5, 5, 3, 4, 5, 5, 4, 3),
    "timid": (9, 2, 2, 2, 6, 8, 6, 3),
    "aggressive": (2, 9, 4, 6, 3, 3, 2, 5),
    "unpredictable": (5, 6, 10, 6, 4, 4, 4, 6),
    "escalator": (3, 6, 3, 10, 4, 4, 3, 7),
    "opportunist": (6, 5, 3, 5, 10, 5, 5, 4),
    "opportunistic": (6, 5, 3, 5, 10, 5, 5, 4),
}


def get_npc_traits(npc=None):
    """Return all eight integer traits in 1..10; never mutate the input.

    Migration is deterministic by NPC ID (no process-randomized hash), so an
    older save/roster does not change personality every time the game starts.
    """
    npc = npc if isinstance(npc, dict) else {}
    legacy = str(npc.get("game_personality", "balanced")).lower()
    defaults = LEGACY_TRAITS.get(legacy, LEGACY_TRAITS["balanced"])
    identity = str(npc.get("id") or npc.get("name") or "balanced")
    seed = int.from_bytes(hashlib.sha256(identity.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    values = {key: max(1, min(10, value + rng.randint(-1, 1)))
              for key, value in zip(TRAIT_NAMES, defaults)}
    # New traits have their own full-range identity instead of inheriting
    # every emotional/survival tendency from a single old betting archetype.
    for key in ("tenacity", "pessimism", "bitterness"):
        values[key] = rng.randint(1, 10)
    # Generated defaults usually balance these tendencies; explicit values
    # are allowed to describe a careful but assertive player.
    values["caution"] = max(1, min(10, 11 - values["aggressiveness"] + rng.randint(-1, 1)))
    raw = npc.get("personality_traits", npc.get("traits", {}))
    if not isinstance(raw, dict):
        raw = {}
    for key in TRAIT_NAMES:
        try:
            values[key] = max(1, min(10, int(raw.get(key, values[key]))))
        except (TypeError, ValueError, OverflowError):
            pass
    return values


def trait_units(traits):
    return {key: (value - 1) / 9.0 for key, value in get_npc_traits(
        {"personality_traits": traits}).items()}


def personality_summary(npc):
    traits = get_npc_traits(npc)
    strongest = sorted(TRAIT_NAMES, key=lambda key: traits[key], reverse=True)[:2]
    return " / ".join(TRAIT_LABELS[key] for key in strongest)


def build_trait_profile(traits, rng=None):
    """Translate the full personality into continuous shared betting weights."""
    rng = rng or random
    t = trait_units(traits)
    a, c, s = t["aggressiveness"], t["caution"], t["selectivity"]
    # Unpredictability varies appraisal and pressure, not the NPC's identity.
    swing = rng.uniform(-0.16, 0.16) * t["unpredictability"]
    clamp = lambda x, lo=0.0, hi=1.0: max(lo, min(hi, x))
    return {
        "fold_threshold": clamp(0.20 + 0.18*c + 0.12*s - 0.14*a, 0.08, 0.60),
        "open_base": clamp(0.025 + 0.27*a - 0.07*c - 0.06*s + swing, 0.01, 0.40),
        "open_strength": 0.35 + 0.36*s + 0.10*a,
        "raise_threshold": clamp(0.64 + 0.16*s + 0.10*c - 0.25*a + swing, 0.30, 0.92),
        "raise_chance": clamp(0.16 + 0.52*a + 0.16*t["escalation"] + swing, 0.05, 0.90),
        "bet_min": clamp(0.20 + 0.48*a - 0.10*c + swing, 0.12, 0.80),
        "bet_max": clamp(0.45 + 0.58*a + 0.20*s - 0.14*c + swing, 0.30, 1.25),
        "player_aggression_bonus": 0.38*t["escalation"],
        "bluff_chance": clamp(0.025 + 0.18*a + 0.08*t["unpredictability"] - 0.13*s - 0.05*c, 0.005, 0.30),
        "trap_chance": 0.02 + 0.10*s + 0.035*c,
        "call_margin": 0.02 + 0.075*c + 0.025*s - 0.055*a,
        "position_sensitivity": 0.65 + 0.55*s,
        "memory_sensitivity": 0.40 + 0.50*s,
        "traits": dict(traits),
        "trait_units": t,
    }


def npc_identity(npc, seat=None):
    if seat == 0:
        return "player"
    return str(npc.get("id") or npc.get("name") or f"seat_{seat}")


class PokerGrudgeMemory:
    """Bounded session memory. Repeated losses build resentment; time cools it."""
    def __init__(self):
        self.entries = {}
        self.recorded = set()

    def clear(self):
        self.entries.clear()
        self.recorded.clear()

    def intensity(self, observer, opponent, hand_number, bitterness):
        entry = self.entries.get((observer, opponent))
        if entry is None:
            return 0.0
        unit = (max(1, min(10, bitterness)) - 1) / 9.0
        age = max(0, int(hand_number) - entry["hand"])
        decay = 0.38 - 0.355*unit
        return max(0.0, min(1.0, entry["score"] - age*decay))

    def record_loss(self, observer, opponent, hand_number, bitterness, severity=0.5):
        if observer == opponent or bitterness <= 1:
            return
        marker = (int(hand_number), observer, opponent)
        if marker in self.recorded:
            return
        self.recorded.add(marker)
        # Keep duplicate protection bounded for long sessions.
        self.recorded = {key for key in self.recorded if key[0] >= hand_number - 2}
        prior = self.intensity(observer, opponent, hand_number, bitterness)
        unit = (bitterness - 1) / 9.0
        self.entries[(observer, opponent)] = {
            "hand": int(hand_number),
            "score": min(1.0, prior + unit*(0.30 + 0.50*max(0.0, min(1.0, severity)))),
        }

    def context(self, npc, seat, opponents, last_raiser, hand_number):
        """Opponents contain only public identity, stack, round contribution."""
        observer = npc_identity(npc, seat)
        bitterness = get_npc_traits(npc)["bitterness"]
        targets = []
        for opponent in opponents:
            score = self.intensity(observer, opponent["id"], hand_number, bitterness)
            if score > 0.0:
                targets.append((score, opponent))
        result = {"grudge_pressure": 0.0, "grudge_target": None,
                  "grudge_intensity": 0.0, "grudge_target_round_total": 0}
        if targets:
            score, target = max(targets, key=lambda item: item[0])
            result.update(grudge_target=target["name"], grudge_intensity=score,
                          grudge_target_round_total=target["stack"] + target.get("round_bet", 0))
        for score, opponent in targets:
            if opponent["seat"] == last_raiser:
                result.update(grudge_pressure=score, grudge_target=opponent["name"],
                              grudge_intensity=score,
                              grudge_target_round_total=opponent["stack"] + opponent.get("round_bet", 0))
                break
        return result
