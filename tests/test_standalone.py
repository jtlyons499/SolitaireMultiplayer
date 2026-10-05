import random,unittest,pygame
from standalone_table import StandaloneTable
from standalone_view import TableView
import texas_holdem_ui as ui

class StandaloneTests(unittest.TestCase):
 def setUp(self):
  pygame.init();pygame.display.set_mode((1366,768));random.seed(42)
  ui._holdem_fonts=None
 def tearDown(self):pygame.quit()
 def test_local_table_seats_and_name(self):
  t=StandaloneTable(' John ');self.assertEqual(t.name,'John');self.assertEqual(len(t.game.npcs),3)
  self.assertEqual(t.game.player_stack+sum(t.game.npc_stacks)+t.game.pot,20000)
 def test_complete_hands_chip_conservation(self):
  for seed in range(30):
   random.seed(seed);t=StandaloneTable('Tester');g=t.game;now=0
   for step in range(1000):
    if g.hand_complete:break
    if g.can_player_act_now():
     action='fold' if seed%3==0 else 'check_call'
     self.assertTrue(t.act(action))
    now+=10000;t.update(now)
   self.assertTrue(g.hand_complete,f'Unfinished seed {seed}, actor {g.current_actor}, stage {g.current_stage}')
   self.assertEqual(g.player_stack+sum(g.npc_stacks),20000)
   if not t.finished:self.assertTrue(t.act('next_hand'));self.assertEqual(g.hand_number,2)
 def test_betting_render_and_manual_input(self):
  t=StandaloneTable('Tester');out=pygame.Surface((1366,768));view=TableView(out)
  view.draw(t);pygame.image.save(out,'../standalone_preview.png')
  ui.holdem_manual_bet_active=True;ui.holdem_manual_bet_text=''
  ui.handle_holdem_manual_bet_key(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_1,unicode='1'),t.game)
  self.assertEqual(ui.holdem_manual_bet_text,'1')
 def test_complete_all_in_runout(self):
  t=StandaloneTable('Tester');g=t.game;now=0
  for step in range(2000):
   if g.hand_complete:break
   if g.can_player_act_now():
    ui.holdem_bet_fraction=1
    if g.can_player_raise() or g.get_player_amount_to_call()>=g.player_stack:t.act('bet_raise')
    else:t.act('check_call')
   now+=10000;t.update(now)
  self.assertTrue(g.hand_complete);self.assertEqual(g.player_stack+sum(g.npc_stacks),20000)
 def test_actual_launcher_enters_table_and_quits(self):
  import main
  from unittest.mock import patch
  batches=[[],[pygame.event.Event(pygame.TEXTINPUT,text='John'),pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN)],[],[pygame.event.Event(pygame.KEYDOWN,key=pygame.K_1,unicode='1')],[],[pygame.event.Event(pygame.QUIT)]]
  with patch('pygame.event.get',side_effect=batches):main.main()
 def test_auto_deal_and_recap_pause(self):
  t=StandaloneTable('Tester');g=t.game
  for now in range(10000,1000000,10000):
   if g.can_player_act_now():t.act('fold')
   t.update(now)
   if g.hand_complete:break
  self.assertTrue(g.hand_complete)
  g.recap_open=True;hand=g.hand_number;t.update(2000000);self.assertEqual(g.hand_number,hand)
  g.recap_open=False;t.update(2000001);t.update(2100000);self.assertEqual(g.hand_number,hand+1)
