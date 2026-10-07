"""Host/client session facade used by the same Pygame poker screen."""
import queue
import texas_holdem_ui as ui
from lan_transport import LanPeer,PORT
from lan_protocol import ClientGame
from lan_table import HostedTable

def clean_name(value):
    return ''.join(c for c in str(value) if c.isprintable())[:32].strip() or 'Player'

class OnlineTable:
    def __init__(self,name,hosting,address='127.0.0.1',port=PORT,relay=False,code=''):
        self.name=clean_name(name)
        if relay:
            from relay_transport import RelayPeer
            self.peer=RelayPeer(hosting,address,self.name,code)
        else:self.peer=LanPeer(hosting,address,self.name,port)
        self.hosting=hosting;self.seat=0 if hosting else 1
        self.game=ClientGame();self.authority=None;self.status='Waiting for connection…';self.connected=False;self.failed=False;self.pending=False;self.last_sent=-1
        ui.holdem_options_open=False;ui.holdem_chat_history.clear();ui.clear_holdem_manual_bet()
    @property
    def playable(self):return self.connected and self.game.revision>=0 and not self.failed
    @property
    def finished(self):return False
    def close(self):self.peer.close()
    def update(self,now):
        while True:
            try:message=self.peer.inbox.get_nowait()
            except queue.Empty:break
            kind=message.get('type')
            if kind=='disconnected':self.failed=True;self.connected=False;self.status='Disconnected: '+str(message.get('text','Connection ended'))[:100]
            elif kind=='status':self.status=message.get('text','Waiting')
            elif kind=='hello':
                if message.get('version')!=1:self.failed=True;self.status='Incompatible protocol version';self.peer.close();continue
                self.connected=True
                if self.hosting and self.authority is None:self.authority=HostedTable(self.name,clean_name(message.get('name','Guest')))
            elif kind=='state' and not self.hosting:
                self.game.apply(message);self.pending=False;self.status='Connected • Waiting for your turn' if self.game.current_actor!=0 else 'Connected • Your turn'
            elif kind=='ack' and not self.hosting:
                self.pending=False
                if not message.get('ok'):self.status='Action rejected; wait for the latest table state'
            elif kind=='action' and self.hosting and self.authority:
                ok=self.authority.act(1,message.get('action'),message.get('amount',0),message.get('revision'))
                self.peer.send({'type':'ack','ok':ok});self.last_sent=-1
        if self.hosting and self.authority and not self.failed:
            self.authority.update(now)
            self.game.apply(self.authority.view(0))
            if self.last_sent!=self.authority.revision:
                if self.peer.send(self.authority.view(1)):self.last_sent=self.authority.revision
            self.status='Connected • Your turn' if self.game.current_actor==0 else 'Connected • Waiting for other seats'
        return None
    def act(self,action):
        if not self.playable or self.pending:return False
        amount=ui.get_holdem_bet_amount(self.game) if action=='bet_raise' else 0
        if self.hosting:
            ok=self.authority.act(0,action,amount,self.authority.revision)
            if ok:self.last_sent=-1
        else:
            ok=self.peer.send({'type':'action','action':action,'amount':amount,'revision':self.game.revision})
            self.pending=ok
        if ok and action=='next_hand':self.status='Ready for next hand • Both humans must click Next Hand'
        if ok and action=='bet_raise':ui.clear_holdem_manual_bet()
        return ok
