<!-- Modification 2026-10-07: Rewritten as a concise teammate handoff for current player controls, Power/Stratagem, AI and public state fields. -->

# Motor — quick guide for Front

Updated 7 October 2026. Supports PvP and human versus AI, complete rounds/results, Heroic Power and Stratagem. Other card effects remain deferred. [Full rules](Motor-rm-GPT_formatted.md).

## 1. Input and player identity

Back sends you **only your player view**: XX1 for P1, XX2 for P2. `Client_Player_Number` identifies you. P1/P2 identities never swap when another player starts a later round. Back supplies account, room, deck and AI-mode information; these are not included in the player view.

Build enabled controls from **`Available_Commands`**. Send one exact offered code as a **string**, then wait for Back's updated view. Do not reuse old codes: hand positions and legal actions change.

During turns, only `Active_Player` has input priority. During initial mulligans, both humans choose simultaneously. Against AI, Front submits only the human's choices; Motor plays AI automatically.

## 2. Heroic Power and Stratagem

| | Heroic Power | Stratagem |
| --- | --- | --- |
| Who has it? | Both players, once per game | P1 only; Witcher card 126 or Wild Hunt card 152 |
| Effect | Draw one card from the deck | If you have a unit on your board, +5 to your board score for this round |
| Empty deck/board | Empty deck: draw nothing, still consume Power | No unit: consume Stratagem with no effect |
| Timing | Instead of your normal card play | Before or after your normal card **or** Power, before End Turn |
| Enables End Turn? | Yes | No, not by itself |
| Blocks Pass Round? | Yes | Yes |
| Where does it go? | Not a hand card | Removed from the game, **not** placed in graveyard |
| Tracking | `Player_N_Power_Used` | Its disappearance from P1's hand; use offered commands |

**One normal card OR Heroic Power per turn, never both.** Stratagem can accompany either. After the normal card/Power, End Turn is available and any remaining Stratagem may still be used. Concede remains available while you have priority.

Stratagem does **not** boost an individual unit or row. Render `Player_N_Board_Strength` directly: it can be **5 higher than the two row totals combined**. The bonus survives this round only; it resets before the next round. Using Stratagem on an empty board does not grant a bonus when a unit enters later.

A hand containing only Stratagem counts as empty for automatic passing. An unused Stratagem stays in hand between rounds.

## 3. Commands to recognize

Use the actual offered code, rather than constructing one from this table.

| Action | P1 | P2 |
| --- | --- | --- |
| Pass Round | `10000000000000` | `20000000000000` |
| Concede | `11000000000000` | `21000000000000` |
| Heroic Power | `12000000000000` | `22000000000000` |
| End Turn | `16000000000000` | `26000000000000` |

Ordinary codes have 14 digits: `P A CCC ZNN Z00 TTT`: player, action, card ID, source zone/position, destination zone/no position, target. Action **3** plays a normal card or Stratagem. Zones: 2 hand, 3 front row, 4 back row, 5 graveyard. Current targets are always `000`; row placement position is `00`.

Examples, valid only when offered:
- `13101201300000`: P1 plays card 101 from hand position 01 to the front row.
- `13126211500000`: P1 uses Stratagem 126 from hand position 11. Its command uses destination 5 like a spell, **but Motor removes it from the game**.

Mulligans: P1 may return up to 3, P2 up to 2. Codes are `15XXXYYYZZZ` / `25XXXYYY`, with unused `000` slots **first**, then distinct selected full card IDs in **ascending order**.
- Keep all: P1 `15000000000`; P2 `25000000`.
- Return P1 card 101: `15000000101`.
- Return P1 cards 101 and 105: `15000101105`.

## 4. New and important state fields

Here `N` means **1 or 2**. Both players' counts and Power-use flags are visible in each view.

| Field | Type / meaning |
| --- | --- |
| `Player_N_Power_Used` | Boolean; true once Power is consumed, stays true across rounds |
| `Player_N_Hand_Count` | Integer; includes Stratagem while it is in hand |
| `Player_N_Deck_Count` | Integer; cards remaining in draw deck (“library”) |
| `Player_N_Graveyard_Count` | Integer; excludes consumed Stratagem and AFK-removed cards |
| `Card_has_been_played` | 0/1 for the current turn; 1 after a normal card **or Power**, not Stratagem |
| `Available_Commands` | Your currently legal string codes; inactive seat has an empty list |
| `Game_Phase`, `Mulligan` | Current interaction state: Mulligan, Turn or Game_End |
| `Active_Player`, `Active_Opponent` | Current actor/opponent; both 0 at Game_End and initial Mulligan |
| `Round_number`, `Turn_number` | Round and global turn count; the latter includes automatic passed-player turns |
| `Player_N_has_passed`, `Player_N_Crown` | Round-pass flag and crowns |
| `Winner`, `End_Reason` | Final result, interpreted only with Game_Phase = Game_End |
| `Last_Phases` | Diagnostic trace of the latest operation; not extra input opportunities |

Existing lists: your `Player_N_Hand`, both players' Front_Row, Back_Row and Graveyard. Existing scores: Front_Row_Strength, Back_Row_Strength and Board_Strength.

**Not supplied:** opponent hand IDs, shuffled decks, `Last_Command`, private round bonus/Stratagem flags, AI completed-turn counters, or individual dynamic Card_ID records. Per-card Current_Strength/Boosted/Hurt rendering needs a future view extension; this Stratagem requires only the published board score.

## 5. Passing, AFK, AI and game end

- **End Turn** follows a normal card or Power. **Pass Round** is available only before taking an action that turn; no more actions that round afterward.
- Empty normal hands automatically pass at their own turn start. Rounds 2/3 draw up to three cards first. Passed-player automatic turns require no UI input.
- Back owns timers. On turn expiry, Motor removes a random normal hand card only if neither a normal card nor Power was used, then ends the turn. Stratagem alone does not prevent this penalty. Removed cards do not enter graveyard.
- Mulligan timeout keeps the timed-out player's hand; Back supplies its keep-all code.
- AI updates arrive through Back after Motor finishes processing. Do not request AI choices, run an AI timer or interpret intermediate file writes as animations.
- Higher board score earns one crown; a round tie gives one each. Reaching two crowns ends the game. At `Game_Phase="Game_End"`, Winner 1/2 identifies the winner; Winner 0 means draw. End_Reason is `Crowns` or `Concede`. Disable input; final commands are empty.

Frost fields remain present, but damage/weather creation effects are deferred. Locations currently go to graveyard like spells, without effects; do not render a persistent Location effect yet.
