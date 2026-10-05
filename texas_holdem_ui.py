from poker_recap import draw_recap, get_recap_action
import math

import pygame

from poker_speech import (
    PokerSpeechOverlay,
    is_poker_chat_popups_enabled,
    set_poker_chat_popups_enabled,
)
from poker_ui_assets import draw_poker_logo


# ==================================================
# ACTIONS
# ==================================================

ACTION_DEAL = "deal"
ACTION_FLOP = "flop"
ACTION_TURN = "turn"
ACTION_RIVER = "river"
ACTION_SHOWDOWN = "showdown"
ACTION_RETURN = "return"
ACTION_FOLD = "fold"
ACTION_CHECK_CALL = "check_call"
ACTION_BET_RAISE = "bet_raise"
ACTION_NEXT_HAND = "next_hand"

# ==================================================
# HOLDEM LOG
# ==================================================

HOLDEM_LOG_RECT = pygame.Rect(
    18,
    610,
    410,
    140
)

holdem_log_scroll = 0

# ==================================================
# LOAD ASSETS/IMAGES
# ==================================================
_poker_chip_images = None


def get_poker_chip_images():

    global _poker_chip_images

    if _poker_chip_images is None:

        _poker_chip_images = {
            "black": pygame.image.load(
                "assets/poker/chip_black.png"
            ).convert_alpha(),

            "blue": pygame.image.load(
                "assets/poker/chip_blue.png"
            ).convert_alpha(),

            "green": pygame.image.load(
                "assets/poker/chip_green.png"
            ).convert_alpha(),

            "red": pygame.image.load(
                "assets/poker/chip_red.png"
            ).convert_alpha(),

            "yellow": pygame.image.load(
                "assets/poker/chip_yellow.png"
            ).convert_alpha(),
        }

    return _poker_chip_images

# ==================================================
# HOLDEM FONTS
# ==================================================

_holdem_fonts = None


def get_holdem_fonts():

    global _holdem_fonts

    if _holdem_fonts is None:

        if not pygame.font.get_init():
            pygame.font.init()

        _holdem_fonts = {
            "title": pygame.font.SysFont(
                "cambria",
                31,
                bold=True
            ),

            "name": pygame.font.SysFont(
                "cambria",
                20,
                bold=True
            ),

            "small": pygame.font.SysFont(
                "cambria",
                17,
                bold=True
            ),

            "tiny": pygame.font.SysFont(
                "cambria",
                15,
                bold=True
            ),
        }

    return _holdem_fonts

# ==================================================
# COLORS
# ==================================================

WHITE = (
    255,
    255,
    255
)

BLACK = (
    20,
    20,
    20
)

TABLE_GREEN = (
    30,
    105,
    55
)

TABLE_EDGE = (
    95,
    65,
    35
)

PANEL_DARK = (
    20,
    35,
    25
)


# ==================================================
# HOLDEM HUD RECTS
# ==================================================

holdem_next_hand_rect = pygame.Rect(
    1010,
    626,
    250,
    42
)

holdem_action_panel_rect = pygame.Rect(
    925,
    610,
    420,
    140
)

# Main poker actions
holdem_fold_rect = pygame.Rect(
    942,
    622,
    112,
    40
)

holdem_call_rect = pygame.Rect(
    1064,
    622,
    132,
    40
)

holdem_raise_rect = pygame.Rect(
    1206,
    622,
    122,
    40
)

# ==================================================
# BET SLIDER STATE
# ==================================================

holdem_bet_fraction = 0.25

holdem_bet_slider_dragging = False

holdem_manual_bet_text = ""
holdem_manual_bet_active = False

# Raise slider
holdem_slider_rect = pygame.Rect(
    942,
    683,
    250,
    14
)

# Direct numeric bet / raise-to entry.
holdem_manual_bet_rect = pygame.Rect(
    1202,
    674,
    126,
    30
)

# Raise shortcuts
holdem_min_rect = pygame.Rect(
    942,
    708,
    68,
    28
)

holdem_half_rect = pygame.Rect(
    1018,
    708,
    68,
    28
)

holdem_pot_rect = pygame.Rect(
    1094,
    708,
    68,
    28
)

holdem_max_rect = pygame.Rect(
    1170,
    708,
    68,
    28
)

# Top-right utility buttons
holdem_options_rect = pygame.Rect(
    1180,
    20,
    90,
    38
)

holdem_exit_rect = pygame.Rect(
    1280,
    20,
    68,
    38
)

# ==================================================
# HOLDEM LOG STATE
# ==================================================

holdem_log_history = []

holdem_log_scroll = 0

holdem_chat_history = []
_holdem_speech_overlay = PokerSpeechOverlay()

holdem_active_tab = "log"

holdem_chat_scroll = 0

holdem_chat_unread = False

_holdem_last_stage = None
_holdem_last_result = None

# ==================================================
# HOLDEM OPTIONS STATE
# ==================================================

holdem_options_open = False

holdem_table_speed = "normal"

holdem_auto_deal_enabled = True

holdem_table_chat_enabled = True


# ==================================================
# HOLDEM OPTIONS RECTS
# ==================================================

holdem_options_panel_rect = pygame.Rect(
    438,
    185,
    490,
    430
)

holdem_options_close_rect = pygame.Rect(
    842,
    220,
    66,
    34
)

# Table speed
holdem_speed_slow_rect = pygame.Rect(
    515,
    325,
    110,
    38
)

holdem_speed_normal_rect = pygame.Rect(
    628,
    325,
    110,
    38
)

holdem_speed_fast_rect = pygame.Rect(
    741,
    325,
    110,
    38
)

# Auto deal
holdem_auto_deal_toggle_rect = pygame.Rect(
    707,
    406,
    144,
    38
)

# Table chat
holdem_chat_toggle_rect = pygame.Rect(
    707,
    468,
    144,
    38
)

# Table chat pop-ups
holdem_chat_popups_toggle_rect = pygame.Rect(
    707,
    530,
    144,
    38
)

# More UI
# ==================================================
# HOLDEM BUY-IN RECTS
# ==================================================

holdem_buy_in_panel_rect = pygame.Rect(
    283,
    180,
    800,
    410
)

holdem_buy_in_25_rect = pygame.Rect(
    318,
    330,
    165,
    100
)

holdem_buy_in_50_rect = pygame.Rect(
    506,
    330,
    165,
    100
)

holdem_buy_in_75_rect = pygame.Rect(
    694,
    330,
    165,
    100
)

holdem_buy_in_max_rect = pygame.Rect(
    882,
    330,
    165,
    100
)

holdem_buy_in_back_rect = pygame.Rect(
    558,
    505,
    250,
    44
)

# ==================================================
# HOLDEM BUY-IN HELPERS
# ==================================================

def get_holdem_buy_in_amounts(
        career_cash
):

    career_cash = max(
        0,
        int(career_cash)
    )

    return {
        "25": int(
            career_cash * 0.25
        ),

        "50": int(
            career_cash * 0.50
        ),

        "75": int(
            career_cash * 0.75
        ),

        "max": career_cash,
    }


def get_texas_holdem_buy_in_action(
        mouse_pos,
        career_cash,
        minimum_buy_in=100
):

    if mouse_pos is None:
        return None

    if holdem_buy_in_back_rect.collidepoint(
            mouse_pos
    ):

        return (
            "back",
            None
        )

    amounts = (
        get_holdem_buy_in_amounts(
            career_cash
        )
    )

    choices = (
        (
            holdem_buy_in_25_rect,
            amounts["25"]
        ),
        (
            holdem_buy_in_50_rect,
            amounts["50"]
        ),
        (
            holdem_buy_in_75_rect,
            amounts["75"]
        ),
        (
            holdem_buy_in_max_rect,
            amounts["max"]
        ),
    )

    for rect, amount in choices:

        if (
                rect.collidepoint(
                    mouse_pos
                )
                and amount
                >= minimum_buy_in
        ):

            return (
                "buy_in",
                amount
            )

    return None

# ==================================================
# HOLDEM OPTIONS HELPERS
# ==================================================

def is_holdem_options_open():

    return holdem_options_open


def toggle_holdem_options():

    global holdem_options_open

    holdem_options_open = (
        not holdem_options_open
    )


def close_holdem_options():

    global holdem_options_open

    holdem_options_open = False


def is_holdem_auto_deal_enabled():

    return holdem_auto_deal_enabled


def is_holdem_table_chat_enabled():

    return holdem_table_chat_enabled


def is_holdem_table_chat_popups_enabled():

    return is_poker_chat_popups_enabled()


def get_holdem_npc_delay():

    delays = {
        "slow": 1800,
        "normal": 1200,
        "fast": 600,
    }

    return delays.get(
        holdem_table_speed,
        1200
    )


def get_holdem_street_delay():

    # Keep enough time for the chip sweep animation
    # to finish before the next street appears.
    delays = {
        "slow": 1700,
        "normal": 1200,
        "fast": 950,
    }

    return delays.get(
        holdem_table_speed,
        1200
    )


def get_holdem_next_hand_delay():

    # Auto-deal countdown itself stays reasonably
    # relaxed, but fast mode trims it somewhat.
    delays = {
        "slow": 18000,
        "normal": 15000,
        "fast": 9000,
    }

    return delays.get(
        holdem_table_speed,
        15000
    )


def handle_holdem_options_click(
        mouse_pos
):

    global holdem_options_open
    global holdem_table_speed
    global holdem_auto_deal_enabled
    global holdem_table_chat_enabled

    if not holdem_options_open:
        return False

    if mouse_pos is None:
        return False

    # ==================================================
    # Close
    # ==================================================

    if holdem_options_close_rect.collidepoint(
            mouse_pos
    ):

        holdem_options_open = False

        return True

    # ==================================================
    # Speed
    # ==================================================

    if holdem_speed_slow_rect.collidepoint(
            mouse_pos
    ):

        holdem_table_speed = "slow"

        return True

    if holdem_speed_normal_rect.collidepoint(
            mouse_pos
    ):

        holdem_table_speed = "normal"

        return True

    if holdem_speed_fast_rect.collidepoint(
            mouse_pos
    ):

        holdem_table_speed = "fast"

        return True

    # ==================================================
    # Auto deal
    # ==================================================

    if holdem_auto_deal_toggle_rect.collidepoint(
            mouse_pos
    ):

        holdem_auto_deal_enabled = (
            not holdem_auto_deal_enabled
        )

        return True

    # ==================================================
    # Table chat
    # ==================================================

    if holdem_chat_toggle_rect.collidepoint(
            mouse_pos
    ):

        holdem_table_chat_enabled = (
            not holdem_table_chat_enabled
        )

        return True

    if (
            holdem_table_chat_enabled
            and holdem_chat_popups_toggle_rect.collidepoint(mouse_pos)
    ):
        set_poker_chat_popups_enabled(
            not is_poker_chat_popups_enabled()
        )
        return True

    return False

# ==================================================
# CARD ANIMATION STATE
# ==================================================

_holdem_card_fx_hand_number = -1
_holdem_card_fx_stage = None

_holdem_card_fx_kind = None
_holdem_card_fx_started_at = 0

# ==================================================
# CHIP ANIMATION STATE
# ==================================================

_holdem_chip_fx_hand_number = -1
_holdem_chip_fx_stage = None

_holdem_chip_fx_signatures = {}
_holdem_chip_fx_started_at = {}
_holdem_chip_fx_indexes = {}

HOLDEM_CHIP_FX_DURATION = 280

# ==================================================
# WAGER SWEEP ANIMATION STATE
# ==================================================

_holdem_wager_sweep_key = None
_holdem_wager_sweep_started_at = 0

HOLDEM_WAGER_SWEEP_DELAY = 200
HOLDEM_WAGER_SWEEP_DURATION = 700

# ==================================================
# POT DISPLAY / PAYOUT ANIMATION
# ==================================================

_holdem_payout_fx_key = None
_holdem_payout_fx_started_at = 0

HOLDEM_PAYOUT_FX_DURATION = 1050


def _holdem_chip_key_for_amount(
        amount,
        base_unit
):
    base_unit = max(
        1,
        int(base_unit)
    )

    if amount >= base_unit * 20:
        return "black"

    if amount >= base_unit * 10:
        return "yellow"

    if amount >= base_unit * 5:
        return "green"

    if amount >= base_unit * 2:
        return "blue"

    return "red"


def _holdem_pot_chip_count(
        amount,
        base_unit
):
    if amount <= 0:
        return 0

    ratio = (
        float(amount)
        / max(
            1.0,
            float(base_unit)
        )
    )

    if ratio < 2:
        return 1
    if ratio < 5:
        return 2
    if ratio < 10:
        return 3
    if ratio < 20:
        return 4
    if ratio < 40:
        return 5
    if ratio < 80:
        return 6

    return 7


def draw_holdem_pot_stack(
        surface,
        amount,
        center,
        base_unit
):
    amount = max(
        0,
        int(amount)
    )

    count = _holdem_pot_chip_count(
        amount,
        base_unit
    )

    if count <= 0:
        return

    chip_images = get_poker_chip_images()
    chip_key = _holdem_chip_key_for_amount(
        amount,
        base_unit
    )
    chip = chip_images.get(
        chip_key
    )

    if chip is None:
        return

    chip_size = 21
    spacing = 11
    row_capacity = 4

    for index in range(count):
        row = index // row_capacity
        column = index % row_capacity

        items_in_row = min(
            row_capacity,
            count - row * row_capacity
        )

        row_width = (
            (items_in_row - 1)
            * spacing
        )

        draw_x = (
            center[0]
            - row_width // 2
            + column * spacing
        )

        draw_y = (
            center[1]
            - row * 7
        )

        scaled = pygame.transform.smoothscale(
            chip,
            (
                chip_size,
                chip_size
            )
        )

        surface.blit(
            scaled,
            scaled.get_rect(
                center=(
                    draw_x,
                    draw_y
                )
            )
        )


def get_holdem_payout_fx_progress(
        holdem_game
):
    global _holdem_payout_fx_key
    global _holdem_payout_fx_started_at

    if (
            holdem_game.current_stage
            != "showdown"
            or not holdem_game.hand_complete
            or not holdem_game.winner_indexes
            or holdem_game.get_display_pot_amount()
            <= 0
    ):
        return None

    key = (
        getattr(
            holdem_game,
            "hand_number",
            0
        ),
        tuple(
            holdem_game.winner_indexes
        ),
        int(
            holdem_game.get_display_pot_amount()
        )
    )

    now = pygame.time.get_ticks()

    if key != _holdem_payout_fx_key:
        _holdem_payout_fx_key = key
        _holdem_payout_fx_started_at = now

    progress = (
        now
        - _holdem_payout_fx_started_at
    ) / HOLDEM_PAYOUT_FX_DURATION

    progress = max(
        0.0,
        min(
            1.0,
            progress
        )
    )

    return get_holdem_chip_ease(
        progress
    )


def draw_holdem_payout_animation(
        surface,
        holdem_game,
        npc_anchors,
        base_unit
):
    progress = get_holdem_payout_fx_progress(
        holdem_game
    )

    if (
            progress is None
            or progress >= 1.0
    ):
        return

    winners = list(
        holdem_game.winner_indexes
    )

    if not winners:
        return

    amount = max(
        1,
        int(
            holdem_game.get_display_pot_amount()
        )
    )

    chip_images = get_poker_chip_images()
    chip = chip_images.get(
        _holdem_chip_key_for_amount(
            amount,
            base_unit
        )
    )

    if chip is None:
        return

    start = (
        683,
        242
    )

    target_by_player = {
        0: (
            683,
            696
        )
    }

    for index, anchor in enumerate(
            npc_anchors
    ):
        target_by_player[
            index + 1
        ] = (
            anchor[0] + 82,
            anchor[1] + 28
        )

    chip_count = max(
        3,
        min(
            8,
            _holdem_pot_chip_count(
                amount,
                base_unit
            ) + 1
        )
    )

    for chip_index in range(
            chip_count
    ):
        winner_index = winners[
            chip_index
            % len(winners)
        ]

        target = target_by_player.get(
            winner_index,
            start
        )

        local_progress = max(
            0.0,
            min(
                1.0,
                progress
                * 1.18
                - chip_index * 0.035
            )
        )

        draw_x = int(
            start[0]
            + (
                target[0]
                - start[0]
            )
            * local_progress
        )

        draw_y = int(
            start[1]
            + (
                target[1]
                - start[1]
            )
            * local_progress
        )

        draw_y -= int(
            math.sin(
                local_progress
                * math.pi
            )
            * 34
        )

        draw_x += (
            chip_index % 3
            - 1
        ) * 7

        scaled = pygame.transform.smoothscale(
            chip,
            (
                24,
                24
            )
        )

        surface.blit(
            scaled,
            scaled.get_rect(
                center=(
                    draw_x,
                    draw_y
                )
            )
        )


def draw_holdem_showdown_banner(
        surface,
        holdem_game
):
    if (
            holdem_game.current_stage
            != "showdown"
            or not holdem_game.result_text
    ):
        return

    fonts = get_holdem_fonts()

    player_won = (
        0 in holdem_game.winner_indexes
    )

    phase = (
        pygame.time.get_ticks()
        % 1200
    ) / 1200.0

    pulse = (
        0.5
        + 0.5
        * math.sin(
            phase
            * math.tau
        )
    )

    border = (
        (
            255,
            int(
                190
                + 55 * pulse
            ),
            65
        )
        if player_won
        else (
            185,
            190,
            195
        )
    )

    rect = pygame.Rect(
        358,
        452,
        650,
        48
    )

    draw_translucent_panel(
        surface,
        rect,
        (
            10,
            12,
            14,
            225
        ),
        border_color=border,
        border_width=(
            4
            if player_won
            else 2
        ),
        radius=12
    )

    blit_text_fit(
        surface,
        holdem_game.result_text,
        fonts["small"],
        WHITE,
        rect,
        padding=18
    )


# ==================================================
# CARD HELPERS // OTHER HELPERS
# ==================================================

def handle_holdem_panel_click(
        mouse_pos
):

    global holdem_active_tab
    global holdem_chat_unread

    if mouse_pos is None:
        return False

    outer_rect = HOLDEM_LOG_RECT

    log_tab_rect = pygame.Rect(
        outer_rect.x + 12,
        outer_rect.y + 10,
        100,
        28
    )

    chat_tab_rect = pygame.Rect(
        outer_rect.x + 118,
        outer_rect.y + 10,
        76,
        28
    )

    if log_tab_rect.collidepoint(
            mouse_pos
    ):

        holdem_active_tab = "log"

        return True

    if chat_tab_rect.collidepoint(
            mouse_pos
    ):

        holdem_active_tab = "chat"

        holdem_chat_unread = False

        return True

    return False

# ==================================================
# DRAW HOLDEM BUY-IN
# ==================================================

def draw_texas_holdem_buy_in(
        game_surface,
        mouse_pos,
        career_cash,
        draw_submenu_background,
        minimum_buy_in=100
):

    draw_submenu_background(
        overlay_alpha=125
    )

    holdem_fonts = (
        get_holdem_fonts()
    )

    title_font = (
        holdem_fonts["title"]
    )

    name_font = (
        holdem_fonts["name"]
    )

    small_font = (
        holdem_fonts["small"]
    )

    # ==================================================
    # Panel
    # ==================================================

    draw_translucent_panel(
        game_surface,
        holdem_buy_in_panel_rect,
        (
            10,
            18,
            18,
            245
        ),
        border_color=(
            185,
            190,
            195
        ),
        border_width=2,
        radius=16
    )

    # ==================================================
    # Title
    # ==================================================

    title_surface = (
        title_font.render(
            "TEXAS HOLD'EM BUY-IN",
            True,
            WHITE
        )
    )

    title_rect = (
        title_surface.get_rect(
            center=(
                holdem_buy_in_panel_rect.centerx,
                225
            )
        )
    )

    game_surface.blit(
        title_surface,
        title_rect
    )

    # ==================================================
    # Career cash
    # ==================================================

    cash_surface = (
        name_font.render(
            (
                f"Career Cash: "
                f"${career_cash:,}"
            ),
            True,
            (
                235,
                240,
                235
            )
        )
    )

    cash_rect = (
        cash_surface.get_rect(
            center=(
                holdem_buy_in_panel_rect.centerx,
                275
            )
        )
    )

    game_surface.blit(
        cash_surface,
        cash_rect
    )

    # ==================================================
    # Buy-in choices
    # ==================================================

    amounts = (
        get_holdem_buy_in_amounts(
            career_cash
        )
    )

    choices = (
        (
            holdem_buy_in_25_rect,
            "25%",
            amounts["25"]
        ),
        (
            holdem_buy_in_50_rect,
            "50%",
            amounts["50"]
        ),
        (
            holdem_buy_in_75_rect,
            "75%",
            amounts["75"]
        ),
        (
            holdem_buy_in_max_rect,
            "MAX",
            amounts["max"]
        ),
    )

    for (
            rect,
            label,
            amount
    ) in choices:

        enabled = (
            amount
            >= minimum_buy_in
        )

        hovered = (
            enabled
            and mouse_pos is not None
            and rect.collidepoint(
                mouse_pos
            )
        )

        if enabled:

            fill_color = (
                (
                    55,
                    105,
                    72,
                    245
                )
                if hovered
                else (
                    32,
                    72,
                    48,
                    245
                )
            )

            border_color = (
                (
                    230,
                    210,
                    110
                )
                if hovered
                else (
                    145,
                    165,
                    150
                )
            )

            text_color = WHITE

        else:

            fill_color = (
                45,
                45,
                48,
                225
            )

            border_color = (
                85,
                85,
                90
            )

            text_color = (
                140,
                140,
                145
            )

        draw_translucent_panel(
            game_surface,
            rect,
            fill_color,
            border_color=border_color,
            border_width=2,
            radius=12
        )

        label_surface = (
            name_font.render(
                label,
                True,
                text_color
            )
        )

        label_rect = (
            label_surface.get_rect(
                center=(
                    rect.centerx,
                    rect.y + 31
                )
            )
        )

        game_surface.blit(
            label_surface,
            label_rect
        )

        amount_surface = (
            small_font.render(
                f"${amount:,}",
                True,
                text_color
            )
        )

        amount_rect = (
            amount_surface.get_rect(
                center=(
                    rect.centerx,
                    rect.y + 69
                )
            )
        )

        game_surface.blit(
            amount_surface,
            amount_rect
        )

    # ==================================================
    # Explanation
    # ==================================================

    info_surface = (
        small_font.render(
            (
                "Unused cash stays in your "
                "Career wallet. Opponents "
                "begin with the same stack."
            ),
            True,
            (
                190,
                195,
                195
            )
        )
    )

    info_rect = (
        info_surface.get_rect(
            center=(
                holdem_buy_in_panel_rect.centerx,
                466
            )
        )
    )

    game_surface.blit(
        info_surface,
        info_rect
    )

    # ==================================================
    # Insufficient cash warning
    # ==================================================

    if career_cash < minimum_buy_in:

        warning_surface = (
            small_font.render(
                (
                    f"At least "
                    f"${minimum_buy_in:,} "
                    f"is required to play."
                ),
                True,
                (
                    235,
                    135,
                    135
                )
            )
        )

        warning_rect = (
            warning_surface.get_rect(
                center=(
                    holdem_buy_in_panel_rect.centerx,
                    495
                )
            )
        )

        game_surface.blit(
            warning_surface,
            warning_rect
        )

    # ==================================================
    # Back
    # ==================================================

    draw_modern_button(
        game_surface,
        holdem_buy_in_back_rect,
        "BACK",
        mouse_pos,
        small_font,
        enabled=True
    )

# ==================================================
# CHIP MOVEMENT ANIMATION
# ==================================================

def sync_holdem_chip_fx_context(
        holdem_game
):

    global _holdem_chip_fx_hand_number
    global _holdem_chip_fx_stage

    global _holdem_chip_fx_signatures
    global _holdem_chip_fx_started_at
    global _holdem_chip_fx_indexes

    global _holdem_wager_sweep_key
    global _holdem_wager_sweep_started_at

    hand_number = getattr(
        holdem_game,
        "hand_number",
        0
    )

    stage = (
        holdem_game.current_stage
    )

    # ==================================================
    # New hand or new betting street
    # ==================================================

    if (
            hand_number
            != _holdem_chip_fx_hand_number
            or stage
            != _holdem_chip_fx_stage
    ):

        _holdem_chip_fx_hand_number = (
            hand_number
        )

        _holdem_chip_fx_stage = (
            stage
        )

        _holdem_chip_fx_signatures = {}
        _holdem_chip_fx_started_at = {}
        _holdem_chip_fx_indexes = {}

        _holdem_wager_sweep_key = None
        _holdem_wager_sweep_started_at = 0

def get_holdem_chip_fx(
        animation_key,
        chunks
):

    global _holdem_chip_fx_signatures
    global _holdem_chip_fx_started_at
    global _holdem_chip_fx_indexes

    if animation_key is None:
        return None, 1.0

    signature = tuple(
        int(amount)
        for amount in chunks
    )

    previous_signature = (
        _holdem_chip_fx_signatures.get(
            animation_key
        )
    )

    now = pygame.time.get_ticks()

    # ==================================================
    # First contribution for this seat
    # ==================================================

    if previous_signature is None:

        _holdem_chip_fx_signatures[
            animation_key
        ] = signature

        if signature:

            _holdem_chip_fx_indexes[
                animation_key
            ] = (
                len(signature) - 1
            )

            _holdem_chip_fx_started_at[
                animation_key
            ] = now

    # ==================================================
    # New wager contribution appeared
    # ==================================================

    elif signature != previous_signature:

        old_length = len(
            previous_signature
        )

        new_length = len(
            signature
        )

        _holdem_chip_fx_signatures[
            animation_key
        ] = signature

        if new_length > old_length:

            _holdem_chip_fx_indexes[
                animation_key
            ] = (
                new_length - 1
            )

            _holdem_chip_fx_started_at[
                animation_key
            ] = now

        else:

            _holdem_chip_fx_indexes.pop(
                animation_key,
                None
            )

            _holdem_chip_fx_started_at.pop(
                animation_key,
                None
            )

    animated_index = (
        _holdem_chip_fx_indexes.get(
            animation_key
        )
    )

    started_at = (
        _holdem_chip_fx_started_at.get(
            animation_key
        )
    )

    if (
            animated_index is None
            or started_at is None
    ):

        return None, 1.0

    progress = (
        (now - started_at)
        / HOLDEM_CHIP_FX_DURATION
    )

    progress = max(
        0.0,
        min(
            progress,
            1.0
        )
    )

    return (
        animated_index,
        progress
    )


def get_holdem_chip_ease(
        progress
):

    progress = max(
        0.0,
        min(
            progress,
            1.0
        )
    )

    return (
        1.0
        - pow(
            1.0 - progress,
            3
        )
    )

def get_holdem_wager_sweep_progress(
        holdem_game
):

    global _holdem_wager_sweep_key
    global _holdem_wager_sweep_started_at

    # ==================================================
    # Only betting streets can sweep
    # ==================================================

    if holdem_game.current_stage not in (
            "preflop",
            "flop",
            "turn",
            "river",
    ):
        return 0.0

    # ==================================================
    # There must actually be chips on the felt
    # ==================================================

    has_player_chips = bool(
        holdem_game.player_bet_chunks
    )

    has_npc_chips = any(
        bool(chunks)
        for chunks
        in holdem_game.npc_bet_chunks
    )

    if not (
            has_player_chips
            or has_npc_chips
    ):
        return 0.0

    # ==================================================
    # main.py sets current_actor to -1 once the
    # betting round is finished and the game is
    # waiting to deal the next street.
    #
    # This is our reliable animation trigger.
    # ==================================================

    if holdem_game.current_actor != -1:
        return 0.0

    hand_number = getattr(
        holdem_game,
        "hand_number",
        0
    )

    sweep_key = (
        hand_number,
        holdem_game.current_stage
    )

    now = pygame.time.get_ticks()

    # ==================================================
    # Start sweep once per street
    # ==================================================

    if (
            _holdem_wager_sweep_key
            != sweep_key
    ):

        _holdem_wager_sweep_key = (
            sweep_key
        )

        _holdem_wager_sweep_started_at = (
            now
        )

    elapsed = (
        now
        - _holdem_wager_sweep_started_at
    )

    # Brief pause after final wager lands.
    if elapsed < HOLDEM_WAGER_SWEEP_DELAY:
        return 0.0

    progress = (
        (
            elapsed
            - HOLDEM_WAGER_SWEEP_DELAY
        )
        / HOLDEM_WAGER_SWEEP_DURATION
    )

    progress = max(
        0.0,
        min(
            progress,
            1.0
        )
    )

    return get_holdem_chip_ease(
        progress
    )

def draw_holdem_chip_chunks(
        game_surface,
        chunks,
        center_x,
        y,
        chip_images,
        base_unit=50,
        origin=None,
        animation_key=None,
        sweep_target=None,
        sweep_progress=0.0
):

    if not chunks:
        return

    # Once they fully reach the pot, hide them.
    if (
            sweep_target is not None
            and sweep_progress >= 1.0
    ):
        return

    holdem_fonts = (
        get_holdem_fonts()
    )

    amount_font = (
        holdem_fonts["tiny"]
    )

    # ==================================================
    # Incoming wager animation
    # ==================================================

    animated_index, progress = (
        get_holdem_chip_fx(
            animation_key,
            chunks
        )
    )

    eased_progress = (
        get_holdem_chip_ease(
            progress
        )
    )

    # ==================================================
    # Chip layout
    # ==================================================

    chip_size = 22
    stack_spacing = 13

    total_width = (
        (len(chunks) - 1)
        * stack_spacing
    )

    start_x = (
        center_x
        - total_width // 2
    )

    # ==================================================
    # Draw each contribution
    # ==================================================

    for chunk_index, amount in enumerate(
            chunks
    ):

        if amount <= 0:
            continue

        # ------------------------------------------
        # Chip color
        # ------------------------------------------

        if amount >= base_unit * 20:
            chip_key = "black"

        elif amount >= base_unit * 10:
            chip_key = "yellow"

        elif amount >= base_unit * 5:
            chip_key = "green"

        elif amount >= base_unit * 2:
            chip_key = "blue"

        else:
            chip_key = "red"

        chip_image = (
            chip_images.get(
                chip_key
            )
        )

        if chip_image is None:
            continue

        # ==================================================
        # Normal wager position
        # ==================================================

        target_x = (
            start_x
            + chunk_index
            * stack_spacing
        )

        target_y = y

        draw_x = target_x
        draw_y = target_y
        draw_size = chip_size

        # ==================================================
        # Newly-added wager slides from seat
        # ==================================================

        if (
                chunk_index
                == animated_index
                and progress < 1.0
                and origin is not None
                and sweep_progress <= 0.0
        ):

            origin_x, origin_y = (
                origin
            )

            draw_x = int(
                origin_x
                + (
                    target_x
                    - origin_x
                )
                * eased_progress
            )

            draw_y = int(
                origin_y
                + (
                    target_y
                    - origin_y
                )
                * eased_progress
            )

            arc = (
                math.sin(
                    progress
                    * math.pi
                )
                * 18
            )

            draw_y -= int(
                arc
            )

            scale = (
                0.78
                + 0.22
                * eased_progress
            )

            draw_size = max(
                10,
                int(
                    chip_size
                    * scale
                )
            )

        # ==================================================
        # Completed wagers sweep toward pot
        # ==================================================

        if (
                sweep_target is not None
                and sweep_progress > 0.0
        ):

            pot_x, pot_y = (
                sweep_target
            )

            draw_x = int(
                target_x
                + (
                    pot_x
                    - target_x
                )
                * sweep_progress
            )

            draw_y = int(
                target_y
                + (
                    pot_y
                    - target_y
                )
                * sweep_progress
            )

            # Slight arc inward
            sweep_arc = (
                math.sin(
                    sweep_progress
                    * math.pi
                )
                * 12
            )

            draw_y -= int(
                sweep_arc
            )

            # Chips shrink a little as they merge
            # into the center pile.
            draw_size = max(
                13,
                int(
                    chip_size
                    * (
                        1.0
                        - 0.30
                        * sweep_progress
                    )
                )
            )

        # ==================================================
        # Draw chip
        # ==================================================

        scaled_chip = (
            pygame.transform.smoothscale(
                chip_image,
                (
                    draw_size,
                    draw_size
                )
            )
        )

        chip_rect = (
            scaled_chip.get_rect(
                center=(
                    draw_x,
                    draw_y
                )
            )
        )

        game_surface.blit(
            scaled_chip,
            chip_rect
        )

    # ==================================================
    # Contribution amount
    #
    # Fade it away while chips move into the pot.
    # ==================================================

    total_amount = sum(
        chunks
    )

    total_surface = (
        amount_font.render(
            f"${total_amount:,}",
            True,
            WHITE
        )
    )

    if sweep_progress > 0.0:

        total_surface.set_alpha(
            max(
                0,
                int(
                    255
                    * (
                        1.0
                        - sweep_progress
                    )
                )
            )
        )

    total_rect = (
        total_surface.get_rect(
            center=(
                center_x,
                y + 27
            )
        )
    )

    game_surface.blit(
        total_surface,
        total_rect
    )

def set_holdem_bet_slider_from_mouse(
        mouse_pos
):

    global holdem_bet_fraction
    global holdem_manual_bet_text
    global holdem_manual_bet_active

    if mouse_pos is None:
        return False

    mouse_x = max(
        holdem_slider_rect.left,
        min(
            mouse_pos[0],
            holdem_slider_rect.right
        )
    )

    relative_x = (
        mouse_x
        - holdem_slider_rect.left
    )

    holdem_bet_fraction = (
        relative_x
        / max(
            1,
            holdem_slider_rect.width
        )
    )

    holdem_bet_fraction = max(
        0.0,
        min(
            holdem_bet_fraction,
            1.0
        )
    )

    holdem_manual_bet_text = ""
    holdem_manual_bet_active = False

    return True


def drag_holdem_bet_slider(
        mouse_pos
):

    if not holdem_bet_slider_dragging:
        return False

    return (
        set_holdem_bet_slider_from_mouse(
            mouse_pos
        )
    )


def stop_holdem_bet_slider_drag():

    global holdem_bet_slider_dragging

    was_dragging = (
        holdem_bet_slider_dragging
    )

    holdem_bet_slider_dragging = False

    return was_dragging

def update_holdem_bet_slider(
        mouse_pos,
        holdem_game
):

    global holdem_bet_fraction
    global holdem_bet_slider_dragging
    global holdem_manual_bet_text
    global holdem_manual_bet_active

    if mouse_pos is None:
        return False

    # ==================================================
    # Is wager adjustment currently meaningful?
    # ==================================================

    if (
            holdem_game.hand_complete
            or holdem_game.player_folded
            or holdem_game.player_all_in
            or holdem_game.player_stack <= 0
    ):
        return False

    # If facing an existing bet, only allow the
    # slider when raising is actually legal.
    if (
            holdem_game.current_bet > 0
            and not holdem_game.can_player_raise()
    ):
        return False

    # ==================================================
    # Slider
    #
    # Use a taller hitbox than the visual track so
    # grabbing the knob feels forgiving.
    # ==================================================

    slider_hit_rect = (
        holdem_slider_rect.inflate(
            0,
            24
        )
    )

    if slider_hit_rect.collidepoint(
            mouse_pos
    ):

        holdem_bet_slider_dragging = True

        set_holdem_bet_slider_from_mouse(
            mouse_pos
        )

        return True

    # ==================================================
    # Shortcut buttons
    # ==================================================

    if holdem_min_rect.collidepoint(
            mouse_pos
    ):

        holdem_bet_fraction = 0.0
        holdem_manual_bet_text = ""
        holdem_manual_bet_active = False

        return True

    if holdem_half_rect.collidepoint(
            mouse_pos
    ):

        holdem_bet_fraction = 0.5
        holdem_manual_bet_text = ""
        holdem_manual_bet_active = False

        return True

    if holdem_pot_rect.collidepoint(
            mouse_pos
    ):

        if holdem_game.player_stack <= 0:
            return False

        pot_target = min(
            holdem_game.pot,
            holdem_game.player_stack
        )

        holdem_bet_fraction = (
            pot_target
            / holdem_game.player_stack
        )

        holdem_bet_fraction = max(
            0.0,
            min(
                holdem_bet_fraction,
                1.0
            )
        )

        holdem_manual_bet_text = ""
        holdem_manual_bet_active = False

        return True

    if holdem_max_rect.collidepoint(
            mouse_pos
    ):

        holdem_bet_fraction = 1.0
        holdem_manual_bet_text = ""
        holdem_manual_bet_active = False

        return True

    return False

def clear_holdem_manual_bet():

    global holdem_manual_bet_text
    global holdem_manual_bet_active

    holdem_manual_bet_text = ""
    holdem_manual_bet_active = False


def handle_holdem_manual_bet_click(
        mouse_pos,
        holdem_game
):

    global holdem_manual_bet_active

    if mouse_pos is None:
        return False

    can_edit = (
        not holdem_game.hand_complete
        and holdem_game.can_player_act_now()
        and (
            holdem_game.current_bet == 0
            or holdem_game.can_player_raise()
        )
    )

    if can_edit and holdem_manual_bet_rect.collidepoint(mouse_pos):
        holdem_manual_bet_active = True
        return True

    if holdem_manual_bet_active:
        holdem_manual_bet_active = False

    return False


def handle_holdem_manual_bet_key(
        event,
        holdem_game
):

    global holdem_manual_bet_text
    global holdem_manual_bet_active

    if not holdem_manual_bet_active:
        return False

    if event.type != pygame.KEYDOWN:
        return False

    if event.key == pygame.K_ESCAPE:
        holdem_manual_bet_active = False
        return True

    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        holdem_manual_bet_active = False
        return True

    if event.key == pygame.K_BACKSPACE:
        holdem_manual_bet_text = holdem_manual_bet_text[:-1]
        return True

    character = getattr(event, "unicode", "")

    if character.isdigit() and len(holdem_manual_bet_text) < 9:
        holdem_manual_bet_text += character

    return True


def get_holdem_manual_bet_amount(holdem_game):

    if not holdem_manual_bet_text:
        return None

    try:
        requested = int(holdem_manual_bet_text)
    except ValueError:
        return None

    if requested <= 0 or holdem_game.player_stack <= 0:
        return None

    if holdem_game.current_bet == 0:
        minimum = holdem_game.get_minimum_open_bet()
        maximum = holdem_game.player_stack

        if maximum <= minimum:
            return maximum

        return max(minimum, min(requested, maximum))

    minimum = holdem_game.get_minimum_raise_to()
    maximum = holdem_game.get_player_maximum_raise_to()

    if maximum <= minimum:
        return maximum

    return max(minimum, min(requested, maximum))


def get_holdem_bet_amount(
        holdem_game
):

    global holdem_bet_fraction

    available_stack = (
        holdem_game.player_stack
    )

    if available_stack <= 0:
        return 0

    manual_amount = get_holdem_manual_bet_amount(
        holdem_game
    )

    if manual_amount is not None:
        return manual_amount

    # ==================================================
    # Opening bet
    # ==================================================

    if holdem_game.current_bet == 0:

        minimum = (
            holdem_game.get_minimum_open_bet()
        )

        maximum = (
            available_stack
        )

        if maximum <= minimum:
            return maximum

        amount = int(
            minimum
            + (
                maximum
                - minimum
            )
            * holdem_bet_fraction
        )

        return max(
            minimum,
            min(
                amount,
                maximum
            )
        )

    # ==================================================
    # Raise TO amount
    # ==================================================

    minimum_raise_to = (
        holdem_game.get_minimum_raise_to()
    )

    maximum_raise_to = (
        holdem_game
        .get_player_maximum_raise_to()
    )

    if (
            maximum_raise_to
            <= minimum_raise_to
    ):

        return maximum_raise_to

    amount = int(
        minimum_raise_to
        + (
            maximum_raise_to
            - minimum_raise_to
        )
        * holdem_bet_fraction
    )

    return max(
        minimum_raise_to,
        min(
            amount,
            maximum_raise_to
        )
    )

def scroll_holdem_log(
        wheel_y,
        total_lines
):

    global holdem_log_scroll
    global holdem_chat_scroll

    visible_line_count = 3

    # ==================================================
    # CHAT
    # ==================================================

    if holdem_active_tab == "chat":

        total_chat_lines = (
            len(
                holdem_chat_history
            )
        )

        max_scroll = max(
            0,
            total_chat_lines
            - visible_line_count
        )

        holdem_chat_scroll += (
            wheel_y
        )

        holdem_chat_scroll = max(
            0,
            min(
                holdem_chat_scroll,
                max_scroll
            )
        )

        return

    # ==================================================
    # GAME LOG
    # ==================================================

    max_scroll = max(
        0,
        total_lines
        - visible_line_count
    )

    holdem_log_scroll += (
        wheel_y
    )

    holdem_log_scroll = max(
        0,
        min(
            holdem_log_scroll,
            max_scroll
        )
    )

def add_holdem_chat_message(
        speaker,
        message
):

    global holdem_chat_scroll
    global holdem_chat_unread

    if not message:
        return

    if not holdem_table_chat_enabled:
        return

    if speaker and is_poker_chat_popups_enabled():
        _holdem_speech_overlay.post(
            speaker,
            message
        )

    if speaker:

        text = (
            f"{speaker}: {message}"
        )

    else:

        text = message

    holdem_chat_history.append(
        text
    )

    # Keep history from growing forever
    if len(
            holdem_chat_history
    ) > 100:

        del holdem_chat_history[
            :-100
        ]

    # New messages return view to newest
    holdem_chat_scroll = 0

    # If player is not currently looking at chat,
    # light up the Chat tab.
    if holdem_active_tab != "chat":

        holdem_chat_unread = True

def update_holdem_log(
        holdem_game
):

    global _holdem_last_stage
    global _holdem_last_result
    global holdem_log_scroll

    # ==================================================
    # Engine-owned hand history
    #
    # TexasHoldemGame now records the actual sequence of
    # blinds, actions, streets, showdown hands, side pots,
    # payouts, and eliminations. The UI simply mirrors it.
    # ==================================================

    get_history = getattr(
        holdem_game,
        "get_hand_history_lines",
        None
    )

    if callable(get_history):

        engine_lines = get_history()

        if engine_lines != holdem_log_history:

            holdem_log_history[:] = (
                engine_lines
            )

            # New information always returns the log view
            # to the most recent action.
            holdem_log_scroll = 0

        return

    # ==================================================
    # Compatibility fallback
    #
    # This remains only so an older poker engine can still
    # be displayed without crashing.
    # ==================================================

    stage = holdem_game.current_stage

    if stage != _holdem_last_stage:

        stage_messages = {
            "ready":
                "Waiting for next hand.",

            "preflop":
                "Hole cards dealt.",

            "showdown":
                "Showdown.",
        }

        message = stage_messages.get(
            stage
        )

        if message:
            holdem_log_history.append(
                message
            )

        _holdem_last_stage = stage
        holdem_log_scroll = 0

    result_text = getattr(
        holdem_game,
        "result_text",
        ""
    )

    if (
            result_text
            and result_text
            != _holdem_last_result
    ):

        holdem_log_history.append(
            result_text
        )

        _holdem_last_result = (
            result_text
        )

        holdem_log_scroll = 0

def draw_translucent_panel(
        surface,
        rect,
        fill_color,
        border_color=(185, 185, 190),
        border_width=2,
        radius=12
):

    panel = pygame.Surface(
        (
            rect.width,
            rect.height
        ),
        pygame.SRCALPHA
    )

    pygame.draw.rect(
        panel,
        fill_color,
        panel.get_rect(),
        border_radius=radius
    )

    surface.blit(
        panel,
        rect.topleft
    )

    if border_width > 0:

        pygame.draw.rect(
            surface,
            border_color,
            rect,
            border_width,
            border_radius=radius
        )

def draw_modern_button(
        surface,
        rect,
        text,
        mouse_pos,
        font,
        enabled=True,
        accent_color=None
):

    hovered = (
        mouse_pos is not None
        and rect.collidepoint(mouse_pos)
    )

    if not enabled:

        fill_color = (
            65,
            65,
            70
        )

        border_color = (
            100,
            100,
            105
        )

        text_color = (
            155,
            155,
            160
        )

    else:

        if accent_color is not None:

            fill_color = (
                accent_color
                if not hovered
                else (
                    min(255, accent_color[0] + 18),
                    min(255, accent_color[1] + 18),
                    min(255, accent_color[2] + 18),
                )
            )

            border_color = (
                235,
                165,
                165
            )

        elif hovered:

            fill_color = (
                70,
                76,
                84
            )

            border_color = (
                180,
                190,
                200
            )

        else:

            fill_color = (
                45,
                50,
                57
            )

            border_color = (
                120,
                125,
                135
            )

        text_color = WHITE

    draw_translucent_panel(
        surface,
        rect,
        (
            *fill_color,
            235
        ),
        border_color=border_color,
        border_width=2,
        radius=10
    )

    blit_text_fit(
        surface,
        text,
        font,
        text_color,
        rect,
        padding=8
    )

def blit_text_fit(
        surface,
        text,
        font,
        color,
        rect,
        padding=10
):
    text_surface = font.render(
        text,
        True,
        color
    )

    max_width = rect.width - padding * 2

    if text_surface.get_width() > max_width:
        scale = (
            max_width
            / text_surface.get_width()
        )

        new_width = max(
            1,
            int(
                text_surface.get_width()
                * scale
            )
        )

        new_height = max(
            1,
            int(
                text_surface.get_height()
                * scale
            )
        )

        text_surface = pygame.transform.smoothscale(
            text_surface,
            (
                new_width,
                new_height
            )
        )

    text_rect = text_surface.get_rect(
        center=rect.center
    )

    surface.blit(
        text_surface,
        text_rect
    )

def draw_holdem_log_panel(
        game_surface,
        detail_font,
        mouse_pos,
        active_tab="log",
        log_lines=None
):

    holdem_fonts = get_holdem_fonts()

    holdem_small_font = (
        holdem_fonts["small"]
    )

    if log_lines is None:
        log_lines = []

    outer_rect = HOLDEM_LOG_RECT

    draw_translucent_panel(
        game_surface,
        outer_rect,
        (
            8,
            16,
            18,
            205
        ),
        border_color=(
            185,
            185,
            190
        ),
        border_width=2,
        radius=12
    )

    # ==================================================
    # Tabs
    # ==================================================

    log_tab_rect = pygame.Rect(
        outer_rect.x + 12,
        outer_rect.y + 10,
        100,
        28
    )

    chat_tab_rect = pygame.Rect(
        outer_rect.x + 118,
        outer_rect.y + 10,
        76,
        28
    )

    draw_holdem_glossy_button(
        game_surface,
        log_tab_rect,
        "Game Log",
        mouse_pos,
        holdem_small_font,
        enabled=True,
        selected=(
            active_tab == "log"
        )
    )

    draw_holdem_glossy_button(
        game_surface,
        chat_tab_rect,
        "Chat",
        mouse_pos,
        holdem_small_font,
        enabled=True,
        selected=(
                active_tab == "chat"
        ),
        attention=(
                holdem_chat_unread
                and active_tab != "chat"
        )
    )

    # ==================================================
    # Inner text area
    # ==================================================

    inner_rect = pygame.Rect(
        outer_rect.x + 12,
        outer_rect.y + 48,
        outer_rect.width - 24,
        outer_rect.height - 58
    )

    draw_translucent_panel(
        game_surface,
        inner_rect,
        (
            0,
            0,
            0,
            150
        ),
        border_color=(
            90,
            95,
            100
        ),
        border_width=1,
        radius=8
    )

    # ==================================================
    # Visible log lines
    # ==================================================

    if active_tab == "log":

        visible_line_count = 3
        line_spacing = 23

        end_index = (
            len(log_lines)
            - holdem_log_scroll
        )

        end_index = max(
            0,
            min(
                end_index,
                len(log_lines)
            )
        )

        start_index = max(
            0,
            end_index
            - visible_line_count
        )

        visible_lines = log_lines[
            start_index:end_index
        ]


    else:

        visible_line_count = 4
        line_spacing = 18

        end_index = (

                len(holdem_chat_history)

                - holdem_chat_scroll

        )

        end_index = max(

            0,

            min(

                end_index,

                len(holdem_chat_history)

            )

        )

        start_index = max(

            0,

            end_index

            - visible_line_count

        )

        visible_lines = (

            holdem_chat_history[

                start_index:end_index

            ]

        )

        if not visible_lines:
            visible_lines = [

                "No table chat yet."

            ]

    # ==================================================
    # Draw lines
    # ==================================================

    text_y = (
        inner_rect.y + 9
    )

    for line in visible_lines:

        line_surface = (
            holdem_small_font.render(
                line,
                True,
                WHITE
            )
        )

        max_text_width = (
                inner_rect.width - 24
        )

        if (
                line_surface.get_width()
                > max_text_width
        ):
            scale = (
                    max_text_width
                    / line_surface.get_width()
            )

            new_width = max(
                1,
                int(
                    line_surface.get_width()
                    * scale
                )
            )

            new_height = max(
                1,
                int(
                    line_surface.get_height()
                    * scale
                )
            )

            line_surface = (
                pygame.transform.smoothscale(
                    line_surface,
                    (
                        new_width,
                        new_height
                    )
                )
            )

        line_rect = (
            line_surface.get_rect(
                midleft=(
                    inner_rect.x + 10,
                    text_y
                    + line_spacing // 2
                )
            )
        )

        game_surface.blit(
            line_surface,
            line_rect
        )

        text_y += line_spacing

    # ==================================================
    # Scroll indicator
    # ==================================================

    if (
            active_tab == "log"
            and len(log_lines) > 3
    ):

        track_rect = pygame.Rect(
            inner_rect.right - 7,
            inner_rect.y + 6,
            3,
            inner_rect.height - 12
        )

        pygame.draw.rect(
            game_surface,
            (
                70,
                75,
                80
            ),
            track_rect,
            border_radius=2
        )

        max_scroll = max(
            1,
            len(log_lines) - 3
        )

        thumb_height = max(
            12,
            int(
                track_rect.height
                * (
                    3
                    / len(log_lines)
                )
            )
        )

        available_travel = (
            track_rect.height
            - thumb_height
        )

        scroll_fraction = (
            holdem_log_scroll
            / max_scroll
        )

        # scroll=0 means newest, so thumb sits at bottom
        thumb_y = (
            track_rect.bottom
            - thumb_height
            - int(
                available_travel
                * scroll_fraction
            )
        )

        thumb_rect = pygame.Rect(
            track_rect.x,
            thumb_y,
            track_rect.width,
            thumb_height
        )

        pygame.draw.rect(
            game_surface,
            (
                190,
                195,
                200
            ),
            thumb_rect,
            border_radius=2
        )

    return {
        "log_tab": log_tab_rect,
        "chat_tab": chat_tab_rect,
    }

def get_holdem_player_hand_text(
        holdem_game
):

    # ==================================================
    # Rank helpers
    # ==================================================

    rank_values = {
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

    singular_names = {
        "A": "Ace",
        "K": "King",
        "Q": "Queen",
        "J": "Jack",
        "10": "Ten",
        "9": "Nine",
        "8": "Eight",
        "7": "Seven",
        "6": "Six",
        "5": "Five",
        "4": "Four",
        "3": "Three",
        "2": "Two",
    }

    plural_names = {
        "A": "Aces",
        "K": "Kings",
        "Q": "Queens",
        "J": "Jacks",
        "10": "Tens",
        "9": "Nines",
        "8": "Eights",
        "7": "Sevens",
        "6": "Sixes",
        "5": "Fives",
        "4": "Fours",
        "3": "Threes",
        "2": "Twos",
    }

    # ==================================================
    # PREFLOP
    # ==================================================

    if (
            holdem_game.current_stage
            == "preflop"
            and len(
                holdem_game.player_hand
            ) >= 2
    ):

        card_1 = (
            holdem_game.player_hand[0]
        )

        card_2 = (
            holdem_game.player_hand[1]
        )

        rank_1 = str(
            card_1["rank"]
        )

        rank_2 = str(
            card_2["rank"]
        )

        # ------------------------------------------
        # Pocket pair
        # ------------------------------------------

        if rank_1 == rank_2:

            return (
                f"A pair of "
                f"{plural_names.get(rank_1, rank_1)}"
            )

        # ------------------------------------------
        # High card
        # ------------------------------------------

        high_rank = max(
            (
                rank_1,
                rank_2
            ),
            key=lambda rank:
                rank_values.get(
                    rank,
                    0
                )
        )

        return (
            f"{singular_names.get(high_rank, high_rank)} "
            f"high"
        )

    # ==================================================
    # FLOP / TURN / RIVER / SHOWDOWN
    # ==================================================

    raw_text = ""

    if hasattr(
            holdem_game,
            "get_player_hand_name"
    ):

        raw_text = (
            holdem_game
            .get_player_hand_name()
            or ""
        )

    if not raw_text:
        return ""

    lowered = (
        str(raw_text)
        .strip()
        .lower()
    )

    all_cards = (
        holdem_game.player_hand
        + holdem_game.community_cards
    )

    # ==================================================
    # Pair
    # ==================================================

    if lowered in (
            "pair",
            "one pair",
    ):

        rank_counts = {}

        for card in all_cards:

            rank = str(
                card["rank"]
            )

            rank_counts[rank] = (
                rank_counts.get(
                    rank,
                    0
                )
                + 1
            )

        paired_ranks = [
            rank
            for rank, count
            in rank_counts.items()
            if count >= 2
        ]

        if paired_ranks:

            best_pair_rank = max(
                paired_ranks,
                key=lambda rank:
                    rank_values.get(
                        rank,
                        0
                    )
            )

            return (
                f"A pair of "
                f"{plural_names.get(
                    best_pair_rank,
                    best_pair_rank
                )}"
            )

        return "A pair"

    # ==================================================
    # Other hand names
    # ==================================================

    hand_names = {
        "high card":
            "High card",

        "two pair":
            "Two pair",

        "two pairs":
            "Two pair",

        "three of a kind":
            "Three of a kind",

        "straight":
            "A straight",

        "flush":
            "A flush",

        "full house":
            "A full house",

        "four of a kind":
            "Four of a kind",

        "straight flush":
            "A straight flush",

        "royal flush":
            "A royal flush",
    }

    return hand_names.get(
        lowered,
        str(raw_text)
    )

def draw_holdem_side_panel(
        surface,
        holdem_game,
        title_font,
        detail_font,
        mouse_pos,
        next_hand_seconds=None
):
    player_is_current_actor = (
            not holdem_game.hand_complete
            and holdem_game.current_actor == 0
            and not holdem_game.player_has_acted
    )

    holdem_fonts = get_holdem_fonts()

    holdem_small_font = (
        holdem_fonts["small"]
    )

    panel_rect = (
        holdem_action_panel_rect
    )

    draw_translucent_panel(
        surface,
        panel_rect,
        (
            8,
            18,
            18,
            220
        ),
        border_color=(
            200,
            200,
            205
        ),
        border_width=2,
        radius=14
    )

    # ==================================================
    # Hand complete / next-hand controls
    # ==================================================

    if holdem_game.hand_complete:

        # ==================================================
        # Player busted
        # ==================================================

        if holdem_game.player_busted:
            draw_modern_button(
                surface,
                holdem_next_hand_rect,
                "BUSTED",
                mouse_pos,
                holdem_small_font,
                enabled=False
            )

            return

        # ==================================================
        # Player cleared table
        # ==================================================

        if holdem_game.all_npcs_busted():
            draw_modern_button(
                surface,
                holdem_next_hand_rect,
                "TABLE CLEARED +100",
                mouse_pos,
                holdem_small_font,
                enabled=True,
                accent_color=(
                    105,
                    82,
                    32
                )
            )

            return

        # ==================================================
        # Normal completed hand
        # ==================================================

        draw_modern_button(
            surface,
            holdem_next_hand_rect,
            "NEXT HAND",
            mouse_pos,
            holdem_small_font,
            enabled=True
        )

        if next_hand_seconds is not None:
            countdown_text = (
                f"Auto-deal in "
                f"{next_hand_seconds}s"
            )

            countdown_surface = (
                holdem_small_font.render(
                    countdown_text,
                    True,
                    WHITE
                )
            )

            countdown_rect = (
                countdown_surface.get_rect(
                    center=(
                        holdem_action_panel_rect.centerx,
                        704
                    )
                )
            )

            surface.blit(
                countdown_surface,
                countdown_rect
            )

        return

    # ==================================================
    # Context-sensitive button labels
    # ==================================================

    amount_to_call = (
        holdem_game.get_player_amount_to_call()
    )

    bet_amount = (
        get_holdem_bet_amount(
            holdem_game
        )
    )

    if amount_to_call > 0:

        call_amount = min(
            amount_to_call,
            holdem_game.player_stack
        )

        call_text = (
            f"CALL ${call_amount:,}"
        )

    else:

        call_text = "CHECK"

    # ==================================================
    # Bet / Raise button label
    # ==================================================

    if holdem_game.current_bet > 0:

        maximum_action_amount = (
            holdem_game
            .get_player_maximum_raise_to()
        )

    else:

        maximum_action_amount = (
            holdem_game.player_stack
        )

    is_all_in_amount = (
            maximum_action_amount > 0
            and bet_amount
            >= maximum_action_amount
    )

    if is_all_in_amount:

        raise_text = "ALL IN"

    elif holdem_game.current_bet > 0:

        raise_text = (
            f"RAISE TO ${bet_amount:,}"
        )

    else:

        raise_text = (
            f"BET ${bet_amount:,}"
        )

    # ==================================================
    # Button enabled states
    # ==================================================

    player_can_act = (
        holdem_game.can_player_act_now()
    )

    fold_enabled = (
        player_can_act
    )

    call_enabled = (
        player_can_act
    )

    all_in_call = amount_to_call > 0 and amount_to_call >= holdem_game.player_stack
    if all_in_call:
        call_text = f"ALL-IN CALL ${holdem_game.player_stack:,}"
        raise_text = "ALL IN"
    raise_enabled = player_can_act and (holdem_game.can_player_raise() or all_in_call)

    call_accent = None

    if (
            player_is_current_actor
            and call_enabled
    ):
        pulse = (
                        pygame.time.get_ticks()
                        % 1600
                ) / 1600.0

        pulse_strength = (
                0.5
                + 0.5
                * abs(
            2.0 * pulse - 1.0
        )
        )

        call_accent = (
            int(150 + 70 * pulse_strength),
            int(115 + 65 * pulse_strength),
            int(25 + 35 * pulse_strength)
        )

    # ==================================================
    # Main action row
    # ==================================================

    draw_modern_button(
        surface,
        holdem_fold_rect,
        "FOLD",
        mouse_pos,
        holdem_small_font,
        enabled=fold_enabled,
        accent_color=(
            185,
            45,
            45
        )
    )

    draw_modern_button(
        surface,
        holdem_call_rect,
        call_text,
        mouse_pos,
        holdem_small_font,
        enabled=call_enabled,
        accent_color=call_accent
    )

    draw_modern_button(
        surface,
        holdem_raise_rect,
        raise_text,
        mouse_pos,
        holdem_small_font,
        enabled=raise_enabled,
        accent_color=(
            45,
            125,
            80
        )
    )

    # ==================================================
    # Raise slider
    # ==================================================

    pygame.draw.rect(
        surface,
        (
            70,
            75,
            85
        ),
        holdem_slider_rect,
        border_radius=7
    )

    knob_width = 18

    knob_x = int(
        holdem_slider_rect.x
        + (
                holdem_slider_rect.width
                - knob_width
        )
        * holdem_bet_fraction
    )

    knob_rect = pygame.Rect(
        knob_x,
        holdem_slider_rect.y - 3,
        knob_width,
        holdem_slider_rect.height + 6
    )

    if holdem_bet_slider_dragging:

        knob_color = (
            175,
            205,
            240
        )

        knob_border = (
            235,
            245,
            255
        )

    else:

        knob_color = (
            130,
            170,
            220
        )

        knob_border = (
            170,
            195,
            225
        )

    pygame.draw.rect(
        surface,
        knob_color,
        knob_rect,
        border_radius=6
    )

    pygame.draw.rect(
        surface,
        knob_border,
        knob_rect,
        2,
        border_radius=6
    )

    # ==================================================
    # Manual bet / raise-to entry
    # ==================================================

    manual_enabled = (
        player_can_act
        and (
            holdem_game.current_bet == 0
            or holdem_game.can_player_raise()
        )
    )

    manual_fill = (18, 24, 27, 235) if manual_enabled else (48, 48, 52, 220)
    manual_border = (235, 190, 70) if holdem_manual_bet_active else ((150, 175, 205) if holdem_manual_bet_text else (105, 110, 118))

    draw_translucent_panel(
        surface,
        holdem_manual_bet_rect,
        manual_fill,
        border_color=manual_border,
        border_width=2 if holdem_manual_bet_active else 1,
        radius=7
    )

    if holdem_manual_bet_text:
        manual_label = f"${holdem_manual_bet_text}"
        manual_color = WHITE if manual_enabled else (150, 150, 155)
    else:
        manual_label = (
            "BET $"
            if holdem_game.current_bet == 0
            else "RAISE $"
        )
        manual_color = (165, 170, 178) if manual_enabled else (120, 120, 125)

    manual_surface = holdem_small_font.render(
        manual_label,
        True,
        manual_color
    )

    surface.blit(
        manual_surface,
        manual_surface.get_rect(center=holdem_manual_bet_rect.center)
    )

    # ==================================================
    # Slider shortcuts
    # ==================================================

    draw_modern_button(
        surface,
        holdem_min_rect,
        "MIN",
        mouse_pos,
        holdem_small_font,
        enabled=True
    )

    draw_modern_button(
        surface,
        holdem_half_rect,
        "1/2",
        mouse_pos,
        holdem_small_font,
        enabled=True
    )

    draw_modern_button(
        surface,
        holdem_pot_rect,
        "POT",
        mouse_pos,
        holdem_small_font,
        enabled=True
    )

    draw_modern_button(
        surface,
        holdem_max_rect,
        "MAX",
        mouse_pos,
        holdem_small_font,
        enabled=True
    )

def draw_holdem_glossy_button(
        game_surface,
        rect,
        text,
        mouse_pos,
        font,
        enabled=True,
        selected=False,
        danger=False,
        attention=False
):

    hovered = (
        mouse_pos is not None
        and rect.collidepoint(mouse_pos)
    )

    if not enabled:
        base_color = (62, 62, 66)
        border_color = (110, 110, 116)
        text_color = (150, 150, 155)

    elif danger:
        base_color = (205, 48, 48) if hovered else (185, 42, 42)
        border_color = (255, 175, 175)
        text_color = WHITE


    elif selected:

        base_color = (72, 102, 132)

        border_color = (180, 220, 255)

        text_color = WHITE


    elif attention:

        # Soft pulsing notification glow.

        pulse = (
                        pygame.time.get_ticks()
                        % 1200
                ) / 1200.0

        pulse = (
                0.5
                + 0.5
                * math.sin(
            pulse
            * math.pi
            * 2
        )
        )

        base_color = (

            int(105 + 35 * pulse),

            int(82 + 28 * pulse),

            int(32 + 12 * pulse),

        )

        border_color = (

            255,

            int(195 + 45 * pulse),

            80,

        )

        text_color = WHITE

    elif hovered:
        base_color = (80, 88, 96)
        border_color = (185, 190, 195)
        text_color = WHITE

    else:
        base_color = (58, 62, 68)
        border_color = (145, 150, 155)
        text_color = (238, 238, 238)

    button_surface = pygame.Surface(
        (rect.width, rect.height),
        pygame.SRCALPHA
    )

    button_surface.fill((0, 0, 0, 0))

    pygame.draw.rect(
        button_surface,
        (*base_color, 215),
        button_surface.get_rect(),
        border_radius=12
    )

    gloss_rect = pygame.Rect(
        3,
        3,
        rect.width - 6,
        max(
            8,
            rect.height // 2 - 3
        )
    )

    pygame.draw.rect(
        button_surface,
        (255, 255, 255, 28),
        gloss_rect,
        border_radius=10
    )

    pygame.draw.rect(
        button_surface,
        border_color,
        button_surface.get_rect(),
        2,
        border_radius=12
    )

    game_surface.blit(
        button_surface,
        rect.topleft
    )

    text_surface = font.render(
        text,
        True,
        text_color
    )

    text_rect = text_surface.get_rect(
        center=rect.center
    )

    game_surface.blit(
        text_surface,
        text_rect
    )


# ==================================================
# DEALER / BLIND POSITION BADGES
# ==================================================

def get_holdem_position_labels(
        holdem_game,
        table_index
):

    labels = []

    if getattr(
            holdem_game,
            "dealer_index",
            None
    ) == table_index:
        labels.append("D")

    if getattr(
            holdem_game,
            "small_blind_index",
            None
    ) == table_index:
        labels.append("SB")

    if getattr(
            holdem_game,
            "big_blind_index",
            None
    ) == table_index:
        labels.append("BB")

    return labels


def draw_holdem_position_badges(
        game_surface,
        holdem_game,
        table_index,
        start_x,
        y
):

    labels = (
        get_holdem_position_labels(
            holdem_game,
            table_index
        )
    )

    if not labels:
        return

    holdem_fonts = get_holdem_fonts()
    font = holdem_fonts["tiny"]

    badge_styles = {
        "D": (
            (122, 92, 24, 245),
            (245, 205, 90)
        ),
        "SB": (
            (52, 72, 92, 245),
            (155, 190, 220)
        ),
        "BB": (
            (92, 48, 48, 245),
            (220, 145, 145)
        ),
    }

    x = int(start_x)

    for label in labels:

        width = (
            30
            if label == "D"
            else 36
        )

        rect = pygame.Rect(
            x,
            int(y),
            width,
            22
        )

        fill_color, border_color = (
            badge_styles[label]
        )

        draw_translucent_panel(
            game_surface,
            rect,
            fill_color,
            border_color=border_color,
            border_width=2,
            radius=8
        )

        text_surface = font.render(
            label,
            True,
            WHITE
        )

        text_rect = text_surface.get_rect(
            center=rect.center
        )

        game_surface.blit(
            text_surface,
            text_rect
        )

        x += width + 5


def draw_holdem_player_hud(
        game_surface,
        player_name,
        player_stack,
        panel_center_x,
        panel_y,
        label_font,
        detail_font,
        panel_width=270,
        panel_height=78,
        is_current_actor=False,
        is_winner=False
):

    # ==================================================
    # Dedicated poker fonts
    # ==================================================

    holdem_fonts = get_holdem_fonts()

    name_font = holdem_fonts["title"]
    stack_font = holdem_fonts["small"]

    # ==================================================
    # Main HUD rectangle
    # ==================================================

    panel_rect = pygame.Rect(
        panel_center_x - panel_width // 2,
        panel_y,
        panel_width,
        panel_height
    )

    draw_translucent_panel(
        game_surface,
        panel_rect,
        (
            18,
            20,
            24,
            255
        ),
        border_color=(
            (235, 190, 70)
            if (is_current_actor or is_winner)
            else (185, 185, 190)
        ),
        border_width=(
            4
            if is_winner
            else (
                3
                if is_current_actor
                else 2
            )
        ),
        radius=12
    )

    # ==================================================
    # Player name
    # ==================================================

    name_text = player_name

    name_surface = name_font.render(
        name_text,
        True,
        (255, 255, 255)
    )

    name_rect = name_surface.get_rect(
        center=(
            panel_rect.centerx,
            panel_rect.y + 24
        )
    )

    # 1px black outline
    for offset_x, offset_y in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1),
    ):
        outline_surface = name_font.render(
            name_text,
            True,
            (0, 0, 0)
        )

        game_surface.blit(
            outline_surface,
            (
                name_rect.x + offset_x,
                name_rect.y + offset_y
            )
        )

    game_surface.blit(
        name_surface,
        name_rect
    )

    # ==================================================
    # Money box
    # ==================================================

    money_rect = pygame.Rect(
        panel_rect.centerx - 60,
        panel_rect.y + 43,
        120,
        24
    )

    draw_translucent_panel(
        game_surface,
        money_rect,
        (
            10,
            12,
            14,
            255
        ),
        border_color=(
            120,
            120,
            125
        ),
        border_width=1,
        radius=10
    )

    # ==================================================
    # Money text
    # ==================================================

    stack_text = (
        f"${player_stack:,}"
    )

    stack_surface = stack_font.render(
        stack_text,
        True,
        (
            240,
            255,
            235
        )
    )

    stack_rect = stack_surface.get_rect(
        center=money_rect.center
    )

    # Small shadow
    stack_shadow = stack_font.render(
        stack_text,
        True,
        (
            0,
            0,
            0
        )
    )

    game_surface.blit(
        stack_shadow,
        (
            stack_rect.x + 1,
            stack_rect.y + 1
        )
    )

    game_surface.blit(
        stack_surface,
        stack_rect
    )

def get_card_key(
        card
):

    if card is None:
        return None

    rank = card["rank"]
    suit = card["suit"]

    suit_letter_map = {
        "Clubs": "C",
        "Diamonds": "D",
        "Hearts": "H",
        "Spades": "S",
    }

    return (
        f"{rank}"
        f"{suit_letter_map[suit]}"
    )


def draw_card_face(
        game_surface,
        card,
        x,
        y,
        card_fronts,
        width=72,
        height=101
):

    card_key = (
        get_card_key(
            card
        )
    )

    if (
            card_key is None
            or card_key not in card_fronts
    ):
        return

    card_image = (
        pygame.transform.smoothscale(
            card_fronts[
                card_key
            ],
            (
                width,
                height
            )
        )
    )

    game_surface.blit(
        card_image,
        (
            x,
            y
        )
    )


def draw_card_back(
        game_surface,
        card_back,
        x,
        y,
        width=72,
        height=101
):

    back_image = (
        pygame.transform.smoothscale(
            card_back,
            (
                width,
                height
            )
        )
    )

    game_surface.blit(
        back_image,
        (
            x,
            y
        )
    )

# ==================================================
# TEXAS HOLD'EM CARD ANIMATION HELPERS
# ==================================================

def sync_holdem_card_fx(
        holdem_game
):

    global _holdem_card_fx_hand_number
    global _holdem_card_fx_stage

    global _holdem_card_fx_kind
    global _holdem_card_fx_started_at

    now = pygame.time.get_ticks()

    hand_number = getattr(
        holdem_game,
        "hand_number",
        0
    )

    stage = (
        holdem_game.current_stage
    )

    # ==================================================
    # New hand
    # ==================================================

    if (
            hand_number
            != _holdem_card_fx_hand_number
    ):

        _holdem_card_fx_hand_number = (
            hand_number
        )

        _holdem_card_fx_stage = (
            stage
        )

        _holdem_card_fx_kind = (
            "deal"
        )

        _holdem_card_fx_started_at = (
            now
        )

    # ==================================================
    # New street
    # ==================================================

    elif stage != _holdem_card_fx_stage:

        _holdem_card_fx_stage = (
            stage
        )

        if stage in (
                "flop",
                "turn",
                "river",
                "showdown",
        ):

            _holdem_card_fx_kind = (
                stage
            )

            _holdem_card_fx_started_at = (
                now
            )

    elapsed = max(
        0,
        now
        - _holdem_card_fx_started_at
    )

    return (
        _holdem_card_fx_kind,
        elapsed
    )


def get_holdem_card_fx_progress(
        elapsed,
        delay=0,
        duration=180
):

    if elapsed <= delay:
        return 0.0

    progress = (
        (elapsed - delay)
        / max(
            1,
            duration
        )
    )

    return max(
        0.0,
        min(
            progress,
            1.0
        )
    )


def get_holdem_eased_progress(
        progress
):

    progress = max(
        0.0,
        min(
            progress,
            1.0
        )
    )

    # Ease-out cubic
    return (
        1.0
        - pow(
            1.0 - progress,
            3
        )
    )


def draw_holdem_popping_card_face(
        game_surface,
        card,
        x,
        y,
        card_fronts,
        width,
        height,
        progress
):

    if progress <= 0:
        return

    if progress >= 1:

        draw_card_face(
            game_surface,
            card,
            x,
            y,
            card_fronts,
            width=width,
            height=height
        )

        return

    eased = (
        get_holdem_eased_progress(
            progress
        )
    )

    scale = (
        0.58
        + 0.42
        * eased
    )

    temp_surface = pygame.Surface(
        (
            width,
            height
        ),
        pygame.SRCALPHA
    )

    draw_card_face(
        temp_surface,
        card,
        0,
        0,
        card_fronts,
        width=width,
        height=height
    )

    scaled_width = max(
        2,
        int(
            width
            * scale
        )
    )

    scaled_height = max(
        2,
        int(
            height
            * scale
        )
    )

    scaled_surface = (
        pygame.transform.smoothscale(
            temp_surface,
            (
                scaled_width,
                scaled_height
            )
        )
    )

    scaled_surface.set_alpha(
        int(
            255
            * progress
        )
    )

    target_rect = (
        scaled_surface.get_rect(
            center=(
                x + width // 2,
                y + height // 2
            )
        )
    )

    game_surface.blit(
        scaled_surface,
        target_rect
    )


def draw_holdem_popping_card_back(
        game_surface,
        card_back,
        x,
        y,
        width,
        height,
        progress
):

    if progress <= 0:
        return

    if progress >= 1:

        draw_card_back(
            game_surface,
            card_back,
            x,
            y,
            width=width,
            height=height
        )

        return

    eased = (
        get_holdem_eased_progress(
            progress
        )
    )

    scale = (
        0.58
        + 0.42
        * eased
    )

    temp_surface = pygame.Surface(
        (
            width,
            height
        ),
        pygame.SRCALPHA
    )

    draw_card_back(
        temp_surface,
        card_back,
        0,
        0,
        width=width,
        height=height
    )

    scaled_width = max(
        2,
        int(
            width
            * scale
        )
    )

    scaled_height = max(
        2,
        int(
            height
            * scale
        )
    )

    scaled_surface = (
        pygame.transform.smoothscale(
            temp_surface,
            (
                scaled_width,
                scaled_height
            )
        )
    )

    scaled_surface.set_alpha(
        int(
            255
            * progress
        )
    )

    target_rect = (
        scaled_surface.get_rect(
            center=(
                x + width // 2,
                y + height // 2
            )
        )
    )

    game_surface.blit(
        scaled_surface,
        target_rect
    )


def draw_holdem_flipping_card(
        game_surface,
        card,
        card_back,
        x,
        y,
        card_fronts,
        width,
        height,
        progress
):

    progress = max(
        0.0,
        min(
            progress,
            1.0
        )
    )

    # ==================================================
    # First half: card back narrows
    # ==================================================

    if progress < 0.5:

        phase = (
            progress
            / 0.5
        )

        width_scale = (
            1.0
            - phase
        )

        temp_surface = pygame.Surface(
            (
                width,
                height
            ),
            pygame.SRCALPHA
        )

        draw_card_back(
            temp_surface,
            card_back,
            0,
            0,
            width=width,
            height=height
        )

    # ==================================================
    # Second half: face expands
    # ==================================================

    else:

        phase = (
            (progress - 0.5)
            / 0.5
        )

        width_scale = (
            phase
        )

        temp_surface = pygame.Surface(
            (
                width,
                height
            ),
            pygame.SRCALPHA
        )

        draw_card_face(
            temp_surface,
            card,
            0,
            0,
            card_fronts,
            width=width,
            height=height
        )

    scaled_width = max(
        2,
        int(
            width
            * width_scale
        )
    )

    scaled_surface = (
        pygame.transform.smoothscale(
            temp_surface,
            (
                scaled_width,
                height
            )
        )
    )

    target_rect = (
        scaled_surface.get_rect(
            center=(
                x + width // 2,
                y + height // 2
            )
        )
    )

    game_surface.blit(
        scaled_surface,
        target_rect
    )

# ==================================================
# DRAW HOLDEM OPTIONS OVERLAY
# ==================================================

def draw_holdem_options_overlay(
        surface,
        mouse_pos
):

    if not holdem_options_open:
        return

    holdem_fonts = (
        get_holdem_fonts()
    )

    title_font = (
        holdem_fonts["title"]
    )

    name_font = (
        holdem_fonts["name"]
    )

    small_font = (
        holdem_fonts["small"]
    )

    # ==================================================
    # Dim table behind overlay
    # ==================================================

    dim_surface = pygame.Surface(
        surface.get_size(),
        pygame.SRCALPHA
    )

    dim_surface.fill(
        (
            0,
            0,
            0,
            125
        )
    )

    surface.blit(
        dim_surface,
        (0, 0)
    )

    # ==================================================
    # Main panel
    # ==================================================

    draw_translucent_panel(
        surface,
        holdem_options_panel_rect,
        (
            12,
            18,
            20,
            248
        ),
        border_color=(
            175,
            180,
            190
        ),
        border_width=2,
        radius=16
    )

    # ==================================================
    # Title
    # ==================================================

    title_surface = (
        title_font.render(
            "POKER OPTIONS",
            True,
            WHITE
        )
    )

    title_rect = (
        title_surface.get_rect(
            center=(
                holdem_options_panel_rect.centerx,
                247
            )
        )
    )

    surface.blit(
        title_surface,
        title_rect
    )

    # ==================================================
    # Close
    # ==================================================

    draw_modern_button(
        surface,
        holdem_options_close_rect,
        "X",
        mouse_pos,
        small_font,
        enabled=True
    )

    # ==================================================
    # TABLE SPEED
    # ==================================================

    speed_label = (
        name_font.render(
            "Table Speed",
            True,
            WHITE
        )
    )

    surface.blit(
        speed_label,
        (
            515,
            287
        )
    )

    draw_modern_button(
        surface,
        holdem_speed_slow_rect,
        "SLOW",
        mouse_pos,
        small_font,
        enabled=True,
        accent_color=(
            (70, 95, 125)
            if holdem_table_speed
            == "slow"
            else None
        )
    )

    draw_modern_button(
        surface,
        holdem_speed_normal_rect,
        "NORMAL",
        mouse_pos,
        small_font,
        enabled=True,
        accent_color=(
            (70, 95, 125)
            if holdem_table_speed
            == "normal"
            else None
        )
    )

    draw_modern_button(
        surface,
        holdem_speed_fast_rect,
        "FAST",
        mouse_pos,
        small_font,
        enabled=True,
        accent_color=(
            (70, 95, 125)
            if holdem_table_speed
            == "fast"
            else None
        )
    )

    # ==================================================
    # AUTO DEAL
    # ==================================================

    auto_label = (
        name_font.render(
            "Auto Deal Next Hand",
            True,
            WHITE
        )
    )

    surface.blit(
        auto_label,
        (
            515,
            413
        )
    )

    auto_text = (
        "ON"
        if holdem_auto_deal_enabled
        else "OFF"
    )

    auto_color = (
        (45, 115, 75)
        if holdem_auto_deal_enabled
        else (130, 55, 55)
    )

    draw_modern_button(
        surface,
        holdem_auto_deal_toggle_rect,
        auto_text,
        mouse_pos,
        small_font,
        enabled=True,
        accent_color=auto_color
    )

    # ==================================================
    # TABLE CHAT
    # ==================================================

    chat_label = (
        name_font.render(
            "NPC Table Chat",
            True,
            WHITE
        )
    )

    surface.blit(
        chat_label,
        (
            515,
            475
        )
    )

    chat_text = (
        "ON"
        if holdem_table_chat_enabled
        else "OFF"
    )

    chat_color = (
        (45, 115, 75)
        if holdem_table_chat_enabled
        else (130, 55, 55)
    )

    draw_modern_button(
        surface,
        holdem_chat_toggle_rect,
        chat_text,
        mouse_pos,
        small_font,
        enabled=True,
        accent_color=chat_color
    )

    # ==================================================
    # TABLE CHAT POP-UPS
    # ==================================================

    popup_label = name_font.render(
        "Table Chat Pop-ups",
        True,
        WHITE if holdem_table_chat_enabled else (125, 130, 135)
    )
    surface.blit(popup_label, (515, 537))

    popup_enabled = is_poker_chat_popups_enabled()
    popup_text = "ON" if popup_enabled else "OFF"
    popup_color = (45, 115, 75) if popup_enabled else (130, 55, 55)

    draw_modern_button(
        surface,
        holdem_chat_popups_toggle_rect,
        popup_text,
        mouse_pos,
        small_font,
        enabled=holdem_table_chat_enabled,
        accent_color=popup_color
    )

    # ==================================================
    # Small explanatory text
    # ==================================================

    note_surface = (
        small_font.render(
            "Settings apply immediately.",
            True,
            (
                180,
                185,
                190
            )
        )
    )

    note_rect = (
        note_surface.get_rect(
            center=(
                holdem_options_panel_rect.centerx,
                592
            )
        )
    )

    surface.blit(
        note_surface,
        note_rect
    )

# ==================================================
# MAIN DRAW
# ==================================================

def draw_texas_holdem(
        game_surface,
        mouse_pos,
        holdem_game,
        card_fronts,
        card_back,
        draw_submenu_background,
        draw_submenu_title,
        draw_menu_button,
        draw_npc_portrait,
        title_font,
        label_font,
        detail_font,
        player_name,
        felt_surface,
        next_hand_seconds=None
):
    poker_chip_images = (
        get_poker_chip_images()
    )

    card_fx_kind, card_fx_elapsed = (
        sync_holdem_card_fx(
            holdem_game
        )
    )

    sync_holdem_chip_fx_context(
        holdem_game
    )

    wager_sweep_progress = (
        get_holdem_wager_sweep_progress(
            holdem_game
        )
    )

    # ==================================================
    # Background
    # ==================================================

    draw_submenu_background(
        overlay_alpha=110
    )

    holdem_fonts = get_holdem_fonts()

    holdem_title_font = holdem_fonts["title"]
    holdem_name_font = holdem_fonts["name"]
    holdem_small_font = holdem_fonts["small"]
    holdem_tiny_font = holdem_fonts["tiny"]



    # ==================================================
    # Table
    # ==================================================

    table_rect = pygame.Rect(
        233,
        105,
        900,
        460
    )

    wager_sweep_target = (
        table_rect.centerx,
        235
    )

    pygame.draw.ellipse(
        game_surface,
        TABLE_EDGE,
        table_rect
    )

    inner_table_rect = (
        table_rect.inflate(
            -30,
            -30
        )
    )

    if felt_surface is not None:

        scaled_felt = pygame.transform.smoothscale(
            felt_surface,
            inner_table_rect.size
        )

        felt_layer = pygame.Surface(
            inner_table_rect.size,
            pygame.SRCALPHA
        )

        felt_layer.blit(
            scaled_felt,
            (0, 0)
        )

        felt_mask = pygame.Surface(
            inner_table_rect.size,
            pygame.SRCALPHA
        )

        pygame.draw.ellipse(
            felt_mask,
            (
                255,
                255,
                255,
                255
            ),
            felt_mask.get_rect()
        )

        felt_layer.blit(
            felt_mask,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_MULT
        )

        game_surface.blit(
            felt_layer,
            inner_table_rect.topleft
        )

    else:

        pygame.draw.ellipse(
            game_surface,
            TABLE_GREEN,
            inner_table_rect
        )

    pygame.draw.ellipse(
        game_surface,
        WHITE,
        inner_table_rect,
        2
    )

    # ==================================================
    # Center table information backdrop
    #
    # Draw this before the seats so upper NPC HUDs/cards
    # always sit on top of it, matching Draw and Stud.
    # ==================================================

    info_panel_rect = pygame.Rect(
        table_rect.centerx - 142,
        184,
        284,
        88
    )

    draw_translucent_panel(
        game_surface,
        info_panel_rect,
        (0, 0, 0, 82),
        border_color=(110, 120, 115),
        border_width=1,
        radius=10
    )

    # ==================================================
    # NPC SEAT ANCHORS
    # ==================================================

    npc_anchors = [
        (180, 325),  # left
        (450, 120),  # upper-left: higher + farther left
        (900, 120),  # upper-right: higher + farther right
        (1090, 325),  # right
    ]

    # ==================================================
    # NPC DRAWING
    # ==================================================

    for index, npc in enumerate(
            holdem_game.npcs
    ):

        if index >= len(
                npc_anchors
        ):
            break

        anchor_x, anchor_y = (
            npc_anchors[index]
        )

        npc_is_busted = (
                index < len(
            holdem_game.npc_busted
        )
                and holdem_game.npc_busted[
                    index
                ]
        )

        npc_is_current_actor = (
                not holdem_game.hand_complete
                and not npc_is_busted
                and holdem_game.current_actor
                == index + 1
        )

        npc_is_folded = (
                index < len(
            holdem_game.npc_folded
        )
                and holdem_game.npc_folded[
                    index
                ]
        )

        npc_is_winner = (
                holdem_game.current_stage == "showdown"
                and index + 1 in holdem_game.winner_indexes
        )


        npc_is_all_in = (
                index < len(
            holdem_game.npc_all_in
        )
                and holdem_game.npc_all_in[
                    index
                ]
                and not npc_is_busted
                and not npc_is_folded
        )

        portrait_size = 72

        card_width = 64
        card_height = 88
        card_overlap = 20

        name_width = 165
        name_height = 40

        money_width = 118
        money_height = 28

        # ------------------------------------------
        # Portrait
        # ------------------------------------------

        portrait_rect = pygame.Rect(
            anchor_x - 52,
            anchor_y,
            portrait_size,
            portrait_size
        )

        draw_npc_portrait(
            npc,
            portrait_rect,
            "holdem"
        )

        # ==================================================
        # Portrait state overlay
        # ==================================================

        if npc_is_busted:

            busted_overlay = pygame.Surface(
                (
                    portrait_rect.width,
                    portrait_rect.height
                ),
                pygame.SRCALPHA
            )

            pygame.draw.circle(
                busted_overlay,
                (
                    5,
                    5,
                    5,
                    205
                ),
                (
                    portrait_rect.width // 2,
                    portrait_rect.height // 2
                ),
                min(
                    portrait_rect.width,
                    portrait_rect.height
                ) // 2
            )

            game_surface.blit(
                busted_overlay,
                portrait_rect.topleft
            )

            # Small X over eliminated portrait.
            pygame.draw.line(
                game_surface,
                (
                    150,
                    150,
                    150
                ),
                (
                    portrait_rect.left + 18,
                    portrait_rect.top + 18
                ),
                (
                    portrait_rect.right - 18,
                    portrait_rect.bottom - 18
                ),
                3
            )

            pygame.draw.line(
                game_surface,
                (
                    150,
                    150,
                    150
                ),
                (
                    portrait_rect.right - 18,
                    portrait_rect.top + 18
                ),
                (
                    portrait_rect.left + 18,
                    portrait_rect.bottom - 18
                ),
                3
            )

        elif npc_is_folded:

            fold_overlay = pygame.Surface(
                (
                    portrait_rect.width,
                    portrait_rect.height
                ),
                pygame.SRCALPHA
            )

            pygame.draw.circle(
                fold_overlay,
                (
                    0,
                    0,
                    0,
                    165
                ),
                (
                    portrait_rect.width // 2,
                    portrait_rect.height // 2
                ),
                min(
                    portrait_rect.width,
                    portrait_rect.height
                ) // 2
            )

            game_surface.blit(
                fold_overlay,
                portrait_rect.topleft
            )

        # ------------------------------------------
        # Current-turn gold border
        # ------------------------------------------

        if npc_is_current_actor or npc_is_winner:
            pygame.draw.rect(
                game_surface,
                (
                    235,
                    190,
                    70
                ),
                portrait_rect.inflate(
                    6,
                    6
                ),
                4 if npc_is_winner else 3,
                border_radius=9
            )

        # ------------------------------------------
        # Dealer / blind position badges
        # ------------------------------------------

        draw_holdem_position_badges(
            game_surface,
            holdem_game,
            index + 1,
            portrait_rect.x,
            portrait_rect.y - 26
        )

        # ------------------------------------------
        # Cards above portrait/name
        # ------------------------------------------

        cards_y = (
                anchor_y - 56
        )

        first_card_x = (
                anchor_x + 8
        )

        second_card_x = (
                first_card_x
                + card_width
                - card_overlap
        )

        # ------------------------------------------
        # Show cards at showdown if NPC did not fold
        # ------------------------------------------

        npc_is_busted = (
                index
                < len(
            holdem_game.npc_busted
        )
                and holdem_game.npc_busted[
                    index
                ]
        )

        show_npc_cards = (
                (holdem_game.current_stage == "showdown"
                 or holdem_game.should_reveal_runout_hands())
                and not npc_is_folded
                and not npc_is_busted
                and index
                < len(
            holdem_game.npc_hands
        )
                and len(
            holdem_game.npc_hands[
                index
            ]
        ) >= 2
        )

        # ==================================================
        # Busted NPCs receive no cards
        # ==================================================

        if not npc_is_busted:

            for card_number in range(2):

                card_x = (
                    first_card_x
                    if card_number == 0
                    else second_card_x
                )

                # ==========================================
                # SHOWDOWN FLIP
                # ==========================================

                if show_npc_cards:

                    if (
                            card_fx_kind
                            == "showdown"
                    ):

                        flip_order = (
                                index * 2
                                + card_number
                        )

                        progress = (
                            get_holdem_card_fx_progress(
                                card_fx_elapsed,
                                delay=(
                                        flip_order
                                        * 90
                                ),
                                duration=240
                            )
                        )

                        draw_holdem_flipping_card(
                            game_surface,
                            holdem_game.npc_hands[
                                index
                            ][
                                card_number
                            ],
                            card_back,
                            card_x,
                            cards_y,
                            card_fronts,
                            card_width,
                            card_height,
                            progress
                        )

                    else:

                        draw_card_face(
                            game_surface,
                            holdem_game.npc_hands[
                                index
                            ][
                                card_number
                            ],
                            card_x,
                            cards_y,
                            card_fronts,
                            width=card_width,
                            height=card_height
                        )

                # ==========================================
                # HIDDEN HOLE CARD
                # ==========================================

                else:

                    if card_fx_kind == "deal":

                        # Deal:
                        # NPC 0,1,2,3 → player
                        # then repeat for second card.
                        deal_order = (
                                card_number * 5
                                + index
                        )

                        progress = (
                            get_holdem_card_fx_progress(
                                card_fx_elapsed,
                                delay=(
                                        deal_order
                                        * 70
                                ),
                                duration=180
                            )
                        )

                        draw_holdem_popping_card_back(
                            game_surface,
                            card_back,
                            card_x,
                            cards_y,
                            card_width,
                            card_height,
                            progress
                        )

                    else:

                        draw_card_back(
                            game_surface,
                            card_back,
                            card_x,
                            cards_y,
                            width=card_width,
                            height=card_height
                        )

            # Once a player folds, keep their hidden cards visibly inactive
            # for the rest of the hand even after the transient FOLDED action
            # label is cleared on a later street.
            if npc_is_folded:

                folded_card_overlay = pygame.Surface(
                    (
                        card_width,
                        card_height
                    ),
                    pygame.SRCALPHA
                )

                folded_card_overlay.fill(
                    (
                        105,
                        105,
                        105,
                        185
                    )
                )

                for folded_card_x in (
                        first_card_x,
                        second_card_x
                ):

                    game_surface.blit(
                        folded_card_overlay,
                        (
                            folded_card_x,
                            cards_y
                        )
                    )

        # ------------------------------------------
        # Name box
        # ------------------------------------------

        name_rect = pygame.Rect(
            anchor_x,
            anchor_y + 6,
            name_width,
            name_height
        )

        if npc_is_busted:

            name_fill = (
                24,
                24,
                26,
                225
            )

            name_border = (
                75,
                75,
                80
            )

            name_text_color = (
                145,
                145,
                150
            )

        elif npc_is_folded:

            name_fill = (
                10,
                10,
                10,
                210
            )

            name_border = (
                85,
                85,
                90
            )

            name_text_color = (
                185,
                185,
                190
            )

        else:

            name_fill = (
                18,
                20,
                24,
                235
            )

            name_border = (
                (
                    235,
                    190,
                    70
                )
                if (npc_is_current_actor or npc_is_winner)
                else (
                    120,
                    125,
                    130
                )
            )

            name_text_color = WHITE

        draw_translucent_panel(
            game_surface,
            name_rect,
            name_fill,
            border_color=name_border,
            border_width=(
                4
                if npc_is_winner
                else (
                    3
                    if npc_is_current_actor
                    else 2
                )
            ),
            radius=10
        )

        npc_display_name = (
            holdem_game.get_table_player_name(
                index + 1
            )
        )

        blit_text_fit(
            game_surface,
            npc_display_name,
            holdem_name_font,
            name_text_color,
            name_rect,
            padding=10
        )

        # ==================================================
        # Money / status box
        # ==================================================

        money_rect = pygame.Rect(
            name_rect.centerx
            - money_width // 2,
            name_rect.bottom - 2,
            money_width,
            money_height
        )

        npc_stack = 0

        if index < len(
                holdem_game.npc_stacks
        ):
            npc_stack = (
                holdem_game.npc_stacks[
                    index
                ]
            )

        if npc_is_busted:

            money_fill = (
                28,
                28,
                30,
                240
            )

            money_border = (
                85,
                85,
                90
            )

            money_text = "OUT"

            money_text_color = (
                165,
                165,
                170
            )

        else:

            money_fill = (
                12,
                14,
                16,
                240
            )

            money_border = (
                90,
                95,
                100
            )

            money_text = (
                f"${npc_stack:,}"
            )

            money_text_color = (
                240,
                255,
                235
            )

        draw_translucent_panel(
            game_surface,
            money_rect,
            money_fill,
            border_color=money_border,
            border_width=1,
            radius=8
        )

        money_text_surface = (
            holdem_small_font.render(
                money_text,
                True,
                money_text_color
            )
        )

        money_text_rect = (
            money_text_surface.get_rect(
                center=money_rect.center
            )
        )

        game_surface.blit(
            money_text_surface,
            money_text_rect
        )


        # ------------------------------------------
        # Action box
        # ------------------------------------------

        action_rect = pygame.Rect(
            money_rect.x,
            money_rect.bottom + 4,
            money_rect.width,
            money_rect.height
        )

        action_text = ""

        if index < len(
                holdem_game.npc_action_texts
        ):
            action_text = (
                holdem_game.npc_action_texts[
                    index
                ]
            )

        # ==================================================
        # Persistent status takes priority over last action
        # ==================================================

        if npc_is_busted:

            action_text = (
                "ELIMINATED"
            )

        elif npc_is_all_in:

            action_text = (
                "ALL IN"
            )

        if action_text:

            # ==================================================
            # Eliminated
            # ==================================================

            if action_text == "ELIMINATED":

                action_fill = (
                    30,
                    30,
                    32,
                    240
                )

                action_border = (
                    85,
                    85,
                    90
                )

                action_text_color = (
                    150,
                    150,
                    155
                )

            # ==================================================
            # Folded
            # ==================================================

            elif action_text == "Folded":

                action_fill = (
                    70,
                    25,
                    25,
                    235
                )

                action_border = (
                    145,
                    75,
                    75
                )

                action_text_color = (
                    225,
                    205,
                    205
                )

            # ==================================================
            # All in
            # ==================================================

            elif action_text == "ALL IN":

                action_fill = (
                    105,
                    72,
                    18,
                    240
                )

                action_border = (
                    240,
                    190,
                    70
                )

                action_text_color = WHITE

            # ==================================================
            # Normal action
            # ==================================================

            else:

                action_fill = (
                    10,
                    12,
                    14,
                    235
                )

                action_border = (
                    110,
                    115,
                    120
                )

                action_text_color = WHITE

            draw_translucent_panel(
                game_surface,
                action_rect,
                action_fill,
                border_color=action_border,
                border_width=1,
                radius=8
            )

            blit_text_fit(
                game_surface,
                action_text,
                holdem_small_font,
                action_text_color,
                action_rect,
                padding=6
            )

        # ------------------------------------------
        # Chips committed this betting round
        # ------------------------------------------

        npc_chunks = []

        if index < len(
                holdem_game.npc_bet_chunks
        ):

            npc_chunks = (
                holdem_game.npc_bet_chunks[
                    index
                ]
            )

        if (
                npc_chunks
                and not npc_is_busted
        ):

            # ======================================
            # Position chips toward center of table
            # ======================================

            npc_chip_positions = [
                # Left seat
                (
                    anchor_x + 190,
                    anchor_y + 55
                ),

                # Upper-left seat
                (
                    anchor_x + 95,
                    anchor_y + 125
                ),

                # Upper-right seat
                (
                    anchor_x - 5,
                    anchor_y + 125
                ),

                # Right seat
                (
                    anchor_x - 105,
                    anchor_y + 55
                ),
            ]

            chip_center_x, chip_y = (
                npc_chip_positions[
                    index
                ]
            )

            draw_holdem_chip_chunks(
                game_surface,
                npc_chunks,
                chip_center_x,
                chip_y,
                poker_chip_images,
                base_unit=max(
                    1,
                    holdem_game.ante
                ),
                origin=(
                    money_rect.centerx,
                    money_rect.centery
                ),
                animation_key=(
                    f"npc_{index}"
                ),
                sweep_target=(
                    wager_sweep_target
                ),
                sweep_progress=(
                    wager_sweep_progress
                )
            )


    # ==================================================
    # Community cards
    # ==================================================

    community_card_width = 100
    community_card_height = 138
    community_card_gap = 12

    community_y = 282

    total_community_width = (
            community_card_width * 5
            + community_card_gap * 4
    )

    community_start_x = (
            table_rect.centerx
            - total_community_width // 2
    )

    # ==================================================
    # Pot
    # ==================================================

    display_pot = (
        holdem_game.get_display_pot_amount()
        if hasattr(holdem_game, "get_display_pot_amount")
        else holdem_game.pot
    )

    pot_base_unit = max(
        1,
        int(
            getattr(
                holdem_game,
                "ante",
                1
            )
        )
    )

    draw_holdem_pot_stack(
        game_surface,
        display_pot,
        (
            table_rect.centerx,
            community_y - 48
        ),
        pot_base_unit
    )

    pot_surface = holdem_small_font.render(
        f"Pot: ${display_pot:,}",
        True,
        WHITE
    )

    pot_rect = (
        pot_surface.get_rect(
            center=(
                table_rect.centerx,
                community_y - 18
            )
        )
    )

    game_surface.blit(
        pot_surface,
        pot_rect
    )

    # ==================================================
    # Blind level
    # ==================================================

    small_blind = getattr(
        holdem_game,
        "small_blind",
        max(
            1,
            getattr(
                holdem_game,
                "ante",
                1
            )
        )
    )

    big_blind = getattr(
        holdem_game,
        "big_blind",
        max(
            2,
            small_blind * 2
        )
    )

    blinds_surface = (
        holdem_tiny_font.render(
            (
                f"Blinds: "
                f"${small_blind:,} / "
                f"${big_blind:,}"
            ),
            True,
            (
                225,
                225,
                230
            )
        )
    )

    blinds_rect = (
        blinds_surface.get_rect(
            center=(
                table_rect.centerx,
                205
            )
        )
    )

    game_surface.blit(
        blinds_surface,
        blinds_rect
    )


    for index in range(5):

        card_x = (
                community_start_x
                + index
                * (
                        community_card_width
                        + community_card_gap
                )
        )

        if index < len(
                holdem_game.community_cards
        ):

            animate_card = False
            animation_delay = 0

            # ==========================================
            # FLOP
            # ==========================================

            if (
                    card_fx_kind == "flop"
                    and index <= 2
            ):

                animate_card = True

                animation_delay = (
                        index * 110
                )

            # ==========================================
            # TURN
            # ==========================================

            elif (
                    card_fx_kind == "turn"
                    and index == 3
            ):

                animate_card = True

            # ==========================================
            # RIVER
            # ==========================================

            elif (
                    card_fx_kind == "river"
                    and index == 4
            ):

                animate_card = True

            # ==========================================
            # Animated reveal
            # ==========================================

            if animate_card:

                progress = (
                    get_holdem_card_fx_progress(
                        card_fx_elapsed,
                        delay=animation_delay,
                        duration=220
                    )
                )

                draw_holdem_popping_card_face(
                    game_surface,
                    holdem_game.community_cards[
                        index
                    ],
                    card_x,
                    community_y,
                    card_fronts,
                    community_card_width,
                    community_card_height,
                    progress
                )

            # ==========================================
            # Already-established card
            # ==========================================

            else:

                draw_card_face(
                    game_surface,
                    holdem_game.community_cards[
                        index
                    ],
                    card_x,
                    community_y,
                    card_fronts,
                    width=community_card_width,
                    height=community_card_height
                )


    # ==================================================
    # Player area
    # ==================================================

    player_center_x = 683

    player_card_width = 126
    player_card_height = 174
    player_card_overlap = 34

    player_cards_total_width = (
            player_card_width * 2
            - player_card_overlap
    )

    player_start_x = (
            player_center_x
            - player_cards_total_width // 2
    )

    player_cards_y = 563

    # ==================================================
    # Player hole cards
    # ==================================================

    for card_number in range(
            min(
                2,
                len(
                    holdem_game.player_hand
                )
            )
    ):

        card_x = (
                player_start_x
                + card_number
                * (
                        player_card_width
                        - player_card_overlap
                )
        )

        if card_fx_kind == "deal":

            # Player is fifth in each deal cycle:
            #
            # NPC0 NPC1 NPC2 NPC3 PLAYER
            deal_order = (
                    card_number * 5
                    + 4
            )

            progress = (
                get_holdem_card_fx_progress(
                    card_fx_elapsed,
                    delay=(
                            deal_order
                            * 70
                    ),
                    duration=180
                )
            )

            draw_holdem_popping_card_face(
                game_surface,
                holdem_game.player_hand[
                    card_number
                ],
                card_x,
                player_cards_y,
                card_fronts,
                player_card_width,
                player_card_height,
                progress
            )

        else:

            draw_card_face(
                game_surface,
                holdem_game.player_hand[
                    card_number
                ],
                card_x,
                player_cards_y,
                card_fronts,
                width=player_card_width,
                height=player_card_height
            )

    # ==================================================
    # Player chips
    # ==================================================

    if holdem_game.player_bet_chunks:
        draw_holdem_chip_chunks(
            game_surface,
            holdem_game.player_bet_chunks,
            player_center_x + 130,
            535,
            poker_chip_images,
            base_unit=max(
                1,
                holdem_game.ante
            ),
            origin=(
                player_center_x,
                700
            ),
            animation_key="player",
            sweep_target=(
                wager_sweep_target
            ),
            sweep_progress=(
                wager_sweep_progress
            )
        )

    draw_holdem_position_badges(
        game_surface,
        holdem_game,
        0,
        player_center_x + 144,
        686
    )

    draw_holdem_player_hud(
        game_surface=game_surface,
        player_name=player_name,
        player_stack=holdem_game.player_stack,
        panel_center_x=player_center_x,
        panel_y=680,
        label_font=label_font,
        detail_font=detail_font,
        is_current_actor=(
                not holdem_game.hand_complete
                and holdem_game.current_actor == 0
                and not holdem_game.player_has_acted
        ),
        is_winner=(
                holdem_game.current_stage == "showdown"
                and 0 in holdem_game.winner_indexes
        )
    )

    draw_holdem_payout_animation(
        game_surface,
        holdem_game,
        npc_anchors,
        max(
            1,
            getattr(
                holdem_game,
                "ante",
                1
            )
        )
    )

    draw_holdem_showdown_banner(
        game_surface,
        holdem_game
    )

    # ==================================================
    # Game log content
    # ==================================================

    update_holdem_log(
        holdem_game
    )

    # ==================================================
    # Game logo
    # ==================================================

    draw_poker_logo(
        game_surface,
        "texas_holdem",
        pygame.Rect(32, 66, 280, 75)
    )

    # ==================================================
    # Game log / Chat panel
    # ==================================================

    draw_holdem_log_panel(
        game_surface=game_surface,
        detail_font=detail_font,
        mouse_pos=mouse_pos,
        active_tab=holdem_active_tab,
        log_lines=holdem_log_history
    )

    # ==================================================
    # Current hand above controls
    # ==================================================

    hand_text = (
        get_holdem_player_hand_text(
            holdem_game
        )
    )

    if hand_text:
        hand_surface = holdem_small_font.render(
            hand_text,
            True,
            WHITE
        )

        hand_rect = (
            hand_surface.get_rect(
                bottomright=(
                    holdem_action_panel_rect.right - 6,
                    holdem_action_panel_rect.y - 8
                )
            )
        )

        game_surface.blit(
            hand_surface,
            hand_rect
        )

    # ==================================================
    # Poker controls
    # ==================================================

    draw_holdem_side_panel(
        surface=game_surface,
        holdem_game=holdem_game,
        title_font=label_font,
        detail_font=detail_font,
        mouse_pos=mouse_pos,
        next_hand_seconds=next_hand_seconds
    )

    # ==================================================
    # Top-right utility buttons
    # ==================================================

    draw_modern_button(
        game_surface,
        holdem_options_rect,
        "OPTIONS",
        mouse_pos,
        holdem_small_font,
        enabled=True
    )

    draw_modern_button(
        game_surface,
        holdem_exit_rect,
        "EXIT",
        mouse_pos,
        holdem_small_font,
        enabled=bool(holdem_game.hand_complete)
    )

    # ==================================================
    # Final speech-bubble overlay pass
    # ==================================================

    if is_poker_chat_popups_enabled():
        for index, _npc in enumerate(holdem_game.npcs[:4]):
            anchor_x, anchor_y = npc_anchors[index]
            name_rect = pygame.Rect(anchor_x, anchor_y + 6, 165, 40)
            _holdem_speech_overlay.draw(
                game_surface,
                holdem_game.get_table_player_name(index + 1),
                name_rect,
                holdem_small_font
            )

    # ==================================================
    # Options overlay
    # ==================================================

    draw_holdem_options_overlay(
        game_surface,
        mouse_pos
    )
    draw_recap(game_surface, mouse_pos, holdem_game)


def get_texas_holdem_action(
        mouse_pos,
        holdem_game
):

    if mouse_pos is None:
        return None

    recap_action = get_recap_action(mouse_pos, holdem_game)
    if recap_action:
        return recap_action

    if holdem_options_open:
        return None

    # ==================================================
    # Next hand
    # ==================================================

    if (
            holdem_game.hand_complete
            and holdem_next_hand_rect.collidepoint(
        mouse_pos
    )
    ):
        return ACTION_NEXT_HAND

    # ==================================================
    # Main poker actions
    # ==================================================

    if holdem_game.can_player_act_now():

        if holdem_fold_rect.collidepoint(
                mouse_pos
        ):
            return ACTION_FOLD

        if holdem_call_rect.collidepoint(
                mouse_pos
        ):
            return ACTION_CHECK_CALL

        if holdem_raise_rect.collidepoint(
                mouse_pos
        ):
            return ACTION_BET_RAISE

    # ==================================================
    # Exit
    # ==================================================

    if (
            holdem_game.hand_complete
            and holdem_exit_rect.collidepoint(mouse_pos)
    ):
        return ACTION_RETURN

    # ==================================================
    # Options
    # ==================================================

    if holdem_options_rect.collidepoint(
            mouse_pos
    ):
        return "options"

    return None
