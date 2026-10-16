"""Modification 2026-09-27: Vanilla play, explicit End Turn and concession.

Stable steps T10-T40/A10-A50/E10-E30 match readme/Turn-flow.md.
Modification 2026-09-27: Added passing, effect-only pseudo-turns, AFK removal,
round scoring/draws and crown results. Card effects and AI decisions remain deferred.
Modification 2026-10-07: Heroic Power replaces normal play; Stratagem blocks
round passing, gives a current-round board bonus with a unit, and is removed.
Modification 2026-10-07: Count completed input turns for AI Power timing;
reset each round and exclude automatic pseudo-turns.
"""

import copy
import random

from game_state import ensure_turn_fields, refresh_state
from mulligan import InvalidCommand, StateError


def action_code(player, action, card=0, source=0, position=0, destination=0):
	"""14 digits: P A CCC ZNN Z00 000; append-only placement, no targets."""
	return f"{player}{action}{card:03d}{source}{position:02d}{destination}00000"


def card_type(library, card):
	entry = library.get(f"Card_{card}")
	if not isinstance(entry, dict) or entry.get("Type") not in ("Unit", "Spell", "Location", "Stratagem"):
		raise StateError(f"Card {card}: missing or unsupported catalogue type.")
	return entry["Type"]


def legal_commands(state, player, library):
	if state["Game_Phase"] != "Turn" or state["Active_Player"] != player or state[f"Player_{player}_has_passed"]:
		return []
	commands = [action_code(player, 1)]  # Concession is always available in priority.
	played = state["Card_has_been_played"] == 1
	if played:
		commands.append(action_code(player, 6))
	else:
		if state["Stratagem_has_been_played"] == 0:
			commands.append(action_code(player, 0))
		if not state[f"Player_{player}_Power_Used"] and normal_hand(state, player):
			commands.append(action_code(player, 2))
	for position, card in enumerate(state[f"Player_{player}_Hand"], 1):
		kind = card_type(library, card)
		if kind == "Stratagem":
			if player != 1 or (not played and not normal_hand(state, player)):
				continue
		elif played:
			continue
		if position > 99:
			raise StateError("The current command format supports hand positions 01-99.")
		for destination in ((3, 4) if kind == "Unit" else (5,)):
			commands.append(action_code(player, 3, card, 2, position, destination))
	return commands


def start_turn(state):
	"""T10-T40: swap, open an own-turn frost bucket, trigger phase, priority."""
	if state["Game_Phase"] in ("Round_End", "Game_End"):
		raise StateError("Cannot start another turn after round or game end.")
	if (state["Active_Player"], state["Active_Opponent"]) not in ((1, 2), (2, 1)):
		raise StateError("Turn start needs two distinct player identities.")
	ensure_turn_fields(state)
	state["Active_Player"], state["Active_Opponent"] = state["Active_Opponent"], state["Active_Player"]
	state["Game_Phase"] = "Turn_Start"
	state["Last_Phases"].append("Turn_Start")
	state["Turn_number"] += 1
	state["Card_has_been_played"] = 0
	state["Stratagem_has_been_played"] = 0
	player = state["Active_Player"]
	for age in range(5, 1, -1):
		state[f"Player_{player}_Frost_Damage_Turn_{age}"] = state[f"Player_{player}_Frost_Damage_Turn_{age-1}"]
	state[f"Player_{player}_Frost_Damage_Turn_1"] = 0
	# T30: future start-turn effects (including frost damage) resolve here.
	# Duration advances on the owner's normal AND pseudo-turn; damage is deferred.
	for row in ("Front", "Back"):
		key = f"Player_{player}_{row}_Frost"
		state[key] = max(0, state[key] - 1)
	state[f"Frost on 2 Rows in P{player}"] = all(
		state[f"Player_{player}_{row}_Frost"] > 0 for row in ("Front", "Back")
	)
	state["Game_Phase"] = "Turn"
	state["Last_Phases"].append("Turn")


def normal_hand(state, player):
	"""The retained P1 stratagem never counts as a normal card or AFK penalty."""
	return [card for card in state[f"Player_{player}_Hand"] if card != state["Player_1_Stratagem"]]


def end_game(state, winner, reason):
	state["Winner"] = winner  # 0 means no sole winner (draw); phase distinguishes it.
	state["End_Reason"] = reason
	state["Game_Phase"] = "Game_End"
	state["Last_Phases"].append("Game_End")
	state["Active_Player"] = state["Active_Opponent"] = 0


def resolve_round(state):
	"""Q10-Q50: score, crown check BEFORE cleanup, then next-round draw/setup."""
	state["Game_Phase"] = "Round_End"
	state["Last_Phases"].append("Round_End")
	# Future round-end effects belong before the final score calculation.
	refresh_state(state)
	scores = [state[f"Player_{p}_Board_Strength"] for p in (1, 2)]
	winner = 0 if scores[0] == scores[1] else (1 if scores[0] > scores[1] else 2)
	for player in (1, 2):
		if winner in (0, player):
			state[f"Player_{player}_Crown"] += 1
	finished = [p for p in (1, 2) if state[f"Player_{p}_Crown"] >= 2]
	if finished:
		end_game(state, finished[0] if len(finished) == 1 else 0, "Crowns")
		return
	starter = state["Round_Starting_Player"]
	state["Previous_Round_Starting_Player"] = starter
	state["Round_Starting_Player"] = winner or (3 - starter)
	for player in (1, 2):
		for row in ("Front", "Back"):
			zone = state[f"Player_{player}_{row}_Row"]
			for card in zone:
				entry = state[f"Card_{card}"]
				entry["Current_Strength"] = entry["Base Strength"]
			state[f"Player_{player}_Graveyard"].extend(zone)
			zone.clear()
			state[f"Player_{player}_{row}_Frost"] = 0
		state[f"Frost on 2 Rows in P{player}"] = False
		state[f"Player_{player}_has_passed"] = False
		state[f"Player_{player}_Round_Bonus"] = 0
		state[f"Player_{player}_Completed_Turns_This_Round"] = 0
	# Frost history, hands (including unused stratagem) and global turn count persist.
	state["Round_number"] += 1
	state["Game_Phase"] = "Round_Start"
	state["Last_Phases"].append("Round_Start")
	for player in (1, 2):
		deck = state[f"Player_{player}_Deck"]
		for _ in range(min(3, len(deck))):
			state[f"Player_{player}_Hand"].append(deck.pop())
		state[f"Player_{player}_has_passed"] = not normal_hand(state, player)
	starter = state["Round_Starting_Player"]
	state["Active_Player"], state["Active_Opponent"] = 3 - starter, starter


def advance_to_input(state):
	"""T/E/Q loop: never publish input for passed players or recurse forever."""
	while True:
		if all(state[f"Player_{p}_has_passed"] for p in (1, 2)):
			resolve_round(state)
			if state["Game_Phase"] == "Game_End":
				return
			# Both new hands may be empty after short/empty-deck draws.
			continue
		start_turn(state)
		player = state["Active_Player"]
		if not normal_hand(state, player):
			state[f"Player_{player}_has_passed"] = True
		if not state[f"Player_{player}_has_passed"]:
			return
		# Passed players get start/end phases and own-turn history, never input.
		state["Game_Phase"] = "Turn_End"
		state["Last_Phases"].append("Turn_End")
		# E20: future end-turn effects also run for pseudo-turns.


def finish_turn(state):
	state[f"Player_{state['Active_Player']}_Completed_Turns_This_Round"] += 1
	state["Game_Phase"] = "Turn_End"
	state["Last_Phases"].append("Turn_End")
	# E20: future board end-turn effects. E30: stop if both passed.
	advance_to_input(state)


def first_turn(state):
	"""R10-R30: add P1 stratagem once and arrange the first swap to select P1."""
	ensure_turn_fields(state)
	stratagem = state["Player_1_Stratagem"]
	if any(stratagem in state[f"Player_{p}_{zone}"] for p in (1, 2)
		for zone in ("Deck", "Hand", "Front_Row", "Back_Row", "Graveyard")):
		raise StateError("P1 stratagem was already placed in a zone before round 1.")
	state["Player_1_Hand"].append(stratagem)
	state["Round_number"] = 1
	state["Round_Starting_Player"] = 1
	state["Previous_Round_Starting_Player"] = 0
	state["Turn_number"] = 0
	state["Game_Phase"] = "Round_Start"
	state["Last_Phases"] = ["Round_Start"]
	state["Active_Player"], state["Active_Opponent"] = 2, 1
	advance_to_input(state)


def validate_turn_state(room, state, views, library):
	if not isinstance(state, dict) or state.get("Room_number") != room:
		raise StateError("Motor state does not match the requested room.")
	if state.get("Game_Phase") != "Turn":
		raise InvalidCommand("Player actions require Turn phase.")
	if (state.get("Active_Player"), state.get("Active_Opponent")) not in ((1, 2), (2, 1)):
		raise StateError("Exactly one player must have turn priority.")
	if type(state.get("Card_has_been_played")) is not int or state["Card_has_been_played"] not in (0, 1):
		raise StateError("Card_has_been_played must be 0 or 1.")
	if type(state.get("Turn_number")) is not int or state["Turn_number"] < 1 or state.get("Mulligan") is not False:
		raise StateError("Turn state has inconsistent phase counters.")
	if state.get("Round_Starting_Player") not in (1, 2) or state.get("Previous_Round_Starting_Player") not in (0, 1, 2):
		raise StateError("Round starter tracking is missing or invalid; initialize a fresh match.")
	for player in (1, 2):
		if type(state.get(f"Player_{player}_has_passed")) is not bool:
			raise StateError("Round pass flags must be booleans.")
		if type(state.get(f"Player_{player}_Crown")) is not int or not 0 <= state[f"Player_{player}_Crown"] < 2:
			raise StateError("An ongoing game must have fewer than two crowns per player.")
		for row in ("Front", "Back"):
			value = state.get(f"Player_{player}_{row}_Frost")
			if type(value) is not int or value < 0:
				raise StateError("Frost duration must be a nonnegative integer.")
	if state[f"Player_{state['Active_Player']}_has_passed"]:
		raise StateError("A passed player cannot await input.")
	# Validate zone structure before looking up catalogue types or generating actions.
	refresh_state(state)
	for player in (1, 2):
		completed = state[f"Player_{player}_Completed_Turns_This_Round"]
		if type(completed) is not int or completed < 0:
			raise StateError("Completed playable turns must be nonnegative integers.")
	if type(state["Stratagem_has_been_played"]) is not int or state["Stratagem_has_been_played"] not in (0, 1):
		raise StateError("Stratagem turn flag must be 0 or 1.")
	for player in (1, 2):
		view = views.get(player)
		if not isinstance(view, dict) or view.get("Client_Player_Number") != player:
			raise StateError(f"Player {player}: invalid saved view.")
		for key in ("Active_Player", "Active_Opponent", "Game_Phase", "Turn_number", "Card_has_been_played", f"Player_{player}_Hand"):
			if view.get(key) != state[key]:
				raise StateError(f"Player {player}: stale or inconsistent saved view ({key}).")
		if view.get("Available_Commands") != legal_commands(state, player, library):
			raise StateError(f"Player {player}: saved legal commands are inconsistent.")


def apply_command(room, state, views, command, library):
	"""A10-A50: validate then update a copy; caller refreshes and publishes."""
	result = copy.deepcopy(state)
	validate_turn_state(room, result, views, library)
	player = result["Active_Player"]
	if command not in views[player]["Available_Commands"]:
		raise InvalidCommand("Command was not offered to the player with priority.")
	result["Last_Command"] = f"P {command}"
	result["Last_Phases"] = ["Turn"]
	action = int(command[1])
	if action == 1:
		end_game(result, result["Active_Opponent"], "Concede")
	elif action == 0:
		result[f"Player_{player}_has_passed"] = True
		finish_turn(result)
	elif action == 2:
		result[f"Player_{player}_Power_Used"] = True
		deck = result[f"Player_{player}_Deck"]
		if deck:
			result[f"Player_{player}_Hand"].append(deck.pop())
		# Empty deck still consumes Power and enables End Turn; no AFK penalty.
		result["Card_has_been_played"] = 1
	elif action == 3:
		card = int(command[2:5])
		destination = int(command[8])
		zone = {3: "Front_Row", 4: "Back_Row", 5: "Graveyard"}[destination]
		result[f"Player_{player}_Hand"].remove(card)
		if card_type(library, card) == "Stratagem":
			board = result[f"Player_{player}_Front_Row"] + result[f"Player_{player}_Back_Row"]
			if any(card_type(library, unit) == "Unit" for unit in board):
				result[f"Player_{player}_Round_Bonus"] += 5
			result[f"Card_{card}"].update(Exist=False, Location="0000")
			result["Stratagem_has_been_played"] = 1
			return result  # Keep prior normal-play flag; no graveyard entry.
		# A30: future play-from-hand handler. A40: board entry/battlecry or graveyard.
		result[f"Player_{player}_{zone}"].append(card)
		result["Card_has_been_played"] = 1
		# Retain priority: player must explicitly End Turn or Concede.
	elif action == 6:
		finish_turn(result)
	else:
		raise StateError("An unsupported action was generated as legal.")
	return result


def apply_timeout(room, state, views, library, rng=None):
	"""Back alone owns timer identity/expiry; T affects the current turn only."""
	result = copy.deepcopy(state)
	validate_turn_state(room, result, views, library)
	result["Last_Command"] = "T"
	result["Last_Phases"] = ["Turn"]
	player = result["Active_Player"]
	if result["Card_has_been_played"] == 0:
		eligible = normal_hand(result, player)
		if eligible:
			rng = rng if rng is not None else random.SystemRandom()
			card = rng.choice(eligible)
			result[f"Player_{player}_Hand"].remove(card)
			result[f"Card_{card}"].update(Exist=False, Location="0000")
	finish_turn(result)
	return result


def result_code(state):
	if state["Game_Phase"] == "Game_End":
		return 60 + state["Winner"] if state["Winner"] else 63
	return state["Active_Player"]
