import copy,json,random,time,unittest
import pygame
from lan_table import HostedTable
from lan_protocol import ClientGame
from lan_transport import LanPeer
from lan_session import OnlineTable
from standalone_table import load_roster

class LanTests(unittest.TestCase):
 def setUp(self):random.seed(42)
 def test_private_snapshots_and_seat_projection(self):
  table=HostedTable('Host','Guest');g=table.game
  for seat in (0,1):
   message=table.view(seat);data=message['data'];self.assertNotIn('deck',data);self.assertEqual(data['npc_hands'],[[],[],[]])
   self.assertEqual(data['player_hand'],g.player_hand if seat==0 else g.npc_hands[0])
   view=ClientGame();view.apply(message);self.assertEqual(view.player_stack,g.player_stack if seat==0 else g.npc_stacks[0]);self.assertEqual(view.get_table_player_name(0),['Host','Guest'][seat])
   self.assertEqual(json.loads(json.dumps(message)),message)
 def test_two_humans_complete_and_conserve_chips(self):
  for seed in range(35):
   random.seed(seed);t=HostedTable('H','G');g=t.game;now=0
   for step in range(1000):
    if g.hand_complete:break
    if g.current_actor in (0,1) and g.actor_needs_action(g.current_actor):
     self.assertTrue(t.act(g.current_actor,'check_call',0,t.revision))
    now+=10000;t.update(now)
   self.assertTrue(g.hand_complete,f'Seed {seed} stalled at actor {g.current_actor}')
   self.assertEqual(g.player_stack+sum(g.npc_stacks),20000)
   rev=t.revision;self.assertTrue(t.act(0,'next_hand',0,rev));self.assertEqual(g.hand_number,1)
   self.assertTrue(t.act(1,'next_hand',0,rev))
   if sum(stack>0 for stack in [g.player_stack,*g.npc_stacks])>1:self.assertEqual(g.hand_number,2)
 def test_invalid_and_stale_actions_no_mutation(self):
  t=HostedTable('H','G');before=copy.deepcopy(t.view(0))
  self.assertFalse(t.act(0,'check_call',0,-1));self.assertFalse(t.act(0,'cheat',0,t.revision));self.assertFalse(t.act(1,'bet_raise',-100,t.revision))
  self.assertEqual(t.view(0),before)
 def test_host_fold_keeps_guest_round_alive(self):
  t=HostedTable('H','G');g=t.game;g.current_actor=0
  self.assertTrue(t.act(0,'fold',0,t.revision));self.assertFalse(g.hand_complete);self.assertEqual(len(g.community_cards),0)
  self.assertFalse(g.npc_folded[0])
 def test_guest_bet_raise_and_runout_privacy(self):
  t=HostedTable('H','G');g=t.game;g.current_actor=1;g.current_bet=0;g.npc_round_bets=[0,0,0];g.player_round_bet=0
  self.assertTrue(t.act(1,'bet_raise',200,t.revision));self.assertEqual(g.current_bet,200)
  g.player_stack=0;g.player_all_in=True;g.npc_stacks=[0,5000,5000];g.npc_all_in=[True,False,False];g.npc_folded=[False,True,True];g.current_stage='flop'
  self.assertTrue(g.should_reveal_runout_hands());self.assertEqual(t.view(0)['data']['npc_hands'][0],g.npc_hands[0]);self.assertEqual(t.view(0)['data']['npc_hands'][1:], [[],[]])
 def test_real_localhost_transport_and_disconnect(self):
  host=LanPeer(True,name='Host',port=0);guest=None
  try:
   deadline=time.monotonic()+3
   while host.port==0 and time.monotonic()<deadline:time.sleep(.01)
   self.assertNotEqual(host.port,0);guest=LanPeer(False,'127.0.0.1','Guest',host.port)
   hello=False
   while time.monotonic()<deadline and not hello:
    while not host.inbox.empty():hello=host.inbox.get().get('type')=='hello' or hello
    time.sleep(.01)
   self.assertTrue(hello);host.send({'type':'example','value':123})
   received=False
   while time.monotonic()<deadline and not received:
    while not guest.inbox.empty():received=guest.inbox.get().get('value')==123 or received
    time.sleep(.01)
   self.assertTrue(received);guest.close();disconnected=False
   while time.monotonic()<deadline and not disconnected:
    while not host.inbox.empty():disconnected=host.inbox.get().get('type')=='disconnected' or disconnected
    time.sleep(.01)
   self.assertTrue(disconnected)
  finally:
   host.close()
   if guest:guest.close()
 def test_two_live_session_instances(self):
  host=OnlineTable('H',True,port=0);guest=None
  try:
   deadline=time.monotonic()+5
   while host.peer.port==0 and time.monotonic()<deadline:time.sleep(.01)
   guest=OnlineTable('G',False,'127.0.0.1',host.peer.port);now=0
   while time.monotonic()<deadline and (not host.playable or not guest.playable):
    now+=10;host.update(now);guest.update(now);time.sleep(.01)
   self.assertTrue(host.playable);self.assertTrue(guest.playable)
   g=host.authority.game
   while time.monotonic()<deadline and not g.hand_complete:
    now+=10000;host.update(now);guest.update(now)
    actor=g.current_actor
    if actor==0 and g.actor_needs_action(0):host.act('check_call')
    elif actor==1 and g.actor_needs_action(1) and guest.game.current_actor==0 and guest.game.revision==host.authority.revision and not guest.pending:guest.act('check_call')
    time.sleep(.01)
   self.assertTrue(g.hand_complete);self.assertEqual(g.player_stack+sum(g.npc_stacks),20000)
  finally:
   host.close()
   if guest:guest.close()
 def test_guest_side_pot_indexes_and_new_hand_recap(self):
  t=HostedTable('H','G');g=t.game
  g.last_pot_awards=[{'amount':300,'eligible':[0,1,2],'winners':[1],'share':300,'remainder':0,'hand':'Pair'}]
  v=t.view(1);self.assertEqual(v['data']['last_pot_awards'][0]['winners'],[0]);self.assertEqual(v['data']['last_pot_awards'][0]['eligible'],[1,0,2])
  client=ClientGame();client.apply(v);client.recap_open=True;v['data']['hand_number']+=1;client.apply(v);self.assertFalse(client.recap_open)
 def test_busted_host_can_spectate_next_hand(self):
  t=HostedTable('H','G');g=t.game;g.player_stack=0;g.npc_stacks=[10000,5000,5000];g.refresh_busted_state();g.hand_complete=True
  t.act(0,'next_hand',0,t.revision);t.act(1,'next_hand',0,t.revision)
  self.assertEqual(g.hand_number,2);self.assertTrue(g.player_busted);self.assertEqual(g.player_hand,[]);self.assertEqual(len(g.npc_hands[0]),2)
 def test_both_seats_all_in_and_folds(self):
  for seed in range(20):
   random.seed(seed);t=HostedTable('H','G');g=t.game;now=0
   for step in range(1000):
    if g.hand_complete:break
    actor=g.current_actor
    if actor in (0,1) and g.actor_needs_action(actor):
     view=ClientGame();view.apply(t.view(actor))
     action='fold' if seed%4==0 else 'bet_raise' if view.can_player_raise() else 'check_call'
     amount=view.player_stack+view.player_round_bet if g.current_bet else view.player_stack
     self.assertTrue(t.act(actor,action,amount if action=='bet_raise' else 0,t.revision))
    now+=10000;t.update(now)
   self.assertTrue(g.hand_complete);self.assertEqual(g.player_stack+sum(g.npc_stacks),20000)
