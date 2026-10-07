"""Public seat-relative snapshots. Never serialize a deck, AI memory or hidden hand."""
import copy
from texas_holdem import TexasHoldemGame

PAIRS=(('player_stack','npc_stacks'),('player_hand_contribution','npc_hand_contributions'),('player_busted','npc_busted'),('player_bet_chunks','npc_bet_chunks'),('player_action_text','npc_action_texts'),('player_round_bet','npc_round_bets'),('player_folded','npc_folded'),('player_all_in','npc_all_in'),('player_has_acted','npc_has_acted'))
FIELDS=('hand_number','starting_stack','ante','small_blind','big_blind','pot','last_resolved_pot','current_bet','last_raise_size','betting_round_complete','current_stage','hand_complete','community_cards')

def snapshot(game,viewer,revision,names):
    order=[viewer]+[i for i in range(len(names)) if i!=viewer];index={seat:i for i,seat in enumerate(order)}
    data={k:copy.deepcopy(getattr(game,k)) for k in FIELDS}
    for human,npc in PAIRS:
        values=[getattr(game,human),*getattr(game,npc)]
        data[human]=copy.deepcopy(values[viewer]);data[npc]=[copy.deepcopy(values[i]) for i in order[1:]]
    for key in ('current_actor','dealer_index','small_blind_index','big_blind_index','last_raiser'):
        data[key]=index.get(getattr(game,key),getattr(game,key))
    for key in ('winner_indexes','hand_seat_indexes','last_hand_busted_indexes'):
        data[key]=[index[i] for i in getattr(game,key) if i in index]
    hands=[game.player_hand,*game.npc_hands];folded=[game.player_folded,*game.npc_folded]
    reveal=game.current_stage=='showdown' or game.should_reveal_runout_hands()
    data['player_hand']=copy.deepcopy(hands[viewer])
    data['npc_hands']=[copy.deepcopy(hands[i]) if reveal and not folded[i] else [] for i in order[1:]]
    data['npcs']=[{'id':f'seat_{i}','name':names[i],'portrait':game.npcs[i-1].get('portrait','') if i>1 else ''} for i in order[1:]]
    data['last_pot_awards']=copy.deepcopy(game.last_pot_awards)
    for pot in data['last_pot_awards']:
        for key in ('winners','eligible'): 
            if key in pot:pot[key]=[index[i] for i in pot[key] if i in index]
    data['result_text']=' | '.join(f"{names[i]} wins" for i in game.winner_indexes) if game.hand_complete else ''
    return {'type':'state','revision':revision,'data':data,'names':[names[i] for i in order]}

class ClientGame(TexasHoldemGame):
    def __init__(self):super().__init__();self.names=[];self.revision=-1;self.ready_count=0;self.you_ready=False
    def apply(self,message):
        if message['data']['hand_number']!=self.hand_number:self.recap_open=False;self.recap_page=0
        self.revision=message['revision'];self.names=message['names']
        self.ready_count=message.get('ready_count',0);self.you_ready=message.get('you_ready',False)
        for key,value in message['data'].items():setattr(self,key,value)
    def get_table_player_name(self,index):return self.names[index] if 0<=index<len(self.names) else 'Player'
    def get_hand_history_lines(self):
        lines=[f'Hand {self.hand_number}: {self.current_stage.title()}',f'Blinds ${self.small_blind} / ${self.big_blind}']
        for name,action in zip(self.names,[self.player_action_text,*self.npc_action_texts]):
            if action:lines.append(f'{name}: {action}')
        return lines
