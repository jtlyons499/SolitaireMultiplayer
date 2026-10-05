"""Table chatter sampled from the NPC's full trait mix, using public events."""
import random
from npc_personality import get_npc_traits, TRAIT_NAMES, npc_identity
from poker_strategy import strategy_chat_line

# Lines describe intent or visible events, never unseen opponent cards.
TRAIT_CHAT = {
    "caution": {
        "check": ("Let's keep this small.", "I'll wait."),
        "fold": ("Too much risk.", "Keeping my chips."),
        "call": ("Just a call.", "Carefully."),
        "bet": ("A measured bet.",), "raise": ("I've thought this through.",),
        "all_in": ("No chips left to hold back.",), "loss": ("That was costly.",),
    },
    "aggressiveness": {
        "check": ("Your move.",), "bet": ("Let's put some chips in.", "Keep up."),
        "raise": ("Make it bigger.", "I'm pushing back."), "call": ("You're on.",),
        "all_in": ("All of it. Let's go.",), "win": ("That's how you do it.",),
    },
    "unpredictability": {
        "check": ("Plot twist: I check.",), "bet": ("Feeling adventurous.",),
        "raise": ("Didn't expect that, did you?",), "fold": ("Changed my mind.",),
        "call": ("Let's see where this goes.",), "split": ("Well, that was weird.",),
    },
    "escalation": {
        "raise": ("You push, I push back.", "Let's take it up a notch."),
        "call": ("I'm not backing off yet.",), "bet": ("Let's turn up the pressure.",),
        "player_raise": ("Oh, we're doing this?",), "player_bet": ("Challenge accepted.",),
    },
    "selectivity": {
        "check": ("Waiting for my spot.",), "fold": ("This isn't my spot.",),
        "bet": ("Time to commit.",), "raise": ("I like this spot.",),
        "win": ("Patience pays.",), "call": ("Worth a look.",),
    },
    "tenacity": {
        "fold": ("I'm staying in this game.", "Live to play another hand."),
        "check": ("Still here.",), "call": ("I'm not done yet.",),
        "all_in": ("This is my last stand.",), "bust": ("I tried to hang on.",),
        "loss": ("I've still got chips.",),
    },
    "pessimism": {
        "fold": ("I don't see this improving.", "Already feels like trouble."),
        "check": ("Not feeling hopeful.",), "call": ("This might end badly.",),
        "win": ("Huh. Better than I expected.",), "loss": ("Saw that coming.",),
        "player_raise": ("Of course it gets worse.",),
    },
    "bitterness": {
        "loss": ("I'll remember that.", "We're not finished."),
        "win": ("That feels good.",), "raise": ("Let's settle this.",),
        "bust": ("I'll remember this table.",),
    },
}
NEUTRAL_CHAT = {
    "check": ("Check.",), "call": ("I'll call.",), "bet": ("Let's play.",),
    "raise": ("A little more.",), "fold": ("Next hand.",),
    "all_in": ("All in.",), "win": ("Nice.",), "loss": ("Good hand.",),
    "split": ("Fair enough.",), "bust": ("Good game.",),
    "player_bet": ("Interesting.",), "player_raise": ("A raise, huh?",),
    "player_all_in": ("Everything on the line.",), "player_call": ("Let's see.",),
    "player_fold": ("Next one.",), "player_check": ("Okay.",),
}


def trait_chat(npc, event, rng=None, grudge_target=None, grudge_intensity=0.0):
    rng = rng or random
    traits = get_npc_traits(npc)
    if (grudge_target and traits["bitterness"] >= 7 and grudge_intensity >= 0.30
            and event in ("raise", "call", "bet", "loss", "player_raise", "player_bet")
            and rng.random() < 0.65):
        target = str(grudge_target)
        if target.casefold() in ("you", "player"):
            return rng.choice(("I haven't forgotten that hand.", "I'm coming for your chips."))
        if event == "loss":
            return f"I'll remember that, {target}."
        return rng.choice((f"Your turn, {target}.", f"I'm not done with you, {target}."))
    pools = [(NEUTRAL_CHAT.get(event, ("Let's play.",)), 5)]
    for key in TRAIT_NAMES:
        lines = TRAIT_CHAT[key].get(event)
        if lines:
            pools.append((lines, max(0, traits[key] - 2)**2))
    pool = rng.choices(pools, weights=[weight for _, weight in pools], k=1)[0][0]
    return rng.choice(pool)


def game_trait_chat(game, npc_index, event, rng=None, target_player=False):
    rng = rng or random
    context = game.get_npc_grudge_context(npc_index)
    if target_player:
        npc = game.npcs[npc_index]
        score = game.personality_memory.intensity(npc_identity(npc, npc_index + 1),
                                                  "player", game.hand_number,
                                                  get_npc_traits(npc)["bitterness"])
        context = {"grudge_target": "You", "grudge_intensity": score}
    # Existing specific grudges retain priority. Replies to a player's action
    # must not reuse a stale decision from the NPC's previous turn.
    decisions = getattr(game, "npc_ai_last_decisions", ())
    if (not target_player and context.get("grudge_intensity", 0) < .30
            and 0 <= npc_index < len(decisions)):
        line = strategy_chat_line(decisions[npc_index], event, rng)
        if line:
            return line
    return trait_chat(game.npcs[npc_index], event, rng,
                      grudge_target=context.get("grudge_target"),
                      grudge_intensity=context.get("grudge_intensity", 0.0))
