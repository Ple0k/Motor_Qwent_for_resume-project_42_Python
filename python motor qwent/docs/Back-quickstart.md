<!-- Modification 2026-10-07: Rewritten as a concise teammate handoff for AI setup, human requests, process results, view delivery and timers. -->

# Motor — quick guide for Back

Updated 7 October 2026. Python 3, standard library only. Examples run from `motor/`; invoking motor.py by absolute path also works. [Full contract](Motor-rm-GPT_formatted.md).

## 1. What changes for games versus AI?

**Back sends only human input. Motor chooses and executes AI actions automatically.** No new AI-turn command or AI timer is required.

The CLI remains:
```text
./motor.py XX I <player1> <player2>
./motor.py XX M <human-mulligan-code> [<second-human-code>]
./motor.py XX P <offered-human-command>
./motor.py XX T
```

Room `XX` is exactly two digits, 00–99. Run only one operation at a time per room, including timeouts.

## 2. Initialize the match

Each player token is **type + fixed seat + deck**:
- Type: `P` human, `I` AI.
- Seat: 1 or 2; identities remain fixed throughout the match.
- Deck: 1 Witcher, 2 Wild Hunt.

At most one AI; AI always receives Witcher, even if its token requests deck 2.

| Match | Initialization | Human's view |
| --- | --- | --- |
| Human P1 Witcher vs AI P2 | `./motor.py 07 I P11 I21` | 071.json |
| AI P1 vs human P2 Wild Hunt | `./motor.py 07 I I11 P22` | 072.json |
| Two humans | `./motor.py 07 I P11 P22` | Each receives its own view |

Successful I returns **0** and creates fresh XXM/XX1/XX2 with mulligan offers. **I replaces all previous contents of that room's three files**; do not use it to resume a game. Motor builds the initial state; Back does not edit JSON or simulate AI.

## 3. Submit mulligans

| Match | Example keeping all human cards |
| --- | --- |
| Human P1, AI P2 | `./motor.py 07 M 15000000000` |
| AI P1, human P2 | `./motor.py 07 M 25000000` |
| PvP | `./motor.py 07 M 15000000000 25000000` |

Use the human's actual offered code. **No AI code or placeholder.** In PvP, collect both human choices before invoking M once; either argument order works.

Mulligan timeout: supply the timed-out seat's keep-all code, retaining the other human's choice. Use `15000000000` for P1 or `25000000` for P2—not a bare 0. T is rejected during Mulligan.

AI replaces Spells/Locations first, then weakest Units, up to its seat limit. If AI is P1, M also executes its opening turn before returning **2** for human P2. Human P1 games return **1**.

## 4. Normal actions and AI progression

Front sends an exact string from its latest Available_Commands. Authenticate the account, verify its fixed player prefix and invoke P. Motor validates legality again.

P supports normal play, Pass Round, End Turn, Concede, Heroic Power and Stratagem. New controls:
- Power: P1 `12000000000000`, P2 `22000000000000`.
- Stratagem: offered action-3 code, with its hand position and destination 5; do not construct it yourself.

Power replaces the normal card play. Stratagem may accompany either. These actions retain the player's priority until explicit End Turn; therefore a successful P can return the **same** human seat again.

Whenever M/P/T gives AI priority, Motor handles AI's actions and End Turn internally, continuing until a human can act or the game ends. If the human passed the round, several AI turns may run in one invocation. **Do not invoke Motor again to “play the AI.”**

## 5. Read the process status, then publish the correct view

Status is the **process exit code**, not stdout JSON. Nonzero can mean success.

| Code | Meaning | Back action |
| --- | --- | --- |
| 0 | Initialization complete; human mulligan choice(s) needed | Send each human its view with offers |
| 1 | Success; human P1 input needed | Send updated human view(s); enable P1 input |
| 2 | Success; human P2 input needed | Send updated human view(s); enable P2 input |
| 3 | Invalid request; no room writes, no automatic defeat | Handle rejection; do not infer cheating/loss or a new state |
| 4 | Internal/state/I/O failure | Cancel match; do not publish potentially partial files |
| 61 | P1 wins | Send final human view(s); record result for the account in seat 1 |
| 62 | P2 wins | Send final human view(s); record result for the account in seat 2 |
| 63 | Draw | Send final human view(s); record draw |

Code 5 is a documented crash classification, **not a guaranteed emitted code**. Detect killed/crashed processes or unexpected termination separately and cancel. Preserve stderr diagnostics. If your process wrapper treats nonzero exits as exceptions, inspect its exit code before deciding it failed.

Files live **beside motor.py**, regardless of Back's working directory:
- XXM.json: full private Motor state; never send to Front.
- XX1.json / XX2.json: send each human only the file matching their fixed seat.
- ai_prediction/XX/<command>.json: private AI predictions; never send these to Front.

**Wait for process completion before reading files.** Motor refreshes all three after each accepted action; intermediate writes are not a network/event stream. Writes are sequential, so failed saving can leave mixed versions. The agreed policy is cancellation, not retry/rollback.

## 6. Game results and new state fields

At Game_End, both active IDs are 0 and command lists are empty. Winner is 1/2 for a winner or 0 for a draw. End_Reason is `Crowns` or `Concede`. Winner 0 in an ongoing game does **not** mean draw.

Both player views now expose:
- `Player_N_Power_Used`: once-game Power consumption.
- `Player_N_Hand_Count`, `Player_N_Deck_Count`, `Player_N_Graveyard_Count` for both seats.
- `Card_has_been_played`: 1 after a normal card or Power; Stratagem alone leaves it 0.

Hand count includes Stratagem; automatic empty-hand passing excludes it. Board_Strength includes its current-round +5 bonus when activated with an own-board unit. Forward Motor's score; do not recalculate from row sums.

Private completed-turn counters in XXM are maintained by Motor for AI timing; Back must not manage them. Last_Command remains private. Supply account/room/deck/AI-mode context through Back's existing match data, since player views omit those details.

## 7. Timers and integration checks

Back alone owns human timers and rejects callbacks from obsolete turns or reused matches under the same room serialization. T takes no actor argument and applies to the current human turn only.

T removes a random non-stratagem hand card if Card_has_been_played is 0, otherwise removes nothing; then ends the turn and runs AI if needed. Start no timers for AI or automatic passed-player turns. Timer duration/reset policy belongs to Back.

Before sharing with Front, test both AI seats: I → human-only M → human P/End Turn → updated human priority; then concession and a normal crown result. Use a fresh test room for this version rather than silently migrating an older match.
