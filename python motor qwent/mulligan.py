"""Modification 2026-09-27: Validate and resolve simultaneous mulligans.

All validation precedes mutation. Zone changes here deliberately do not trigger
play-from-hand, board-entry, death, or graveyard effects.
Modification 2026-10-07: AI returns Spells/Locations first, then weakest Units;
the old Roach-first heuristic is superseded. Equal priorities use card ID.
"""

import copy
import random
import re


class InvalidCommand(ValueError):
	"""Bad request from Back/Front; exit 3, no state changes."""


class StateError(Exception):
	"""Missing, corrupt, or inconsistent stored data; exit 4."""


def validate_state(room, state, views, legal_commands):
	"""Check the initial-state invariants before trusting saved offers."""
	if not isinstance(state, dict) or state.get("Room_number") != room:
		raise StateError("Motor state does not match the requested room.")
	if state.get("Game_Phase") != "Mulligan" or state.get("Mulligan") is not True:
		raise InvalidCommand("Mulligan phase is already over or has not started.")
	if any(state.get(k) != 0 for k in ("Round_number", "Active_Player", "Active_Opponent")):
		raise StateError("Unexpected round or active player during initial mulligans.")
	types = [state.get(f"Player_{p}_Type") for p in (1, 2)]
	if any(t not in ("Human", "AI") for t in types) or types.count("AI") > 1:
		raise StateError("Invalid player types in Motor state.")
	if state.get("Game_Type") != ("AI" if "AI" in types else "PvP"):
		raise StateError("Game type disagrees with player types.")
	for player in (1, 2):
		prefix = f"Player_{player}"
		deck_name = state.get(f"{prefix}_Decklist")
		if deck_name not in ("Witcher", "Wild Hunt"):
			raise StateError(f"Player {player}: unknown deck.")
		if types[player - 1] == "AI" and deck_name != "Witcher":
			raise StateError("AI must use Witcher.")
		hand, deck = state.get(f"{prefix}_Hand"), state.get(f"{prefix}_Deck")
		if not isinstance(hand, list) or not isinstance(deck, list):
			raise StateError(f"Player {player}: hand/deck must be lists.")
		short_ids = range(1, 26) if deck_name == "Witcher" else range(27, 52)
		if (len(hand) != 10 or len(deck) != 15
			or any(type(c) is not int for c in hand + deck)
			or set(hand + deck) != {player * 100 + c for c in short_ids}):
			raise StateError(f"Player {player}: invalid initial hand/deck contents.")
		for zone in ("Front_Row", "Back_Row", "Graveyard"):
			if state.get(f"{prefix}_{zone}") != []:
				raise StateError(f"Player {player}: initial {zone} must be empty.")
		for zone, code in ((hand, 2), (deck, 1)):
			for position, card in enumerate(zone, 1):
				entry = state.get(f"Card_{card}")
				if (not isinstance(entry, dict) or entry.get("Exist") is not True
					or entry.get("Location") != f"{player}{code}{position:02d}"):
					raise StateError(f"Card {card}: inconsistent existence/location.")
		view = views.get(player)
		if (not isinstance(view, dict) or view.get("Client_Player_Number") != player
			or view.get("Game_Phase") != "Mulligan" or view.get("Mulligan") is not True
			or view.get(f"{prefix}_Hand") != hand):
			raise StateError(f"Player {player}: saved view is inconsistent with Motor state.")
		offered = view.get("Available_Commands")
		expected = legal_commands(hand, player)
		if (not isinstance(offered, list) or any(not isinstance(c, str) for c in offered)
			or len(offered) != len(expected) or set(offered) != set(expected)):
			raise StateError(f"Player {player}: saved command list is inconsistent.")


def ai_selection(hand, player, library):
	"""Return up to the seat limit, treating Locations like Spells."""
	def priority(card):
		entry = library.get(f"Card_{card}")
		if not isinstance(entry, dict) or entry.get("Type") not in ("Spell", "Location", "Unit"):
			raise StateError(f"Card {card}: missing or unsupported AI mulligan type.")
		if entry["Type"] in ("Spell", "Location"):
			return (0, 0, card)
		strength = entry.get("Strength")
		if type(strength) is not int:
			raise StateError(f"Card {card}: invalid catalogue strength.")
		return (1, strength, card)
	return sorted(hand, key=priority)[:(3 if player == 1 else 2)]


def resolve_mulligans(room, state, views, commands, legal_commands, rng=None, library=None):
	validate_state(room, state, views, legal_commands)
	humans = {p for p in (1, 2) if state[f"Player_{p}_Type"] == "Human"}
	if len(commands) != len(humans):
		raise InvalidCommand(f"Expected {len(humans)} human mulligan command(s); omit AI placeholders.")
	selections = {}
	for command in commands:
		if not isinstance(command, str) or not re.fullmatch(r"(?:15[0-9]{9}|25[0-9]{6})", command):
			raise InvalidCommand("Malformed mulligan code: P1 needs 11 digits; P2 needs 8.")
		player = int(command[0])
		if player not in humans or player in selections:
			raise InvalidCommand(f"Player {player}: unexpected or duplicate human command.")
		if command not in views[player]["Available_Commands"]:
			raise InvalidCommand(f"Player {player}: command was not offered in the saved player view.")
		selections[player] = [int(command[i:i+3]) for i in range(2, len(command), 3) if command[i:i+3] != "000"]
	for player in (1, 2):
		if player not in humans:
			selections[player] = ai_selection(state[f"Player_{player}_Hand"], player, library or {})

	# No input/file validation below this point: both choices are accepted together.
	result = copy.deepcopy(state)
	rng = random.SystemRandom() if rng is None else rng
	for player in (1, 2):
		hand = result[f"Player_{player}_Hand"]
		deck = result[f"Player_{player}_Deck"]
		returned = selections[player]
		if not returned:
			continue
		# Position 01 is the bottom; the last stored deck ID is the top.
		replacements = [deck.pop() for _ in returned]
		hand[:] = [card for card in hand if card not in returned] + replacements
		deck.extend(returned)
		rng.shuffle(deck)
	result["Mulligan"] = False
	result["Game_Phase"] = "Turn"
	result["Round_number"] = 1
	result["Active_Player"] = 1
	result["Active_Opponent"] = 2
	return result
