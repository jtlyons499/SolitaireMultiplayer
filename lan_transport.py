"""One-peer TCP JSON transport. Socket work stays off Pygame's main thread."""
import json,queue,socket,threading,time
PORT=50007
MAX_LINE=65536

class LanPeer:
    def __init__(self,hosting,address='',name='Player',port=PORT):
        self.hosting=hosting;self.address=address;self.name=name;self.port=port;self.inbox=queue.Queue();self.outbox=queue.Queue(maxsize=32);self.closed=threading.Event();self.socket=None;self.listener=None
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def send(self,message):
        try:self.outbox.put_nowait(message);return True
        except queue.Full:return False
    def close(self):
        self.closed.set()
        for sock in (self.socket,self.listener):
            if sock:
                try:sock.close()
                except OSError:pass
    def run(self):
        try:
            if self.hosting:
                self.listener=socket.socket();self.listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);self.listener.bind(('0.0.0.0',self.port));self.port=self.listener.getsockname()[1];self.listener.listen(1);self.listener.settimeout(.2)
                self.inbox.put({'type':'status','text':f'Waiting for player on port {self.port}'})
                while not self.closed.is_set():
                    try:self.socket,_=self.listener.accept();break
                    except socket.timeout:continue
                if self.closed.is_set():return
                self.listener.close()
            else:self.socket=socket.create_connection((self.address,self.port),timeout=5)
            self.socket.settimeout(.02);self.inbox.put({'type':'connected'})
            self.send({'type':'hello','version':1,'name':self.name})
            pending=b''
            while not self.closed.is_set():
                while not self.outbox.empty():
                    message=self.outbox.get_nowait();payload=(json.dumps(message,separators=(',',':'))+'\n').encode('utf-8')
                    if len(payload)>MAX_LINE:raise ValueError('Message too large')
                    self.socket.settimeout(2);self.socket.sendall(payload);self.socket.settimeout(.02)
                try:
                    chunk=self.socket.recv(8192)
                    if not chunk:raise ConnectionError('Other player disconnected')
                    pending+=chunk
                    while b'\n' in pending:
                        line,pending=pending.split(b'\n',1)
                        if len(line)>MAX_LINE:raise ValueError('Message too large')
                        message=json.loads(line)
                        if not isinstance(message,dict):raise ValueError('Invalid message')
                        self.inbox.put(message)
                    if len(pending)>MAX_LINE:raise ValueError('Message too large')
                except socket.timeout:pass
        except (OSError,ValueError,UnicodeError) as error:
            if not self.closed.is_set():self.inbox.put({'type':'disconnected','text':str(error)})
        finally:self.close()
