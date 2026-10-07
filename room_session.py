"""Main-thread room coordinator; relay routes only explicitly targeted views."""
import queue
from lan_protocol import ClientGame
from lan_session import clean_name
from relay_transport import RelayPeer
from room_table import RoomAuthority

class RoomTable:
    def __init__(self,name,hosting,address,code=''):
        self.name=clean_name(name);self.hosting=hosting;self.identity=0 if hosting else None
        self.peer=RelayPeer(hosting,address,self.name,code,version=2)
        self.authority=RoomAuthority(self.name) if hosting else None
        self.game=ClientGame();self.message={'type':'connecting'};self.status='Connecting to relay…';self.failed=False;self.last_sent=-1;self.pending=False
    @property
    def code(self):return self.peer.code
    def close(self):self.peer.close()
    def update(self,now):
        while True:
            try:m=self.peer.inbox.get_nowait()
            except queue.Empty:break
            kind=m.get('type')
            if kind=='disconnected':self.failed=True;self.status=m.get('text','Disconnected')
            elif kind=='status':self.status=m.get('text','Connecting')
            elif kind in ('room','joined'):
                self.identity=m['identity'];self.peer.code=m['code'];self.last_sent=-1
            elif kind=='peer_joined' and self.hosting:
                self.authority.join(m['identity'],clean_name(m['name']));self.last_sent=-1
            elif kind=='peer_left' and self.hosting:self.authority.leave(m['identity']);self.last_sent=-1
            elif kind in ('lobby','state','waiting') and not self.hosting:self.apply(m)
            elif kind=='action' and self.hosting:
                who=m.get('sender');ok=self.authority.act(who,m.get('action'),m.get('amount',0),m.get('revision'))
                self.peer.send({'type':'ack','target':who,'ok':ok});self.last_sent=-1
            elif kind=='ack':
                self.pending=False
                if not m.get('ok'):self.status='Table changed; try again after the next update'
        if self.hosting and not self.failed:
            self.authority.update(now);self.apply(self.authority.view(0))
            if self.code and self.last_sent!=self.authority.revision:
                sent=True
                for identity in self.authority.connections:
                    if identity:
                        m=self.authority.view(identity);m['target']=identity
                        sent=self.peer.send(m) and sent
                if sent:self.last_sent=self.authority.revision
    def apply(self,m):
        self.message=m;self.pending=False
        if m['type']=='state':self.game.apply(m);self.status='Your turn' if self.game.current_actor==0 else 'Waiting for other seats'
        elif m['type']=='lobby':self.status='Host selects NPCs and starts the table'
        else:self.status=m.get('text','Waiting for next hand')
    def act(self,action,amount=0):
        if self.failed or self.pending:return False
        revision=self.message.get('revision',0)
        if self.hosting:
            ok=self.authority.act(0,action,amount,revision)
            if ok:self.last_sent=-1
        else:
            ok=self.peer.send({'type':'action','action':action,'amount':amount,'revision':revision});self.pending=ok
        return ok
