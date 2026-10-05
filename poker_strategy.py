"""Rating-scaled poker tactics learned exclusively from public table events.

Range bands describe likely relative strength, not calculated winning equity.
No observer reads a deck, hole cards, NPC traits, or an unrevealed player hand.
Reads are specific to an opponent; optional profile-owned rival memories survive sessions.
"""
from collections import deque
from hashlib import sha256
from poker_learning import RivalLearning


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


ACTION_TYPES = frozenset(("check", "bet", "call", "raise", "fold"))
LATE_STREETS = frozenset(("turn", "river", "post_draw", "fifth", "sixth", "seventh"))
SIGNATURES = {
    "pressure": "Pressure player",
    "trapper": "Patient trapper",
    "value": "Value hunter",
    "counter": "Counterpuncher",
    "analyst": "Measured analyst",
}


class PokerTableReads:
    """Bounded public-action histories for every seat, including NPC seats."""

    def __init__(self):
        self.clear()

    def clear(self):
        self.histories = {}
        self.reveals = {}
        self.hand_number = None
        self.street = None
        self.street_bets = {}
        self.hand_actions = {}
        self.draw_counts = {}
        self.learning = None

    def bind_learning(self, store, game, identities):
        self.learning = RivalLearning(store, game, identities)

    def observe(self, event, actor, *, hand_number, stage, amount=0,
                round_total=0, pot=0, draw_count=None, hand_name=None,
                facing_amount=None):
        # The caller supplies only named public facts; never whole history data.
        if hand_number != self.hand_number:
            self.hand_number = hand_number
            self.hand_actions = {}
            self.draw_counts = {}
            self.street = None
        if stage != self.street:
            self.street = stage
            self.street_bets = {}
        if actor is None:
            return
        if event == "draw" and draw_count is not None:
            self.draw_counts[actor] = max(0, min(5, int(draw_count)))
        if event == "showdown_hand":
            # A weak hand shown after late aggression is evidence, not proof,
            # that this opponent sometimes represents more than they hold.
            late_aggression = any(a[0] in ("bet", "raise") and a[1] in LATE_STREETS
                                  for a in self.hand_actions.get(actor, ()))
            if late_aggression:
                weak = str(hand_name).casefold() in ("high card", "one pair", "pair")
                self.reveals.setdefault(actor, deque(maxlen=24)).append(weak)
                if self.learning:
                    self.learning.record(actor, "reveals", weak)
        if event not in ACTION_TYPES:
            if event in ("blind", "bring_in", "completion"):
                self.street_bets[actor] = max(0, int(round_total))
            return
        amount = max(0, int(amount or 0))
        facing = max(0, max(self.street_bets.values(), default=0)
                     - self.street_bets.get(actor, 0))
        if facing_amount is not None:
            facing = max(0, int(facing_amount))
        pot_before = max(1, int(pot) - amount)
        size = amount / pot_before
        item = (event, stage, facing > 0, size)
        self.histories.setdefault(actor, deque(maxlen=96)).append(item)
        if self.learning:
            self.learning.record(actor, "history", item)
        self.hand_actions.setdefault(actor, deque(maxlen=24)).append(item)
        self.street_bets[actor] = max(0, int(round_total))

    def snapshot(self, actor, observer=None):
        record = self.learning.samples(observer, actor) if self.learning and observer else None
        history = list(record["history"] if record is not None else self.histories.get(actor, ()))
        pressure = [a for a in history if a[2]]
        aggressive = [a for a in history if a[0] in ("bet", "raise")]
        samples = list(record["reveals"] if record is not None else self.reveals.get(actor, ()))
        return {
            "seat": actor,
            "decisions": len(history),
            "confidence": clamp(len(history) / 24),
            "fold_to_pressure": (sum(a[0] == "fold" for a in pressure) + 2) / (len(pressure) + 4),
            "pressure_confidence": clamp(len(pressure) / 12),
            "aggression": (len(aggressive) + 2) / (len(history) + 6),
            "call_under_pressure": (sum(a[0] == "call" for a in pressure) + 1) / (len(pressure) + 4),
            "average_bet_fraction": (sum(a[3] for a in aggressive) + 1) / (len(aggressive) + 2),
            "shown_weak_aggression": (sum(samples) + 1) / (len(samples) + 5),
            "reveal_confidence": clamp(len(samples) / 8),
            "hand_actions": [tuple(a) for a in self.hand_actions.get(actor, ())],
            "draw_count": self.draw_counts.get(actor),
        }


def signature_for(identity, traits):
    """Stable lean within the existing eight-trait personality, never a reroll."""
    t = {key: clamp((value - 1) / 9) for key, value in traits.items()}
    scores = {
        "pressure": t.get("aggressiveness", .5) + .40*t.get("unpredictability", .5),
        "trapper": t.get("caution", .5) + .40*t.get("tenacity", .5),
        "value": t.get("selectivity", .5) + .40*t.get("pessimism", .5),
        "counter": t.get("escalation", .5) + .40*t.get("bitterness", .5),
        "analyst": .75 + .30*(1-t.get("unpredictability", .5)),
    }
    for key in scores:
        digest = sha256(f"poker-style:{identity}:{key}".encode()).digest()
        scores[key] += digest[0] / 255 * .18
    return max(scores, key=scores.get)


def estimate_range(read, game, stage, exposed_cards=()):
    """Three-band estimate based on public actions, public draws and Stud upcards."""
    shift = 0.0
    confidence = read.get("confidence", 0)
    aggression = read.get("aggression", 1/3)
    actions = read.get("hand_actions", ())
    for action, action_stage, _facing, size in actions[-3:]:
        if action in ("bet", "raise"):
            # Rare aggression means more than the same bet from a loose seat.
            shift += (.15 - .19*aggression) * (.65 if action_stage != stage else 1)
            shift += min(.035, max(0, size - .75)*.035)
        elif action == "call":
            shift += .025
        elif action == "check":
            shift -= .035
    shift -= .10*(read.get("shown_weak_aggression", .2)-.2)*read.get("reveal_confidence", 0)
    # Do not claim certainty from a few bets.
    shift *= .4 + .6*confidence
    if game == "five_card_draw" and stage == "post_draw":
        count = read.get("draw_count")
        if count is not None:
            shift += {0: .16, 1: .07, 2: .015, 3: -.07, 4: -.12, 5: -.15}[count]
    if game == "seven_card_stud" and exposed_cards:
        ranks = [card.get("rank") for card in exposed_cards]
        counts = [ranks.count(rank) for rank in set(ranks)]
        shift += .10*sum(n >= 2 for n in counts) + .10*any(n >= 3 for n in counts)
        suits = [card.get("suit") for card in exposed_cards]
        if len(suits) >= 3 and len(set(suits)) == 1:
            shift += .06  # A possible flush, not knowledge of a completed one.
    shift = clamp(shift, -.20, .30)
    strong = .28 + shift
    weak = .38 - shift
    return {"weak": round(weak, 4), "medium": .34, "strong": round(strong, 4),
            "pressure_shift": shift, "confidence": confidence}


def strategic_context(context):
    """Return a copy with tactical deltas; small/unknown ratings retain trait play."""
    result = dict(context)
    reads = context.get("opponent_reads", ())
    weight = clamp((context.get("skill_factor", .55) - .58) / .30)
    if not context.get("npc_identity") or not reads or weight <= 0:
        result["advanced_strategy"] = {"enabled": False, "weight": 0.0}
        return result
    identity = context["npc_identity"]
    signature = signature_for(identity, context.get("personality_traits", {}))
    raiser = context.get("last_raiser")
    focus = next((r for r in reads if r["seat"] == raiser), None)
    focus = focus or max(reads, key=lambda r: (r.get("confidence", 0), -r["seat"]))
    game = context.get("game", "texas_holdem")
    stage = context.get("stage", "")
    ranges = [estimate_range(r, game, stage, r.get("exposed_cards", ())) for r in reads]
    target_range = estimate_range(focus, game, stage, focus.get("exposed_cards", ()))
    # Bluffing into several callers is unattractive, even if one seat folds often.
    fold_edge = sum((r["fold_to_pressure"]-.5)*r["pressure_confidence"] for r in reads) / len(reads)
    calling_edge = sum((r["call_under_pressure"]-.25)*r["pressure_confidence"] for r in reads) / len(reads)
    facing = context.get("amount_to_call", 0) > 0
    own_strength = context.get("hand_strength", 0)
    range_shift = target_range["pressure_shift"] if facing else max(r["pressure_shift"] for r in ranges)
    bluff_delta = weight*(.28*fold_edge - .22*calling_edge)
    call_delta = weight*range_shift*.30 if facing else 0
    raise_delta = weight*(.12*fold_edge - .10*range_shift)
    trap_delta = 0.0
    fraction = {"pressure": .70, "trapper": .52, "value": .65,
                "counter": .62, "analyst": .55}[signature]
    if signature == "pressure":
        raise_delta += .045*weight
    elif signature == "trapper":
        trap_delta = .10*weight if len(reads) <= 2 else .035*weight
    elif signature == "counter" and facing:
        raise_delta += .045*weight*focus["aggression"]
    elif signature == "value" and own_strength < .45:
        bluff_delta -= .035*weight
    if own_strength >= .65:
        fraction += .25*max(0, calling_edge)*weight
    elif own_strength < .43:
        fraction -= .18*max(0, calling_edge)*weight
    if facing and range_shift > .065:
        tactic = "respect_range"
    elif own_strength >= .65 and calling_edge > .08:
        tactic = "value_callers"
    elif own_strength < .43 and fold_edge > .08:
        tactic = "pressure_folders"
    elif facing and signature == "counter":
        tactic = "counter_pressure"
    else:
        tactic = signature
    result["advanced_strategy"] = {
        "enabled": True, "weight": weight, "signature": signature,
        "signature_name": SIGNATURES[signature], "tactic": tactic,
        "target_seat": focus["seat"], "range": target_range,
        "bluff_delta": bluff_delta, "call_requirement_delta": call_delta,
        "raise_threshold_delta": weight*max(0, range_shift)*.25,
        "raise_delta": raise_delta, "trap_delta": trap_delta,
        "bet_fraction": clamp(fraction, .35, .85),
    }
    return result


def strategic_fraction(context, original):
    strategy = strategic_context(context)["advanced_strategy"]
    if not strategy["enabled"] or context.get("fixed_limit"):
        return original
    weight = strategy["weight"]
    return original*(1-weight) + strategy["bet_fraction"]*weight


def effective_wager_cap(context, minimum, maximum):
    """Avoid wagering more than any live opponent can match, subject to legality."""
    strategy = strategic_context(context)["advanced_strategy"]
    if not strategy["enabled"] or context.get("fixed_limit"):
        return maximum
    opponents = context.get("public_opponents", ())
    if not opponents:
        return maximum
    matchable = max(int(row["round_bet"]) + int(row["stack"]) for row in opponents)
    # When everyone else is short/all-in, a minimum legal bet remains allowed;
    # the engine returns unmatched chips through its existing side-pot logic.
    return min(maximum, max(minimum, matchable))


STRATEGY_CHAT = {
    "pressure_folders": {"bet": ("Let's see who stays.",), "raise": ("Make a decision.",)},
    "value_callers": {"bet": ("Let's put a price on it.",), "raise": ("A little more for this one.",)},
    "respect_range": {"fold": ("You've earned some respect.",), "call": ("That's a convincing bet.",)},
    "counter_pressure": {"raise": ("Pressure goes both ways.",), "call": ("You don't get a free pass.",)},
    "pressure": {"bet": ("Keep pace.",), "raise": ("Time to turn the screw.",)},
    "trapper": {"check": ("No hurry.",), "call": ("Let's let this develop.",)},
    "value": {"fold": ("I'll wait for my spot.",), "bet": ("Worth committing here.",)},
    "counter": {"raise": ("Back at you.",), "call": ("I'm listening.",)},
    "analyst": {"check": ("Let's see what develops.",), "fold": ("The price doesn't suit me.",),
                "bet": ("A measured price.",)},
}


def strategy_chat_line(decision, event, rng):
    strategy = (decision or {}).get("strategy", {})
    if not strategy.get("enabled") or event != (decision or {}).get("action"):
        return None
    lines = STRATEGY_CHAT.get(strategy.get("tactic"), {}).get(event)
    if lines and rng.random() < .45*strategy["weight"]:
        return rng.choice(lines)
    return None
