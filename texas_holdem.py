import random
from npc_personality import get_npc_traits, PokerGrudgeMemory, npc_identity
from poker_strategy import PokerTableReads
from collections import Counter
from itertools import combinations

from poker_core import (
    PokerHandHistory,
    describe_poker_score,
    format_poker_cards,
    format_poker_display_name,
)

from poker_ai import (
    PokerOpponentModel,
    calculate_pot_odds,
    choose_poker_open_bet_amount,
    choose_poker_raise_to_amount,
    decide_poker_action,
    get_effective_poker_personality,
    get_poker_personality,
    get_poker_personality_profile,
    get_poker_skill_factor,
)


# ==================================================
# CARD CONSTANTS
# ==================================================

RANKS = [
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "J",
    "Q",
    "K",
    "A",
]

SUITS = [
    "Clubs",
    "Diamonds",
    "Hearts",
    "Spades",
]

RANK_VALUES = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
}


HAND_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "Pair",
    0: "High Card",
}

class TexasHoldemGame:

    def __init__(self):

        # ==================================================
        # CARDS / TABLE
        # ==================================================

        self.deck = []

        self.player_hand = []
        self.npc_hands = []

        self.community_cards = []

        self.npcs = []

        self.hand_number = 0

        self.last_hand_busted_indexes = []

        # ==================================================
        # SHARED POKER HAND HISTORY
        # ==================================================

        self.hand_history = PokerHandHistory()

        # Shared session-level model of how the human player
        # has actually been behaving at this poker table.
        self.player_model = PokerOpponentModel()
        self.table_reads = PokerTableReads()
        self.learning_store = None
        self.personality_memory = PokerGrudgeMemory()

        # Snapshot of seats that began the current hand. This
        # remains stable even if somebody moves all-in mid-hand.
        self.hand_seat_indexes = []

        # Last structured AI decision for each NPC. This is kept
        # primarily for debugging and future AI-facing UI tools.
        self.npc_ai_last_decisions = []

        # ==================================================
        # SESSION MONEY
        # ==================================================

        self.starting_stack = 0

        # ``ante`` is retained as the session's base blind unit
        # for compatibility with the rest of the project.
        self.ante = 0
        self.small_blind = 1
        self.big_blind = 2

        # Table indexes: 0 = human, 1+ = NPCs.
        self.dealer_index = -1
        self.small_blind_index = None
        self.big_blind_index = None

        self.player_stack = 0
        self.npc_stacks = []

        self.pot = 0

        # ==================================================
        # ENTIRE-HAND CONTRIBUTIONS
        #
        # Used for main pots and side pots.
        # These include blinds + every later wager.
        # ==================================================

        self.player_hand_contribution = 0

        self.npc_hand_contributions = []

        self.last_pot_awards = []
        self.recap_open = False
        self.recap_page = 0

        # Final pot amount retained after payout so the UI can
        # continue showing the completed hand's pot at showdown.
        self.last_resolved_pot = 0

        # ==================================================
        # TABLE STATUS
        # ==================================================

        self.player_busted = False

        self.npc_busted = []

        # ==================================================
        # BETTING DISPLAY STATE
        # ==================================================

        self.player_bet_chunks = []

        self.npc_bet_chunks = []

        self.player_action_text = ""

        self.npc_action_texts = []

        # ==================================================
        # CURRENT BETTING ROUND
        # ==================================================

        self.current_bet = 0

        self.player_round_bet = 0

        self.npc_round_bets = []

        self.player_folded = False

        self.npc_folded = []

        self.player_all_in = False

        self.npc_all_in = []

        self.player_has_acted = False

        self.npc_has_acted = []

        self.current_actor = 0

        self.last_raiser = None

        self.last_raise_size = 0

        self.betting_round_complete = False

        # ==================================================
        # HAND STATE
        # ==================================================

        self.current_stage = "idle"

        self.hand_complete = False

        self.winner_indexes = []

        self.result_text = ""

    # ==================================================
    # HAND HISTORY HELPERS
    # ==================================================

    def log_hand_event(
            self,
            event_type,
            text,
            actor_index=None,
            amount=None,
            **data
    ):

        round_total = 0
        if actor_index == 0:
            round_total = self.player_round_bet
        elif actor_index is not None and 0 < actor_index <= len(self.npc_round_bets):
            round_total = self.npc_round_bets[actor_index - 1]
        facing_amount = None
        if event_type in ("call", "fold", "check"):
            previous_total = round_total - int(amount or 0) if event_type == "call" else round_total
            facing_amount = max(0, self.current_bet - previous_total)
        if self.table_reads.learning:
            self.table_reads.learning.active_observers = {
                npc_identity(npc, seat) for seat, npc in enumerate(self.npcs, 1)
                if seat - 1 >= len(self.npc_busted) or not self.npc_busted[seat - 1]
            }
        self.table_reads.observe(
            event_type, actor_index, hand_number=self.hand_number,
            stage=self.current_stage, amount=amount, round_total=round_total,
            pot=self.pot, draw_count=data.get("draw_count"),
            hand_name=data.get("hand_name"),
            facing_amount=facing_amount,
        )
        self.hand_history.add(
            event_type,
            text,
            hand_number=self.hand_number,
            stage=self.current_stage,
            actor_index=actor_index,
            amount=amount,
            **data
        )

    def get_hand_history_lines(self):

        return self.hand_history.get_lines()

    def get_hand_history_events(self):

        return self.hand_history.get_events()

    def get_player_tendencies(self):

        return self.player_model.snapshot()

    def record_player_tendency_action(
            self,
            action,
            amount=0,
            amount_to_call=None,
            pot_before=None
    ):

        if amount_to_call is None:
            amount_to_call = (
                self.get_player_amount_to_call()
            )

        if pot_before is None:
            pot_before = self.pot

        self.player_model.record_action(
            action,
            stage=self.current_stage,
            amount_to_call=amount_to_call,
            pot_before=pot_before,
            amount=amount
        )

    def log_newly_busted_players(
            self,
            player_indexes
    ):

        for player_index in player_indexes:

            name = self.get_table_player_name(
                player_index
            )

            if player_index == 0:
                text = "You are eliminated from the table."
            else:
                text = f"{name} is eliminated from the table."

            self.log_hand_event(
                "elimination",
                text,
                actor_index=player_index
            )

    # ==================================================
    # DECK
    # ==================================================

    def build_deck(self):

        self.deck = []

        for suit in SUITS:

            for rank in RANKS:

                self.deck.append(
                    {
                        "rank": rank,
                        "suit": suit,
                    }
                )

        random.shuffle(
            self.deck
        )

    def draw_card(self):

        if not self.deck:
            return None

        return self.deck.pop()

    # ==================================================
    # SESSION
    # ==================================================

    def start_session(
            self,
            npcs,
            starting_stack,
            ante
    ):

        self.hand_number = 0
        self.rating_seen_hands = set()
        self.rating_final_stacks = None
        self.session_rating_rewarded = False

        self.last_hand_busted_indexes = []

        self.hand_history.clear()
        self.player_model.reset()
        self.table_reads.clear()
        self.personality_memory.clear()
        self.hand_seat_indexes = []

        # ==================================================
        # Participants
        # ==================================================

        self.npcs = list(
            npcs
        )

        identities = {0: "player"}
        identities.update({seat: npc_identity(npc, seat) for seat, npc in enumerate(self.npcs, 1)})
        self.table_reads.bind_learning(self.learning_store, self.rating_game_key, identities)

        self.starting_stack = int(
            starting_stack
        )

        self.ante = max(
            1,
            int(ante)
        )

        # The old ante value now acts as the small-blind unit.
        # Keeping the parameter name avoids touching main.py.
        self.small_blind = max(
            1,
            self.ante
        )

        self.big_blind = max(
            2,
            self.small_blind * 2
        )

        # The first hand rotates from -1 to seat 0, making the
        # human the opening dealer when still active.
        self.dealer_index = -1
        self.small_blind_index = None
        self.big_blind_index = None

        # ==================================================
        # Stacks
        # ==================================================

        self.player_stack = (
            self.starting_stack
        )

        self.npc_stacks = [
            self.starting_stack
            for _ in self.npcs
        ]

        self.npc_ai_last_decisions = [
            None
            for _ in self.npcs
        ]

        # ==================================================
        # Bust state
        # ==================================================

        self.player_busted = False

        self.npc_busted = [
            False
            for _ in self.npcs
        ]

        # ==================================================
        # Hand contributions
        # ==================================================

        self.player_hand_contribution = 0

        self.npc_hand_contributions = [
            0
            for _ in self.npcs
        ]

        self.last_pot_awards = []
        self.recap_open = False
        self.recap_page = 0
        self.last_resolved_pot = 0

        # ==================================================
        # Betting state
        # ==================================================

        self.player_bet_chunks = []

        self.npc_bet_chunks = [
            []
            for _ in self.npcs
        ]

        self.player_action_text = ""

        self.npc_action_texts = [
            ""
            for _ in self.npcs
        ]

        self.player_round_bet = 0

        self.npc_round_bets = [
            0
            for _ in self.npcs
        ]

        self.player_folded = False

        self.npc_folded = [
            False
            for _ in self.npcs
        ]

        self.player_all_in = False

        self.npc_all_in = [
            False
            for _ in self.npcs
        ]

        self.player_has_acted = False

        self.npc_has_acted = [
            False
            for _ in self.npcs
        ]

        self.current_bet = 0

        self.last_raise_size = 0

        self.last_raiser = None

        self.current_actor = 0

        self.betting_round_complete = False

        # ==================================================
        # Session state
        # ==================================================

        self.pot = 0

        self.current_stage = "ready"

        self.hand_complete = False

        self.winner_indexes = []

        self.result_text = ""

    # ==================================================
    # CHIP COMMITMENT HELPERS
    # ==================================================

    def commit_player_chips(
            self,
            amount,
            count_round_bet=True,
            show_chunk=True
    ):

        amount = max(
            0,
            int(amount)
        )

        amount_paid = min(
            amount,
            self.player_stack
        )

        if amount_paid <= 0:
            return 0

        self.player_stack -= (
            amount_paid
        )

        self.player_hand_contribution += (
            amount_paid
        )

        self.pot += (
            amount_paid
        )

        if count_round_bet:
            self.player_round_bet += (
                amount_paid
            )

        if show_chunk:
            self.player_bet_chunks.append(
                amount_paid
            )

        if self.player_stack == 0:
            self.player_all_in = True

        return amount_paid

    def commit_npc_chips(
            self,
            npc_index,
            amount,
            count_round_bet=True,
            show_chunk=True
    ):

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return 0

        amount = max(
            0,
            int(amount)
        )

        amount_paid = min(
            amount,
            self.npc_stacks[
                npc_index
            ]
        )

        if amount_paid <= 0:
            return 0

        self.npc_stacks[
            npc_index
        ] -= amount_paid

        self.npc_hand_contributions[
            npc_index
        ] += amount_paid

        self.pot += (
            amount_paid
        )

        if count_round_bet:
            self.npc_round_bets[
                npc_index
            ] += amount_paid

        if show_chunk:
            self.npc_bet_chunks[
                npc_index
            ].append(
                amount_paid
            )

        if (
                self.npc_stacks[
                    npc_index
                ]
                == 0
        ):
            self.npc_all_in[
                npc_index
            ] = True

        return amount_paid

    # ==================================================
    # TABLE POSITION / BLIND HELPERS
    # ==================================================

    def get_live_player_indexes(self):

        live_indexes = []

        if (
                not self.player_busted
                and self.player_stack > 0
        ):
            live_indexes.append(0)

        for npc_index, stack in enumerate(
                self.npc_stacks
        ):

            busted = (
                    npc_index < len(self.npc_busted)
                    and self.npc_busted[npc_index]
            )

            if not busted and stack > 0:
                live_indexes.append(
                    npc_index + 1
                )

        return live_indexes

    def get_next_live_player_index(
            self,
            current_index
    ):

        actor_count = len(self.npcs) + 1
        live_indexes = set(
            self.get_live_player_indexes()
        )

        if not live_indexes:
            return None

        for offset in range(
                1,
                actor_count + 1
        ):

            candidate = (
                    current_index + offset
            ) % actor_count

            if candidate in live_indexes:
                return candidate

        return None

    def rotate_dealer(self):

        live_indexes = (
            self.get_live_player_indexes()
        )

        if not live_indexes:
            self.dealer_index = None
            return None

        next_dealer = (
            self.get_next_live_player_index(
                self.dealer_index
                if self.dealer_index is not None
                else -1
            )
        )

        self.dealer_index = next_dealer

        return next_dealer

    def assign_blind_positions(self):

        live_indexes = (
            self.get_live_player_indexes()
        )

        self.small_blind_index = None
        self.big_blind_index = None

        if len(live_indexes) < 2:
            return False

        # Heads-up exception: dealer posts the small blind.
        if len(live_indexes) == 2:
            self.small_blind_index = (
                self.dealer_index
            )

            self.big_blind_index = (
                self.get_next_live_player_index(
                    self.dealer_index
                )
            )

            return True

        self.small_blind_index = (
            self.get_next_live_player_index(
                self.dealer_index
            )
        )

        self.big_blind_index = (
            self.get_next_live_player_index(
                self.small_blind_index
            )
        )

        return True

    def get_preflop_first_actor_index(self):

        live_indexes = (
            self.get_live_player_indexes()
        )

        if len(live_indexes) < 2:
            return None

        # Heads-up: dealer / small blind acts first preflop.
        if len(live_indexes) == 2:
            return self.dealer_index

        # Three or more: action begins left of the big blind.
        return self.get_next_live_player_index(
            self.big_blind_index
        )

    def get_postflop_first_actor_index(self):

        # Postflop action always starts with the first live seat
        # clockwise from the dealer. Folded/all-in seats are then
        # skipped by set_first_actor_from().
        if self.dealer_index is None:
            return None

        return self.get_next_live_player_index(
            self.dealer_index
        )

    def set_first_actor_from(
            self,
            starting_index
    ):

        if starting_index is None:
            self.current_actor = -1
            self.betting_round_complete = True
            return None

        actor_count = len(self.npcs) + 1

        for offset in range(actor_count):

            candidate = (
                    starting_index + offset
            ) % actor_count

            if self.actor_needs_action(
                    candidate
            ):
                self.current_actor = candidate
                self.betting_round_complete = False
                return candidate

        self.current_actor = -1
        self.betting_round_complete = True

        return None

    def post_blind(
            self,
            player_index,
            blind_amount,
            blind_label
    ):

        blind_amount = max(
            0,
            int(blind_amount)
        )

        if blind_amount <= 0:
            return 0

        if player_index == 0:

            amount_paid = (
                self.commit_player_chips(
                    blind_amount,
                    count_round_bet=True,
                    show_chunk=True
                )
            )

            if amount_paid > 0:
                self.player_action_text = (
                    f"{blind_label} ${amount_paid:,}"
                )

                blind_name = (
                    "small blind"
                    if blind_label == "SB"
                    else "big blind"
                )

                suffix = (
                    " and are all-in."
                    if self.player_all_in
                    else "."
                )

                self.log_hand_event(
                    "blind",
                    (
                        f"You post the {blind_name} "
                        f"${amount_paid:,}{suffix}"
                    ),
                    actor_index=0,
                    amount=amount_paid,
                    blind=blind_name,
                    all_in=self.player_all_in
                )

            return amount_paid

        npc_index = player_index - 1

        if not (
                0 <= npc_index < len(self.npcs)
        ):
            return 0

        amount_paid = (
            self.commit_npc_chips(
                npc_index,
                blind_amount,
                count_round_bet=True,
                show_chunk=True
            )
        )

        if amount_paid > 0:
            self.npc_action_texts[npc_index] = (
                f"{blind_label} ${amount_paid:,}"
            )

            blind_name = (
                "small blind"
                if blind_label == "SB"
                else "big blind"
            )

            name = self.get_table_player_name(
                player_index
            )

            suffix = (
                " and is all-in."
                if self.npc_all_in[npc_index]
                else "."
            )

            self.log_hand_event(
                "blind",
                (
                    f"{name} posts the {blind_name} "
                    f"${amount_paid:,}{suffix}"
                ),
                actor_index=player_index,
                amount=amount_paid,
                blind=blind_name,
                all_in=self.npc_all_in[npc_index]
            )

        return amount_paid

    # ==================================================
    # NEW HAND
    # ==================================================

    def start_hand(self):

        # ==================================================
        # Determine who is still at the table
        # ==================================================

        self.refresh_busted_state()

        if self.player_busted:
            self.hand_complete = True
            self.current_actor = -1
            self.current_stage = "busted"
            self.result_text = (
                "You are out of chips."
            )
            return False

        live_indexes = (
            self.get_live_player_indexes()
        )

        if len(live_indexes) < 2:
            self.hand_complete = True
            self.current_actor = -1
            self.current_stage = "showdown"
            self.result_text = (
                "The table has been cleared."
            )
            return False

        self.hand_seat_indexes = list(
            live_indexes
        )

        self.player_model.start_hand()

        self.hand_number += 1
        self.last_hand_busted_indexes = []

        self.hand_history.start_hand(
            self.hand_number,
            "Texas Hold'em",
            stage="preflop"
        )

        # ==================================================
        # New hand
        # ==================================================

        self.build_deck()

        self.player_hand = []

        self.npc_hands = [
            []
            for _ in self.npcs
        ]

        self.community_cards = []
        self.pot = 0
        self.hand_complete = False
        self.winner_indexes = []
        self.result_text = ""
        self.last_pot_awards = []
        self.recap_open = False
        self.recap_page = 0
        self.last_resolved_pot = 0

        # ==================================================
        # Reset ENTIRE-HAND contributions
        # ==================================================

        self.player_hand_contribution = 0

        self.npc_hand_contributions = [
            0
            for _ in self.npcs
        ]

        # ==================================================
        # Whole-hand status
        # ==================================================

        self.player_folded = False

        self.npc_folded = [
            busted
            for busted in self.npc_busted
        ]

        self.player_all_in = False

        self.npc_all_in = [
            False
            for _ in self.npcs
        ]

        # ==================================================
        # Rotate dealer and assign blinds
        # ==================================================

        self.rotate_dealer()
        self.assign_blind_positions()

        self.current_stage = "preflop"

        dealer_name = self.get_table_player_name(
            self.dealer_index
        )

        self.log_hand_event(
            "dealer",
            f"Dealer: {dealer_name}.",
            actor_index=self.dealer_index
        )

        # Reset the street before blinds are posted so the blind
        # chips count toward the preflop round wagers.
        self.reset_betting_round(
            assign_actor=False
        )

        # ==================================================
        # Post small blind / big blind
        # ==================================================

        self.post_blind(
            self.small_blind_index,
            self.small_blind,
            "SB"
        )

        self.post_blind(
            self.big_blind_index,
            self.big_blind,
            "BB"
        )

        # The nominal big blind establishes the opening wager even
        # if the BB seat could only post a short all-in blind.
        self.current_bet = (
            self.big_blind
        )

        self.last_raise_size = (
            self.big_blind
        )

        self.last_raiser = None

        # ==================================================
        # Busted seat labels
        # ==================================================

        for npc_index in range(
                len(self.npcs)
        ):

            if self.npc_busted[npc_index]:
                self.npc_action_texts[
                    npc_index
                ] = "Busted"

        # ==================================================
        # Hole cards
        # ==================================================

        for _ in range(2):

            self.player_hand.append(
                self.draw_card()
            )

            for npc_index in range(
                    len(self.npcs)
            ):

                if self.npc_busted[
                    npc_index
                ]:
                    continue

                self.npc_hands[
                    npc_index
                ].append(
                    self.draw_card()
                )

        player_cards_text = format_poker_cards(
            self.player_hand
        )

        self.log_hand_event(
            "hole_cards",
            f"You are dealt {player_cards_text}.",
            actor_index=0,
            cards=[
                dict(card)
                for card in self.player_hand
                if card
            ]
        )

        # ==================================================
        # Correct preflop action order
        # ==================================================

        self.set_first_actor_from(
            self.get_preflop_first_actor_index()
        )

        return True

    # ==================================================
    # BETTING HELPERS
    # ==================================================
    def npc_raise(
            self,
            npc_index,
            raise_to
    ):

        self.ensure_npc_bet_chunk_state()
        self.ensure_npc_action_state()

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return False

        if (
                self.npc_busted[npc_index]
                or self.npc_folded[npc_index]
                or self.npc_all_in[npc_index]
        ):
            return False

        if self.current_bet <= 0:
            return False

        stack = (
            self.npc_stacks[
                npc_index
            ]
        )

        if stack <= 0:
            return False

        maximum_raise_to = (
                self.npc_round_bets[
                    npc_index
                ]
                + stack
        )

        minimum_raise_to = (
            self.get_minimum_raise_to()
        )

        raise_to = int(
            raise_to
        )

        if raise_to <= self.current_bet:
            return False

        if (
                raise_to < minimum_raise_to
                and raise_to < maximum_raise_to
        ):
            return False

        target = min(
            raise_to,
            maximum_raise_to
        )

        old_current_bet = (
            self.current_bet
        )

        amount_needed = (
                target
                - self.npc_round_bets[
                    npc_index
                ]
        )

        if amount_needed <= 0:
            return False

        amount_paid = (
            self.commit_npc_chips(
                npc_index,
                amount_needed
            )
        )

        if amount_paid <= 0:
            return False

        if (
                self.npc_round_bets[
                    npc_index
                ]
                > old_current_bet
        ):

            actual_raise_size = (
                    self.npc_round_bets[
                        npc_index
                    ]
                    - old_current_bet
            )

            self.current_bet = (
                self.npc_round_bets[
                    npc_index
                ]
            )

            required_raise_size = (
                self.get_minimum_raise_size()
            )

            if (
                    actual_raise_size
                    >= required_raise_size
            ):
                self.last_raise_size = (
                    actual_raise_size
                )

                self.last_raiser = (
                        npc_index + 1
                )

                self.reset_actions_after_aggression(
                    npc_index + 1
                )

        self.npc_has_acted[
            npc_index
        ] = True

        self.npc_action_texts[
            npc_index
        ] = (
            f"Raised to "
            f"${self.npc_round_bets[npc_index]:,}"
        )

        name = self.get_table_player_name(
            npc_index + 1
        )

        suffix = (
            " and is all-in."
            if self.npc_all_in[npc_index]
            else "."
        )

        self.log_hand_event(
            "raise",
            (
                f"{name} raises to "
                f"${self.npc_round_bets[npc_index]:,}"
                f"{suffix}"
            ),
            actor_index=npc_index + 1,
            amount=amount_paid,
            raise_to=self.npc_round_bets[npc_index],
            all_in=self.npc_all_in[npc_index]
        )

        return True

    def npc_bet(
            self,
            npc_index,
            amount
    ):

        self.ensure_npc_bet_chunk_state()
        self.ensure_npc_action_state()

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return False

        if self.current_bet > 0:
            return False

        if (
                self.npc_busted[npc_index]
                or self.npc_folded[npc_index]
                or self.npc_all_in[npc_index]
        ):
            return False

        stack = (
            self.npc_stacks[
                npc_index
            ]
        )

        if stack <= 0:
            return False

        amount = int(
            amount
        )

        minimum_bet = (
            self.get_minimum_open_bet()
        )

        if (
                amount < minimum_bet
                and amount < stack
        ):
            return False

        target_amount = min(
            max(
                1,
                amount
            ),
            stack
        )

        old_current_bet = (
            self.current_bet
        )

        amount_paid = (
            self.commit_npc_chips(
                npc_index,
                target_amount
            )
        )

        if amount_paid <= 0:
            return False

        self.current_bet = (
            self.npc_round_bets[
                npc_index
            ]
        )

        actual_raise_size = (
                self.current_bet
                - old_current_bet
        )

        if actual_raise_size >= minimum_bet:
            self.last_raise_size = (
                actual_raise_size
            )

            self.last_raiser = (
                    npc_index + 1
            )

            self.reset_actions_after_aggression(
                npc_index + 1
            )

        self.npc_has_acted[
            npc_index
        ] = True

        self.npc_action_texts[
            npc_index
        ] = (
            f"Bet ${amount_paid:,}"
        )

        name = self.get_table_player_name(
            npc_index + 1
        )

        suffix = (
            " and is all-in."
            if self.npc_all_in[npc_index]
            else "."
        )

        self.log_hand_event(
            "bet",
            f"{name} bets ${amount_paid:,}{suffix}",
            actor_index=npc_index + 1,
            amount=amount_paid,
            all_in=self.npc_all_in[npc_index]
        )

        return True

    # ==================================================
    # RESET ACTIONS AFTER BET / RAISE
    # ==================================================

    def reset_actions_after_aggression(
            self,
            aggressor_index
    ):

        # ==================================================
        # Human
        # ==================================================

        if (
                not self.player_busted
                and not self.player_folded
                and not self.player_all_in
        ):
            self.player_has_acted = False

        # ==================================================
        # NPCs
        # ==================================================

        for npc_index in range(
                len(self.npcs)
        ):

            if (
                    not self.npc_busted[npc_index]
                    and not self.npc_folded[npc_index]
                    and not self.npc_all_in[npc_index]
            ):
                self.npc_has_acted[
                    npc_index
                ] = False

        # ==================================================
        # Aggressor already acted
        # ==================================================

        if aggressor_index == 0:

            self.player_has_acted = True

        else:

            npc_index = (
                    aggressor_index - 1
            )

            if (
                    0
                    <= npc_index
                    < len(self.npc_has_acted)
            ):
                self.npc_has_acted[
                    npc_index
                ] = True

    # ==================================================
    # ACTOR / TURN HELPERS
    # ==================================================

    def refresh_busted_state(self):

        # ==================================================
        # Remember previous state
        # ==================================================

        previous_player_busted = (
            self.player_busted
        )

        previous_npc_busted = list(
            self.npc_busted
        )

        # Make defensive length correction.
        if len(previous_npc_busted) != len(
                self.npcs
        ):
            previous_npc_busted = [
                False
                for _ in self.npcs
            ]

        # ==================================================
        # Refresh current state
        # ==================================================

        self.player_busted = (
                self.player_stack <= 0
        )

        self.npc_busted = [
            stack <= 0
            for stack in self.npc_stacks
        ]

        # ==================================================
        # Who JUST busted?
        #
        # Table indexes:
        # 0 = player
        # 1+ = NPCs
        # ==================================================

        newly_busted = []

        if (
                self.player_busted
                and not previous_player_busted
        ):
            newly_busted.append(
                0
            )

        for npc_index in range(
                len(self.npcs)
        ):

            if (
                    self.npc_busted[npc_index]
                    and not previous_npc_busted[
                npc_index
            ]
            ):
                newly_busted.append(
                    npc_index + 1
                )

        self.last_hand_busted_indexes = (
            newly_busted
        )

        return newly_busted

    def all_npcs_busted(self):

        return (
                bool(self.npcs)
                and all(
            self.npc_busted
        )
        )

    def table_is_over(self):

        return (
                self.player_busted
                or self.all_npcs_busted()
        )

    def ensure_npc_bet_chunk_state(self):

        npc_count = len(
            self.npcs
        )

        if len(
                self.npc_bet_chunks
        ) != npc_count:
            self.npc_bet_chunks = [
                []
                for _ in range(
                    npc_count
                )
            ]

    def ensure_npc_action_state(self):

        npc_count = len(
            self.npcs
        )

        if len(
                self.npc_action_texts
        ) != npc_count:
            self.npc_action_texts = [
                ""
                for _ in range(
                    npc_count
                )
            ]

    def actor_needs_action(
            self,
            actor_index
    ):

        # ==================================================
        # Human player
        # ==================================================

        if actor_index == 0:

            if (
                    self.player_busted
                    or self.player_folded
            ):
                return False

            # Only truly all-in if the stack is actually 0.
            if (
                    self.player_all_in
                    and self.player_stack <= 0
            ):
                return False

            # Repair stale all-in state.
            if (
                    self.player_all_in
                    and self.player_stack > 0
            ):
                self.player_all_in = False

            return (
                    not self.player_has_acted
                    or self.player_round_bet
                    < self.current_bet
            )

        # ==================================================
        # NPC
        # ==================================================

        npc_index = (
                actor_index - 1
        )

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return False

        if (
                self.npc_busted[npc_index]
                or self.npc_folded[npc_index]
        ):
            return False

        # Only skip an all-in NPC when that NPC
        # actually has no chips remaining.
        if (
                self.npc_all_in[npc_index]
                and self.npc_stacks[npc_index] <= 0
        ):
            return False

        # Repair impossible/stale state:
        # positive stack + all-in flag.
        if (
                self.npc_all_in[npc_index]
                and self.npc_stacks[npc_index] > 0
        ):
            self.npc_all_in[npc_index] = False

        return (
                not self.npc_has_acted[npc_index]
                or self.npc_round_bets[npc_index]
                < self.current_bet
        )

    def advance_to_next_actor(self):

        actor_count = (
                len(self.npcs) + 1
        )

        for offset in range(
                1,
                actor_count + 1
        ):

            candidate = (
                                self.current_actor + offset
                        ) % actor_count

            if self.actor_needs_action(
                    candidate
            ):
                self.current_actor = (
                    candidate
                )

                self.betting_round_complete = False

                return candidate

        self.betting_round_complete = True

        return None

    # ==================================================
    # ACTIVE PLAYERS
    # ==================================================

    def get_active_player_indexes(self):

        active_indexes = []

        # Human = index 0
        if (
                not self.player_busted
                and not self.player_folded
        ):
            active_indexes.append(
                0
            )

        # NPCs = indexes 1+
        for npc_index in range(
                len(self.npcs)
        ):

            if (
                    not self.npc_busted[npc_index]
                    and not self.npc_folded[npc_index]
            ):
                active_indexes.append(
                    npc_index + 1
                )

        return active_indexes

    # ==================================================
    # SIDE POT HELPERS
    # ==================================================

    def get_hand_contributions(self):

        return [
            self.player_hand_contribution,
            *self.npc_hand_contributions
        ]

    def is_showdown_eligible(
            self,
            player_index
    ):

        # Human
        if player_index == 0:
            return (
                    not self.player_folded
                    and len(self.player_hand) >= 2
            )

        # NPC
        npc_index = (
                player_index - 1
        )

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return False

        return (
                not self.npc_folded[npc_index]
                and len(
            self.npc_hands[
                npc_index
            ]
        ) >= 2
        )

    def build_side_pots(self):

        contributions = (
            self.get_hand_contributions()
        )

        levels = sorted(
            {
                amount
                for amount in contributions
                if amount > 0
            }
        )

        side_pots = []

        previous_level = 0

        for level in levels:

            contributors = [
                player_index
                for player_index, amount
                in enumerate(
                    contributions
                )
                if amount >= level
            ]

            layer_size = (
                    level
                    - previous_level
            )

            pot_amount = (
                    layer_size
                    * len(contributors)
            )

            eligible = [
                player_index
                for player_index
                in contributors
                if self.is_showdown_eligible(
                    player_index
                )
            ]

            if pot_amount > 0:
                side_pots.append(
                    {
                        "amount":
                            pot_amount,

                        "contributors":
                            contributors,

                        "eligible":
                            eligible,
                    }
                )

            previous_level = level

        return side_pots

    def get_display_pot_amount(self):
        """Pot amount the table should display right now."""
        if (
                self.current_stage == "showdown"
                or self.hand_complete
        ):
            return max(
                0,
                int(self.last_resolved_pot)
            )

        return max(
            0,
            int(self.pot)
        )

    def has_true_side_pots(self, showdown_indexes):
        """Return True only when live showdown players had unequal stakes.

        Folded dead money can cause build_side_pots() to create accounting
        layers even when every player still eligible for showdown invested
        the same amount. Those layers are not useful to label as side pots
        in the hand history.
        """
        contributions = self.get_hand_contributions()

        showdown_levels = {
            contributions[player_index]
            for player_index in showdown_indexes
            if (
                    0 <= player_index < len(contributions)
                    and contributions[player_index] > 0
            )
        }

        return (
                len(showdown_levels) > 1
                and len(self.last_pot_awards) > 1
        )

    def log_detailed_pot_awards(self, showdown_indexes):
        if not self.has_true_side_pots(showdown_indexes):
            return False

        for pot_index, pot_award in enumerate(
                self.last_pot_awards
        ):
            pot_label = (
                "Main pot"
                if pot_index == 0
                else f"Side pot {pot_index}"
            )

            pot_amount = int(
                pot_award.get(
                    "amount",
                    0
                )
            )

            winners = list(
                pot_award.get(
                    "winners",
                    []
                )
            )

            winner_names = [
                self.get_table_player_name(player_index)
                for player_index in winners
            ]

            if len(winner_names) == 1:
                award_text = (
                    f"{pot_label} ${pot_amount:,}: "
                    f"{winner_names[0]} wins."
                )
            else:
                award_text = (
                    f"{pot_label} ${pot_amount:,}: "
                    f"split between {', '.join(winner_names)}."
                )

            detail = pot_award.get("hand", "")
            if detail:
                share = int(pot_award.get("share", pot_amount))
                award_text += f" Winning hand: {detail}. Each receives ${share:,}"
                if pot_award.get("remainder", 0):
                    award_text += " (plus odd chips in seat order)"
                award_text += "."
            self.log_hand_event(
                "pot_award",
                award_text,
                amount=pot_amount,
                winners=winners,
                pot_index=pot_index
            )

        return True

    def finalize_showdown_display_state(self):
        """Clear stale action labels while preserving final statuses."""
        if self.player_busted:
            self.player_action_text = "Busted"
        elif self.player_folded:
            self.player_action_text = "Folded"
        else:
            self.player_action_text = ""

        cleaned_actions = []

        for npc_index in range(len(self.npcs)):
            if (
                    npc_index < len(self.npc_busted)
                    and self.npc_busted[npc_index]
            ):
                cleaned_actions.append("Busted")

            elif (
                    npc_index < len(self.npc_folded)
                    and self.npc_folded[npc_index]
            ):
                cleaned_actions.append("Folded")

            else:
                cleaned_actions.append("")

        self.npc_action_texts = cleaned_actions

    def get_showdown_result(
            self,
            player_index
    ):

        if player_index == 0:
            return self.evaluate_best_hand(
                self.player_hand
                + self.community_cards
            )

        npc_index = (
                player_index - 1
        )

        return self.evaluate_best_hand(
            self.npc_hands[
                npc_index
            ]
            + self.community_cards
        )

    def get_table_player_name(
            self,
            player_index
    ):

        if player_index == 0:
            return "You"

        npc_index = (
                player_index - 1
        )

        return format_poker_display_name(
            self.npcs[
                npc_index
            ].get(
                "name",
                "Opponent"
            )
        )

    def award_chips_to_player(
            self,
            player_index,
            amount
    ):

        if amount <= 0:
            return

        if player_index == 0:

            self.player_stack += (
                amount
            )

        else:

            npc_index = (
                    player_index - 1
            )

            self.npc_stacks[
                npc_index
            ] += amount

    # ==================================================
    # AWARD POT TO ONE REMAINING PLAYER
    # ==================================================

    def award_pot_to_single_player(
            self,
            winner_index
    ):

        # ==================================================
        # Defensive protection against duplicate resolution
        # ==================================================

        if self.hand_complete:
            return False

        winnings = self.pot
        self.last_resolved_pot = max(
            0,
            int(winnings)
        )

        self.award_chips_to_player(
            winner_index,
            winnings
        )

        winner_name = (
            self.get_table_player_name(
                winner_index
            )
        )

        if winner_index == 0:

            self.result_text = (
                f"You win ${winnings:,}."
            )

        else:

            self.result_text = (
                f"{winner_name} wins "
                f"${winnings:,}."
            )

        self.last_pot_awards = [
            {
                "amount":
                    winnings,

                "winners":
                    [winner_index],

                "share":
                    winnings,
            }
        ]

        self.winner_indexes = [
            winner_index
        ]

        self.log_hand_event(
            "result",
            self.result_text,
            actor_index=winner_index,
            amount=winnings,
            winners=[winner_index]
        )

        self.pot = 0

        self.hand_complete = True

        self.current_actor = -1

        self.current_stage = "showdown"

        newly_busted = self.refresh_busted_state()

        self.log_newly_busted_players(
            newly_busted
        )

        self.finalize_showdown_display_state()

        return True

    # ==================================================
    # COMPLETE BOARD AFTER PLAYER FOLDS
    # ==================================================

    def complete_board_after_fold(self):

        # ------------------------------------------
        # Preflop -> Flop
        # ------------------------------------------

        if self.current_stage == "preflop":

            if not self.deal_flop():
                return False

        # ------------------------------------------
        # Flop -> Turn
        # ------------------------------------------

        if self.current_stage == "flop":

            if not self.deal_turn():
                return False

        # ------------------------------------------
        # Turn -> River
        # ------------------------------------------

        if self.current_stage == "turn":

            if not self.deal_river():
                return False

        # ------------------------------------------
        # River -> Showdown
        # ------------------------------------------

        if self.current_stage == "river":
            return self.showdown()

        return False

    # ==================================================
    # RESOLVE HAND AFTER FOLD
    # ==================================================

    def resolve_after_fold(self):

        # ==================================================
        # A completed hand has already been resolved.
        # Never pay or rewrite its result a second time.
        # ==================================================

        if self.hand_complete:
            return False

        active_indexes = (
            self.get_active_player_indexes()
        )

        # ------------------------------------------
        # Nobody active
        # Should never happen, but guard against it.
        # ------------------------------------------

        if not active_indexes:
            return False

        # ------------------------------------------
        # Only one player remains
        # ------------------------------------------

        if len(active_indexes) == 1:
            return (
                self.award_pot_to_single_player(
                    active_indexes[0]
                )
            )

        # ------------------------------------------
        # Human folded, NPCs remain
        #
        # Finish board and evaluate remaining NPCs.
        # ------------------------------------------

        if self.player_folded:
            return (
                self.complete_board_after_fold()
            )

        return False

    # ==================================================
    # ADVANCE AFTER BETTING ROUND
    # ==================================================

    def advance_after_betting_round(self):

        if not self.is_betting_round_complete():
            return False

        if self.current_stage == "preflop":

            return self.deal_flop()

        elif self.current_stage == "flop":

            return self.deal_turn()

        elif self.current_stage == "turn":

            return self.deal_river()

        elif self.current_stage == "river":

            return self.showdown()

        return False

    def get_npc_amount_to_call(
            self,
            npc_index
    ):

        if not (
                0
                <= npc_index
                < len(self.npc_stacks)
        ):
            return 0

        return max(
            0,
            self.current_bet
            - self.npc_round_bets[
                npc_index
            ]
        )

    def npc_check(
            self,
            npc_index
    ):

        if self.npc_folded[npc_index]:
            return False

        if (
                self.npc_all_in[npc_index]
                and self.npc_stacks[npc_index] <= 0
        ):
            return False

        if (
                self.get_npc_amount_to_call(
                    npc_index
                )
                != 0
        ):
            return False

        self.npc_has_acted[
            npc_index
        ] = True

        self.npc_action_texts[
            npc_index
        ] = "Checked"

        name = self.get_table_player_name(
            npc_index + 1
        )

        self.log_hand_event(
            "check",
            f"{name} checks.",
            actor_index=npc_index + 1
        )

        return True

    def npc_fold(
            self,
            npc_index
    ):

        self.ensure_npc_action_state()

        if self.npc_folded[npc_index]:
            return False

        if (
                self.npc_all_in[npc_index]
                and self.npc_stacks[npc_index] <= 0
        ):
            return False

        self.npc_folded[
            npc_index
        ] = True

        self.npc_has_acted[
            npc_index
        ] = True

        self.npc_action_texts[
            npc_index
        ] = "Folded"

        name = self.get_table_player_name(
            npc_index + 1
        )

        self.log_hand_event(
            "fold",
            f"{name} folds.",
            actor_index=npc_index + 1
        )

        # ==================================================
        # If this fold leaves only one player,
        # award the pot immediately.
        # ==================================================

        active_indexes = (
            self.get_active_player_indexes()
        )

        if len(active_indexes) == 1:
            self.award_pot_to_single_player(
                active_indexes[0]
            )

        return True

    def npc_call(
            self,
            npc_index
    ):

        self.ensure_npc_action_state()
        self.ensure_npc_bet_chunk_state()

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return False

        if (
                self.npc_busted[npc_index]
                or self.npc_folded[npc_index]
                or self.npc_all_in[npc_index]
        ):
            return False

        amount_to_call = (
            self.get_npc_amount_to_call(
                npc_index
            )
        )

        if amount_to_call <= 0:
            return False

        amount_paid = (
            self.commit_npc_chips(
                npc_index,
                amount_to_call
            )
        )

        if amount_paid <= 0:
            return False

        self.npc_has_acted[
            npc_index
        ] = True

        self.npc_action_texts[
            npc_index
        ] = (
            f"Called ${amount_paid:,}"
        )

        name = self.get_table_player_name(
            npc_index + 1
        )

        suffix = (
            " and is all-in."
            if self.npc_all_in[npc_index]
            else "."
        )

        self.log_hand_event(
            "call",
            f"{name} calls ${amount_paid:,}{suffix}",
            actor_index=npc_index + 1,
            amount=amount_paid,
            all_in=self.npc_all_in[npc_index]
        )

        return True

    # ==================================================
    # NPC BETTING LOOP
    # ==================================================

    # ==================================================
    # NPC PERSONALITY HELPERS
    # ==================================================

    def get_npc_personality(
            self,
            npc_index
    ):

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return "balanced"

        return get_poker_personality(
            self.npcs[npc_index]
        )

    def get_npc_effective_personality(
            self,
            npc_index
    ):

        return get_effective_poker_personality(
            self.get_npc_personality(
                npc_index
            )
        )

    def get_npc_personality_profile(
            self,
            npc_index
    ):

        if not 0 <= npc_index < len(self.npcs):
            return "balanced", get_poker_personality_profile("balanced")

        effective_personality = (
            self.get_npc_effective_personality(
                npc_index
            )
        )

        return (
            effective_personality,
            get_poker_personality_profile(self.npcs[npc_index])
        )

    rating_game_key = "texas_holdem"

    def get_npc_skill_factor(
            self,
            npc_index
    ):

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return 0.55

        return get_poker_skill_factor(
            self.npcs[npc_index], self.rating_game_key
        )

    def get_poker_position_label(
            self,
            player_index
    ):

        if player_index == self.dealer_index:
            return "button"

        if player_index == self.small_blind_index:
            return "small_blind"

        if player_index == self.big_blind_index:
            return "big_blind"

        hand_indexes = list(
            self.hand_seat_indexes
        )

        if not hand_indexes:
            hand_indexes = (
                self.get_live_player_indexes()
            )

        if player_index not in hand_indexes:
            return "unknown"

        if self.big_blind_index is None:
            return "unknown"

        actor_count = len(self.npcs) + 1

        non_blind_indexes = [
            index
            for index in hand_indexes
            if index not in (
                self.dealer_index,
                self.small_blind_index,
                self.big_blind_index,
            )
        ]

        non_blind_indexes.sort(
            key=lambda index: (
                index
                - self.big_blind_index
            ) % actor_count
        )

        if player_index not in non_blind_indexes:
            return "unknown"

        if len(non_blind_indexes) == 1:
            return "early"

        if player_index == non_blind_indexes[-1]:
            return "cutoff"

        if player_index == non_blind_indexes[0]:
            return "early"

        return "middle"

    def build_npc_ai_context(
            self,
            npc_index,
            strength=None
    ):

        if strength is None:
            strength = (
                self.get_npc_hand_strength(
                    npc_index
                )
            )

        stack = self.npc_stacks[npc_index]
        current_round_bet = (
            self.npc_round_bets[npc_index]
        )

        maximum_raise_to = (
            current_round_bet
            + stack
        )

        minimum_raise_to = (
            self.get_minimum_raise_to()
        )

        stage_cap = (
            self.get_npc_stage_bet_cap(
                npc_index
            )
        )

        soft_maximum_raise_to = min(
            maximum_raise_to,
            stage_cap
        )

        active_indexes = (
            self.get_active_player_indexes()
        )

        context = {
            "game": "texas_holdem",
            "stage": self.current_stage,
            "position": self.get_poker_position_label(
                npc_index + 1
            ),
            "hand_strength": strength,
            "pot": self.pot,
            "amount_to_call": self.get_npc_amount_to_call(
                npc_index
            ),
            "stack": stack,
            "current_bet": self.current_bet,
            "current_round_bet": current_round_bet,
            "minimum_open_bet": self.get_minimum_open_bet(),
            "maximum_open_bet": min(
                stack,
                stage_cap
            ),
            "minimum_raise_size": self.get_minimum_raise_size(),
            "minimum_raise_to": minimum_raise_to,
            "maximum_raise_to": maximum_raise_to,
            "soft_maximum_raise_to": soft_maximum_raise_to,
            "can_raise": self.can_npc_raise(
                npc_index
            ),
            "players_remaining": len(
                active_indexes
            ),
            "opponents_remaining": max(
                0,
                len(active_indexes) - 1
            ),
            "last_raiser": self.last_raiser,
            "last_raiser_is_player": (
                self.last_raiser == 0
            ),
            "player_active": (
                not self.player_busted
                and not self.player_folded
            ),
            "player_tendencies": self.get_player_tendencies(),
            "skill_factor": self.get_npc_skill_factor(
                npc_index
            ),
        }
        context["personality_traits"] = get_npc_traits(self.npcs[npc_index])
        context["starting_stack"] = self.starting_stack
        context["hand_number"] = self.hand_number
        context["npc_identity"] = npc_identity(self.npcs[npc_index], npc_index + 1)
        context["opponent_reads"] = [
            self.table_reads.snapshot(seat, observer=context["npc_identity"])
            for seat in active_indexes if seat != npc_index + 1
        ]
        context["public_opponents"] = [
            {"seat": seat,
             "stack": self.player_stack if seat == 0 else self.npc_stacks[seat - 1],
             "round_bet": self.player_round_bet if seat == 0 else self.npc_round_bets[seat - 1]}
            for seat in active_indexes if seat != npc_index + 1
        ]
        context.update(self.get_npc_grudge_context(npc_index))
        return context


    # ==================================================
    # NPC HAND STRENGTH
    #
    # Returns roughly:
    #
    # 0.00 = garbage
    # 0.25 = weak
    # 0.50 = decent
    # 0.75 = strong
    # 1.00 = monster
    # ==================================================

    def get_npc_grudge_context(self, npc_index):
        opponents = []
        for seat in self.get_active_player_indexes():
            if seat == npc_index + 1:
                continue
            npc = self.npcs[seat - 1] if seat else {}
            opponents.append({
                "seat": seat, "id": npc_identity(npc, seat),
                "name": self.get_table_player_name(seat),
                "stack": self.player_stack if seat == 0 else self.npc_stacks[seat - 1],
                "round_bet": self.player_round_bet if seat == 0 else self.npc_round_bets[seat - 1],
            })
        return self.personality_memory.context(self.npcs[npc_index], npc_index + 1,
                                              opponents, self.last_raiser, self.hand_number)

    def record_personality_showdown(self, results):
        """Only resent an opponent who actually beat this NPC in a contested pot.

        A side-pot winner may still lose another pot, and folded players do not
        get invented showdown grudges. The memory deduplicates repeated hooks.
        """
        for pot in self.last_pot_awards:
            eligible = set(pot.get("eligible", results)) & set(results)
            winners = set(pot.get("winners", []))
            for seat in eligible - winners:
                if seat == 0:
                    continue
                npc = self.npcs[seat - 1]
                observer = npc_identity(npc, seat)
                severity = min(1.0, self.npc_hand_contributions[seat - 1]
                               / max(1, self.starting_stack))
                for winner in winners:
                    opponent = self.npcs[winner - 1] if winner else {}
                    self.personality_memory.record_loss(
                        observer, npc_identity(opponent, winner), self.hand_number,
                        get_npc_traits(npc)["bitterness"], severity)

    def get_npc_hand_strength(
            self,
            npc_index
    ):

        if not (
                0
                <= npc_index
                < len(self.npc_hands)
        ):
            return 0.0

        hand = (
            self.npc_hands[
                npc_index
            ]
        )

        if len(hand) < 2:
            return 0.0

        # ==================================================
        # PREFLOP
        # ==================================================

        if len(
                self.community_cards
        ) < 3:

            rank_1 = (
                RANK_VALUES[
                    hand[0]["rank"]
                ]
            )

            rank_2 = (
                RANK_VALUES[
                    hand[1]["rank"]
                ]
            )

            high_rank = max(
                rank_1,
                rank_2
            )

            low_rank = min(
                rank_1,
                rank_2
            )

            suited = (
                    hand[0]["suit"]
                    == hand[1]["suit"]
            )

            gap = abs(
                rank_1 - rank_2
            )

            # ------------------------------------------
            # Pocket pair
            # ------------------------------------------

            if rank_1 == rank_2:
                strength = (
                        0.43
                        + (
                                high_rank - 2
                        )
                        / 12.0
                        * 0.52
                )

                return max(
                    0.0,
                    min(
                        strength,
                        1.0
                    )
                )

            # ------------------------------------------
            # Non-pair
            # ------------------------------------------

            strength = (
                    0.08
                    + (
                            high_rank - 2
                    )
                    / 12.0
                    * 0.42
                    + (
                            low_rank - 2
                    )
                    / 12.0
                    * 0.12
            )

            # Suited cards
            if suited:
                strength += 0.07

            # Connected / nearly connected
            if gap == 1:
                strength += 0.07

            elif gap == 2:
                strength += 0.035

            # Two broadway cards
            if (
                    high_rank >= 10
                    and low_rank >= 10
            ):
                strength += 0.08

            # Ace bonus
            if high_rank == 14:
                strength += 0.035

            return max(
                0.0,
                min(
                    strength,
                    0.92
                )
            )

        # ==================================================
        # FLOP / TURN / RIVER
        # ==================================================

        cards = (
                hand
                + self.community_cards
        )

        result = (
            self.evaluate_best_hand(
                cards
            )
        )

        if result is None:
            return 0.0

        score = (
            result[0]
        )

        category = (
            score[0]
        )

        category_strengths = {
            0: 0.18,  # High card
            1: 0.40,  # Pair
            2: 0.58,  # Two pair
            3: 0.69,  # Trips
            4: 0.78,  # Straight
            5: 0.83,  # Flush
            6: 0.91,  # Full house
            7: 0.97,  # Quads
            8: 1.00,  # Straight flush
        }

        strength = (
            category_strengths.get(
                category,
                0.20
            )
        )

        # Give a small boost based on the most
        # important rank in the evaluated hand.
        if (
                len(score) >= 2
                and isinstance(
            score[1],
            int
        )
        ):
            strength += (
                    score[1]
                    / 14.0
                    * 0.06
            )

        return max(
            0.0,
            min(
                strength,
                1.0
            )
        )

    def can_npc_raise(
            self,
            npc_index
    ):

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            return False

        if (
                self.npc_busted[npc_index]
                or self.npc_folded[npc_index]
                or self.npc_all_in[npc_index]
        ):
            return False

        amount_to_call = (
            self.get_npc_amount_to_call(
                npc_index
            )
        )

        stack = (
            self.npc_stacks[
                npc_index
            ]
        )

        if stack <= amount_to_call:
            return False

        # NPC already acted and only returned because
        # of a short all-in raise.
        #
        # Call/Fold are legal, but raising is not reopened.
        if self.npc_has_acted[
            npc_index
        ]:
            return False

        maximum_raise_to = (
                self.npc_round_bets[
                    npc_index
                ]
                + stack
        )

        return (
                maximum_raise_to
                > self.current_bet
        )

    # ==================================================
    # NPC BET SIZING
    # ==================================================

    # ==================================================
    # NPC STREET BETTING CAP
    #
    # This is a SOFT AI cap, not a poker-rule cap.
    # It keeps NPCs from voluntarily detonating their
    # entire stack too early in the hand.
    # ==================================================

    def get_npc_stage_bet_cap(
            self,
            npc_index
    ):

        stack = self.npc_stacks[npc_index]

        if stack <= 0:
            return self.npc_round_bets[npc_index]

        stage_fractions = {
            "preflop": 0.12,
            "flop": 0.22,
            "turn": 0.40,
            "river": 1.00,
        }

        fraction = stage_fractions.get(
            self.current_stage,
            0.25
        )

        base_stack = max(
            1,
            self.starting_stack
        )

        target_cap = int(
            base_stack
            * fraction
        )

        target_cap = max(
            target_cap,
            self.get_minimum_open_bet()
        )

        maximum_total = (
            self.npc_round_bets[npc_index]
            + stack
        )

        return min(
            target_cap,
            maximum_total
        )

    def get_npc_open_bet_amount(
            self,
            npc_index,
            strength,
            profile,
            bluff=False
    ):

        context = self.build_npc_ai_context(
            npc_index,
            strength=strength
        )

        return choose_poker_open_bet_amount(
            context,
            profile,
            strength,
            bluff=bluff
        )

    def get_npc_raise_to_amount(
            self,
            npc_index,
            strength,
            profile,
            bluff=False
    ):

        context = self.build_npc_ai_context(
            npc_index,
            strength=strength
        )

        return choose_poker_raise_to_amount(
            context,
            profile,
            strength,
            bluff=bluff
        )

    # ==================================================
    # RUN ONE NPC ACTION
    # ==================================================

    def run_next_npc_action(self):

        self.ensure_npc_action_state()
        self.ensure_npc_bet_chunk_state()

        if (
                self.hand_complete
                or self.betting_round_complete
        ):
            return False

        if self.current_actor == 0:
            return False

        npc_index = self.current_actor - 1

        if not (
                0
                <= npc_index
                < len(self.npcs)
        ):
            self.advance_to_next_actor()
            return False

        # Repair impossible stale all-in state.
        if (
                self.npc_all_in[npc_index]
                and self.npc_stacks[npc_index] > 0
        ):
            self.npc_all_in[npc_index] = False

        if not self.actor_needs_action(
                self.current_actor
        ):
            self.advance_to_next_actor()
            return False

        if (
                self.npc_busted[npc_index]
                or self.npc_folded[npc_index]
                or self.npc_all_in[npc_index]
        ):
            self.advance_to_next_actor()
            return False

        if self.npc_stacks[npc_index] <= 0:
            self.npc_all_in[npc_index] = True
            self.npc_has_acted[npc_index] = True
            self.advance_to_next_actor()
            return False

        personality = self.get_npc_personality(
            npc_index
        )

        strength = self.get_npc_hand_strength(
            npc_index
        )

        context = self.build_npc_ai_context(
            npc_index,
            strength=strength
        )

        decision = decide_poker_action(
            personality,
            context
        )

        if len(self.npc_ai_last_decisions) != len(
                self.npcs
        ):
            self.npc_ai_last_decisions = [
                None
                for _ in self.npcs
            ]

        self.npc_ai_last_decisions[npc_index] = dict(
            decision
        )

        action = decision.get(
            "action",
            "check"
        )

        profile = decision.get(
            "profile",
            get_poker_personality_profile(
                "balanced"
            )
        )

        bluff = bool(
            decision.get(
                "bluff",
                False
            )
        )

        success = False

        if action == "fold":
            success = self.npc_fold(
                npc_index
            )

        elif action == "call":
            success = self.npc_call(
                npc_index
            )

        elif action == "check":
            success = self.npc_check(
                npc_index
            )

        elif action == "bet":
            bet_amount = self.get_npc_open_bet_amount(
                npc_index,
                strength,
                profile,
                bluff=bluff
            )

            if bet_amount is not None:
                success = self.npc_bet(
                    npc_index,
                    bet_amount
                )

        elif action == "raise":
            raise_to = self.get_npc_raise_to_amount(
                npc_index,
                strength,
                profile,
                bluff=bluff
            )

            if raise_to is not None:
                success = self.npc_raise(
                    npc_index,
                    raise_to
                )

        # ==================================================
        # Defensive legal fallback
        # ==================================================

        if not success and not self.hand_complete:
            amount_to_call = self.get_npc_amount_to_call(
                npc_index
            )

            if amount_to_call > 0:
                # If the desired action failed, a legal call is
                # preferable to leaving the turn unresolved.
                success = self.npc_call(
                    npc_index
                )

                if not success:
                    success = self.npc_fold(
                        npc_index
                    )

            else:
                success = self.npc_check(
                    npc_index
                )

        # npc_fold() may have awarded the pot immediately.
        if self.hand_complete:
            return success

        self.advance_to_next_actor()

        return success

    def get_actionable_player_indexes(self):

        actionable = []

        if (
                not self.player_busted
                and not self.player_folded
                and self.player_stack > 0
        ):
            actionable.append(0)

        for npc_index in range(
                len(self.npcs)
        ):

            if (
                    self.npc_busted[npc_index]
                    or self.npc_folded[npc_index]
                    or self.npc_stacks[npc_index] <= 0
            ):
                continue

            actionable.append(
                npc_index + 1
            )

        return actionable

    def should_reveal_runout_hands(self):
        """Expose live hands only once no further betting or outstanding call exists."""
        if self.current_stage not in ('preflop','flop','turn','river') or self.hand_complete:
            return False
        if len(self.get_active_player_indexes())<2 or len(self.get_actionable_player_indexes())>1:
            return False
        if not self.player_folded and not self.player_busted and self.player_stack>0 and self.player_round_bet<self.current_bet:
            return False
        for index in range(len(self.npcs)):
            if not self.npc_folded[index] and not self.npc_busted[index] and self.npc_stacks[index]>0 and self.npc_round_bets[index]<self.current_bet:
                return False
        return True

    def is_betting_round_complete(self):

        active_indexes = (
            self.get_active_player_indexes()
        )

        actionable_indexes = (
            self.get_actionable_player_indexes()
        )

        # ==================================================
        # First make sure every player who still CAN respond
        # has matched the current wager. This must happen before
        # the all-in auto-runout shortcut.
        # ==================================================

        if (
                not self.player_busted
                and not self.player_folded
                and self.player_stack > 0
        ):

            if self.player_all_in:
                self.player_all_in = False

            if (
                    self.player_round_bet
                    < self.current_bet
            ):
                return False

        for npc_index in range(
                len(self.npcs)
        ):

            if (
                    self.npc_busted[npc_index]
                    or self.npc_folded[npc_index]
                    or self.npc_stacks[npc_index] <= 0
            ):
                continue

            if self.npc_all_in[npc_index]:
                self.npc_all_in[npc_index] = False

            if (
                    self.npc_round_bets[npc_index]
                    < self.current_bet
            ):
                return False

        # ==================================================
        # Once all outstanding calls are settled, there is no
        # reason to make the lone player with chips check through
        # empty streets against only all-in opponents.
        # ==================================================

        if (
                len(active_indexes) > 1
                and len(actionable_indexes) <= 1
        ):
            return True

        # ==================================================
        # Normal acted-state checks
        # ==================================================

        if 0 in actionable_indexes:
            if not self.player_has_acted:
                return False

        for player_index in actionable_indexes:

            if player_index == 0:
                continue

            npc_index = player_index - 1

            if not self.npc_has_acted[npc_index]:
                return False

        return True

    # ==================================================
    # RESET BETTING ROUND
    # ==================================================

    def reset_betting_round(
            self,
            first_actor=None,
            assign_actor=True
    ):

        self.current_bet = 0
        self.last_raise_size = 0
        self.last_raiser = None

        # ==================================================
        # Round wagers
        # ==================================================

        self.player_round_bet = 0

        self.npc_round_bets = [
            0
            for _ in self.npcs
        ]

        self.player_bet_chunks = []

        self.npc_bet_chunks = [
            []
            for _ in self.npcs
        ]

        # ==================================================
        # Action labels
        # ==================================================

        self.player_action_text = ""

        self.npc_action_texts = [
            ""
            for _ in self.npcs
        ]

        # ==================================================
        # Acted flags
        # ==================================================

        self.player_has_acted = (
                self.player_busted
                or self.player_folded
                or (
                    self.player_all_in
                    and self.player_stack <= 0
                )
        )

        self.npc_has_acted = []

        for npc_index in range(
                len(self.npcs)
        ):

            inactive = (
                    self.npc_busted[npc_index]
                    or self.npc_folded[npc_index]
                    or (
                        self.npc_all_in[npc_index]
                        and self.npc_stacks[npc_index] <= 0
                    )
            )

            self.npc_has_acted.append(
                inactive
            )

        self.current_actor = -1
        self.betting_round_complete = False

        if not assign_actor:
            return

        if first_actor is None:
            first_actor = (
                self.get_postflop_first_actor_index()
            )

        self.set_first_actor_from(
            first_actor
        )

    # ==================================================
    # BETTING RULE HELPERS
    # ==================================================

    def get_minimum_open_bet(self):

        # A legal opening bet is one big blind.
        return max(
            1,
            self.big_blind
        )

    def get_minimum_raise_size(self):

        if self.last_raise_size > 0:
            return self.last_raise_size

        return max(
            1,
            self.big_blind
        )

    def get_minimum_raise_to(self):

        if self.current_bet <= 0:
            return self.get_minimum_open_bet()

        return (
                self.current_bet
                + self.get_minimum_raise_size()
        )

    def get_player_maximum_raise_to(self):

        return (
                self.player_round_bet
                + self.player_stack
        )

    def get_player_amount_to_call(self):

        return max(
            0,
            self.current_bet
            - self.player_round_bet
        )

    def can_player_act_now(self):

        if (
                self.current_actor != 0
                or self.player_stack <= 0
                or self.player_busted
                or self.player_folded
                or self.player_all_in
                or self.hand_complete
        ):
            return False

        # The player may already have acted earlier
        # in the betting round but still owe money
        # because of a later raise.
        return (
                not self.player_has_acted
                or self.player_round_bet
                < self.current_bet
        )

    def can_player_check(self):

        return (
                self.can_player_act_now()
                and self.get_player_amount_to_call() == 0
        )

    def can_player_call(self):

        return (
                self.can_player_act_now()
                and self.get_player_amount_to_call() > 0
        )

    def can_player_raise(self):

        if not self.can_player_act_now():
            return False

        # If the player already acted and has only
        # been brought back by a short all-in raise,
        # Call/Fold are allowed, but raising is not
        # reopened.
        if self.player_has_acted:
            return False

        return (
                self.get_player_maximum_raise_to()
                > self.current_bet
        )

    def player_fold(self):

        if (
                self.player_stack <= 0
                or self.player_folded
                or self.player_all_in
                or self.hand_complete
        ):
            return False

        self.record_player_tendency_action(
            "fold"
        )

        self.player_folded = True
        self.player_has_acted = True

        self.player_action_text = (
            "Folded"
        )

        self.log_hand_event(
            "fold",
            "You fold.",
            actor_index=0
        )

        self.resolve_after_fold()

        return True

    def player_check(self):

        if not self.can_player_check():
            return False

        self.record_player_tendency_action(
            "check"
        )

        self.player_has_acted = True
        self.player_action_text = "Checked"

        self.log_hand_event(
            "check",
            "You check.",
            actor_index=0
        )

        self.advance_to_next_actor()

        return True

    def player_call(self):

        if not self.can_player_call():
            return False

        amount_to_call = (
            self.get_player_amount_to_call()
        )

        pot_before = self.pot

        amount_paid = (
            self.commit_player_chips(
                amount_to_call
            )
        )

        if amount_paid <= 0:
            return False

        self.record_player_tendency_action(
            "call",
            amount=amount_paid,
            amount_to_call=amount_to_call,
            pot_before=pot_before
        )

        self.player_has_acted = True

        self.player_action_text = (
            f"Called ${amount_paid:,}"
        )

        suffix = (
            " and are all-in."
            if self.player_all_in
            else "."
        )

        self.log_hand_event(
            "call",
            f"You call ${amount_paid:,}{suffix}",
            actor_index=0,
            amount=amount_paid,
            all_in=self.player_all_in
        )

        self.advance_to_next_actor()

        return True

    def player_bet(
            self,
            amount
    ):

        if not self.can_player_act_now():
            return False

        if self.current_bet > 0:
            return False

        if self.player_stack <= 0:
            return False

        amount = int(
            amount
        )

        if amount <= 0:
            return False

        minimum_bet = (
            self.get_minimum_open_bet()
        )

        maximum_bet = (
            self.player_stack
        )

        if (
                amount < minimum_bet
                and amount < maximum_bet
        ):
            return False

        old_current_bet = self.current_bet
        pot_before = self.pot

        amount_paid = (
            self.commit_player_chips(
                min(
                    amount,
                    maximum_bet
                )
            )
        )

        if amount_paid <= 0:
            return False

        self.record_player_tendency_action(
            "bet",
            amount=amount_paid,
            amount_to_call=0,
            pot_before=pot_before
        )

        self.current_bet = (
            self.player_round_bet
        )

        actual_raise_size = (
            self.current_bet
            - old_current_bet
        )

        if actual_raise_size >= minimum_bet:
            self.last_raise_size = actual_raise_size
            self.last_raiser = 0
            self.reset_actions_after_aggression(
                0
            )

        self.player_has_acted = True

        self.player_action_text = (
            f"Bet ${amount_paid:,}"
        )

        suffix = (
            " and are all-in."
            if self.player_all_in
            else "."
        )

        self.log_hand_event(
            "bet",
            f"You bet ${amount_paid:,}{suffix}",
            actor_index=0,
            amount=amount_paid,
            all_in=self.player_all_in
        )

        self.advance_to_next_actor()

        return True

    def player_raise(
            self,
            raise_to
    ):

        # An all-in call uses the same chips as Call; it must remain available
        # even when the stack cannot reach the opponent's bet.
        if self.can_player_call() and self.get_player_amount_to_call() >= self.player_stack:
            return self.player_call()
        if not self.can_player_raise():
            return False

        if self.current_bet <= 0:
            return False

        raise_to = int(
            raise_to
        )

        maximum_raise_to = (
            self.get_player_maximum_raise_to()
        )

        minimum_raise_to = (
            self.get_minimum_raise_to()
        )

        if raise_to <= self.current_bet:
            return False

        if (
                raise_to < minimum_raise_to
                and raise_to < maximum_raise_to
        ):
            return False

        target = min(
            raise_to,
            maximum_raise_to
        )

        old_current_bet = self.current_bet
        amount_to_call = self.get_player_amount_to_call()
        pot_before = self.pot

        amount_needed = (
            target
            - self.player_round_bet
        )

        if amount_needed <= 0:
            return False

        amount_paid = (
            self.commit_player_chips(
                amount_needed
            )
        )

        if amount_paid <= 0:
            return False

        self.record_player_tendency_action(
            "raise",
            amount=amount_paid,
            amount_to_call=amount_to_call,
            pot_before=pot_before
        )

        if self.player_round_bet > old_current_bet:
            actual_raise_size = (
                self.player_round_bet
                - old_current_bet
            )

            self.current_bet = self.player_round_bet

            required_raise_size = (
                self.get_minimum_raise_size()
            )

            if actual_raise_size >= required_raise_size:
                self.last_raise_size = actual_raise_size
                self.last_raiser = 0
                self.reset_actions_after_aggression(
                    0
                )

        self.player_has_acted = True

        self.player_action_text = (
            f"Raised to "
            f"${self.player_round_bet:,}"
        )

        suffix = (
            " and are all-in."
            if self.player_all_in
            else "."
        )

        self.log_hand_event(
            "raise",
            (
                f"You raise to "
                f"${self.player_round_bet:,}"
                f"{suffix}"
            ),
            actor_index=0,
            amount=amount_paid,
            raise_to=self.player_round_bet,
            all_in=self.player_all_in
        )

        self.advance_to_next_actor()

        return True

    # ==================================================
    # COMMUNITY CARDS
    # ==================================================

    def deal_flop(self):

        if self.current_stage != "preflop":
            return False

        # Burn
        self.draw_card()

        for _ in range(3):
            self.community_cards.append(
                self.draw_card()
            )

        self.current_stage = "flop"

        flop_cards = self.community_cards[:3]

        self.log_hand_event(
            "flop",
            f"Flop: {format_poker_cards(flop_cards)}.",
            cards=[
                dict(card)
                for card in flop_cards
                if card
            ]
        )

        self.reset_betting_round(
            first_actor=(
                self.get_postflop_first_actor_index()
            )
        )

        return True

    def deal_turn(self):

        if self.current_stage != "flop":
            return False

        # Burn
        self.draw_card()

        self.community_cards.append(
            self.draw_card()
        )

        self.current_stage = "turn"

        turn_card = self.community_cards[-1]

        self.log_hand_event(
            "turn",
            f"Turn: {format_poker_cards([turn_card])}.",
            cards=[dict(turn_card)] if turn_card else []
        )

        self.reset_betting_round(
            first_actor=(
                self.get_postflop_first_actor_index()
            )
        )

        return True

    def deal_river(self):

        if self.current_stage != "turn":
            return False

        # Burn
        self.draw_card()

        self.community_cards.append(
            self.draw_card()
        )

        self.current_stage = "river"

        river_card = self.community_cards[-1]

        self.log_hand_event(
            "river",
            f"River: {format_poker_cards([river_card])}.",
            cards=[dict(river_card)] if river_card else []
        )

        self.reset_betting_round(
            first_actor=(
                self.get_postflop_first_actor_index()
            )
        )

        return True

    # ==================================================
    # FIVE-CARD HAND EVALUATION
    # ==================================================

    def evaluate_five_cards(
            self,
            cards
    ):

        values = sorted(
            [
                RANK_VALUES[
                    card["rank"]
                ]
                for card in cards
            ],
            reverse=True
        )

        suits = [
            card["suit"]
            for card in cards
        ]

        counts = Counter(
            values
        )

        is_flush = (
            len(
                set(
                    suits
                )
            ) == 1
        )

        unique_values = sorted(
            set(
                values
            ),
            reverse=True
        )

        # Ace-low straight
        if 14 in unique_values:
            unique_values.append(
                1
            )

        straight_high = None

        for index in range(
                len(
                    unique_values
                ) - 4
        ):

            window = (
                unique_values[
                    index:
                    index + 5
                ]
            )

            if (
                    window[0]
                    - window[4]
                    == 4
            ):

                straight_high = (
                    window[0]
                )

                break

        # ==========================================
        # Straight Flush
        # ==========================================

        if (
                is_flush
                and straight_high is not None
        ):

            return (
                8,
                straight_high
            )

        # ==========================================
        # Four of a Kind
        # ==========================================

        quads = sorted(
            [
                value
                for value, count
                in counts.items()
                if count == 4
            ],
            reverse=True
        )

        if quads:

            quad_value = (
                quads[0]
            )

            kicker = max(
                value
                for value in values
                if value != quad_value
            )

            return (
                7,
                quad_value,
                kicker
            )

        # ==========================================
        # Full House
        # ==========================================

        triples = sorted(
            [
                value
                for value, count
                in counts.items()
                if count == 3
            ],
            reverse=True
        )

        pairs = sorted(
            [
                value
                for value, count
                in counts.items()
                if count >= 2
            ],
            reverse=True
        )

        if triples:

            trip_value = (
                triples[0]
            )

            pair_candidates = [
                value
                for value in pairs
                if value != trip_value
            ]

            if len(
                    triples
            ) >= 2:

                pair_candidates.append(
                    triples[1]
                )

            if pair_candidates:

                return (
                    6,
                    trip_value,
                    max(
                        pair_candidates
                    )
                )

        # ==========================================
        # Flush
        # ==========================================

        if is_flush:

            return (
                5,
                *values
            )

        # ==========================================
        # Straight
        # ==========================================

        if straight_high is not None:

            return (
                4,
                straight_high
            )

        # ==========================================
        # Three of a Kind
        # ==========================================

        if triples:

            trip_value = (
                triples[0]
            )

            kickers = sorted(
                [
                    value
                    for value in values
                    if value != trip_value
                ],
                reverse=True
            )[:2]

            return (
                3,
                trip_value,
                *kickers
            )

        # ==========================================
        # Two Pair / Pair
        # ==========================================

        exact_pairs = sorted(
            [
                value
                for value, count
                in counts.items()
                if count == 2
            ],
            reverse=True
        )

        if len(
                exact_pairs
        ) >= 2:

            high_pair = (
                exact_pairs[0]
            )

            low_pair = (
                exact_pairs[1]
            )

            kicker = max(
                value
                for value in values
                if value not in (
                    high_pair,
                    low_pair
                )
            )

            return (
                2,
                high_pair,
                low_pair,
                kicker
            )

        if len(
                exact_pairs
        ) == 1:

            pair_value = (
                exact_pairs[0]
            )

            kickers = sorted(
                [
                    value
                    for value in values
                    if value != pair_value
                ],
                reverse=True
            )[:3]

            return (
                1,
                pair_value,
                *kickers
            )

        # ==========================================
        # High Card
        # ==========================================

        return (
            0,
            *values
        )

    # ==================================================
    # BEST 5 OF 7
    # ==================================================

    def evaluate_best_hand(
            self,
            cards
    ):

        if len(
                cards
        ) < 5:

            return None

        best_score = None
        best_cards = None

        for combo in combinations(
                cards,
                5
        ):

            score = (
                self.evaluate_five_cards(
                    combo
                )
            )

            if (
                    best_score is None
                    or score > best_score
            ):

                best_score = (
                    score
                )

                best_cards = list(
                    combo
                )

        return (
            best_score,
            best_cards
        )

    # ==================================================
    # SHOWDOWN
    # ==================================================

    def showdown(self):

        if len(
                self.community_cards
        ) != 5:
            return False

        active_indexes = (
            self.get_active_player_indexes()
        )

        if not active_indexes:
            return False

        # ==================================================
        # One player remains
        # ==================================================

        if len(active_indexes) == 1:
            return (
                self.award_pot_to_single_player(
                    active_indexes[0]
                )
            )

        # ==================================================
        # Evaluate every active hand ONCE
        # ==================================================

        results = {}

        for player_index in active_indexes:

            result = (
                self.get_showdown_result(
                    player_index
                )
            )

            if result is not None:
                results[
                    player_index
                ] = result

        if not results:
            return False

        self.last_resolved_pot = max(
            0,
            int(self.pot)
        )

        self.log_hand_event(
            "showdown",
            "Showdown."
        )

        for player_index, result in results.items():

            if player_index == 0:
                cards = self.player_hand
                prefix = "You show"
            else:
                npc_index = player_index - 1
                cards = self.npc_hands[npc_index]
                prefix = (
                    f"{self.get_table_player_name(player_index)} "
                    f"shows"
                )

            category = HAND_NAMES[
                result[0][0]
            ]

            hand_detail = describe_poker_score(
                result[0],
                compact=True
            )

            self.log_hand_event(
                "showdown_hand",
                (
                    f"{prefix} "
                    f"{format_poker_cards(cards)} "
                    f"({hand_detail})."
                ),
                actor_index=player_index,
                cards=[
                    dict(card)
                    for card in cards
                    if card
                ],
                hand_name=category,
                hand_detail=hand_detail
            )

        # ==================================================
        # Build main pot + side pots
        # ==================================================

        side_pots = (
            self.build_side_pots()
        )

        payout_totals = {
            player_index: 0
            for player_index
            in results
        }

        self.last_pot_awards = []
        self.recap_open = False
        self.recap_page = 0

        # ==================================================
        # Resolve each pot separately
        # ==================================================

        for pot_data in side_pots:

            pot_amount = (
                pot_data[
                    "amount"
                ]
            )

            eligible = [
                player_index
                for player_index
                in pot_data[
                    "eligible"
                ]
                if player_index in results
            ]

            if not eligible:
                continue

            best_score = max(
                results[
                    player_index
                ][0]
                for player_index
                in eligible
            )

            winners = [
                player_index
                for player_index
                in eligible
                if (
                        results[
                            player_index
                        ][0]
                        == best_score
                )
            ]

            if not winners:
                continue

            # Deterministic order for odd chips.
            #
            # Once we add a rotating dealer button,
            # odd-chip priority can follow real position.
            winners = sorted(
                winners
            )

            share = (
                    pot_amount
                    // len(winners)
            )

            remainder = (
                    pot_amount
                    % len(winners)
            )

            for winner_order, winner_index in enumerate(
                    winners
            ):

                winnings = share

                if winner_order < remainder:
                    winnings += 1

                self.award_chips_to_player(
                    winner_index,
                    winnings
                )

                payout_totals[
                    winner_index
                ] += winnings

            self.last_pot_awards.append(
                {
                    "amount":
                        pot_amount,

                    "eligible": eligible.copy(),
                    "winners":
                        winners.copy(),

                    "share":
                        share,

                    "remainder":
                        remainder,
                    "hand": describe_poker_score(best_score, compact=True),
                }
            )

        # ==================================================
        # Record everybody who won at least one pot
        # ==================================================

        self.winner_indexes = sorted(
            [
                player_index
                for player_index, winnings
                in payout_totals.items()
                if winnings > 0
            ]
        )

        # ==================================================
        # Result text
        # ==================================================

        payout_winners = [
            player_index
            for player_index
            in self.winner_indexes
            if payout_totals.get(
                player_index,
                0
            ) > 0
        ]

        # ------------------------------------------
        # One player collected everything
        # ------------------------------------------

        if len(payout_winners) == 1:

            winner_index = (
                payout_winners[0]
            )

            winnings = (
                payout_totals[
                    winner_index
                ]
            )

            winner_result = (
                results[
                    winner_index
                ]
            )

            category = (
                HAND_NAMES[
                    winner_result[0][0]
                ]
            )

            hand_detail = describe_poker_score(
                winner_result[0],
                compact=True
            )

            if winner_index == 0:

                self.result_text = (
                    f"You win ${winnings:,} "
                    f"with {hand_detail}!"
                )

            else:

                winner_name = (
                    self.get_table_player_name(
                        winner_index
                    )
                )

                self.result_text = (
                    f"{winner_name} wins "
                    f"${winnings:,} with "
                    f"{hand_detail}."
                )

        # ------------------------------------------
        # Different players won different pots
        # ------------------------------------------

        else:

            payout_parts = []

            for player_index in payout_winners:
                name = (
                    self.get_table_player_name(
                        player_index
                    )
                )

                winnings = (
                    payout_totals[
                        player_index
                    ]
                )

                payout_parts.append(
                    f"{name} ${winnings:,} with {describe_poker_score(results[player_index][0], compact=True)}"
                )

            self.result_text = (
                    "Payouts: "
                    + "; ".join(
                payout_parts
            )
                    + "."
            )

        # ==================================================
        # Detailed side-pot history
        # ==================================================

        # Keep the result in the normal payout banner. Detailed review is opt-in.
        self.recap_open = False
        self.log_detailed_pot_awards(
            results.keys()
        )

        self.log_hand_event(
            "result",
            self.result_text,
            winners=self.winner_indexes.copy(),
            payouts={
                player_index: amount
                for player_index, amount
                in payout_totals.items()
                if amount > 0
            }
        )

        # ==================================================
        # Finish hand
        # ==================================================

        self.record_personality_showdown(results)

        self.pot = 0

        self.hand_complete = True

        self.current_actor = -1

        self.current_stage = "showdown"

        # Only NOW is a $0 stack actually busted.
        #
        # Somebody who was temporarily at $0 because
        # they were all-in may have just won chips.
        newly_busted = self.refresh_busted_state()

        self.log_newly_busted_players(
            newly_busted
        )

        self.finalize_showdown_display_state()

        return True

    # ==================================================
    # DISPLAY HELPERS
    # ==================================================

    def get_player_hand_name(self):

        cards = (
            self.player_hand
            + self.community_cards
        )

        if len(cards) < 5:
            return ""

        result = (
            self.evaluate_best_hand(
                cards
            )
        )

        if result is None:
            return ""

        return HAND_NAMES[
            result[0][0]
        ]

    def get_npc_hand_name(
            self,
            npc_index
    ):

        if not (
                0
                <= npc_index
                < len(
                    self.npc_hands
                )
        ):

            return ""

        cards = (
            self.npc_hands[
                npc_index
            ]
            + self.community_cards
        )

        if len(cards) < 5:
            return ""

        result = (
            self.evaluate_best_hand(
                cards
            )
        )

        if result is None:
            return ""

        return HAND_NAMES[
            result[0][0]
        ]
