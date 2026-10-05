from npc_personality import get_npc_traits
from npc_personality_chat import game_trait_chat
import random


# ==================================================
# CHAT FREQUENCY
# ==================================================

ACTION_CHAT_CHANCE = {
    "check": 0.12,
    "call": 0.20,
    "bet": 0.32,
    "raise": 0.52,
    "fold": 0.18,
    "all_in": 0.72,
}

PLAYER_REACTION_CHANCE = {
    "check": 0.06,
    "call": 0.10,
    "bet": 0.22,
    "raise": 0.35,
    "all_in": 0.52,
}


# ==================================================
# NPC ACTION CHAT
# ==================================================


# ==================================================
# REACTIONS TO PLAYER
# ==================================================


# ==================================================
# HELPERS
# ==================================================


def get_npc_name(
        holdem_game,
        npc_index
):

    if not (
            0
            <= npc_index
            < len(holdem_game.npcs)
    ):
        return "Opponent"

    get_name = getattr(
        holdem_game,
        "get_table_player_name",
        None
    )

    if callable(get_name):
        return get_name(
            npc_index + 1
        )

    return (
        holdem_game.npcs[
            npc_index
        ].get(
            "name",
            "Opponent"
        )
    )


def get_action_type(
        holdem_game,
        npc_index
):

    if not (
            0
            <= npc_index
            < len(holdem_game.npc_action_texts)
    ):
        return None

    action_text = (
        holdem_game.npc_action_texts[
            npc_index
        ].strip().lower()
    )

    # All-in takes priority over the visible
    # Bet / Call / Raise wording.
    if (
            npc_index
            < len(holdem_game.npc_all_in)
            and holdem_game.npc_all_in[
                npc_index
            ]
    ):

        if action_text.startswith(
                (
                    "called",
                    "bet",
                    "raised",
                )
        ):
            return "all_in"

    if action_text.startswith("checked"):
        return "check"

    if action_text.startswith("called"):
        return "call"

    if action_text.startswith("bet"):
        return "bet"

    if action_text.startswith("raised"):
        return "raise"

    if action_text.startswith("folded"):
        return "fold"

    return None


# ==================================================
# CHAT AFTER AN NPC ACTION
# ==================================================

def generate_npc_action_chat(holdem_game, npc_index):
    action = get_action_type(holdem_game, npc_index)
    if action is None:
        return None
    traits = get_npc_traits(holdem_game.npcs[npc_index])
    chance = ACTION_CHAT_CHANCE.get(action, 0.15) + 0.008*(traits["unpredictability"] - 1)
    if random.random() > chance:
        return None
    return get_npc_name(holdem_game, npc_index), game_trait_chat(holdem_game, npc_index, action)


# ==================================================
# REACTION TO A PLAYER ACTION
# ==================================================

def generate_player_action_reaction(
        holdem_game,
        action_type
):

    if (
            holdem_game.player_all_in
            and action_type in (
                "bet",
                "raise",
                "call",
            )
    ):
        action_type = "all_in"

    chance = (
        PLAYER_REACTION_CHANCE.get(
            action_type,
            0.0
        )
    )

    if random.random() > chance:
        return None

    possible_npcs = []

    for npc_index in range(
            len(holdem_game.npcs)
    ):

        if (
                holdem_game.npc_busted[
                    npc_index
                ]
                or holdem_game.npc_folded[
                    npc_index
                ]
        ):
            continue

        possible_npcs.append(
            npc_index
        )

    if not possible_npcs:
        return None

    npc_index = random.choice(
        possible_npcs
    )

    return (get_npc_name(holdem_game, npc_index),
            game_trait_chat(holdem_game, npc_index, "player_" + action_type, target_player=True))


# ==================================================
# SHOWDOWN / KNOCKOUT CHAT
# ==================================================


def get_showdown_phrase(holdem_game, npc_index, reaction_type):
    return game_trait_chat(holdem_game, npc_index, reaction_type)


def generate_showdown_chat(
        holdem_game
):

    messages = []

    newly_busted = set(
        holdem_game.last_hand_busted_indexes
    )

    # ==================================================
    # BUSTED NPCS ALWAYS GET A FINAL LINE
    # ==================================================

    busted_npc_indexes = []

    for player_index in newly_busted:

        if player_index <= 0:
            continue

        npc_index = (
            player_index - 1
        )

        if not (
                0
                <= npc_index
                < len(holdem_game.npcs)
        ):
            continue

        phrase = (
            get_showdown_phrase(
                holdem_game,
                npc_index,
                "bust"
            )
        )

        if phrase:

            messages.append(
                (
                    get_npc_name(
                        holdem_game,
                        npc_index
                    ),
                    phrase
                )
            )

            busted_npc_indexes.append(
                npc_index
            )

    # ==================================================
    # NORMAL SHOWDOWN REACTION
    #
    # Only one extra NPC talks so the table doesn't
    # become a wall of dialogue every hand.
    # ==================================================

    if holdem_game.table_is_over():

        return messages

    winner_indexes = list(
        holdem_game.winner_indexes
    )

    # ------------------------------------------
    # Player won at least part of the pot
    # ------------------------------------------

    if 0 in winner_indexes:

        # True split pot
        if len(winner_indexes) > 1:

            npc_winners = [
                player_index - 1
                for player_index
                in winner_indexes
                if player_index > 0
            ]

            if npc_winners:

                npc_index = random.choice(
                    npc_winners
                )

                phrase = (
                    get_showdown_phrase(
                        holdem_game,
                        npc_index,
                        "split"
                    )
                )

                if phrase:

                    messages.append(
                        (
                            get_npc_name(
                                holdem_game,
                                npc_index
                            ),
                            phrase
                        )
                    )

        # Player won without an NPC co-winner.
        else:

            possible_losers = []

            for npc_index in range(
                    len(holdem_game.npcs)
            ):

                if npc_index in busted_npc_indexes:
                    continue

                if holdem_game.npc_busted[
                        npc_index
                ]:
                    continue

                possible_losers.append(
                    npc_index
                )

            if (
                    possible_losers
                    and random.random() < 0.60
            ):

                npc_index = random.choice(
                    possible_losers
                )

                phrase = (
                    get_showdown_phrase(
                        holdem_game,
                        npc_index,
                        "loss"
                    )
                )

                if phrase:

                    messages.append(
                        (
                            get_npc_name(
                                holdem_game,
                                npc_index
                            ),
                            phrase
                        )
                    )

    # ------------------------------------------
    # NPC won
    # ------------------------------------------

    else:

        npc_winners = [
            player_index - 1
            for player_index
            in winner_indexes
            if player_index > 0
        ]

        npc_winners = [
            npc_index
            for npc_index
            in npc_winners
            if (
                0
                <= npc_index
                < len(holdem_game.npcs)
                and not holdem_game.npc_busted[
                    npc_index
                ]
            )
        ]

        if npc_winners:

            npc_index = random.choice(
                npc_winners
            )

            reaction_type = (
                "split"
                if len(winner_indexes) > 1
                else "win"
            )

            phrase = (
                get_showdown_phrase(
                    holdem_game,
                    npc_index,
                    reaction_type
                )
            )

            if phrase:

                messages.append(
                    (
                        get_npc_name(
                            holdem_game,
                            npc_index
                        ),
                        phrase
                    )
                )

    return messages
