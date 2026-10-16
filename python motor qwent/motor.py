#!/usr/bin/env python3
"""Initialize a room with I and resolve all human mulligan choices with M.

Modification 2026-09-26: Added initialization, shuffled hands/decks,
private player views, and zero-padded mulligan choices. No turn/AI logic yet.
Files are written beside this script, independently of Back's working directory.
Modification 2026-09-27: Repaired indentation in parse_players and normalized
this file to four-space Python indentation after the executable failed to load.
Modification 2026-09-27: Use tabs for indentation; add M dispatch, shared state
refresh/output, and phase-aware player commands. No card effects or turns yet.
Modification 2026-09-27: Centralized refresh before publication, protected the
Card_has_been_played flag from card pruning, and recorded commands privately.
Modification 2026-09-27: Added vanilla P dispatch, first-turn setup, command
publication for exclusive priority, explicit End Turn and concession results.
Modification 2026-09-27: Added Back-owned T dispatch and round/pass results;
retained the explicitly approved cancellation policy for partial saves.
Modification 2026-09-27: Keep Last_Command private in XXM; player templates
no longer expose it and no mulligan redaction field is added to views.
Modification 2026-10-07: Automatically resolve AI decisions after M/P/T,
publishing every accepted action and returning only human priority or Game_End.
"""

import copy
import itertools
import json
from pathlib import Path
import random
import re
import sys

from mulligan import InvalidCommand, StateError, resolve_mulligans
from game_state import refresh_state
from turns import apply_command, apply_timeout, first_turn, legal_commands, result_code
from ai import choose_command, prediction_folder


BASE = Path(__file__).resolve().parent
PLAYER_TEMPLATES = {
	1: "player1_game_state_template copy.json",
	2: "player2_game_state_template.json",
}
CHANGE_NOTE = "Created by Motor initialization (2026-09-26); replaces previous room contents."


def read_json(path):
	"""Accept the UTF-8 BOM present in the supplied source files."""
	data = json.loads(path.read_text(encoding="utf-8-sig"))
	if not isinstance(data, dict):
		raise StateError(f"{path.name} must contain a JSON object.")
	return data


def parse_players(room, action, player1, player2):
	if not re.fullmatch(r"[0-9]{2}", room):
		raise ValueError("Room must be exactly two digits, 00 through 99.")
	if action != "I":
		raise ValueError("Initialization requires action I.")
	players = []
	for number, token in enumerate((player1, player2), start=1):
		if not re.fullmatch(rf"[PI]{number}[12]", token):
			raise ValueError(
				f"Player {number} must use P{number}1, P{number}2, "
				f"I{number}1, or I{number}2."
			)
		kind = "AI" if token[0] == "I" else "Human"
		# AI always uses Witcher, even if Back requests deck 2.
		deck = 1 if kind == "AI" else int(token[2])
		players.append((kind, deck))
	if sum(kind == "AI" for kind, _ in players) > 1:
		raise ValueError("At most one AI is allowed.")
	return players


def mulligan_commands(hand, player):
	"""One code per subset; unused slots first, then IDs in ascending order."""
	limit = 3 if player == 1 else 2
	return [
		f"{player}5" + "000" * (limit - count)
		+ "".join(f"{card:03d}" for card in selected)
		for count in range(limit + 1)
		for selected in itertools.combinations(sorted(hand), count)
	]


def player_view(state, player):
	# The supplied template is the allowlist: never copy hidden Motor fields.
	view = read_json(BASE / PLAYER_TEMPLATES[player])
	for key in view:
		if key in state:
			view[key] = copy.deepcopy(state[key])
	view["Available_Commands"] = copy.deepcopy(state["Available_Commands"][str(player)])
	view["_comment"] = state.get("_comment", CHANGE_NOTE)
	return view


def initialize(room, action, player1, player2, output_dir=None, rng=None):
	"""Build all three documents before replacing any previous room files."""
	players = parse_players(room, action, player1, player2)
	state = read_json(BASE / "motor_game_state_template.json")
	state["Game_Type"] = "AI" if any(p[0] == "AI" for p in players) else "PvP"
	state["Room_number"] = room
	state["Game_Phase"] = "Mulligan"
	state["Mulligan"] = True
	state["Round_number"] = 0
	state["Active_Player"] = 0
	state["Active_Opponent"] = 0
	state["Card_has_been_played"] = 0
	state["Turn_number"] = 0
	state["Last_Command"] = f"I {player1} {player2}"
	state["_comment"] = CHANGE_NOTE
	rng = rng if rng is not None else random.SystemRandom()
	retained = set()

	for player, (kind, deck) in enumerate(players, start=1):
		prefix = f"Player_{player}"
		state[f"{prefix}_Type"] = kind
		state[f"{prefix}_Decklist"] = "Witcher" if deck == 1 else "Wild Hunt"
		short_ids = range(1, 26) if deck == 1 else range(27, 52)
		cards = [player * 100 + short_id for short_id in short_ids]
		retained.update(f"Card_{card}" for card in cards)
		rng.shuffle(cards)
		state[f"{prefix}_Hand"] = cards[:10]
		state[f"{prefix}_Deck"] = cards[10:]
		for zone_name, zone_code in (("Hand", 2), ("Deck", 1)):
			for position, card in enumerate(state[f"{prefix}_{zone_name}"], start=1):
				entry = state[f"Card_{card}"]
				entry["Exist"] = True
				entry["Location"] = f"{player}{zone_code}{position:02d}"
		state[f"Player {player} Roach in Deck"] = player * 100 + 8 in cards[10:]
		state[f"Player {player} Winter Queen in Deck"] = player * 100 + 32 in cards[10:]

	# Keep only P1's chosen stratagem, aside at location 0000, outside all zones.
	stratagem = 126 if players[0][1] == 1 else 152
	retained.add(f"Card_{stratagem}")
	state[f"Card_{stratagem}"]["Exist"] = True
	state[f"Card_{stratagem}"]["Location"] = "0000"
	state["Player_1_Stratagem"] = stratagem
	for key in list(state):
		if key.startswith("Card_") and key[5:].isdigit() and key not in retained:
			del state[key]

	return write_room(room, state, output_dir)


def write_room(room, state, output_dir=None):
	"""Serialize everything before writing; Back publishes only after success."""
	refresh_state(state)
	# V10: generate fresh offers after all C10-C50 derived-state checks.
	library = read_json(BASE / "library.json") if state["Game_Phase"] == "Turn" else {}
	state["Available_Commands"] = {
		str(player): (mulligan_commands(state[f"Player_{player}_Hand"], player)
			if state["Game_Phase"] == "Mulligan" else legal_commands(state, player, library))
		for player in (1, 2)
	}
	# V20: each player receives only its own offers and visible state.
	documents = {
		f"{room}M.json": state,
		f"{room}1.json": player_view(state, 1),
		f"{room}2.json": player_view(state, 2),
	}
	serialized = {name: json.dumps(data, indent=2) + "\n" for name, data in documents.items()}
	destination = BASE if output_dir is None else Path(output_dir)
	# V30: complete all output writes before main returns priority/result status.
	# Considered recoverable publication with the user (2026-09-27): keep these
	# sequential writes for now. A partial write failure cancels the match;
	# Back must not publish the files or retry the failed action as a recovery.
	for name, content in serialized.items():
		# write_text truncates existing contents as requested; files aren't deleted.
		(destination / name).write_text(content, encoding="utf-8")
	return documents


def refresh_cards(state):
	"""Compatibility entry point for the centralized refresh."""
	refresh_state(state)


def publish_and_run_ai(room, state, output_dir=None):
	"""Back receives final human priority; intermediate writes are not signals."""
	directory = BASE if output_dir is None else Path(output_dir)
	documents = write_room(room, state, output_dir)
	library = None
	turn_identity = None
	for _ in range(1000):
		if state["Game_Phase"] != "Turn" or state[f"Player_{state['Active_Player']}_Type"] != "AI":
			return documents
		if library is None:
			library = read_json(BASE / "library.json")
		identity = (state["Round_number"], state["Turn_number"], state["Active_Player"])
		if identity != turn_identity:
			turn_identity = identity
			player = state["Active_Player"]
			start_margin = state[f"Player_{player}_Board_Strength"] - state[f"Player_{3-player}_Board_Strength"]
		views = {p: documents[f"{room}{p}.json"] for p in (1, 2)}
		command = choose_command(room, state, views, library, directory, start_margin)
		state = apply_command(room, state, views, command, library)
		state["_comment"] = "Modification 2026-10-07: AI action resolved through normal rules."
		documents = write_room(room, state, output_dir)
	# Internal guard, not a game limit: vanilla resources cannot require this many
	# automatic actions. Back cancels on failure, like other internal errors.
	raise StateError("AI automatic progression exceeded its internal safety bound.")


def mulligan(room, commands, output_dir=None, rng=None):
	if not re.fullmatch(r"[0-9]{2}", room):
		raise InvalidCommand("Room must be exactly two digits, 00 through 99.")
	directory = BASE if output_dir is None else Path(output_dir)
	try:
		state = read_json(directory / f"{room}M.json")
		views = {p: read_json(directory / f"{room}{p}.json") for p in (1, 2)}
	except (OSError, ValueError) as error:
		raise StateError(f"Cannot load room {room}: {error}") from error
	library = read_json(BASE / "library.json") if state.get("Game_Type") == "AI" else None
	state = resolve_mulligans(room, state, views, commands, mulligan_commands, rng, library)
	if state["Game_Type"] == "AI":
		# Only after request validation: bad M cannot erase previous predictions.
		prediction_folder(directory, room, reset=True)
	state["Last_Command"] = "M " + " ".join(commands)
	first_turn(state)
	state["_comment"] = "Modification 2026-09-27: Mulligans resolved; stratagem in P1 hand; first turn ready."
	return publish_and_run_ai(room, state, output_dir)


def play(room, command, output_dir=None, *, timeout=False, rng=None):
	if not re.fullmatch(r"[0-9]{2}", room):
		raise InvalidCommand("Room must be exactly two digits, 00 through 99.")
	directory = BASE if output_dir is None else Path(output_dir)
	try:
		state = read_json(directory / f"{room}M.json")
		views = {p: read_json(directory / f"{room}{p}.json") for p in (1, 2)}
		library = read_json(BASE / "library.json")
	except (OSError, ValueError) as error:
		raise StateError(f"Cannot load room/catalogue: {error}") from error
	if state.get("Game_Phase") == "Turn" and state.get(f"Player_{state.get('Active_Player')}_Type") == "AI":
		raise InvalidCommand("AI turns are handled internally, not by Front or a timer.")
	state = (apply_timeout(room, state, views, library, rng) if timeout
		else apply_command(room, state, views, command, library))
	state["_comment"] = "Modification 2026-09-27: Player action resolved and all state checks refreshed."
	return publish_and_run_ai(room, state, output_dir)


def main(argv=None):
	args = sys.argv[1:] if argv is None else argv
	if len(args) < 2:
		print("Usage: ./motor.py XX I A1B C2D | XX M <human-code> [<human-code>] | XX P <code> | XX T", file=sys.stderr)
		return 3
	try:
		room, action, *payload = args
		if action == "I" and len(payload) == 2:
			initialize(room, action, *payload)
			return 0
		if action == "M":
			docs = mulligan(room, payload)
			return result_code(docs[f"{room}M.json"])
		if action == "P" and len(payload) == 1:
			docs = play(room, payload[0])
			return result_code(docs[f"{room}M.json"])
		if action == "T" and not payload:
			# No actor argument: Back prevents stale timer calls under room locking.
			# Mulligan AFK uses the offered zero-return M code, never T.
			docs = play(room, None, timeout=True)
			return result_code(docs[f"{room}M.json"])
		raise InvalidCommand("Unsupported action or invalid argument count; use I, M, P or T.")
	except StateError as error:
		print(f"Room state error: {error}", file=sys.stderr)
		return 4
	except ValueError as error:
		# Bad JSON is an internal data failure, not an invalid Back command.
		code = 4 if isinstance(error, json.JSONDecodeError) else 3
		print(str(error), file=sys.stderr)
		return code
	except (OSError, KeyError, TypeError) as error:
		print(f"Motor failed: {error}", file=sys.stderr)
		return 4


if __name__ == "__main__":
	sys.exit(main())
