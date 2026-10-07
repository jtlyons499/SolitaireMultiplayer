"""Readable six-seat table and host lobby; uses existing card/portrait art."""
import pygame
from texas_holdem_ui import get_card_key as card_key

class RoomView:
    def __init__(self,surface,assets):
        self.surface=surface;self.assets=assets;self.buttons=[];self.raise_amount=100;self.hand=-1;self.editing=False;self.amount_text=''
        self.font=pygame.font.Font(None,27);self.small=pygame.font.Font(None,23);self.large=pygame.font.Font(None,38)
    def text(self,text,x,y,font=None,color=(246,237,207)):
        self.surface.blit((font or self.font).render(str(text),True,color),(x,y))
    def button(self,label,rect,action,enabled=True):
        rect=pygame.Rect(rect);pygame.draw.rect(self.surface,(52,111,77) if enabled else (48,61,56),rect,border_radius=7)
        image=self.small.render(label,True,(250,242,213) if enabled else (138,149,141));self.surface.blit(image,image.get_rect(center=rect.center))
        if enabled:self.buttons.append((rect,action))
    def event(self,event,mouse,table):
        if event.type==pygame.TEXTINPUT and self.editing:
            self.amount_text=(self.amount_text+''.join(c for c in event.text if c.isdigit()))[:7]
            self.raise_amount=int(self.amount_text or 0);return True
        if event.type==pygame.KEYDOWN and self.editing:
            if event.key==pygame.K_BACKSPACE:self.amount_text=self.amount_text[:-1];self.raise_amount=int(self.amount_text or 0)
            elif event.key in (pygame.K_RETURN,pygame.K_KP_ENTER):table.act('bet_raise',self.raise_amount);self.editing=False;pygame.key.stop_text_input()
            elif event.key==pygame.K_ESCAPE:self.editing=False;pygame.key.stop_text_input()
            return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for rect,action in self.buttons:
                if rect.collidepoint(mouse):
                    if action=='copy':
                        try:pygame.scrap.put_text(table.code)
                        except pygame.error:table.status='Room code: '+table.code
                    elif isinstance(action,tuple):
                        if action[0]=='npc':table.authority.configure(seat=action[1],delta=action[2])
                        elif action[0]=='stack':table.authority.configure(stack=action[1])
                        elif action[0]=='amount':self.raise_amount=action[1]
                        elif action[0]=='allin':
                            if action[1]<=table.game.current_bet:table.act('check_call')
                            else:table.act('bet_raise',action[1])
                    elif action=='edit':self.editing=True;self.amount_text='';pygame.key.start_text_input()
                    elif action=='raise':table.act('bet_raise',self.raise_amount)
                    else:table.act(action)
                    return True
        return False
    def card(self,card,x,y,w=66,h=92):
        image=self.assets.cards.get(card_key(card),self.assets.back) if card else self.assets.back
        self.surface.blit(pygame.transform.smoothscale(image,(w,h)),(x,y))
    def draw(self,table):
        s=self.surface;s.fill((20,48,36));self.buttons=[]
        self.text('SIX-SEAT HOLD’EM',24,20,self.large)
        self.text('Room '+(table.code or '…'),430,23)
        self.button('Copy code',(650,15,120,38),'copy',bool(table.code))
        self.text(table.status[:95],24,66,self.small)
        if table.failed:
            self.text('Connection ended. Leave and create/join a new room.',230,325,self.large);return
        m=table.message
        if m['type']=='connecting':self.text('Connecting to relay…',440,325,self.large);return
        if m['type'] in ('lobby','waiting'):
            self.text('Room lobby' if m['type']=='lobby' else 'Joining between hands',430,125,self.large)
            for i,seat in enumerate(m['seats']):
                y=190+i*62
                self.text(f"Seat {i+1}  •  {seat['kind']}  •  {seat['name']}",250,y)
                self.text('Connected' if seat['connected'] else 'Disconnected',835,y,self.small)
                if table.hosting and m['type']=='lobby' and seat['kind']=='NPC':
                    self.button('Previous',(1050,y-5,90,36),('npc',i,-1));self.button('Next',(1150,y-5,70,36),('npc',i,1))
            self.text('Starting chips per seat: $'+str(m['starting_stack']),250,585)
            if table.hosting and m['type']=='lobby':
                for j,value in enumerate((1000,5000,10000,25000)):self.button('$'+str(value),(250+j*125,625,112,40),('stack',value))
                self.button('Start table',(860,625,260,50),'start',bool(table.code))
            if m.get('waiting_names'):self.text('Waiting: '+', '.join(m['waiting_names']),250,710,self.small)
            return
        g=table.game
        pygame.draw.ellipse(s,(120,92,55),(160,170,1045,380))
        pygame.draw.ellipse(s,(24,94,59),(176,185,1013,350))
        self.text(f'Hand {g.hand_number} • {g.current_stage.title()} • Blinds ${g.small_blind}/${g.big_blind}',440,272,self.small)
        self.text(f'Pot: ${g.pot if not g.hand_complete else g.last_resolved_pot:,}',570,299,self.large)
        for i,card in enumerate(g.community_cards):self.card(card,490+i*77,345)
        # Viewer always occupies the bottom; physical identity stays attached to labels.
        positions=[(520,553),(55,362),(170,105),(535,105),(1000,105),(1060,362)]
        stacks=[g.player_stack,*g.npc_stacks];hands=[g.player_hand,*g.npc_hands]
        folded=[g.player_folded,*g.npc_folded];actions=[g.player_action_text,*g.npc_action_texts]
        physical=[m['physical_seat']]+[i for i in range(6) if i!=m['physical_seat']]
        for i,(x,y) in enumerate(positions):
            rect=pygame.Rect(x,y,250,190 if i==0 else 155)
            pygame.draw.rect(s,(28,57,44),rect,border_radius=9)
            if g.current_actor==i and not g.hand_complete:pygame.draw.rect(s,(234,193,84),rect,3,border_radius=9)
            seat=m['seats'][physical[i]]
            self.text(g.names[i][:24],x+10,y+7)
            roles=[]
            if g.dealer_index==i:roles.append('D')
            if g.small_blind_index==i:roles.append('SB')
            if g.big_blind_index==i:roles.append('BB')
            self.text(f"${stacks[i]:,} • {seat['kind']} {'/'.join(roles)}",x+10,y+34,self.small)
            self.text(('Disconnected' if not seat['connected'] else actions[i])[:30],x+10,y+59,self.small)
            if not folded[i] and stacks[i]>=0 and (hands[i] or i in g.hand_seat_indexes):
                for j in range(2):self.card(hands[i][j] if len(hands[i])>j else None,x+10+j*(78 if i==0 else 55),y+78,72 if i==0 else 50,100 if i==0 else 70)
            elif folded[i]:self.text('Folded',x+10,y+91,self.small)
            if i>0:self.assets.portrait(g.npcs[i-1],pygame.Rect(x+187,y+83,48,48))
        if g.hand_complete:
            self.text(g.result_text[:100],350,475,self.small)
            ready=m.get('ready_count',0);total=m.get('ready_total',1)
            self.button(f"Ready {ready}/{total}" if m.get('you_ready') else 'Ready for next hand',(865,610,290,55),'next_hand',not m.get('you_ready') and sum(v>0 for v in stacks)>1)
            awards=g.last_pot_awards
            for j,pot in enumerate(awards[:2]):
                winners=', '.join(g.names[i] for i in pot.get('winners',[]))
                self.text(f"Pot {j+1}: ${pot.get('amount',0)} → {winners}"[:85],28,700+j*24,self.small)
        else:
            active=g.current_actor==0 and g.actor_needs_action(0) and not table.pending
            call=g.get_player_amount_to_call();minimum=g.get_minimum_raise_to() if g.current_bet else g.big_blind
            maximum=g.player_stack+g.player_round_bet
            if self.hand!=g.hand_number:self.hand=g.hand_number;self.raise_amount=minimum
            self.raise_amount=min(maximum,max(minimum,self.raise_amount))
            self.button('Fold',(825,555,110,44),'fold',active)
            self.button('Call $'+str(min(call,g.player_stack)) if call else 'Check',(945,555,155,44),'check_call',active)
            canraise=active and (not g.current_bet or g.can_player_raise()) and maximum>g.current_bet
            self.button('Raise to $'+str(self.raise_amount) if g.current_bet else 'Bet $'+str(self.raise_amount),(825,610,275,44),'raise',canraise)
            self.button(('Amount: '+self.amount_text+'|') if self.editing else 'Type amount',(1110,610,230,44),'edit',canraise)
            for j,(label,value) in enumerate((('Min',minimum),('½ pot',max(minimum,g.current_bet+g.pot//2)),('Pot',max(minimum,g.current_bet+g.pot)),('All in',maximum))):
                # A short all-in call remains available even when raising is impossible.
                action=('allin',maximum) if label=='All in' else ('amount',value)
                self.button(label,(825+j*85,670,80,36),action,active)
        if m.get('waiting_names'):self.text('Joining next hand: '+', '.join(m['waiting_names']),24,742,self.small)
