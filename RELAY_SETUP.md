# Room-code poker

Extract this batch over the LAN batch. Existing art and requirements stay in place.

## Test on your own computer

Open a terminal in SolitaireMultiplayer and run:

```powershell
.\.venv\Scripts\python.exe relay_server.py --bind 127.0.0.1
```

Leave it running. Launch `main.py` in two other terminals. In both windows set
Relay address to `127.0.0.1:50008`. In the first, enter your name and click
Create Room. The waiting screen displays an eight-character code. In the second,
enter another name, that code, and click Join Room.

Both humans must click Ready after each hand. Leave Table closes the room.
If someone loses their connection, play pauses and the room closes; create a
new room to start again. Reconnection and restoring a dropped table are not
implemented. LAN and Local Practice buttons still work.

## Let a friend join over the internet

The relay must run on a publicly reachable computer/server. Running it on your
home PC with no network configuration does not make it internet-accessible.
The relay needs Python only, not Pygame, art, or the entire game repository.
Upload `relay_server.py` to that server and start it:

```sh
python3 relay_server.py --port 50008
```

Allow incoming TCP port 50008 in the server's firewall/network settings.
Both players put `tcp://YOUR_SERVER_ADDRESS:50008` in Relay address, then use
Create Room / Join Room. Players do not need router port forwarding when the
relay is hosted on a public server. This is a raw TCP service, not an HTTP
website; use hosting that supports an exposed TCP port.

For encrypted public connections, obtain a valid certificate for the server's
DNS name and start:

```sh
python3 relay_server.py --port 50008 --cert /path/fullchain.pem --key /path/privkey.pem
```

Clients then enter `tls://YOUR_SERVER_DNS_NAME:50008`. Certificate verification
is enabled; a self-signed certificate is not accepted by default. Plain `tcp://`
connections are unencrypted. Keep initial unencrypted tests on localhost/LAN.
The relay operator can inspect forwarded data; the game host remains trusted to
run the rules and deal fairly. Room codes are access tokens: share them only
with your friend. No accounts, career saves, or real money are involved.

The relay has a 500-room limit, 64 KiB message limit, handshake timeouts and
idle connection cleanup. Clients send keepalives. It forwards separate player
views rather than the host's full deck/state. This prototype has no persistent
rooms, matchmaking, reconnect, or abuse-management dashboard.

## Share a Windows build

Build from the project with your existing art:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --contents-directory "." --name "Solitaire Multiplayer" --add-data "assets;assets" --add-data "data;data" main.py
```

Zip the ENTIRE `dist\Solitaire Multiplayer` folder for your friend. The relay
runs separately on the server; it is not started by the game executable.
This batch does not deploy a server or provide a public relay address.

## Checks

```powershell
python -m unittest discover -s tests
```
