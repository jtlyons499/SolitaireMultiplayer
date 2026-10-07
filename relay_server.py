"""Room relay: no poker rules or hidden-card state is stored here."""
import argparse
import asyncio
import json
import secrets
import ssl

MAX_LINE = 65536

async def send(writer, message):
    writer.write((json.dumps(message, separators=(',', ':')) + '\n').encode())
    await asyncio.wait_for(writer.drain(), 10)

class RelayServer:
    def __init__(self):
        self.rooms = {}

    async def handle(self, reader, writer):
        room = None
        code = None
        role = None
        try:
            raw = await asyncio.wait_for(reader.readline(), 10)
            request = json.loads(raw)
            if isinstance(request, dict) and request.get('version') == 2:
                from room_relay import handle_room
                await handle_room(self, reader, writer, request)
                return
            if not isinstance(request, dict) or request.get('version') != 1:
                raise ValueError('Unsupported relay protocol')
            role = request.get('type')
            if role == 'create':
                if len(self.rooms) >= 500:
                    raise ValueError('Relay is full')
                while True:
                    code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
                    if code not in self.rooms:
                        break
                room = {'host': writer, 'guest': None}
                self.rooms[code] = room
                await send(writer, {'type': 'room', 'code': code})
            elif role == 'join':
                code = str(request.get('code', '')).upper().strip()
                room = self.rooms.get(code)
                if room is None or room.get('version') == 2:
                    raise ValueError('Room not found or uses a newer game version')
                if room['guest'] is not None:
                    raise ValueError('Room already has two players')
                room['guest'] = writer
                await send(room['host'], {'type': 'paired'})
                await send(writer, {'type': 'paired'})
            else:
                raise ValueError('Choose create or join')
            while True:
                raw = await asyncio.wait_for(reader.readline(), 900)
                if not raw:
                    break
                if len(raw) > MAX_LINE:
                    raise ValueError('Message too large')
                message = json.loads(raw)
                if not isinstance(message, dict):
                    raise ValueError('Invalid message')
                if message.get('type') == 'ping':
                    await send(writer, {'type': 'pong'})
                    continue
                allowed = {'hello', 'state', 'ack'} if role == 'create' else {'hello', 'action'}
                if message.get('type') not in allowed:
                    raise ValueError('Invalid room message')
                target = room['guest' if role == 'create' else 'host']
                if target is not None:
                    await send(target, message)
        except (ValueError, OSError, asyncio.TimeoutError) as error:
            try:
                await send(writer, {'type': 'error', 'text': str(error)[:100]})
            except (OSError, asyncio.TimeoutError):
                pass
        finally:
            # A rejected third join must never remove an existing room.
            if room and writer in (room['host'], room['guest']):
                self.rooms.pop(code, None)
                other = room['guest' if writer is room['host'] else 'host']
                if other:
                    try:
                        await send(other, {'type': 'error', 'text': 'Other player disconnected. Table paused; create a new room.'})
                    except (OSError, asyncio.TimeoutError):
                        pass
                    other.close()
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

async def serve(args):
    context = None
    if args.cert or args.key:
        if not (args.cert and args.key):
            raise ValueError('Supply both --cert and --key')
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.cert, args.key)
    relay = RelayServer()
    server = await asyncio.start_server(relay.handle, args.bind, args.port, ssl=context, limit=MAX_LINE)
    print(f'Relay listening on {args.bind}:{args.port} ({"TLS" if context else "plain TCP"})', flush=True)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bind', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=50008)
    parser.add_argument('--cert')
    parser.add_argument('--key')
    try:
        asyncio.run(serve(parser.parse_args()))
    except KeyboardInterrupt:
        pass
