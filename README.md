# Solitaire Multiplayer — LAN batch

Two humans enter their names and play Texas Hold'em with two NPCs, using temporary $5,000 stacks and $25/$50 blinds. One program hosts the game; the second joins it. No Career, accounts, profiles or saves are involved. Local Practice remains available with three NPCs.

## Install

Extract this replacement batch into the new `SolitaireMultiplayer` folder, replacing matching files. Install the Local Starter batch first; keep your existing assets, data and poker modules. Do not put these files into the original Solitaire project.

```powershell
python -m pip install -r requirements.txt
python main.py
```

Python 3.14 and pygame-ce 2.5.8. No additional networking packages are required.

## First test: two windows on one computer

1. Open two terminals in this project's folder. Run `python main.py` in both.
2. In the first window, enter your name and click **Host Table**.
3. In the second, enter a different name, leave the address as `127.0.0.1`, and click **Join Table**.
4. The table starts once both are connected. Each window displays its human's cards at the bottom and keeps other hands face-down until a legal showdown/all-in reveal.
5. At the end of a hand, both humans click **Ready for next hand** at the top, or Next Hand. The next hand waits for both players.

When running two windows, click the name/address field you want to type into. The Enter key starts Local Practice; use the Host/Join buttons for networking.

## Two computers on the same network

Both computers need the same batch installed. On the host, run `ipconfig` in PowerShell and find the IPv4 address of the active Wi-Fi/Ethernet adapter, commonly `192.168.x.x` or `10.x.x.x`.

The host clicks Host Table. The joining player types that IPv4 address in the Join address field and clicks Join Table. The default port is TCP **50007**. If Windows asks whether Python may communicate on your network, allow it on the private network used for this test. Only the host listens for incoming connections.

This batch supports localhost and LAN connections. It does not provide public internet matchmaking, NAT traversal, invite codes or relay hosting. Those are later steps after local play is verified.

## Table behavior

- The host owns the deck, legal actions, NPC decisions and payouts. The guest sends actions, never replacement game state.
- Guest snapshots contain their own hole cards, public wagers/board/results, and legally revealed opponents' cards. They exclude the deck, private folded hands, AI decisions and memories.
- Both humans can check/call, bet/raise and fold. Existing wager controls work for the human at the bottom of each window.
- Folded humans can watch the rest of the hand; a host fold does not skip the guest's betting. Eliminated humans can spectate remaining hands and still ready them. No new cards are dealt to eliminated seats.
- Both humans ready the next hand. Online auto-deal does not bypass this handshake; the existing auto-deal option applies to Local Practice. The top Ready counter shows who is waiting.
- Host speed settings govern NPC/street timing. A guest's local Options do not change the host's pacing. Opening Options or POT RECAP is local and does not pause the other computer.
- POT RECAP uses seat-relative winner names and awards for either player. It remains optional.
- Online logs show current public actions and blinds; the full private single-player history is not transmitted. Network chat synchronization is not included in this batch.
- Leave table is always available. A lost connection pauses the game and displays a connection message. Return to the lobby and create a new table; reconnect/resume and automatic NPC replacement are not implemented yet.
- Once one seat owns all the chips, the table is finished. Use Leave table for a new session.

The network uses plain TCP JSON on the local network. It is a private-table prototype, without account authentication or encrypted transport.

## Changed files

- `main.py`: name/address lobby, Local Practice / Host / Join, connected table display, leave and ready controls.
- `lan_transport.py`: one-peer background TCP transport and bounded JSON messages.
- `lan_protocol.py`: explicit public snapshots and seat-relative rendering data.
- `lan_table.py`: host authority, two-human actions, validation and NPC scheduling.
- `lan_session.py`: connection/session orchestration.
- `texas_holdem.py`: optional network spectator support, leaving Local Practice behavior intact.
- `tests/test_lan.py`: privacy, projection, rules, settlement and real socket/session tests.

No extra artwork or SFX are required. Existing graphics and Local Starter chip images are reused. All files in the ZIP are complete new/replacement files; no caches or builds are included. No GitHub commits are pushed by this batch.

## Validation

Headless tests exercise real TCP host/client sessions, 35 two-human call/check hands, 20 all-in/fold hands, wrong-turn/stale-action rejection, hidden-card exclusion, guest side-pot mapping, host-fold continuation, eliminated-host spectators and disconnect notification. Existing Local Starter tests remain included and pass. Guest table rendering was inspected at 1366x768. Python files were compiled with Python 3.14.7 / pygame-ce 2.5.8.

Interactive Windows firewall/LAN play and the PyInstaller build still need local verification.

## Optional Windows build

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --contents-directory "." --name "Solitaire Multiplayer" --add-data "assets;assets" --add-data "data;data" main.py
```

Send the entire `dist\Solitaire Multiplayer` folder zipped, not just its executable.

## Internet room-code relay

See [RELAY_SETUP.md](RELAY_SETUP.md) for localhost testing, public server setup,
TLS, and sharing a Windows build. Create Room and Join Room use the relay
address and eight-character room code. No public relay is deployed by this batch.
