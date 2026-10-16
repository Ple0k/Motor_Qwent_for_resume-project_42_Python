"""Modification 2026-09-27: Central state checks before publishing any views.

Stable flow labels C10-C50 are documented in readme/Turn-flow.md.
Modification 2026-10-07: Add power/stratagem tracking, round board bonus and
public hand/deck/graveyard counts; recompute bonus once, never cumulatively.
Modification 2026-10-07: Private completed playable-turn counters support AI
Power timing; automatic pseudo-turns do not increment these counters.
"""

from mulligan import StateError


ZONES = {"Deck": 1, "Hand": 2, "Front_Row": 3, "Back_Row": 4, "Graveyard": 5}


def ensure_turn_fields(state):
	"""Allow older initialized rooms to acquire newly introduced counters."""
	state.setdefault("Card_has_been_played", 0)
	state.setdefault("Stratagem_has_been_played", 0)
	state.setdefault("Turn_number", 0)
	state.setdefault("Last_Command", "")
	state.setdefault("Last_Phases", [])
	state.setdefault("Winner", 0)
	state.setdefault("End_Reason", "")
	for player in (1, 2):
		state.setdefault(f"Player_{player}_Completed_Turns_This_Round", 0)
		state.setdefault(f"Player_{player}_Power_Used", False)
		state.setdefault(f"Player_{player}_Round_Bonus", 0)
		for age in range(1, 6):
			state.setdefault(f"Player_{player}_Frost_Damage_Turn_{age}", 0)


def refresh_state(state):
	"""C10-C50: locations, strengths, faction flags, statuses, frost totals."""
	ensure_turn_fields(state)
	# C10: zone membership and locations.
	seen = set()
	for player in (1, 2):
		for zone, code in ZONES.items():
			cards = state.get(f"Player_{player}_{zone}")
			if not isinstance(cards, list):
				raise StateError(f"Player {player}: {zone} must be a list.")
			for position, card in enumerate(cards, 1):
				if type(card) is not int or card in seen or not isinstance(state.get(f"Card_{card}"), dict):
					raise StateError("Zone contents have missing or duplicate card records.")
				seen.add(card)
				state[f"Card_{card}"]["Location"] = f"{player}{code}{position:02d}"
				state[f"Card_{card}"]["Exist"] = True
	# C20: row and board strengths.
	for player in (1, 2):
		bonus = state[f"Player_{player}_Round_Bonus"]
		if type(bonus) is not int or bonus < 0:
			raise StateError("Round bonus must be a nonnegative integer.")
		if type(state[f"Player_{player}_Power_Used"]) is not bool:
			raise StateError("Power use must be a boolean.")
		for row in ("Front", "Back"):
			strength = 0
			for card in state[f"Player_{player}_{row}_Row"]:
				value = state[f"Card_{card}"].get("Current_Strength")
				if type(value) is not int:
					raise StateError(f"Card {card}: strength must be an integer.")
				strength += value
			state[f"Player_{player}_{row}_Row_Strength"] = strength
		state[f"Player_{player}_Board_Strength"] = bonus + sum(
			state[f"Player_{player}_{row}_Row_Strength"] for row in ("Front", "Back")
		)
		# C25: public counts include stratagem in hand, never out-of-game records.
		for zone in ("Hand", "Deck", "Graveyard"):
			state[f"Player_{player}_{zone}_Count"] = len(state[f"Player_{player}_{zone}"])
	# C30: only keep deck-presence flags relevant to the chosen faction.
	for player in (1, 2):
		deck = state[f"Player_{player}_Deck"]
		for name, faction, short_id in (("Roach", "Witcher", 8), ("Winter Queen", "Wild Hunt", 32)):
			key = f"Player {player} {name} in Deck"
			if state[f"Player_{player}_Decklist"] == faction:
				state[key] = player * 100 + short_id in deck
			else:
				state.pop(key, None)
	# C40: refresh all retained card records, regardless of zone.
	for key, entry in state.items():
		if not key.startswith("Card_"):
			continue
		# Card_has_been_played is a turn flag, not a card record.
		if not key[5:].isdigit():
			continue
		if not isinstance(entry, dict):
			raise StateError(f"{key}: invalid card record.")
		base, current = entry.get("Base Strength"), entry.get("Current_Strength")
		if type(base) is not int or type(current) is not int:
			raise StateError(f"{key}: strengths must be integers.")
		entry["Boosted"] = current > base
		entry["Hurt"] = current < base
	# C50: publish rolling totals after any current-turn damage updates.
	for player in (1, 2):
		buckets = [state[f"Player_{player}_Frost_Damage_Turn_{age}"] for age in range(1, 6)]
		if any(type(value) is not int or value < 0 for value in buckets):
			raise StateError("Frost damage history must contain nonnegative integers.")
		state[f"Frost Dmg on last 5 turns P{player}"] = sum(buckets)
