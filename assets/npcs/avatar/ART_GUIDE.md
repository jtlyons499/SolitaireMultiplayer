# Prospect and prodigy avatar art

Create your own PNG layers on a **512 × 512 pixel canvas**. Keep every layer
aligned to the same face/body positions and preserve transparent backgrounds.
Each prospect's saved choices select a numbered part from every category.

## Exact filenames

Paths below are relative to the project folder containing `main.py`.
Use all numbers `01`, `02`, `03`, `04`, `05`, `06`, `07`, `08`, `09`, `10`.

| Part | First file | Last file | Required to activate custom art? |
|---|---|---|---|
| Base faces | `assets/npcs/avatar/bases/base_01.png` | `assets/npcs/avatar/bases/base_10.png` | Yes |
| Shirts | `assets/npcs/avatar/shirts/shirt_01.png` | `assets/npcs/avatar/shirts/shirt_10.png` | Yes |
| Noses | `assets/npcs/avatar/noses/nose_01.png` | `assets/npcs/avatar/noses/nose_10.png` | Yes |
| Eyes | `assets/npcs/avatar/eyes/eyes_01.png` | `assets/npcs/avatar/eyes/eyes_10.png` | Yes |
| Smiles/mouths | `assets/npcs/avatar/smiles/smile_01.png` | `assets/npcs/avatar/smiles/smile_10.png` | Yes |
| Eyebrows | `assets/npcs/avatar/eyebrows/eyebrows_01.png` | `assets/npcs/avatar/eyebrows/eyebrows_10.png` | Optional |
| Hair | `assets/npcs/avatar/hair/hair_01.png` | `assets/npcs/avatar/hair/hair_10.png` | Optional |
| Glasses | `assets/npcs/avatar/glasses/glasses_01.png` | `assets/npcs/avatar/glasses/glasses_10.png` | Optional |

You can start with just **one usable PNG in each of the five required folders**.
The compositor uses available variants consistently until you finish the full
bank. It retains the intended saved IDs, so adding the remaining variants later
does not reroll the character. A newly installed intended variant takes over
from the temporary available variant.

No empty/sample character PNGs are included. Until those five categories are
ready, the NPC uses a complete combination of your existing player-avatar art
from `assets/ui/profile/avatar/`. The old drawn-in-code prospect portraits have
been removed. Incomplete custom layers are not mixed with the player's older
300 × 360 coordinate system.

## Alignment and drawing order

Use one master base-face canvas as the reference for all variants. Do not crop
an individual feature to its visible content: export the entire 512 × 512
canvas, even if most of it is transparent. No tint is applied to your layers.

Suggested alignment, which you can adjust as a group:

- Center of face: x = 256.
- Face outline: roughly x = 100–412, y = 80–410.
- Eyes: around y = 210; eyebrows around y = 185.
- Nose: around y = 255; smile around y = 300.
- Neck/shoulders: around y = 350; shirt extends to the canvas bottom.
- Keep the face/hair near the center so circular table icons remain readable.

`ALIGNMENT_GUIDE.svg` is an optional editable guide for an art program. It is
not loaded as game art; hide its labels and lines before exporting your PNGs.

Bottom to top: background → base face → shirt → nose → eyes → smile → eyebrows
→ hair → glasses. Bases should contain the face/skin/neck rather than baked-in
eyes, nose or mouth. Keep feature layers transparent around their linework so
they work with different base skin tones. Shirts should not cover the face.

Eyebrows and hair may also be drawn into a base if that suits your style; the
separate optional folders can stay empty. Glasses are optional per character.

## Optional age versions

Common files work at every age. If you want appearances to mature, put the
same numbered filenames inside an age override folder:

| Age | Example base override |
|---|---|
| 0–12 | `assets/npcs/avatar/ages/child/bases/base_01.png` |
| 13–19 | `assets/npcs/avatar/ages/teen/bases/base_01.png` |
| 20–49 | `assets/npcs/avatar/ages/adult/bases/base_01.png` |
| 50+ | `assets/npcs/avatar/ages/veteran/bases/base_01.png` |

The same structure works for shirts, noses, eyes, smiles, eyebrows, hair and
glasses. For example:
`assets/npcs/avatar/ages/teen/hair/hair_07.png`.

An age-specific file replaces only the same numbered common part. Missing age
parts reuse common art. The saved combination does not change on birthdays.

## Updates and finished portraits

Added/edited PNG layers are picked up within about two seconds while the game
is open. Invalid or partly written PNGs are skipped; the compositor uses usable
art or the player's existing avatar until the required files are ready.

A complete portrait at `assets/npcs/<prospect_id>.png` takes precedence over
the layered avatar. Existing finished portraits continue to work; restart the
game after replacing a finished portrait that was already cached.

## Saved choices

New prospects already have complete numbered selections in
`data/npc_prospects.json`. Activated prospects save their choices in
`career.leaderboard_state.<npc_id>.prospect_record.avatar` in the profile.
Old development-batch saves acquire these choices when loaded, without changing
ages, traits, potential, cash or ratings. Changes to the source pool affect
future arrivals; activated characters retain their saved identity.

For example, `base_04`, `eyes_07`, `nose_02`, `smile_10`, `shirt_03`, `hair_06`,
`eyebrows_01` and optional `glasses_05` form one character. Optional values may
be `null`; required parts retain a valid numbered ID. Background layers are
also supported at `assets/npcs/avatar/backgrounds/background_01.png` through
`background_10.png`; the default background selection is `null` (transparent).
