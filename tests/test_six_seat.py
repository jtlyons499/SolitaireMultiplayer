import unittest
import json
from room_table import RoomAuthority

class SixSeatTests(unittest.TestCase):
    def make(self, count=6):
        t=RoomAuthority('Host')
        for i in range(1,count):t.join(i,'Human '+str(i))
        t.start();return t
    def finish(self,t,now=0):
        for _ in range(2000):
            if t.game.hand_complete:return now
            actor=t.game.current_actor
            human=next((i for i,s in t.humans.items() if s==actor),None)
            if human in t.connections:t.act(human,'check_call',0,t.revision)
            now+=10000;t.update(now)
        self.fail('Hand never completed')
    def test_six_humans_many_hands(self):
        t=self.make();now=0
        for _ in range(30):
            now=self.finish(t,now)
            self.assertEqual(sum([t.game.player_stack,*t.game.npc_stacks]),30000)
            if sum(s>0 for s in [t.game.player_stack,*t.game.npc_stacks])<2:break
            for identity in list(t.connections):self.assertTrue(t.act(identity,'next_hand',0,t.revision))
        self.assertEqual(len(t.game.npcs),5)
    def test_private_views_all_seats(self):
        t=self.make()
        all_hands=[t.game.player_hand,*t.game.npc_hands]
        for identity,seat in t.humans.items():
            m=t.view(identity)
            self.assertEqual(m['data']['player_hand'],all_hands[seat])
            self.assertTrue(all(not cards for cards in m['data']['npc_hands']))
            self.assertNotIn('deck',json.dumps(m))
            self.assertEqual(len(m['names']),6)
    def test_late_join_no_mid_hand_takeover(self):
        t=self.make(2);before=t.names[:];t.join(9,'Late')
        self.assertNotIn(9,t.humans);self.assertEqual(t.view(9)['type'],'waiting')
        self.assertEqual(t.names,before)
        self.finish(t);before_stacks=[t.game.player_stack,*t.game.npc_stacks]
        t.update(999999)
        self.assertIn(9,t.humans)
        self.assertEqual(before_stacks,[t.game.player_stack,*t.game.npc_stacks])
        self.assertEqual(t.names[t.humans[9]],'Late')
        self.assertEqual(t.view(9)['data']['player_hand'],[]) # no inherited private cards until new deal
    def test_disconnect_folds_then_npc(self):
        t=self.make(3);seat=t.humans[2];t.leave(2)
        self.finish(t);t.update(999999)
        self.assertNotIn(2,t.humans);self.assertEqual(t.names[seat],t.npcs[seat-1]['name'])
        self.assertEqual(sum([t.game.player_stack,*t.game.npc_stacks]),30000)
    def test_lobby_config_and_invalid_actions(self):
        t=RoomAuthority('Host');t.configure(stack=10000);t.configure(seat=3,delta=1);t.join(1,'Guest')
        self.assertFalse(t.act(1,'start',0,t.revision));self.assertTrue(t.act(0,'start',0,t.revision))
        self.assertEqual(sum([t.game.player_stack,*t.game.npc_stacks])+t.game.pot,60000)
        self.assertFalse(t.act(99,'fold',0,t.revision));self.assertFalse(t.act(0,'fold',0,-1))
        self.assertFalse(t.configure(stack=1000))
        lobby=RoomAuthority('Host');lobby.join(1,'Guest');lobby.leave(1)
        self.assertNotIn(1,lobby.humans)
        self.assertEqual(lobby.names[1],lobby.npcs[0]['name'])
    def test_sidepots_allin(self):
        t=self.make();g=t.game
        # Restart a hand with uneven existing bankrolls, preserving total money.
        self.finish(t)
        g.player_stack=500;g.npc_stacks=[1000,2000,3000,8000,15500]
        for identity in list(t.connections):t.act(identity,'next_hand',0,t.revision)
        now=0
        for _ in range(500):
            if g.hand_complete:break
            actor=g.current_actor
            human=next((i for i,s in t.humans.items() if s==actor),None)
            if human is not None:
                stack=[g.player_stack,*g.npc_stacks][actor];bet=[g.player_round_bet,*g.npc_round_bets][actor]
                if not t.act(human,'bet_raise',stack+bet,t.revision):t.act(human,'check_call',0,t.revision)
            now+=10000;t.update(now)
        self.assertTrue(g.hand_complete)
        self.assertEqual(sum([g.player_stack,*g.npc_stacks]),30000)
        self.assertGreater(len(g.last_pot_awards),1)
        for i in t.humans:
            for pot in t.view(i)['data']['last_pot_awards']:
                self.assertTrue(all(0<=s<6 for s in pot['winners']))

import test_relay
from room_session import RoomTable
import time

class SixRelayTests(unittest.TestCase):
    setUp=test_relay.RelayTests.setUp
    tearDown=test_relay.RelayTests.tearDown
    def test_six_clients_and_late_join(self):
        host=RoomTable('Host',True,self.address);self.peers.append(host)
        deadline=time.monotonic()+4
        while not host.code and time.monotonic()<deadline:host.update(0);time.sleep(.01)
        self.assertTrue(host.code)
        clients=[host]
        for i in range(1,3):
            client=RoomTable('Guest '+str(i),False,self.address,host.code);self.peers.append(client);clients.append(client)
        def pump(seconds=1):
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                for c in clients:c.update(int(time.monotonic()*1000))
                time.sleep(.005)
        pump(.5)
        self.assertEqual(len(host.authority.humans),3)
        self.assertTrue(host.act('start'));pump(.3)
        for i in range(3,6):
            c=RoomTable('Late '+str(i),False,self.address,host.code);self.peers.append(c);clients.append(c)
        pump(.4)
        self.assertEqual(len(host.authority.waiting),3)
        self.assertTrue(all(c.message['type']=='waiting' for c in clients[3:]))
        deadline=time.monotonic()+10;now=0
        while time.monotonic()<deadline:
            now+=10000
            for c in clients:c.update(now)
            for c in clients:
                if c.message['type']=='state' and not c.game.hand_complete and c.game.current_actor==0:c.act('check_call')
            if host.game.hand_complete and len(host.authority.humans)==6 and all(c.message['type']=='state' for c in clients):break
            time.sleep(.004)
        self.assertEqual(len(host.authority.humans),6)
        self.assertTrue(host.game.hand_complete)
        extra=RoomTable('Seventh',False,self.address,host.code);self.peers.append(extra)
        deadline=time.monotonic()+3
        while not extra.failed and time.monotonic()<deadline:extra.update(now);time.sleep(.01)
        self.assertTrue(extra.failed);self.assertIn('six',extra.status)
        clients[2].close();clients.remove(clients[2]);pump(.3)
        self.assertEqual(len(host.authority.connections),5)
        self.assertFalse(host.failed)
        host.close();pump(.3)
        self.assertTrue(all(c.failed for c in clients[1:]))
