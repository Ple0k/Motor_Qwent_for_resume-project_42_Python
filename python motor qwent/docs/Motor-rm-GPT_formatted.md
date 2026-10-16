<!-- Modification 2026-10-07: Implemented automatic AI, revised mulligans, isolated predictions and documented private round counters. User backup completed. -->

<!-- Modification 2026-10-07: Implemented approved Power/Stratagem/counts; recorded AI specification and mandatory user backup checkpoint. -->

<!-- Modification 2026-09-29: Documented user-approved three-digit targeting; runtime behavior unchanged. -->

<!-- Modification 2026-09-27: User approved keeping Last_Command exclusively in XXM; updated player-view documentation. -->

# Gwent Motor — Rules and Integration Guide

<!-- Modification 2026-09-27: Implemented passing, AFK and crown outcomes; documented approved pseudo-turns, Back-owned timers, retained stratagem and cancellation after partial saves. -->

<!-- Modification 2026-09-27: Recorded confirmed passing/AFK/round rules, explained existing tracking and pending saving/timer decisions, and added teammate quick guides. Documentation only; these future features are not implemented by this edit. -->

Short integration guides: [Back quickstart](Back-quickstart.md) and [Front quickstart](Front-quickstart.md). Communication tasks remain in [todo.md](../../todo.md); creating these guides does not mean teammates have been notified.

Python game engine for the team's custom Gwent-inspired game in **ft_transcendence**.

**Documentation updated:** 7 October 2026.  
**Current milestone (confirmed):** a complete two-human-player game using cards without effects.  
**Status:** complete vanilla PvP match loop implemented: initialization, mulligans, normal play, End Turn, Concede, passing, AFK, round draws/scoring and crown wins/draws. Heroic Power, Stratagem and public counts are now implemented. AI turns and predictions are implemented; other card effects and frost damage remain deferred.

<!-- Modification 2026-09-27: Implemented turn publication checks, explicit End Turn and concession; added stable phase-step labels, new state fields and the Turn flow sheet. Confirmed simultaneous mulligans and own-turn frost windows with the user. -->

<!-- Modification 2026-09-27: Added M command behavior, AI mulligan priorities, first-turn state, error semantics, future effect hooks, and the flow sheet. -->

See [Mulligan flow sheet](Mulligan-flow.md) for the complete request flow, state changes, examples, and Front/Back error cases.
See [Turn flow sheet](Turn-flow.md) for current priority, command formats, phase order and turn error cases.

<!-- Modification 2026-09-27: Linked the canonical prioritized backlog and its maintenance rule. -->

The root [todo.md](../../todo.md) tracks implementation work, known problems and missing logic decisions by group and priority. Update it with every code change, even without an explicit reminder.

<!-- Modification 2026-09-26: Confirmed guide precedence, vanilla milestone, Motor-generated command lists, mulligan encoding, and automatic passing at empty-hand round starts. Updated related interface notes and acceptance checks. -->

**Source of truth:** this formatted guide takes precedence over `Motor-rm.md` wherever they differ. The original notes remain a reference for details not superseded here. For Motor development, assume Front and Back correctly fulfill their agreed responsibilities.

This guide is for the Motor developer, frontend/backend teammates, and evaluators. It describes the engine's scope, rules, state, and command interface. It is a component README, not a replacement for the project's root README, installation guide, database schema, module accounting, or required team-role documentation.

## Contents

1. [Scope and development milestones](#1-scope-and-development-milestones)
2. [Architecture and responsibilities](#2-architecture-and-responsibilities)
3. [Base game rules](#3-base-game-rules)
4. [Command-line integration](#4-command-line-integration)
5. [Player commands](#5-player-commands)
6. [Game data and state](#6-game-data-and-state)
7. [Validation, timeouts, and failures](#7-validation-timeouts-and-failures)
8. [Deferred mechanics](#8-deferred-mechanics)
9. [Evaluation and module planning](#9-evaluation-and-module-planning)
10. [Remaining decisions](#10-remaining-decisions)
11. [Verification checklist](#11-verification-checklist)
12. [Team and project background](#12-team-and-project-background)
13. [Phase order and checks](#13-phase-order-and-checks)

<!-- Modification 2026-09-27: Updated implementation inventory, player-view construction, initialization fields, command examples, test coverage, and next development step. -->

## 1. Scope and development milestones

### Current implementation and files

Initialization (`I`) creates a fresh Motor state and both player views with initial mulligan choices. `M` validates all human submissions against those saved views, chooses the AI's returns if needed, resolves both players together, and prepares round 1 with Player 1 active.

| File | Current purpose |
| --- | --- |
| `motor.py` | Dispatch I/M/P/T, initialize rooms, build views and publish all three room files |
| `ai.py` | AI action priority, independent card projections and scoped prediction cleanup |
| `test_ai.py` | Fourteen tests covering policy, predictions, private counters, full matches, CLI and cleanup |
| `mulligan.py` | Validate initial room state and submitted codes, choose AI returns, and resolve mulligans |
| `game_state.py` | Refresh locations, strengths, faction flags, Boosted/Hurt and frost totals before publication |
| `turns.py` | Turn commands, passing/pseudo-turns, AFK, round transitions and match results |
| `motor_game_state_template.json` | Base Motor state; 102 card records before selecting decks |
| `player1_game_state_template copy.json` | Player 1 view template; the filename includes ` copy` |
| `player2_game_state_template.json` | Player 2 view template |
| `library.json` | Card catalogue with 102 records; not read by the initializer, which uses the Motor template's card data |
| `test_motor.py` | Six initialization tests, including the executable CLI |
| `test_mulligan.py` | Nine mulligan tests, including AI, rejected inputs, preserved files, and CLI status codes |
| `test_turns.py` | Twelve turn tests covering priority, cards, checks, frost windows and concession |
| `test_rounds.py` | Seventeen tests covering passing, AFK, rounds, complete results, CLI, room isolation and interrupted saves |
| `readme/Mulligan-flow.md` | Flow sheet and failure behavior for Front/Back integration |
| `readme/Turn-flow.md` | Turn flow, stable step labels, ordinary command layout and current limits |
| `archive/2026-09-26-before-initializer/` | Original catalogue and Motor template before removing P2 stratagems |
| `readme/GPT.md` | Collaboration preferences and continuation notes |

Paths in this table are relative to the `motor` directory. The original `Motor-rm.md` remains historical reference; this formatted guide is authoritative.

After M, P1's stratagem joins its hand. Motor enters Round_Start → Turn_Start → Turn, sets round/turn 1 and gives P1 priority. Normal plays keep priority; explicit End Turn switches players. Only the active player receives commands, always including Concede. All publications refresh XXM and rebuild XX1/XX2 first. Passing, AFK and round-based wins/draws now complete that loop. AI priority now resolves automatically until a human can act or the match ends.


The game is a custom adaptation inspired by both The Witcher 3's Gwent and standalone Gwent. This project's rules take precedence over either original game's rules.

### First playable milestone: vanilla cards

Implement a complete match with:

- Two human players and two fixed deck choices.
- Shuffled decks, starting hands, and initial mulligans.
- Unit placement and board strength calculation.
- Spells played from hand directly into the graveyard, with no effect.
- Turn progression, passing a round, scoring, and match results.
- Timeout handling and surrender.
- A complete internal state and a filtered JSON view for each player.
- Motor-generated legal commands validated again on receipt.

Card descriptions and targeting metadata are currently placeholders. Missing effects are deliberately outside this milestone. Location cards are played and discarded to the graveyard like spells for now.

### Later milestones

1. Power/Stratagem/counts checkpoint was backed up by the user.
2. Requested AI is implemented and tested; next verify team integration.
3. Defer general card effects, targeting, persistent Locations and weather damage until after vital deadline features.
4. Complete remaining integration and presentation work as prioritized by the user.

Exact sequencing after the vanilla milestone may change. AI strategy and complete effect descriptions do not block the base turn engine.

## 2. Architecture and responsibilities

| Component | Technology | Responsibility |
| --- | --- | --- |
| Front | Team frontend; framework not specified here | Display the player's view, present legal actions, submit a selected command, and prevent multiple pending submissions. |
| Back | NestJS / TypeScript, with Prisma | Authenticate users, map accounts to match players, manage rooms and timers, invoke Motor, serialize requests for each room, and deliver player views. |
| Motor | Python | Own the game rules and full state, generate and validate legal commands, apply actions, calculate results, and produce both player views. |

### Request cycle

1. Back authenticates the sender and identifies their player in the match.
2. Back invokes Motor with an initialization, mulligan, player-action, or timeout command.
3. Motor loads or creates the room state and validates the request.
4. Motor applies the action and resolves the necessary game transitions.
5. Motor writes the full state and the two player views, then reports a result code.
6. Back sends each player only their own view and enables the appropriate next input.

The account identity established by Back is authoritative. A player identifier inside a client command must agree with that identity.

**Concurrency policy:** never run two Motor operations against the same room at the same time. Different rooms may progress independently. Back must enforce this across all workers that can invoke Motor.

## 3. Base game rules

### Decks and identity

Each deck contains 25 cards. Each seat now has the same once-per-game draw-one Heroic Power, replacing its normal play that turn. Stratagems are separate from the 25-card draw deck.

| Deck code | Deck | Card short IDs | Associated stratagem short ID |
| --- | --- | --- | --- |
| `1` | Witcher | `01–25` | `26` — Pirouette |
| `2` | Wild Hunt | `27–51` | `52` — Hen Ichaer Power |

Back randomly assigns the initial starting player as **Player 1** and the other as **Player 2**. These identities remain fixed throughout the match, even when a different player starts a later round.

### Setup and initial mulligan

1. Shuffle each selected deck.
2. Draw 10 cards for each player.
3. Player 1 may replace up to three cards; Player 2 may replace up to two.
4. Set the selected cards aside, draw the same number of replacements, and shuffle the set-aside cards back into the deck.
5. Append P1's stratagem to its hand (11 total entries) and begin round 1, turn 1 with Player 1.

A player may keep their entire starting hand. A mulligan timeout keeps that player's current hand. There are no mulligans between rounds.

### Playing a turn

- Normally, a player may play one card from their hand.
- A unit enters a chosen board row and contributes its current strength to that player's score.
- In the vanilla milestone, playing a spell or Location card moves it directly to the graveyard without an effect.
- A player may voluntarily end their turn only after playing a normal card or using Heroic Power.
- After a normal card play, wait for explicit End Turn or Concede. This confirmed rule supersedes the earlier automatic end-of-turn rule.
- If the opponent has passed the round, the remaining player continues taking normal turns until they also pass. The passed player still receives automatic effect-only pseudo-turns, described below.
- At the start of the player's own turn, an empty normal-card hand automatically passes the round. At a new round, draw first; a stratagem-only hand counts as empty.

There is no hand-size limit and no row-size limit.

Current priority is exclusive during turns, with simultaneous mulligans retained as the setup exception. Units are appended to the chosen row; no chosen placement position or positional effects are used. `Card_has_been_played` resets to 0 at turn start and becomes 1 after a Unit/Spell/Location is played from hand. Heroic Power also sets it, replacing the normal play; Stratagem does not. Concede immediately ends the game; automatic empty-hand passing does not open an input window.

### Passed players and pseudo-turns

Passing removes the right to take player actions for the rest of the round; it does not stop turn-triggered effects. While the opponent has not passed, the passed player still receives automatic **pseudo-turns** in the turn sequence. These apply new-turn effects, including frost damage and its duration decrease, without requesting a command from Front. The player remains passed and cannot play cards or use powers.

An empty normal-card hand sets the round-pass flag at that player's next turn start, not immediately at End Turn or timeout removal. Once both players have passed, resolve the round rather than continuing pseudo-turns. At the start of a new round, after drawing, a player whose normal hand is still empty automatically passes without receiving an input turn. Pseudo-turns increment the global counter, shift only their owner's five-own-turn damage history and decrement that owner's frost durations. Actual frost damage/effects remain deferred.

### Three different ways to stop playing

| Event | Effect on the current turn | May the player act again this round? | Card penalty |
| --- | --- | --- | --- |
| Pass the round | Stop taking player actions; automatic pseudo-turn effects continue while the opponent has not passed | No | None |
| End turn | Finish the current turn normally | Yes, unless automatically passed | None |
| Timeout / forced turn end | End the current turn | Yes, unless automatically passed | Remove one random hand card only if no card was played this turn |

A player may pass the round when they have played nothing during their turn. Using Heroic Power or Stratagem also prevents passing for that turn.

**Implemented timeout rule:** inspect `Card_has_been_played`. At 0, remove one random normal hand card, excluding the stratagem, then end the turn. At 1, only end the turn. Retain the removed card's record with `Exist: false` and `Location: "0000"`, as approved. Automatic empty-hand passing belongs at the player's turn start. The flag already resets to 0 at every new turn and becomes 1 on normal card play; T processing uses this flag.

### End of round

A round ends when both players have passed.

- Each player's score is the sum of unit strength on their front and back rows plus their current-round board bonus.
- The higher score earns one crown.
- A tied score gives one crown to each player.
- Check the match result after awarding crowns to both players.

Immediately after awarding crowns, check whether either or both players have reached two crowns. If so, end the match directly, before cleanup or drawing. Only if continuing, move all vanilla board units to the graveyard and reset their strength to base. Discard frost state/durations, but preserve each player's five-own-turn frost damage history. Later retained cards or persistent weather may override cleanup; these effects are deferred. An unused stratagem remains in hand between rounds.

### Starting the next round

If the match is still ongoing:

- Each player draws up to three cards, limited by the number remaining in their deck.
- The previous round's winner starts.
- After a tied round, the player who did not start that round starts the next one.
- Implemented XXM tracking: `Round_Starting_Player` and `Previous_Round_Starting_Player`, independent of the currently active player. Both start at 0; round 1 sets the current starter to 1.
- Clear the previous round-pass flags, then automatically pass any player whose hand is empty after drawing.
- If only one player has cards, that player receives the next input turn; the passed player follows the pseudo-turn rules.
- If both players have empty hands, resolve the round immediately using the normal scoring and match-result rules, without requesting input.

### End of match

| Crown result | Match result |
| --- | --- |
| `2–0` or `2–1` | Player 1 wins |
| `0–2` or `1–2` | Player 2 wins |
| `2–2` | Draw |

Surrender gives the opponent the victory. A Motor crash or internal failure cancels the game under the current failure policy. Cancellation is distinct from a draw.

## 4. Command-line integration

Motor is invoked through commands and exchanges state through JSON files. Initialization is implemented in `motor/motor.py` using Python 3 and its standard library (no extra dependencies). Run `./motor.py 07 I P11 P22` from the `motor` directory, or invoke that script by its path from Back's working directory. Templates and output files are resolved beside the script.

<!-- Modification 2026-09-26: Documented the first initializer, AI deck normalization, output behavior, stratagem storage, tests, and leading-zero mulligan slots. -->

Initialization replaces all contents of `07M.json`, `071.json`, and `072.json` using fresh templates. Invalid arguments are rejected before changing those files. Successful initialization exits with code `0`; invalid arguments with `3`; handled file/template errors with `4`. Errors are printed to stderr. All three files are prepared in memory before writing, but the three writes are not one atomic transaction; Back must discard outputs after a failed invocation.

P1's selected stratagem is retained in Motor state as `Card_126` or `Card_152`, with `Exist: true`, `Location: "0000"`, and a `Player_1_Stratagem` ID during mulligans. After M, it is appended to P1's hand and its location becomes `1211`. Activation now uses the spell-style action 3 command; see the Power/Stratagem checkpoint below. The other P1 stratagem and unused deck entries are omitted. P2 stratagem entries `Card_226` and `Card_252` were removed from the source catalogue and Motor template; originals are preserved in `motor/archive/2026-09-26-before-initializer/`.

Each deck is independently shuffled: the first ten IDs form the hand, the remaining fifteen form the stored deck. Positions in those lists determine `PZNN` locations; deck position 01 retains the documented bottommost convention. The selected 50 draw cards have `Exist: true`; with P1's stratagem, the Motor output has 51 card records. Initialization sets `Mulligan: true` and `Game_Phase: "Mulligan"`; `Round_number`, `Active_Player`, and `Active_Opponent` remain `0` during this simultaneous-choice phase. Roach/Winter Queen deck-presence flags are updated from the actual shuffled decks. Player views copy matching fields from the supplied player templates, then add `Available_Commands`; they do not copy Motor-only fields or hidden card records. JSON change notes use a `_comment` string, keeping the files valid JSON.

Run all checks from the project root with `python3 -m unittest discover -s motor -p 'test_*.py'`. I, M, P (normal play, Pass Round, End Turn, Concede) and T are implemented.

### Initialize a match

```text
./motor.py XX I A1B C2D
```

| Field | Meaning |
| --- | --- |
| `XX` | Room number, `00–99` |
| `I` | Initialize |
| `A`, `C` | Player type: `P` for human, `I` for AI |
| `1`, `2` | Fixed player identity |
| `B`, `D` | Deck code: `1` for Witcher, `2` for Wild Hunt |

Example: two humans, Player 1 using Witcher and Player 2 using Wild Hunt:

```text
./motor.py 07 I P11 P22
```

Initialization accepts at most one AI player. An AI always receives Witcher, including when its input token requests deck 2. Its mulligan and subsequent turn choices are made internally. If AI is P1, M resolves its opening turn before returning human P2 priority.

### Submit mulligans

```text
./motor.py XX M <player_1_mulligan> <player_2_mulligan>
```

This two-command form is for PvP. With one AI, send only the human's complete code: `./motor.py XX M <human_mulligan>`. Do not send an AI placeholder. Human codes can arrive in either argument order because each code contains its player prefix.

Back collects all human choices before invoking Motor once. If a human times out, Back can supply that player's offered keep-hand code and retain the other's completed choice; T is rejected during Mulligan; use the complete offered zero-return code for that seat, not a bare `0` argument.

Before changing either hand, Motor verifies the saved room's initial state, confirms that each saved player view agrees with that state, and checks that each human code is in that view's `Available_Commands`. A bad request returns 3 without writes; missing/corrupt/inconsistent state returns 4. All accepted choices are applied together.

For each player, draw replacements from the existing deck first, remove selected hand cards, append replacements, return selected cards to the deck, and shuffle that deck. Zero returns preserve that player's deck order. Deck position 01 is bottommost, so draws use the last list element. Refresh locations and cached deck flags, clear mulligan offers, and write all three files.

AI now returns Spells and Locations first, then Units ordered by catalogue Strength (weakest first), up to three for P1 or two for P2. Equal priorities use ascending card ID. This replaces the earlier Roach-first heuristic. Human zero-return mulligans still preserve deck order.

The arguments are the complete mulligan command codes generated by Motor and included in each player's game state:

| Player | Command format | Meaning |
| --- | --- | --- |
| Player 1 | `15XXXYYYZZZ` | Player `1`, action `5`, then three three-digit card slots |
| Player 2 | `25XXXYYY` | Player `2`, action `5`, then two three-digit card slots |

Each slot contains the full ID of a card selected from that player's current hand, or `000` for an unused slot. Unused slots come first; selected IDs follow in ascending order. Nonzero selections must be distinct. Player 1 may replace up to three cards and Player 2 up to two. Motor lists all permitted mulligan selections as complete command codes; Front submits a listed choice.

Examples:

- Player 1 keeps the whole hand: `15000000000`.
- Player 1 replaces card `101` only: `15000000101` (if that card is in hand).
- Player 1 replaces cards `101` and `105`: `15000101105`.
- Player 1 replaces cards `101`, `105`, and `110`: `15101105110`.
- Player 2 replaces card `227` only: `25000227`.
- All selected cards in these examples must be in the submitting player's hand.
- Player 2 keeps the whole hand: `25000000`.
- Player 2 replaces cards `227` and `230`: `25227230` (if both are in hand).

For both players keeping their hands:

```text
./motor.py 07 M 15000000000 25000000
```

Motor generates each selection once, without permutations: for a ten-card hand, P1 receives 1 + 10 + 45 + 120 = 176 commands, and P2 receives 1 + 10 + 45 = 56. The player/action prefix remains even when all card slots are zero.

Do not add another player prefix around these complete codes. AI codes/placeholders are not accepted as input to M.

### Submit a player action

```text
./motor.py XX P <command>
```

`P` identifies a player-action request. `<command>` is a complete code from the legal-command list Motor provided in the player's game state. Back authenticates the sender and ensures that the player prefix in the selected command belongs to that sender before invoking Motor. Motor validates the code against the current state. No additional actor argument is specified by this CLI contract.

For example P1 Pass Round is `10000000000000`, P2 Pass Round is `20000000000000`, P1 Concede is `11000000000000`, and P1 End Turn is `16000000000000`. End Turn is offered only after a normal card play or Heroic Power. A successful play keeps that player's priority; End Turn returns the next player's status. Both player views are rebuilt before every successful return, including concession.

### Signal timeout

```text
./motor.py XX T
```

`T` means Back's current-turn timer expired; the one active player identifies the affected seat. Back alone owns timer identity/expiry and must discard obsolete callbacks before invoking Motor. T takes no player argument and is rejected during Mulligan/Game_End. For mulligan AFK, Back submits M using `15000000000` for timed-out P1 or `25000000` for timed-out P2, preserving the other human's choice; both may time out.

### Output files

| File | Contents | Recipient |
| --- | --- | --- |
| `XXM.json` | Full authoritative Motor state, including hidden information | Motor / trusted Back only |
| `XX1.json` | Player 1's filtered state and legal commands | Player 1 |
| `XX2.json` | Player 2's filtered state and legal commands | Player 2 |

Back must publish a successful update only after Motor has completed it. Incomplete output from a failed invocation must not be presented as a valid new state.

### Result codes

| Code | Meaning |
| --- | --- |
| `0` | Ongoing game; waiting for both players, such as initial mulligans |
| `1` | Ongoing game; waiting for Player 1 |
| `2` | Ongoing game; waiting for Player 2 |
| `3` | Invalid request; no writes or automatic defeat. Back must distinguish input errors, delayed requests, and player misconduct. |
| `4` | An apparently valid command caused an internal error; cancel the match |
| `5` | Crash classification; cancel the match and investigate |
| `61` | Player 1 wins |
| `62` | Player 2 wins |
| `63` | Match draw |

Motor uses process exit status: I success is 0; M success is 1 for human P1 or 2 after AI P1's opening turn; P/T success is 1/2 for human input priority, or 61/62/63 for a match result. Invalid requests are 3; handled internal errors are 4. Back must not treat every nonzero exit as failure. Draws and round-based victories are implemented: Winner is 0 for a draw, otherwise 1/2; End_Reason is Crowns for scoring or Concede for surrender. A crashed or killed process cannot be relied on to emit 5; Back must classify abnormal termination or missing output itself.

## 5. Player commands

Motor includes all possible legal command codes in the receiving player's game state, including complete mulligan choices during setup. Front exposes these choices to the user and submits a selected code. Motor validates the selected command again against the current authoritative state.

### Action codes

| Code | Action | Availability |
| --- | --- | --- |
| `0` | Pass the round | Base game |
| `1` | Surrender | Base game |
| `2` | Heroic Power | Once per game, replacing the normal card play |
| `3` | Play a card | Base game |
| `4` | Target action | Reserved; role to be finalized with later effects |
| `5` | Mulligan | Initial setup |
| `6` | End the current turn | Base game; normally requires a card already played |

Action `6` is distinct from passing the round and from Back's `T` timeout command.

### Card and location identifiers

A card instance has a player prefix followed by a two-digit short ID:

- `101–152`: Player 1's instances.
- `201–252`: Player 2's instances.
- `000`: no card where applicable.

Only cards belonging to the selected deck are initialized as draw-deck cards.

| Zone code | Zone |
| --- | --- |
| `0` | Out of game / nowhere; distinguish the precise meaning in state |
| `1` | Deck |
| `2` | Hand |
| `3` | Front row |
| `4` | Back row |
| `5` | Graveyard |

The internal location format is `PZNN`: absolute player, zone, and position. `00` represents no position. Only draw-deck order has gameplay significance: position 01 is bottommost, and draws use the last entry. Hand, board and graveyard lists retain their current order for bookkeeping/source references; no ordering refactor is made here. `library.json` is the static catalogue, distinct from each player's shuffled draw deck.

The earlier relative side/zone/position proposal is superseded by the confirmed target-token convention below.

The original notes specify the ordinary action fields in this order: player (one digit), action (one digit), card ID (three digits), source zone and position (one plus two digits), played zone and position (one plus two digits), and target zone and position (one plus two digits). Mulligans use the separate format defined above.

The current vanilla format uses the original 14-digit layout `P A CCC ZNN Z00 000`: player, action, card ID, source zone/position, destination zone with placement position 00, and target 000. Destination is 3/4 for Unit rows, 5 for Spell/Location graveyard. Concede/End Turn use zero in every field after player/action. Nonzero target handling is deferred; its confirmed encoding is documented below. See the Turn flow sheet for exact examples. Source hand positions currently support 01–99; future hand growth beyond that requires an encoding extension rather than a silent truncation.

**Transport commands as strings**, even if they contain only digits. This preserves leading zeros and avoids dependence on numeric precision in TypeScript/JavaScript.

### Confirmed targeting convention — not yet implemented

The final three digits are a target token `TTT`, replacing the original target-zone/position interpretation without increasing the 14-digit command length: `P A CCC ZNN Z00 TTT`. Source and destination fields remain unchanged.

| Target | Player 1 | Player 2 |
| --- | --- | --- |
| Deck | `011` | `021` |
| Hand | `012` | `022` |
| Front row | `013` | `023` |
| Back row | `014` | `024` |
| Graveyard | `015` | `025` |
| Player / terrain | `016` | `026` |

- `000` means no target.
- An existing full card-instance ID (`101–152` or `201–252`) targets that specific card, not its position. Different copies have distinct IDs; only existing, eligible instances may be offered.
- Zone/player targets use `0 | absolute player | zone`. Player 1/2 never means self/opponent. A terrain corresponds to its player; the effect determines what it affects there. Zone 6 follows the manual README's player designation; it is not a card-containing list in the current state.
- `010`, `020` and other unlisted zero-prefixed values are unassigned. Out-of-game/nowhere is not an eligible zone target in this convention. Relative side codes 6/7 are not used as side fields.
- A card target identifies one instance; a zone target identifies the zone itself. Card metadata and effect rules must determine eligible targets without revealing hidden hand/deck identities.
- This defines one target per command. Multiple targets, later choices after new information, and the exact role of action 4 still need discussion before implementation.

Only `000` is currently generated. Nonzero targets remain unsupported and must not be submitted. This documentation approval does not authorize implementation: notify the user before changing code. No card effects, catalogue data, source positions, destination semantics or state locations have been changed.

### Later targeting behavior

The current destination `00` and target `000` are unambiguous because they occupy fixed fields. Target value 0 means no target, encoded as `000` in today's three-digit field. Later, Motor must inspect the played card's catalogue effect and target requirements to generate legal choices. Front must send an offered command; a zero target is not permission to bypass an effect requiring a target. The target-token encoding below is confirmed; effect eligibility and extra-choice behavior remain separate implementation work.

Front submits card placement and the chosen target together. Motor's legal-command list represents the permitted target choices. If an effect has no legal target, a no-target play is allowed under the clarified design.

Choosing a target locally does not apply the card: until Front submits a complete play command, a timeout is treated as a full turn timeout. Later effects that ask for a new choice after drawing or revealing information will need their own phase rules.

## 6. Game data and state

### Card catalogue

`library.json` currently provides card IDs, names, types, tags, base strength, effect flags, targeting metadata, and placeholder descriptions. The original notes named `library.db`; whether to convert the catalogue to a database remains an implementation decision. `Library_rm.md` was referenced in the original notes but was not supplied with these sources.

The developer reports correcting the tags for short IDs 18 and 44. The README records that decision; the attached JSON snapshots are not updated by this documentation edit.

### Internal state

`motor_game_state_template.json` is the starting schema. State includes:

- Match/room identity, game type, round, and phase.
- Selected decks, player types, crowns, and pass flags.
- Active player and current/previous round starters (the latter stored in XXM).
- Ordered card lists for decks, hands, rows, and graveyards.
- Card existence, location, base strength, and current strength.
- Turn progress needed to determine whether playing, passing, or ending is legal.
- Later effect state, such as boosts, damage, revival, elixir duration, frost, and power usage.

Phase values and the final schema are owned by the Motor implementation and are not yet frozen here.

Implemented turn state includes `Card_has_been_played` (0/1), `Turn_number` (global turn count), `Last_Command`, `Last_Phases` (latest invocation's phase trace), `Winner` and `End_Reason`. Ten new zero-initialized values, `Player_1_Frost_Damage_Turn_1`…`_5` and the five P2 equivalents, track damage for each player's last five **own turns**. Shift only that player's buckets on its turn start; bucket 1 is current, bucket 5 oldest. Sum them into the existing rolling-total fields before publication. No actual frost effect executes yet.

XXM stores both freshly generated command lists in `Available_Commands` keyed by `"1"`/`"2"`. Player views get only their own list. `Last_Command` stays private in XXM and is absent from both player views.

Keep zone lists and per-card locations consistent. Likewise, cached row scores, board scores, and flags must agree with the underlying cards. `Boosted` means current strength is greater than base strength; `Hurt` means it is lower.

Timeout-removed cards retain their numeric Card_ID record with Exist=false and Location=0000, outside every zone. Never-selected deck records are omitted altogether; the initial aside stratagem has Exist=true.

### Player views and secret removal

The implemented approach starts with each player's supplied template and deep-copies only matching fields from Motor state. It then fills `Available_Commands`. This replaces the earlier plan to copy the entire Motor state and remove secrets. Editing a player view must not change the authoritative state or the other player's view.

The current views contain the recipient's hand IDs and template-defined public fields. They omit both deck lists, the opponent's hand, and all numeric `Card_ID` records (the separate `Card_has_been_played` flag is included). Fields absent from the player templates—such as `Room_number`, `Game_Type`, player types/deck choices, and `Player_1_Stratagem`—are not automatically added. Individual Current_Strength/Boosted/Hurt values therefore still need a privacy-filtered projection before Front can render them. Additional display fields require an explicit template change.

At minimum, remove:

- Opponent hand identities and hidden card locations.
- Both players' shuffled deck order.
- Hidden choices and internal information that exposes future draws or private decisions.
- Commands and internal flags that reveal information the recipient should not know.

Counts may remain visible according to the game's presentation rules. Public fixed deck lists do not make current hand contents or shuffled order public. Back must never send `XXM.json` to Front.

## 7. Validation, timeouts, and failures

### One pending command

Front sends at most one command and waits for the next authorized input state. This prevents ordinary repeated submissions, but it does not resolve every server-side race.

Back must serialize player actions and timeouts for the room. For example, if a valid play is accepted just before the timer callback runs, the callback must not penalize the next turn.

**Approved ownership:** Back alone handles timers, including matching callbacks to the current match/turn under room serialization. Ignore obsolete callbacks, especially after room reuse. No match/revision CLI extension is introduced; Motor cannot independently identify a stale T.

The user now confirms exit 3 for invalid requests, without writes or automatic defeat. This supersedes the original loss-for-invalid-command proposal. Exit 3 alone is not evidence of cheating. Inform Back of this decision.

### Timeout policy

Back owns the timer; the original proposed duration is one minute, pending final agreement.

- Mulligan timeout: keep that player's current hand.
- Normal turn timeout with Card_has_been_played = 0: randomly select one normal hand card, excluding the stratagem, retain its record out of game, and end the turn.
- Local target selection without a submitted play: same as a normal turn timeout.
- Timeout after a card was already played: end the turn normally, with no forced removal.
- Empty/stratagem-only hand: automatically pass at the player's own turn start; do not open an input/timer window.
- Removing the last normal hand card causes automatic passing at the player's next turn start, not immediately at timeout end.
- Passed-player pseudo-turns are automatic effect resolution, not input windows requiring a player timeout.

### Failure policy

The current design cancels the match if Motor crashes, fails internally, or stops responding. Resuming a match after a Motor crash is not required by this design.

Back must detect failures, stop a hung process, avoid delivering partial state, and invalidate remaining commands/timers for that match. Excluding simultaneous writers does not itself prevent partial files after a crash.

### Disconnect policy

The current intended user flow is to declare a disconnected player the loser and show the result when they reconnect to the homepage. The precise time at which disconnect becomes defeat remains to be agreed.

This is separate from the Remote Players module's reconnection requirement. See section 9 before treating this policy as sufficient for that module.

## 8. Deferred mechanics

These rules are recorded now for future work; they are not part of the vanilla milestone.

### Heroic Power and Stratagem

These two simplified abilities are now implemented, as detailed in the checkpoint below. Heroic Power replaces the normal play; Stratagem may accompany either. Other commander/card effects remain deferred.

### Card effects and deaths

Future `library.json` metadata will name dedicated Python handlers for play-from-hand, board entry/battlecry, death, graveyard entry, end-turn, and end-round events. Handlers normally receive the in-memory Motor state and last command, with affected-card/player context where needed. Use a registry of known handler functions. Check the affected card on entry/play/death events and board cards at turn/round end. Keep movement and persistence separate from effect dispatch so effects and commanders can be added later. Mulligan exchanges trigger none of these events. See the flow sheet for event details and remaining ordering decisions.

Cards may trigger additional actions or automatic plays. Units reaching zero strength are destroyed and enter the graveyard. Simultaneous deaths are processed left to right; ordering across different rows/players remains to be defined if needed.

Ordinary destroyed/discarded cards enter the graveyard. Timeout removal remains a separate operation.

### Frost

Frost is placed on one of the opponent's rows. At the start of that player's normal turn or passed-player pseudo-turn:

1. If the row contains units, deal 2 damage to a highest-strength unit.
2. If several units tie for highest strength, choose randomly among them.
3. Decrease frost duration by one, even if the row is empty.

The five-turn damage window now uses five numeric buckets per player, shifted on that player's own turn start and summed before publication. Actual frost damage, stacking/refresh behavior, and cross-row resolution order remain deferred.

In the vanilla milestone, Location cards go directly to the graveyard when played, exactly like spells. Later, a Location will remain attached to a row for the round with zero/no strength; it is not a zero-strength unit and must not be destroyed by the unit death rule merely for having no strength. Locations can change the field's appearance, and frost changes the affected row's appearance. Detailed Location effects and their end-of-round destination will be specified later.

### AI opponent

AI uses Witcher and follows the implemented specification at the end of this guide. It simulates each legal normal-card command through the actual rule engine, then compares the immediate post-play board margins. Control actions and End Turn are handled separately.

Predictions never mutate or publish live room state; private full-state copies stay in ai_prediction/XX. Selection uses AI's own legal cards plus public scores, crowns, pass status and completed-turn counts, not opponent hand/deck order. Current plays are deterministic; future random effects need a sampling/replay decision.

## 9. Evaluation and module planning

Reference: supplied `ft_transcendence` subject, version 21.1.

| Planned module | Subject requirement relevant here | Planning implication |
| --- | --- | --- |
| AI Opponent, major | Competent, human-like play; occasionally able to win; support customization if implemented | Complete the base game first, then demonstrate the AI rather than claiming the module from a heuristic alone. |
| Remote Players, major | Separate computers, graceful latency/disconnection handling, and reconnection logic; subject p. 16 | Returning to the homepage with a lost-game result does not demonstrate resuming an interrupted match. Plan restoration of the ongoing match within a defined grace period as the safer interpretation. |
| Game customization, minor | Power-ups/abilities, different maps or themes, customizable settings, and default options; subject pp. 17–18 | Selectable appearance themes fit an explicitly listed category. Automatic location/frost visuals are game feedback rather than user-selectable customization. Do not assume these visuals alone satisfy the whole module. |

For customization, document the actual user-selectable options and their defaults. The subject does not state that a single theme selector alone guarantees validation; confirm the intended scope with the team/evaluators.

The complete project still needs the required total module points and all mandatory features. This Motor document does not establish overall project compliance.

## 10. Remaining decisions

### Tracking explained

`Game_Phase` is where the game is now. `Last_Phases` is a short trace of phases processed by the latest accepted operation, not the entire match's history. Internal phases finish before Back receives the next playable state.

| Operation | Published phase | Last_Phases | Turn_number |
| --- | --- | --- | --- |
| Resolve initial mulligans | Turn | Round_Start, Turn_Start, Turn | 1: P1 starts |
| P1 plays a card | Turn | Turn | Still 1 |
| P1 sends End Turn | Turn | Turn, Turn_End, Turn_Start, Turn | 2: P2 starts |
| P2 plays, then ends | Turn | Turn, Turn_End, Turn_Start, Turn | 3: P1 starts |

Currently `Turn_number` counts started player turns globally, not commands, cards or pairs of turns. It continues across rounds. Automatic pseudo-turns also increment it, as confirmed. The frost window is separate: only the owner's turn start shifts that owner's five buckets.

`Last_Command` is only the latest accepted request and is overwritten on the next one. For example, XXM can store `M 15000000101 25000000`, revealing that P1 returned card 101. Neither player view includes `Last_Command`, for any operation. Front uses current state and available commands instead. A persistent command log in XXM is now requested in the TODO; its format and retention are not yet decided.

### Saving: approved cancellation policy

Motor builds all three documents in memory, then writes XXM, XX1 and XX2 separately. Example: XXM and XX1 receive the new turn, then the process fails before writing XX2. Disk now contains two new files and one old file. A successful operation publishes all three; a failed operation must not be published by Back.

The user explicitly chose cancellation on internal failure; previous files are not automatically restored. A reminder comment is in motor.py. Recoverable publication remains deferred; changing that contract requires discussion. Renaming each of three files individually would not make the set atomic.

### AFK: a late timer example

P1's turn 7 has a timer. P1 ends the turn and P2 starts turn 8. The old P1 timer callback arrives late. A timeout invocation carrying only the room number could now remove a card from P2, despite being P1's timer.

Approved solution: Back checks its timer identity under room serialization and invokes T only for the current match/turn. Motor receives no timer identifier and trusts that check. Back owns duration and reset behavior; the original one-minute proposal is not enforced by Motor.

These implementation decisions are now settled: pseudo-turn counting/own history, persistent unused stratagem, retained out-of-game marker, cancellation after failed saving and Back-only timers. Last_Phases remains a diagnostic trace; gameplay decisions do not depend on it. It is not a persistent command log.

Resolve the following for the vanilla milestone:

1. **Later targeted actions:** implement the confirmed three-digit target token after notifying the user; discuss multiple targets and extra-choice phases before dependent effects. Current runtime offers still use only 000.
2. **Next work:** Front/Back integration of automatic AI and gameplay verification; general card effects remain deferred.
3. **Request races and saving:** Back owns obsolete-event filtering; cancellation on failed saving is approved. Future Motor-side revisions/recoverable saving require a separate decision.
4. **Disconnects:** immediate defeat or grace period, and how will ongoing-match reconnection satisfy the selected module?

Later decisions include complete effects, phase transitions for chained choices, commander powers, weather stacking, AI information access, and customization scope.

## 11. Verification checklist

The initialization, mulligan, turn, round, power and AI suite contains 68 tests (54 baseline plus 14 AI tests); see the current verification log in todo.md. Coverage includes initial deck combinations, all 48 deck/return-count combinations, hidden information, AI mulligans, rejected inputs preserving files, single turn priority, normal card movement, explicit End Turn, refreshed totals/statuses, own-turn frost windows and concession. Python indentation uses tabs for four-space indentation levels.

Checked items below are covered by current tests. Unchecked items remain future acceptance checks; the multi-round loop and automatic AI are implemented; general effects remain deferred.

- [x] Each selected draw deck contains exactly 25 distinct card instances; stratagems are excluded.
- [x] Both players receive 10 cards and the correct mulligan limit.
- [x] Set-aside mulligan cards cannot be drawn as their own immediate replacements.
- [x] Player views list legal mulligan codes with three card slots for Player 1, two for Player 2, and `000` for unused slots.
- [ ] Only the authenticated, authorized player can act.
- [x] A normal turn cannot play a second card.
- [x] Vanilla spells and Location cards enter the graveyard without an effect.
- [x] Explicit End Turn swaps priority and resets the normal-card flag.
- [x] Active-player concession ends the game, clears priority and returns 61/62.
- [x] Scores and Boosted/Hurt flags refresh before publishing player views.
- [x] Frost history rotates only on the affected player's own turn start.
- [x] Passing a round, ending a turn, and timing out have distinct behavior.
- [x] Timeout-removed cards are absent from the graveyard and cannot be drawn again.
- [x] A passed player cannot act but receives automatic pseudo-turn effects while the opponent continues.
- [x] Both players passing ends the round without further pseudo-turns.
- [x] Units enter the graveyard and reset to base strength between rounds in the vanilla game.
- [x] A timeout removes a random hand card only if no card was played that turn.
- [x] A timeout after an accepted card play ends the turn without a penalty.
- [x] An empty normal hand, including after timeout removal, marks the player as passed at their next turn start; new-round draws happen first.
- [x] Round scores, tied crowns, next starter, and `61`/`62`/`63` results are correct.
- [x] Drawing from a deck with fewer than three remaining cards works.
- [x] An empty hand after the new-round draw automatically passes; if both hands are empty, scoring proceeds without input.
- [ ] Neither player view reveals hidden hands, deck order, or secret state through commands.
- [ ] A play/timeout race cannot penalize the wrong turn.
- [x] Separate rooms progress without corrupting each other's state.
- [ ] A failed Motor invocation cancels the match without publishing partial state.

## 12. Team and project background

The original team joined Lucas and Nima with Quentin and Cyril. The first recorded planning meeting was 31 August 2026, followed by development during September.

| Team member | Development focus recorded in the original notes |
| --- | --- |
| Lucas | Backend |
| Nima | Backend |
| Quentin | Frontend |
| Cyril | Game rules and Python Motor |

These development responsibilities do not establish the subject's formal PO, PM, or Technical Lead assignments; document those in the root project README.

The design goals are a fun, balanced, recognizable Witcher card game, usable on both desktop and mobile, with manageable implementation complexity and room for effects and AI later. The immediate priority is a reliable vanilla match loop that Front and Back can integrate with.

The original late-September target was a bare working Motor, followed by AI, bug fixes, and upgrades in early October. These are planning targets, not evidence of completed work.

Documentation assistance: AI was used to review the supplied design and reorganize this guide using the developer's clarifications. The team should review the final contract and describe AI use in the project's required Resources section.

## 13. Phase order and checks

<!-- Modification 2026-09-27: Stable insertion points for future phases, checks and effect handlers. -->

These labels are permanent reference points; ask to insert a new step between any two labels. The [Turn flow sheet](Turn-flow.md) expands each step with examples and a diagram. Mulligans remain simultaneous; one player has priority during Turn; Game_End has no priority.

| Step | Phase / responsibility |
| --- | --- |
| R10 | After mulligans: append P1 stratagem to hand once |
| R20 | Round_Start: initialize round 1 and turn counter 0 |
| R30 | Seed active/opponent 2/1 so first swap selects P1 |
| T10 | Turn_Start: swap active/opponent, increment turn number |
| T20 | Reset card/Power and Stratagem turn flags; shift active player's own frost window |
| T30 | Decrement own frost durations; actual damage/start-turn effects reserved |
| T35 | Automatically pass an empty normal hand |
| T40 | Enter Turn; passed players continue through E10, otherwise C10–V30 before input |
| A10 | Load submitted P request and check phase, priority and saved views |
| A20 | Validate exact command against current offered actions |
| A30 | Play: remove normal card from hand; reserved on-play effect point |
| A40 | Normal card: append to row/graveyard and set played flag to 1 |
| A42 | Heroic Power: consume once-game use, draw if possible, set played flag to 1 |
| A44 | Stratagem: remove out of game, set Stratagem turn flag; +5 round bonus if own board has a unit |
| A50 | Retain current priority; run C10–V30 |
| A25 | Pass Round: set active player's pass flag, then E10 |
| F10 | Back T: flag 0 removes normal card out of game, flag 1 removes nothing; then E10 |
| E10 | End Turn/Pass/T/pseudo-turn: enter Turn_End; completed input turns increment private round counter, pseudo-turns do not |
| E20 | Reserved board end-turn effects |
| E30 | Both passed → Q10; otherwise T10 |
| Q10 | Round_End: refresh board strengths and award crown(s) |
| Q20 | Two-crown check: Game_End immediately, before cleanup/draw |
| Q30 | If continuing: board to graveyard/base strength, clear frost state, preserve history/unused stratagem |
| Q40 | Round_Start: increment round, reset completed-turn counters, draw up to three each, reset pass flags/check empty hands |
| Q50 | Select next starter: prior winner or opposite prior starter on tie; both empty → Q10, otherwise T10 |
| G10 | Concede: enter Game_End, set opponent as winner, clear priority; run C10–V30 |
| C10 | Validate zone membership and refresh locations |
| C20 | Recalculate row totals and Board_Strength = both rows + Round_Bonus |
| C25 | Refresh both players' Hand/Deck/Graveyard counts |
| C30 | Recalculate faction-relevant Roach/Winter Queen flags; omit other faction flags |
| C40 | Recalculate Boosted/Hurt for all numeric Card_ID records |
| C50 | Sum five own-turn frost buckets per player |
| V10 | Generate legal commands for both players; save in XXM |
| V20 | Rebuild XX1/XX2 with current fields, each player's commands, excluding Last_Command |
| V30 | Write all three files before returning status to Back |
| V40 | If AI has priority, continue N10; otherwise return human priority or final result |
| N10 | Capture AI turn-start margin once; evaluate Stratagem, Power and End/Pass |
| N20 | For normal play: clear room predictions, simulate every legal normal-card command, rank board margins |
| N30 | Apply selected command via normal rules and publish C10–V40; repeat while AI has priority |

Internal Turn_Start/Turn_End phases do not yield input. Their order is recorded in `Last_Phases`; the next published input state is Turn. Round_End and round restarts resolve internally until an input turn or Game_End. Reaching Round_End or Game_End must block automatic swapping into another turn.

## Power, Stratagem and public counts — implemented 7 October 2026

The user confirmed making this checkpoint's backup and authorized the AI stage below. Ordinary card effects remain deferred.

- Both seats have one Heroic Power per game. Command action 2, with other fields zero: P1 `12000000000000`, P2 `22000000000000`. Use only before a normal card play; Power and a normal card cannot share a turn.
- Power draws the top card (last deck entry), sets `Player_N_Power_Used=true` and `Card_has_been_played=1`, retains priority and enables End Turn. An empty deck still consumes Power and enables End Turn. An empty normal hand at turn start still auto-passes before Power can be used.
- P1's Stratagem uses action 3, its card ID and current source hand position, destination 5 and target 000, just like a spell command. It is removed from hand and retained out of game (`Exist=false`, `Location="0000"`), never added to the graveyard.
- Stratagem can be played before or after the normal card or Power, while P1 still has priority. It sets only the private `Stratagem_has_been_played=1` flag, blocking Pass Round. It does not enable End Turn or prevent AFK card removal on its own. Both turn flags reset on each turn start.
- Both deck Stratagems add 5 to `Player_1_Round_Bonus` **only if a unit is on P1's board when activated**. With no unit it is consumed for no effect, including no bonus when a unit is played later.
- Board strength is front-row strength + back-row strength + round bonus. Row/card strengths and Boosted/Hurt flags are unchanged. Recalculation does not add the bonus repeatedly. The bonus resets on preparing a new round; final scoring preserves the final board and bonus after Game_End.
- XXM and both player views now contain `Player_N_Power_Used`, `Player_N_Hand_Count`, `Player_N_Deck_Count`, `Player_N_Graveyard_Count` for N=1/2. Counts refresh on every publication and include Stratagem while in hand. The normal-hand automatic-pass rule still excludes Stratagem.
- Round_Bonus and the Stratagem turn flag stay internal. Front displays Motor's Board_Strength rather than reconstructing it from row sums. No extra per-card projection is needed for this board-only bonus; future card-specific effects still need one.
- Existing saved Turn offers predate these new commands and may be rejected as inconsistent. Use a freshly initialized test room for this milestone; live room files are not rewritten or migrated automatically.

### AI — implemented 7 October 2026

Front selects AI mode; Back uses the existing initialization AI token and submits only the human mulligan code. Motor chooses AI actions and continues automatic progression until human input or Game_End. Keep all player-view publication through Back; never expose private Motor states or predictions.

AI mulligans return Spells and Locations first, then weakest Units up to the seat's maximum, with card ID breaking equal priorities. Locations also enter normal-card simulations and still go to graveyard without effects; future persistent effects remain deferred.

After validating an AI match's mulligan, recreate ai_prediction/XX beside the room files (motor/ai_prediction/XX in normal CLI use). Before card evaluation, clear this room's previous generated predictions, simulate every legal normal-card command independently, and save each refreshed private Motor state as <14-digit-command>.json. Only generated command-named files are deleted; unknown entries, nested directories and symlinks cause a state error before cleanup. Other rooms, sources and archives are untouched. PvP creates no prediction folders.

Decision order, as requested:
1. Use Stratagem only with exactly one other playable normal card left in hand; then reconsider Power. Normal eligibility still applies.
2. Use available Power in round 1 if opponent has not passed the round, has completed at least one full turn this round, and AI is ahead at its turn start. Use it on AI's first playable turn of round 2 if opponent won round 1; otherwise on its first playable turn of round 3 if still available, regardless of which player started the round.
3. If neither special action applies, pass when opponent has zero crowns and either side leads by at least 5; also pass when opponent has already passed and AI leads. Automatic empty-hand passing remains Motor's rule.
4. Otherwise compare projected board margins (AI minus opponent) with exact preference **+1, 0, -1, +2, -2, +3, -3, …**. Equal-ranked commands may be chosen arbitrarily. This intentionally prefers saving commitment over always taking a lead.
5. Apply the selected command through the real rules and refresh player views. End Turn must also be handled automatically after card/Power use; consider any still-eligible Stratagem before ending.

Predictions are independent and private. Current deterministic actions are reapplied through the same rule engine; tests compare the real result with the selected projection. Later random effects require an agreed simulation/replay policy before relying on reapplication. Equal card-action rankings use ascending command code for reproducibility.

#### Private completed-turn counters and turn-start margin

XXM alone holds `Player_1_Completed_Turns_This_Round` and `Player_2_Completed_Turns_This_Round`. Both initialize/reset to zero at round starts. Explicit End Turn, deliberate Pass Round and AFK completion each increment the active player's counter. A card, Power or Stratagem alone does not complete a turn. Automatic passed-player pseudo-turns do not increment these counters (they still increment global Turn_number and rotate frost history).

Counter zero identifies AI's first playable turn; a positive opponent counter satisfies the round-1 completed-turn prerequisite. Example: human starts round 2 and ends; AI still has zero completed turns, so its first-playable-turn Power rule can apply. For round 2's loss condition, opponent has one crown and AI zero; a tied round 1 does not qualify.

Within automatic AI processing, Motor remembers the board margin at the start of each AI turn. Stratagem may increase the current score, but it does not retroactively satisfy a condition requiring an initial lead. Actual card projections use the updated current board.

#### Back integration and output timing

No new Back command is needed: initialize one seat as I, submit only human M/P/T input. After each accepted real action, Motor refreshes and writes XXM/XX1/XX2. AI resolves internally through Stratagem/Power/card/End Turn and possibly further turns if the human has passed. Back waits for process completion, then delivers the final player view; intermediate file writes are not an event/animation stream and must not be read while Motor is running.

Return 1/2 always names the human awaiting input in AI matches; 61/62/63 ends the match. Initialization still returns 0 for mulligans. Front never drives AI actions or starts an AI input timer. Explicit external P/T against AI priority is rejected. Normal no-write invalid-request and cancellation-on-internal-failure policies remain.

A defensive 1000-action bound turns unexpected nontermination into an internal error, not a new game rule. Fresh initialization is recommended for older rooms without the private counters, since completed earlier turns cannot be reconstructed reliably. No existing live rooms are migrated automatically.
