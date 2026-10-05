from poker_strategy import strategic_context, strategic_fraction, effective_wager_cap
import random
from npc_personality import get_npc_traits, build_trait_profile


# ==================================================
# SHARED POKER AI
#
# Game-specific code supplies hand strength and legal
# betting bounds. This module handles personality,
# position, pot odds, bluffing, skill, and opponent
# tendencies so it can be reused by Hold'em, Draw,
# and Stud.
# ==================================================

POKER_PERSONALITY_PROFILES = {
    "balanced": {
        "fold_threshold": 0.27,
        "open_base": 0.10,
        "open_strength": 0.48,
        "raise_threshold": 0.62,
        "raise_chance": 0.35,
        "bet_min": 0.30,
        "bet_max": 0.60,
        "player_aggression_bonus": 0.00,
        "bluff_chance": 0.07,
        "trap_chance": 0.06,
        "call_margin": 0.025,
        "position_sensitivity": 0.90,
        "memory_sensitivity": 0.60,
    },
    "timid": {
        "fold_threshold": 0.38,
        "open_base": 0.03,
        "open_strength": 0.32,
        "raise_threshold": 0.78,
        "raise_chance": 0.20,
        "bet_min": 0.18,
        "bet_max": 0.38,
        "player_aggression_bonus": 0.00,
        "bluff_chance": 0.018,
        "trap_chance": 0.04,
        "call_margin": 0.070,
        "position_sensitivity": 0.55,
        "memory_sensitivity": 0.35,
    },
    "opportunist": {
        "fold_threshold": 0.39,
        "open_base": 0.02,
        "open_strength": 0.65,
        "raise_threshold": 0.64,
        "raise_chance": 0.58,
        "bet_min": 0.38,
        "bet_max": 0.82,
        "player_aggression_bonus": 0.00,
        "bluff_chance": 0.13,
        "trap_chance": 0.10,
        "call_margin": 0.035,
        "position_sensitivity": 1.20,
        "memory_sensitivity": 0.90,
    },
    "aggressive": {
        "fold_threshold": 0.14,
        "open_base": 0.28,
        "open_strength": 0.55,
        "raise_threshold": 0.43,
        "raise_chance": 0.66,
        "bet_min": 0.55,
        "bet_max": 0.95,
        "player_aggression_bonus": 0.00,
        "bluff_chance": 0.18,
        "trap_chance": 0.025,
        "call_margin": -0.015,
        "position_sensitivity": 1.05,
        "memory_sensitivity": 0.55,
    },
    "escalator": {
        "fold_threshold": 0.23,
        "open_base": 0.10,
        "open_strength": 0.45,
        "raise_threshold": 0.56,
        "raise_chance": 0.42,
        "bet_min": 0.45,
        "bet_max": 0.85,
        "player_aggression_bonus": 0.38,
        "bluff_chance": 0.09,
        "trap_chance": 0.045,
        "call_margin": 0.010,
        "position_sensitivity": 0.85,
        "memory_sensitivity": 1.00,
    },
}

POKER_UNPREDICTABLE_TYPES = (
    "timid",
    "opportunist",
    "aggressive",
    "escalator",
)

POKER_SKILL_FACTORS = {
    "low": 0.35,
    "mid": 0.55,
    "strong": 0.75,
    "elite": 0.92,
}

POSITION_AGGRESSION_BONUS = {
    "button": 0.10,
    "cutoff": 0.065,
    "middle": 0.015,
    "early": -0.045,
    "small_blind": -0.015,
    "big_blind": 0.025,
    "unknown": 0.0,
}

POSITION_CALL_BONUS = {
    "button": 0.020,
    "cutoff": 0.012,
    "middle": 0.0,
    "early": -0.018,
    "small_blind": 0.012,
    "big_blind": 0.035,
    "unknown": 0.0,
}


# ==================================================
# SMALL HELPERS
# ==================================================

def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def get_poker_personality(npc):
    if not isinstance(npc, dict):
        return "balanced"

    personality = str(
        npc.get(
            "game_personality",
            "balanced"
        )
    ).strip().lower()

    valid_types = set(
        POKER_PERSONALITY_PROFILES
    ) | {"unpredictable"}

    if personality not in valid_types:
        return "balanced"

    return personality


def get_effective_poker_personality(
        personality,
        rng=None
):
    if rng is None:
        rng = random

    personality = str(
        personality or "balanced"
    ).strip().lower()

    if personality == "unpredictable":
        return rng.choice(
            POKER_UNPREDICTABLE_TYPES
        )

    if personality not in POKER_PERSONALITY_PROFILES:
        return "balanced"

    return personality


def get_poker_personality_profile(personality):
    if isinstance(personality, dict):
        return build_trait_profile(get_npc_traits(personality))

    personality = str(
        personality or "balanced"
    ).strip().lower()

    return dict(
        POKER_PERSONALITY_PROFILES.get(
            personality,
            POKER_PERSONALITY_PROFILES[
                "balanced"
            ]
        )
    )


def get_poker_skill_factor(npc, game_key=None):
    if not isinstance(npc, dict):
        return POKER_SKILL_FACTORS["mid"]

    ratings = npc.get("career_ratings", {})
    if game_key and isinstance(ratings, dict) and game_key in ratings:
        try:
            rating = int(ratings[game_key])
            return max(0.20, min(0.97, 0.35 + (rating - 800) * 0.00030))
        except (TypeError, ValueError, OverflowError):
            pass

    skill_tier = str(
        npc.get(
            "skill_tier",
            "mid"
        )
    ).strip().lower()

    return POKER_SKILL_FACTORS.get(
        skill_tier,
        POKER_SKILL_FACTORS["mid"]
    )


def calculate_pot_odds(
        pot,
        amount_to_call
):
    amount_to_call = max(
        0,
        float(amount_to_call)
    )

    pot = max(
        0,
        float(pot)
    )

    if amount_to_call <= 0:
        return 0.0

    return amount_to_call / max(
        1.0,
        pot + amount_to_call
    )


# ==================================================
# PLAYER / OPPONENT MEMORY
# ==================================================

class PokerOpponentModel:

    def __init__(self):
        self.reset()

    def reset(self):
        self.hands_seen = 0
        self.total_decisions = 0

        self.preflop_decisions = 0
        self.preflop_voluntary_actions = 0
        self.preflop_raises = 0

        self.aggressive_actions = 0
        self.passive_actions = 0

        self.pressure_opportunities = 0
        self.folds_to_pressure = 0

        self.large_call_opportunities = 0
        self.large_calls = 0

    def start_hand(self):
        self.hands_seen += 1

    def record_action(
            self,
            action,
            stage,
            amount_to_call=0,
            pot_before=0,
            amount=0
    ):
        action = str(
            action or ""
        ).strip().lower()

        stage = str(
            stage or ""
        ).strip().lower()

        amount_to_call = max(
            0,
            int(amount_to_call)
        )

        pot_before = max(
            0,
            int(pot_before)
        )

        amount = max(
            0,
            int(amount)
        )

        if action not in (
                "fold",
                "check",
                "call",
                "bet",
                "raise",
        ):
            return

        self.total_decisions += 1

        if stage == "preflop":
            self.preflop_decisions += 1

            if action in (
                    "call",
                    "bet",
                    "raise",
            ):
                self.preflop_voluntary_actions += 1

            if action == "raise":
                self.preflop_raises += 1

        if action in (
                "bet",
                "raise",
        ):
            self.aggressive_actions += 1

        elif action in (
                "check",
                "call",
        ):
            self.passive_actions += 1

        if amount_to_call > 0:
            self.pressure_opportunities += 1

            if action == "fold":
                self.folds_to_pressure += 1

        if amount_to_call > 0:
            call_ratio = (
                amount_to_call
                / max(
                    1,
                    pot_before
                )
            )

            if call_ratio >= 0.45:
                self.large_call_opportunities += 1

                if (
                        action == "call"
                        and amount >= amount_to_call
                ):
                    self.large_calls += 1

    @staticmethod
    def _smoothed_rate(
            successes,
            opportunities,
            prior_rate,
            prior_weight
    ):
        return (
            successes
            + prior_rate * prior_weight
        ) / max(
            1.0,
            opportunities + prior_weight
        )

    def snapshot(self):
        fold_to_pressure_rate = (
            self._smoothed_rate(
                self.folds_to_pressure,
                self.pressure_opportunities,
                0.45,
                4.0
            )
        )

        aggression_rate = (
            self._smoothed_rate(
                self.aggressive_actions,
                self.aggressive_actions
                + self.passive_actions,
                0.35,
                6.0
            )
        )

        preflop_raise_rate = (
            self._smoothed_rate(
                self.preflop_raises,
                self.preflop_decisions,
                0.18,
                6.0
            )
        )

        vpip_rate = (
            self._smoothed_rate(
                self.preflop_voluntary_actions,
                self.preflop_decisions,
                0.36,
                6.0
            )
        )

        large_call_rate = (
            self._smoothed_rate(
                self.large_calls,
                self.large_call_opportunities,
                0.35,
                4.0
            )
        )

        confidence = _clamp(
            self.total_decisions / 24.0
        )

        return {
            "hands_seen": self.hands_seen,
            "total_decisions": self.total_decisions,
            "confidence": confidence,
            "fold_to_pressure_rate": fold_to_pressure_rate,
            "aggression_rate": aggression_rate,
            "preflop_raise_rate": preflop_raise_rate,
            "vpip_rate": vpip_rate,
            "large_call_rate": large_call_rate,
        }


# ==================================================
# POSITION / MEMORY ADJUSTMENTS
# ==================================================

def _get_position_aggression_bonus(
        position,
        stage,
        profile
):
    bonus = POSITION_AGGRESSION_BONUS.get(
        position,
        0.0
    )

    sensitivity = profile.get(
        "position_sensitivity",
        1.0
    )

    # Position matters most before the flop, but remains
    # relevant postflop because late position can attack
    # checked-around pots more effectively.
    stage_multiplier = (
        1.0
        if stage == "preflop"
        else 0.70
    )

    return (
        bonus
        * sensitivity
        * stage_multiplier
    )


def _get_position_call_bonus(
        position,
        profile
):
    return (
        POSITION_CALL_BONUS.get(
            position,
            0.0
        )
        * profile.get(
            "position_sensitivity",
            1.0
        )
    )


def _get_memory_adjustments(
        context,
        profile,
        skill_factor
):
    tendencies = (
        context.get(
            "player_tendencies"
        )
        or {}
    )

    if not context.get(
            "player_active",
            True
    ):
        return {
            "bluff_bonus": 0.0,
            "raise_bonus": 0.0,
            "fold_bonus": 0.0,
        }

    confidence = _clamp(
        float(
            tendencies.get(
                "confidence",
                0.0
            )
        )
    )

    memory_weight = (
        confidence
        * _clamp(skill_factor)
        * profile.get(
            "memory_sensitivity",
            0.5
        )
    )

    fold_to_pressure = float(
        tendencies.get(
            "fold_to_pressure_rate",
            0.45
        )
    )

    aggression_rate = float(
        tendencies.get(
            "aggression_rate",
            0.35
        )
    )

    large_call_rate = float(
        tendencies.get(
            "large_call_rate",
            0.35
        )
    )

    # A player who folds too much invites more pressure.
    bluff_bonus = (
        (fold_to_pressure - 0.45)
        * 0.32
        * memory_weight
    )

    # A sticky player discourages empty bluffs.
    bluff_bonus -= (
        (large_call_rate - 0.35)
        * 0.18
        * memory_weight
    )

    # Aggression matters most to the escalator profile,
    # but all skilled NPCs notice it a little.
    raise_bonus = (
        (aggression_rate - 0.35)
        * 0.12
        * memory_weight
    )

    fold_bonus = (
        (aggression_rate - 0.35)
        * 0.05
        * memory_weight
    )

    return {
        "bluff_bonus": bluff_bonus,
        "raise_bonus": raise_bonus,
        "fold_bonus": fold_bonus,
    }


# ==================================================
# BET / RAISE SIZING
# ==================================================

def _grudge_knockout_target(context, profile, strength, minimum, maximum):
    if context.get("fixed_limit"):
        return None
    t = profile.get("trait_units", {})
    resentment = context.get("grudge_intensity", 0.0) * t.get("bitterness", 0.0)
    target = int(context.get("grudge_target_round_total", 0))
    own_total = context.get("current_round_bet", 0) + context.get("stack", 0)
    # Only deliberate, severe grudges bypass the soft street cap. Tenacity
    # still blocks a reckless near-all-in attack with a poor hand.
    if (resentment >= 0.55 and strength >= 0.44
            and minimum <= target <= maximum
            and (t.get("tenacity", 0.5) < 0.7 or strength >= 0.80
                 or target < own_total * 0.45)):
        return target
    return None


def choose_poker_open_bet_amount(
        context,
        profile,
        strength,
        bluff=False
):
    minimum = max(
        1,
        int(
            context.get(
                "minimum_open_bet",
                1
            )
        )
    )

    maximum = max(
        0,
        int(
            context.get(
                "maximum_open_bet",
                0
            )
        )
    )

    if maximum <= 0:
        return None

    if maximum <= minimum:
        return maximum

    target = _grudge_knockout_target(context, profile, strength, minimum,
                                    min(context.get("stack", maximum),
                                        context.get("hard_maximum_open_bet", context.get("stack", maximum))))
    if target is not None:
        return target

    pot = max(
        minimum,
        int(
            context.get(
                "pot",
                minimum
            )
        )
    )

    if bluff:
        # Bluff sizing intentionally stays believable rather
        # than always using the minimum or shoving.
        fraction = (
            profile.get(
                "bet_min",
                0.30
            )
            + profile.get(
                "bet_max",
                0.60
            )
        ) / 2.0
    else:
        fraction = (
            profile.get(
                "bet_min",
                0.30
            )
            + (
                profile.get(
                    "bet_max",
                    0.60
                )
                - profile.get(
                    "bet_min",
                    0.30
                )
            )
            * _clamp(strength)
        )

    fraction = strategic_fraction(context, fraction)

    amount = int(
        pot * fraction
    )

    amount = max(
        minimum,
        amount
    )

    maximum = effective_wager_cap(context, minimum, maximum)

    return min(
        amount,
        maximum
    )


def choose_poker_raise_to_amount(
        context,
        profile,
        strength,
        bluff=False
):
    current_bet = max(
        0,
        int(
            context.get(
                "current_bet",
                0
            )
        )
    )

    minimum_raise_to = max(
        current_bet + 1,
        int(
            context.get(
                "minimum_raise_to",
                current_bet + 1
            )
        )
    )

    maximum_raise_to = max(
        0,
        int(
            context.get(
                "maximum_raise_to",
                0
            )
        )
    )

    if maximum_raise_to <= current_bet:
        return None

    # A stack too short for a full raise can only make a
    # short all-in raise. Reserve that for strong hands or
    # naturally aggressive profiles.
    if maximum_raise_to < minimum_raise_to:
        if (
                strength >= 0.72
                or profile.get(
                    "raise_chance",
                    0.0
                ) >= 0.60
        ):
            return maximum_raise_to

        return None

    target = _grudge_knockout_target(context, profile, strength,
                                    minimum_raise_to, maximum_raise_to)
    if target is not None:
        return target

    soft_maximum = int(
        context.get(
            "soft_maximum_raise_to",
            maximum_raise_to
        )
    )

    soft_maximum = min(
        maximum_raise_to,
        soft_maximum
    )

    if soft_maximum < minimum_raise_to:
        return None

    minimum_raise_size = max(
        1,
        int(
            context.get(
                "minimum_raise_size",
                minimum_raise_to - current_bet
            )
        )
    )

    pot = max(
        1,
        int(
            context.get(
                "pot",
                1
            )
        )
    )

    if bluff:
        fraction = (
            profile.get(
                "bet_min",
                0.30
            )
            + profile.get(
                "bet_max",
                0.60
            )
        ) / 2.0
    else:
        fraction = (
            profile.get(
                "bet_min",
                0.30
            )
            + (
                profile.get(
                    "bet_max",
                    0.60
                )
                - profile.get(
                    "bet_min",
                    0.30
                )
            )
            * _clamp(strength)
        )

    fraction = strategic_fraction(context, fraction)
    soft_maximum = effective_wager_cap(context, minimum_raise_to, soft_maximum)

    additional_raise = int(
        max(
            pot,
            minimum_raise_size
        )
        * fraction
    )

    additional_raise = max(
        minimum_raise_size,
        additional_raise
    )

    raise_to = (
        current_bet
        + additional_raise
    )

    return max(
        minimum_raise_to,
        min(
            raise_to,
            soft_maximum
        )
    )


# ==================================================
# DECISION ENGINE
# ==================================================

def decide_poker_action(personality, context, rng=None):
    # Enrich only after Draw/Stud have added their public variant-specific facts.
    enriched = strategic_context(context)
    decision = _decide_trait_action(personality, enriched, rng)
    decision["strategy"] = dict(enriched["advanced_strategy"])
    return decision


def _decide_trait_action(
        personality,
        context,
        rng=None
):
    if rng is None:
        rng = random

    base_personality = str(
        personality or "balanced"
    ).strip().lower()

    # Keep the old label as diagnostic metadata only. It must not reroll
    # an archetype and change behavior when explicit traits are present.
    effective_personality = base_personality

    traits = get_npc_traits({
        "game_personality": base_personality,
        "personality_traits": context.get("personality_traits", {}),
    })
    profile = build_trait_profile(traits, rng=rng)
    strategy = context.get("advanced_strategy", {})
    if strategy.get("enabled"):
        profile["bluff_chance"] = _clamp(profile["bluff_chance"] + strategy["bluff_delta"], 0, .42)
        profile["open_base"] = _clamp(profile["open_base"] + strategy["raise_delta"], .005, .8)
        profile["raise_chance"] = _clamp(profile["raise_chance"] + strategy["raise_delta"], .02, .95)
        profile["raise_threshold"] = _clamp(profile["raise_threshold"] + strategy["raise_threshold_delta"], .20, .92)
        profile["trap_chance"] = _clamp(profile["trap_chance"] + strategy["trap_delta"], 0, .35)
    t = profile["trait_units"]
    grudge = float(context.get("grudge_pressure", 0.0)) * t["bitterness"]
    survival_risk = max(0.0, min(1.0, context.get("amount_to_call", 0)
                        / max(1, context.get("stack", 1))))
    stage = str(
        context.get(
            "stage",
            ""
        )
    ).strip().lower()

    position = str(
        context.get(
            "position",
            "unknown"
        )
    ).strip().lower()

    strength = _clamp(
        float(
            context.get(
                "hand_strength",
                0.0
            )
        )
    )

    skill_factor = _clamp(
        float(
            context.get(
                "skill_factor",
                0.55
            )
        )
    )

    amount_to_call = max(
        0,
        int(
            context.get(
                "amount_to_call",
                0
            )
        )
    )

    stack = max(
        0,
        int(
            context.get(
                "stack",
                0
            )
        )
    )

    current_bet = max(
        0,
        int(
            context.get(
                "current_bet",
                0
            )
        )
    )

    can_raise = bool(
        context.get(
            "can_raise",
            False
        )
    )

    opponents_remaining = max(
        1,
        int(
            context.get(
                "opponents_remaining",
                1
            )
        )
    )

    position_aggression = (
        _get_position_aggression_bonus(
            position,
            stage,
            profile
        )
    )

    position_call_bonus = (
        _get_position_call_bonus(
            position,
            profile
        )
    )

    memory = _get_memory_adjustments(
        context,
        profile,
        skill_factor
    )

    # Less-skilled players have more noisy hand appraisal.
    noise_width = (
        0.075 * (1.0 - skill_factor)
        + 0.14 * t["unpredictability"]
    )
    noise_width *= 1.0 - .45*strategy.get("weight", 0)

    perceived_strength = _clamp(
        strength
        + rng.uniform(
            -noise_width,
            noise_width
        )
    )

    early_street = stage in ("preflop", "flop", "pre_draw", "third", "fourth", "forehead_bet")
    pessimism = t["pessimism"] * max(0.0, (0.48 - strength) / 0.48) if early_street else 0.0
    survival = t["tenacity"] * survival_risk * max(0.0, 1.0 - strength)
    profile["open_base"] = max(0.005, profile["open_base"] - 0.18*pessimism)
    profile["bluff_chance"] *= max(0.05, 1.0 - 0.75*pessimism - 0.80*survival)

    # ==================================================
    # CHECKED TO NPC / FREE OPTION
    # ==================================================

    if amount_to_call <= 0:
        bet_chance = (
            profile.get(
                "open_base",
                0.10
            )
            + perceived_strength
            * profile.get(
                "open_strength",
                0.48
            )
            + position_aggression
            + memory[
                "bluff_bonus"
            ]
        )

        # Multiway pots reduce the appeal of pure bluffs.
        bluff_chance = (
            profile.get(
                "bluff_chance",
                0.05
            )
            + memory[
                "bluff_bonus"
            ]
        )

        bluff_chance *= (
            1.0
            / max(
                1.0,
                opponents_remaining * 0.72
            )
        )

        if position in (
                "button",
                "cutoff",
        ):
            bluff_chance *= 1.30

        if stage == "preflop":
            bluff_chance *= 0.72

        bluff_chance = _clamp(
            bluff_chance,
            0.0,
            0.42
        )

        # Strong hands occasionally check behind / trap.
        trap = (
            perceived_strength >= 0.78
            and rng.random()
            < profile.get(
                "trap_chance",
                0.05
            )
        )

        bluff = (
            perceived_strength < 0.43
            and rng.random()
            < bluff_chance
        )

        bet_chance = _clamp(
            bet_chance,
            0.02,
            0.94
        )

        wants_aggression = (
            not trap
            and (
                bluff
                or rng.random()
                < bet_chance
            )
        )

        if wants_aggression:
            # Preflop the big blind may have a free option while
            # current_bet is still the blind. That action is a
            # raise, not an opening bet.
            if current_bet > 0:
                if can_raise:
                    return {
                        "action": "raise",
                        "bluff": bluff,
                        "effective_personality": effective_personality,
                        "profile": profile,
                        "traits": traits,
                        "grudge_target": context.get("grudge_target"),
                        "grudge_pressure": grudge,
                        "pot_odds": 0.0,
                    }

            else:
                return {
                    "action": "bet",
                    "bluff": bluff,
                    "effective_personality": effective_personality,
                    "profile": profile,
                    "traits": traits,
                    "grudge_target": context.get("grudge_target"),
                    "grudge_pressure": grudge,
                    "pot_odds": 0.0,
                }

        return {
            "action": "check",
            "bluff": False,
            "effective_personality": effective_personality,
            "profile": profile,
            "traits": traits,
            "grudge_target": context.get("grudge_target"),
            "grudge_pressure": grudge,
            "pot_odds": 0.0,
        }

    # ==================================================
    # FACING A BET / RAISE
    # ==================================================

    pot_odds = calculate_pot_odds(
        context.get(
            "pot",
            0
        ),
        amount_to_call
    )

    call_ratio = (
        amount_to_call
        / max(
            1,
            stack
        )
    )

    # Better players weight pot odds more heavily. Lower-skill
    # players lean more on personality and perceived strength.
    base_requirement = profile.get(
        "fold_threshold",
        0.27
    )

    pot_odds_requirement = max(
        0.04,
        pot_odds
        + profile.get(
            "call_margin",
            0.02
        )
    )

    odds_weight = (
        0.28
        + 0.48
        * skill_factor
    )

    required_strength = (
        base_requirement
        * (1.0 - odds_weight)
        + pot_odds_requirement
        * odds_weight
    )

    required_strength += min(
        0.16,
        call_ratio * 0.20
    )

    required_strength += memory[
        "fold_bonus"
    ]

    required_strength -= position_call_bonus
    required_strength += strategy.get("call_requirement_delta", 0)
    required_strength += 0.19*pessimism + 0.28*survival
    required_strength -= 0.20*grudge

    if (
            context.get("last_raiser") is not None
            and t["escalation"] > 0.0
    ):
        required_strength -= (
            profile.get(
                "player_aggression_bonus",
                0.0
            )
            * 0.10
        )

    required_strength = _clamp(
        required_strength,
        0.06,
        0.88
    )

    # ==================================================
    # VALUE RAISE / BLUFF RAISE
    # ==================================================

    raise_threshold = (
        profile.get(
            "raise_threshold",
            0.62
        )
        - position_aggression * 0.35
        - memory[
            "raise_bonus"
        ]
    )

    raise_chance = (
        profile.get(
            "raise_chance",
            0.35
        )
        + position_aggression
        + memory[
            "raise_bonus"
        ]
    )

    if (
            context.get("last_raiser") is not None
            and t["escalation"] > 0.0
    ):
        raise_threshold -= (
            profile.get(
                "player_aggression_bonus",
                0.0
            )
            * 0.32
        )

        raise_chance += profile.get(
            "player_aggression_bonus",
            0.0
        )

    raise_threshold += 0.18*pessimism + 0.22*survival - 0.15*grudge
    raise_chance += 0.26*grudge - 0.25*survival

    raise_threshold = _clamp(
        raise_threshold,
        0.20,
        0.92
    )

    raise_chance = _clamp(
        raise_chance,
        0.02,
        0.95
    )

    value_raise = (
        can_raise
        and perceived_strength
        >= raise_threshold
        and rng.random()
        < raise_chance
    )

    bluff_raise_chance = (
        profile.get(
            "bluff_chance",
            0.05
        )
        + memory[
            "bluff_bonus"
        ]
        + max(
            0.0,
            position_aggression
        )
        * 0.55
    )

    bluff_raise_chance *= (
        1.0
        / max(
            1.0,
            opponents_remaining
        )
    )

    if stage == "preflop" and position in (
            "button",
            "cutoff",
    ):
        bluff_raise_chance *= 1.30

    bluff_raise = (
        can_raise
        and not value_raise
        and perceived_strength < 0.52
        and rng.random()
        < _clamp(
            bluff_raise_chance,
            0.0,
            0.32
        )
    )

    if value_raise or bluff_raise:
        return {
            "action": "raise",
            "bluff": bool(bluff_raise),
            "effective_personality": effective_personality,
            "profile": profile,
            "traits": traits,
            "grudge_target": context.get("grudge_target"),
            "grudge_pressure": grudge,
            "pot_odds": pot_odds,
            "required_strength": required_strength,
        }

    # ==================================================
    # FOLD / CALL
    # ==================================================

    if perceived_strength < required_strength:
        difference = (
            required_strength
            - perceived_strength
        )

        fold_probability = _clamp(
            0.48
            + difference * 1.55
            + skill_factor * 0.12,
            0.15,
            0.96
        )

        fold_probability += 0.10*t["caution"] - 0.15*t["aggressiveness"]
        fold_probability += 0.16*pessimism + 0.24*survival - 0.24*grudge

        fold_probability = _clamp(
            fold_probability,
            0.08,
            0.97
        )

        if rng.random() < fold_probability:
            return {
                "action": "fold",
                "bluff": False,
                "effective_personality": effective_personality,
                "profile": profile,
                "traits": traits,
                "grudge_target": context.get("grudge_target"),
                "grudge_pressure": grudge,
                "pot_odds": pot_odds,
                "required_strength": required_strength,
            }

    return {
        "action": "call",
        "bluff": False,
        "effective_personality": effective_personality,
        "profile": profile,
        "traits": traits,
        "grudge_target": context.get("grudge_target"),
        "grudge_pressure": grudge,
        "pot_odds": pot_odds,
        "required_strength": required_strength,
    }
