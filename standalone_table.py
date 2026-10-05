"""Standalone Hold'em orchestration; no Career state or save files."""
import copy
import json
import random
from pathlib import Path
from texas_holdem import TexasHoldemGame
import texas_holdem_ui as ui
from texas_holdem_chat import generate_npc_action_chat, generate_player_action_reaction

ROOT=Path(__file__).resolve().parent

def load_roster():
    roster=json.loads((ROOT/'data/npcs.json').read_text(encoding='utf-8'))
    if not isinstance(roster,list) or len(roster)<3:raise ValueError('data/npcs.json must contain at least three NPCs')
    return roster

class StandaloneTable:
    def __init__(self,name,roster=None):
        self.name=name.strip()[:32] or 'Player'
        self.game=TexasHoldemGame()
        opponents=copy.deepcopy(random.sample(load_roster() if roster is None else roster,3))
        self.game.start_session(opponents,5000,25)
        self.next_action_at=0
        self.hand_complete_at=0
        ui.holdem_chat_history.clear()
        ui.holdem_options_open=False
        ui.clear_holdem_manual_bet()
        self.game.start_hand()
    def update(self,now):
        g=self.game
        if getattr(g,'recap_open',False):
            self.hand_complete_at=now
            return None
        if g.hand_complete:
            if not self.hand_complete_at:self.hand_complete_at=now
            if ui.is_holdem_auto_deal_enabled() and not self.finished and now-self.hand_complete_at>=ui.get_holdem_next_hand_delay():
                self.act('next_hand');return 'card_flip'
            return None
        self.hand_complete_at=0
        if g.is_betting_round_complete():
            if not self.next_action_at:self.next_action_at=now+ui.get_holdem_street_delay()
            if now>=self.next_action_at:
                self.next_action_at=0;g.advance_after_betting_round();return 'card_flip'
        elif g.current_actor!=0:
            if not self.next_action_at:self.next_action_at=now+ui.get_holdem_npc_delay()
            if now>=self.next_action_at:
                self.next_action_at=0
                actor=g.current_actor
                if g.run_next_npc_action() and actor>0:
                    chat=generate_npc_action_chat(g,actor-1)
                    if chat:ui.add_holdem_chat_message(*chat)
                return 'poker_check'
        else:self.next_action_at=0
        return None
    def act(self,action):
        g=self.game
        if action=='next_hand':
            if g.hand_complete and not g.player_busted and not g.all_npcs_busted():
                self.next_action_at=0;self.hand_complete_at=0;return g.start_hand()
            return False
        if not g.can_player_act_now():return False
        was_call=g.get_player_amount_to_call()>0
        if action=='fold':success=g.player_fold()
        elif action=='check_call':success=g.player_call() if g.get_player_amount_to_call()>0 else g.player_check()
        elif action=='bet_raise':
            amount=ui.get_holdem_bet_amount(g)
            success=g.player_bet(amount) if g.current_bet==0 else g.player_raise(amount)
            if success:ui.clear_holdem_manual_bet()
        else:return False
        if success:
            self.next_action_at=0
            chat_action='call' if action=='check_call' and was_call else 'check' if action=='check_call' else 'raise' if action=='bet_raise' else 'fold'
            chat=generate_player_action_reaction(g,chat_action)
            if chat:ui.add_holdem_chat_message(*chat)
        return success
    @property
    def finished(self):return self.game.hand_complete and (self.game.player_busted or self.game.all_npcs_busted())
