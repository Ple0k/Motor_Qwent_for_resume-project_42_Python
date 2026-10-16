"""Modification 2026-10-07: Deterministic AI policy and private command projections.

Generated files live only in ai_prediction/XX; user explicitly authorized their
cleanup. Sources, archives, real room files and unknown entries are never deleted.
Real and simulated actions share turns.apply_command; no hand-written score model.
"""

import json
from pathlib import Path
import re

from game_state import refresh_state
from mulligan import StateError
from turns import action_code, apply_command, legal_commands, normal_hand


def prediction_folder(output_dir, room, reset=False):
	"""Reject symlinks/unknown files before clearing any generated predictions."""
	if not re.fullmatch(r"[0-9]{2}", room):
		raise StateError("Invalid prediction room identifier.")
	root = Path(output_dir) / "ai_prediction"
	folder = root / room
	for path in (root, folder):
		if path.is_symlink() or (path.exists() and not path.is_dir()):
			raise StateError("Prediction directory must be a real directory, not a link.")
	entries = list(folder.iterdir()) if folder.exists() else []
	for path in entries:
		if path.is_symlink() or not path.is_file() or not re.fullmatch(r"[12][0-9]{13}\.json", path.name):
			raise StateError("Prediction folder contains an unexpected entry; nothing was cleared.")
	for path in entries:
		path.unlink()
	if reset and folder.exists():
		folder.rmdir()
	root.mkdir(mode=0o700, exist_ok=True)
	folder.mkdir(mode=0o700, exist_ok=True)
	return folder


def margin_rank(margin):
	"""Exact preference: +1, 0, -1, +2, -2, +3, -3, ... ."""
	if margin == 1:
		return 0
	if margin == 0:
		return 1
	return 2 * abs(margin) if margin < 0 else 2 * margin - 1


def special_command(state, start_margin):
	"""Choose eligible Stratagem, then Power, then End/Pass; else simulate."""
	player = state["Active_Player"]
	opponent = 3 - player
	offers = state["Available_Commands"][str(player)]
	stratagem = state["Player_1_Stratagem"]
	if len(normal_hand(state, player)) == 1:
		for command in offers:
			if command[1] == "3" and int(command[2:5]) == stratagem:
				return command
	power = action_code(player, 2)
	round_number = state["Round_number"]
	first_turn = state[f"Player_{player}_Completed_Turns_This_Round"] == 0
	use_power = (
		(round_number == 1 and not state[f"Player_{opponent}_has_passed"]
			and state[f"Player_{opponent}_Completed_Turns_This_Round"] > 0
			and start_margin > 0)
		or (round_number == 2 and first_turn and state[f"Player_{opponent}_Crown"] == 1
			and state[f"Player_{player}_Crown"] == 0)
		or (round_number == 3 and first_turn)
	)
	if power in offers and use_power:
		return power
	end = action_code(player, 6)
	if end in offers:
		return end
	passing = action_code(player, 0)
	if passing in offers and (
		(state[f"Player_{opponent}_Crown"] == 0 and abs(start_margin) >= 5)
		or (state[f"Player_{opponent}_has_passed"] and start_margin > 0)
	):
		return passing
	return None


def choose_command(room, state, views, library, output_dir, start_margin):
	"""Save independent card projections; pick best margin without hidden input."""
	command = special_command(state, start_margin)
	if command is not None:
		return command
	player = state["Active_Player"]
	candidates = [c for c in state["Available_Commands"][str(player)]
		if c[1] == "3" and int(c[2:5]) != state["Player_1_Stratagem"]]
	if not candidates:
		raise StateError("AI has neither an eligible control action nor a normal play.")
	folder = prediction_folder(output_dir, room)
	best = None
	for command in candidates:
		projected = apply_command(room, state, views, command, library)
		refresh_state(projected)
		projected["Available_Commands"] = {
			str(p): legal_commands(projected, p, library) for p in (1, 2)
		}
		projected["_comment"] = "Modification 2026-10-07: Private AI command projection, not a live room state."
		(folder / f"{command}.json").write_text(json.dumps(projected, indent="\t") + "\n", encoding="utf-8")
		margin = projected[f"Player_{player}_Board_Strength"] - projected[f"Player_{3-player}_Board_Strength"]
		choice = (margin_rank(margin), command)
		if best is None or choice < best:
			best = choice
	# Current effects are deterministic. A future random handler needs an agreed
	# replay/sampling policy before this real-action reapplication can be retained.
	return best[1]
