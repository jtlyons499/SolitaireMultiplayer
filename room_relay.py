"""Six-client routing; identities are assigned by the relay, never by guests."""
import asyncio
import json
import secrets
from relay_server import send, MAX_LINE

def name(value):
    return ''.join(c for c in str(value) if c.isprintable())[:32].strip() or 'Player'

async def handle_room(server, reader, writer, request):
    room = None
    code = None
    identity = None
    try:
        if request.get('type') == 'create':
            if len(server.rooms) >= 500:raise ValueError('Relay is full')
            while True:
                code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
                if code not in server.rooms:break
            identity = 0
            room = {'version': 2, 'clients': {0: writer}, 'next_id': 1}
            server.rooms[code] = room
            await send(writer, {'type': 'room', 'code': code, 'identity': 0})
        elif request.get('type') == 'join':
            code = str(request.get('code', '')).upper().strip()
            room = server.rooms.get(code)
            if not room or room.get('version') != 2:raise ValueError('Room not found or uses an older game version')
            if len(room['clients']) >= 6:raise ValueError('Room already has six humans')
            identity = room['next_id'];room['next_id'] += 1
            room['clients'][identity] = writer
            await send(writer, {'type': 'joined', 'identity': identity, 'code': code})
            await send(room['clients'][0], {'type': 'peer_joined', 'identity': identity, 'name': name(request.get('name', 'Player'))})
        else:raise ValueError('Choose create or join')
        while True:
            raw = await asyncio.wait_for(reader.readline(), 900)
            if not raw:break
            if len(raw) > MAX_LINE:raise ValueError('Message too large')
            message = json.loads(raw)
            if not isinstance(message, dict):raise ValueError('Invalid message')
            if message.get('type') == 'ping':
                await send(writer, {'type': 'pong'});continue
            if identity == 0:
                if message.get('type') not in ('lobby', 'state', 'ack', 'waiting'):raise ValueError('Invalid host message')
                target = room['clients'].get(message.pop('target', None))
                if target and target is not writer:await send(target, message)
            else:
                if message.get('type') != 'action':raise ValueError('Invalid guest message')
                message.pop('target', None);message['sender'] = identity
                await send(room['clients'][0], message)
    except (ValueError, UnicodeError, OSError, asyncio.TimeoutError) as error:
        try:await send(writer, {'type': 'error', 'text': str(error)[:100]})
        except (OSError, asyncio.TimeoutError):pass
    finally:
        if room and identity is not None and room['clients'].get(identity) is writer:
            room['clients'].pop(identity, None)
            if identity == 0:
                server.rooms.pop(code, None)
                for other in list(room['clients'].values()):
                    try:await send(other, {'type': 'error', 'text': 'Host disconnected. Room closed.'})
                    except (OSError, asyncio.TimeoutError):pass
                    other.close()
            elif 0 in room['clients']:
                try:await send(room['clients'][0], {'type': 'peer_left', 'identity': identity})
                except (OSError, asyncio.TimeoutError):pass
