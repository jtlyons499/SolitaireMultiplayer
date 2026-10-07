import asyncio
import queue
import threading
import time
import unittest
from relay_server import RelayServer
from relay_transport import RelayPeer
from lan_session import OnlineTable

class RelayTests(unittest.TestCase):
    def setUp(self):
        self.loop=asyncio.new_event_loop()
        self.thread=threading.Thread(target=self.loop.run_forever,daemon=True)
        self.thread.start()
        self.relay=RelayServer()
        async def start():
            return await asyncio.start_server(self.relay.handle,'127.0.0.1',0,limit=65536)
        self.server=asyncio.run_coroutine_threadsafe(start(),self.loop).result(3)
        self.address='127.0.0.1:'+str(self.server.sockets[0].getsockname()[1])
        self.peers=[]
    def tearDown(self):
        for p in self.peers:p.close()
        async def stop():
            self.server.close()
            await self.server.wait_closed()
            await asyncio.sleep(.1)
            tasks=[t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for t in tasks:t.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
        asyncio.run_coroutine_threadsafe(stop(),self.loop).result(3)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(3)
        self.loop.close()
    def wait(self,p,kind):
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            try:m=p.inbox.get(timeout=.05)
            except queue.Empty:continue
            if m.get('type')==kind:return m
        self.fail('Timed out waiting for '+kind)
    def pair(self):
        host=RelayPeer(True,self.address,'Host');self.peers.append(host)
        self.wait(host,'status')
        guest=RelayPeer(False,self.address,'Guest',host.code);self.peers.append(guest)
        self.assertEqual(self.wait(host,'hello')['name'],'Guest')
        self.assertEqual(self.wait(guest,'hello')['name'],'Host')
        return host,guest
    def test_pair_forward_disconnect(self):
        host,guest=self.pair()
        guest.send({'type':'action','action':'fold','revision':0})
        self.assertEqual(self.wait(host,'action')['action'],'fold')
        host.send({'type':'state','revision':2})
        self.assertEqual(self.wait(guest,'state')['revision'],2)
        guest.close()
        self.assertIn('disconnected',self.wait(host,'disconnected')['text'])
    def test_invalid_and_full_room(self):
        bad=RelayPeer(False,self.address,'Bad','ZZZZZZZZ');self.peers.append(bad)
        self.assertIn('not found',self.wait(bad,'disconnected')['text'])
        host,guest=self.pair()
        third=RelayPeer(False,self.address,'Third',host.code);self.peers.append(third)
        self.assertIn('two players',self.wait(third,'disconnected')['text'])
        guest.send({'type':'action','action':'check_call'})
        self.assertEqual(self.wait(host,'action')['action'],'check_call')
    def test_online_table_hand(self):
        host=OnlineTable('Host',True,self.address,relay=True);self.peers.append(host)
        deadline=time.monotonic()+5
        while not host.peer.code and time.monotonic()<deadline:
            host.update(0);time.sleep(.01)
        self.assertTrue(host.peer.code)
        guest=OnlineTable('Guest',False,self.address,relay=True,code=host.peer.code);self.peers.append(guest)
        deadline=time.monotonic()+10;now=0
        while time.monotonic()<deadline:
            now+=10000;host.update(now);guest.update(now)
            for table in (host,guest):
                if table.playable and not table.game.hand_complete and table.game.current_actor==0:
                    table.act('check_call')
            if host.playable and guest.playable and host.game.hand_complete and guest.game.hand_complete:break
            time.sleep(.003)
        self.assertTrue(host.game.hand_complete)
        self.assertTrue(guest.game.hand_complete)
        self.assertEqual(sum([host.game.player_stack,*host.game.npc_stacks]),20000)
        host.act('next_hand');guest.act('next_hand')
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and guest.game.hand_number==1:
            now+=100;host.update(now);guest.update(now);time.sleep(.01)
        self.assertEqual(guest.game.hand_number,2)
