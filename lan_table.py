"""Authoritative four-seat game with two human seats and two AI seats."""
import copy,random
import texas_holdem_ui as ui
from texas_holdem import TexasHoldemGame
from standalone_table import load_roster
from lan_protocol import snapshot

class TwoHumanGame(TexasHoldemGame):
    def __init__(self):
        super().__init__()
        self.allow_network_spectator=True
    def resolve_after_fold(self):
        if self.hand_complete:return False
        active=self.get_active_player_indexes()
        return self.award_pot_to_single_player(active[0]) if len(active)==1 else False

class HostedTable:
    def __init__(self,host_name,guest_name,roster=None):
        self.names=[host_name,guest_name];self.game=TwoHumanGame();self.revision=0;self.due=0;self.ready=set()
        opponents=copy.deepcopy(random.sample(load_roster() if roster is None else roster,2))
        self.names += [n['name'] for n in opponents]
        self.game.start_session([{'id':'guest','name':guest_name,'skill_tier':'mid'},*opponents],5000,25)
        self.game.start_hand()
    def view(self,seat):
        message=snapshot(self.game,seat,self.revision,self.names)
        message['ready_count']=len(self.ready);message['you_ready']=seat in self.ready
        return message
    def act(self,seat,action,amount,revision):
        g=self.game
        if revision!=self.revision or seat not in (0,1):return False
        if action=='next_hand':
            if not g.hand_complete:return False
            self.ready.add(seat)
            if self.ready=={0,1} and len([i for i in range(4) if not ([g.player_busted,*g.npc_busted][i])])>1:
                self.ready.clear();g.start_hand();self.revision+=1;self.due=0
            return True
        if g.hand_complete or g.current_actor!=seat or not g.actor_needs_action(seat):return False
        if not isinstance(amount,int) or isinstance(amount,bool) or amount<0 or amount>1000000:return False
        if seat==0:
            if action=='fold':ok=g.player_fold()
            elif action=='check_call':ok=g.player_call() if g.get_player_amount_to_call()>0 else g.player_check()
            elif action=='bet_raise':ok=g.player_bet(amount) if g.current_bet==0 else g.player_raise(amount)
            else:return False
        else:
            if action=='fold':ok=g.npc_fold(0)
            elif action=='check_call':ok=g.npc_call(0) if g.get_npc_amount_to_call(0)>0 else g.npc_check(0)
            elif action=='bet_raise':
                if g.current_bet>0 and not g.can_npc_raise(0):return False
                ok=g.npc_bet(0,amount) if g.current_bet==0 else g.npc_raise(0,amount)
            else:return False
        if ok:
            if not g.hand_complete and (seat==1 or action=='fold'):g.advance_to_next_actor()
            self.revision+=1;self.due=0
        return ok
    def update(self,now):
        g=self.game
        if g.hand_complete:return False
        complete=g.is_betting_round_complete()
        if not complete and g.current_actor in (0,1):self.due=0;return False
        if not self.due:self.due=now+(ui.get_holdem_street_delay() if complete else ui.get_holdem_npc_delay());return False
        if now<self.due:return False
        self.due=0
        if complete:g.advance_after_betting_round()
        elif g.current_actor>=2:g.run_next_npc_action()
        else:g.advance_to_next_actor()
        self.revision+=1;return True
