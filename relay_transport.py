"""Threaded room-code connection, optionally protected by verified TLS."""
import json
import queue
import socket
import ssl
import threading
import time
from lan_transport import MAX_LINE

class RelayPeer:
    def __init__(self, hosting, address, name, code='',version=1):
        self.version = version
        self.hosting = hosting
        self.address = address
        self.name = name
        self.code = code.strip().upper()
        self.inbox = queue.Queue()
        self.outbox = queue.Queue(maxsize=32)
        self.closed = threading.Event()
        self.socket = None
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def send(self, message):
        try:
            self.outbox.put_nowait(message)
            return True
        except queue.Full:
            return False

    def close(self):
        self.closed.set()
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()

    def run(self):
        try:
            address = self.address.strip()
            secure = address.startswith('tls://')
            address = address.removeprefix('tls://').removeprefix('tcp://')
            host, separator, port = address.rpartition(':')
            if not separator:
                host, port = address, '50008'
            self.socket = socket.create_connection((host, int(port)), timeout=8)
            if secure:
                self.socket = ssl.create_default_context().wrap_socket(self.socket, server_hostname=host)
            self.send({'type': 'create' if self.hosting else 'join', 'version': self.version, 'code': self.code, 'name': self.name})
            self.socket.settimeout(.05)
            pending = b''
            last_ping = time.monotonic()
            while not self.closed.is_set():
                if time.monotonic() - last_ping > 20:
                    self.send({'type': 'ping'})
                    last_ping = time.monotonic()
                while not self.outbox.empty():
                    payload = (json.dumps(self.outbox.get_nowait(), separators=(',', ':')) + '\n').encode()
                    if len(payload) > MAX_LINE:
                        raise ValueError('Message too large')
                    self.socket.settimeout(5)
                    self.socket.sendall(payload)
                    self.socket.settimeout(.05)
                try:
                    chunk = self.socket.recv(8192)
                    if not chunk:
                        raise ConnectionError('Relay disconnected')
                    pending += chunk
                    while b'\n' in pending:
                        raw, pending = pending.split(b'\n', 1)
                        if len(raw) > MAX_LINE:
                            raise ValueError('Message too large')
                        message = json.loads(raw)
                        if not isinstance(message, dict):
                            raise ValueError('Invalid relay message')
                        kind = message.get('type')
                        if kind == 'room':
                            self.code = message['code']
                            self.inbox.put({'type': 'status', 'text': 'Room ' + self.code + ' • Waiting for friend'})
                            if self.version == 2:self.inbox.put(message)
                        elif kind == 'paired':
                            self.send({'type': 'hello', 'version': 1, 'name': self.name})
                        elif kind == 'error':
                            raise ConnectionError(message.get('text', 'Relay error'))
                        elif kind != 'pong':
                            self.inbox.put(message)
                    if len(pending) > MAX_LINE:
                        raise ValueError('Message too large')
                except socket.timeout:
                    pass
        except (OSError, ValueError, UnicodeError) as error:
            if not self.closed.is_set():
                self.inbox.put({'type': 'disconnected', 'text': str(error)[:100]})
        finally:
            self.close()
