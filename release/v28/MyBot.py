
import hlt
from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move, Square
import simulate
import time
import copy


cardinals = [NORTH, EAST, SOUTH, WEST]
start_time = time.time()
my_id, gamemap = hlt.get_init()


def eval_square(gamemap, square, num_neighbors=3):
	return square.production / max(1, square.strength) + sum(
		[(neighbor.production) / max(1, neighbor.strength) for neighbor in gamemap.neighbors(square, n=num_neighbors)])


def dijkstra(gamemap, target, start=None, available=None):
	if available is None:
		available = set([square for square in gamemap])
	else:
		available = set(available)

	queue = [square for square in available]
	came_from = {square: None for square in available}
	cost_so_far = {square: float("inf") for square in available}
	cost_so_far[target] = 0

	while queue:
		current_square = min(queue, key=lambda x: cost_so_far[x])
		queue.remove(current_square)

		for neighbor in gamemap.neighbors(current_square):
			if neighbor not in available:
				continue
			new_cost = cost_so_far[current_square] + current_square.strength
			if new_cost < cost_so_far[neighbor]:
				cost_so_far[neighbor] = new_cost
				came_from[neighbor] = current_square
	return {"cost_so_far": cost_so_far, "came_from": came_from}


def get_closest_squares(gamemap, my_id):
	my_square = [square for square in gamemap if square.owner == my_id][0]
	targets = [square for square in gamemap if square.owner not in set([0, my_id])]
	closest_squares = []
	for square in gamemap:
		add = True
		my_dist = gamemap.get_distance(square, my_square)
		for target in targets:
			if gamemap.get_distance(square, target) < my_dist:
				add = False
				break
		if add:
			closest_squares.append(square)
	return closest_squares


def get_relative_position(gamemap, from_square, to_square):
	if from_square == to_square:
		return STILL
	return min(cardinals,
			   key=lambda direction: gamemap.get_distance(gamemap.get_target(from_square, direction), to_square))


def find_combo_move(gamemap, square, target, my_id, max_distance=10, exclude=set()):
	strength_so_far = 0
	visited = set()
	prior = target
	goal_strength = target.strength
	combo_square = None
	combo_direction = None
	for num_distance in range(max_distance):
		neighbors = [square for square in gamemap.neighbors(prior) if
					 square.owner == my_id and square not in visited and square not in exclude]
		if len(neighbors) == 0:
			break
		best = max(neighbors, key=lambda square: square.strength)
		visited.add(best)
		strength_so_far += best.strength

		if strength_so_far > goal_strength:
			combo_square = best
			combo_direction = get_relative_position(gamemap, best, prior)
			if gamemap.get_distance(square, combo_square) <= 1:
				return Move(combo_square, combo_direction)
			break
		prior = best
		strength_so_far += best.production

def find_nearest_target_direction(gamemap, square):
	start_time = time.time()
	max_neighbors = min(gamemap.width, gamemap.height) // 2
	distances_empty = {d: max_neighbors for d in cardinals}
	distances_enemy = {}
	for d in (SOUTH, NORTH, WEST, EAST):
		current = square
		for distance in range(1, max_neighbors):
			current = gamemap.get_target(current, d)
			if current.strength > 0:
				if any([gamemap.get_target(current, d, steps).owner not in [0, my_id] for steps in range(1)]):
					distances_enemy[d] = distance
					break
				elif current.owner == 0:
					distances_empty[d] = distance
					break
	if len(distances_enemy) > 0:
		return (True, min(distances_enemy, key=lambda direction: distances_enemy[direction]))
	return  (False, min(distances_empty, key=lambda direction: distances_empty[direction]))


def heuristic(gamemap, square, exclude=set(), alpha=0.99, depth=1):
	if square.owner == my_id or depth < 1:
		return 0
	elif square.owner == 0 and square.strength > 0:
		score = square.production / max(1, square.strength)
	else:
		return sum(
			neighbor.strength for neighbor in gamemap.neighbors(square, 2) if
			neighbor.owner not in set([0, my_id]).union(exclude)) * 100
	return score + alpha * max([heuristic(gamemap, neighbor, exclude.union(square), alpha=alpha, depth=depth-1)
								for neighbor in gamemap.neighbors(square)])

def find_path(d_map, from_square, to_square):
	cost_so_far = d_map["cost_so_far"]
	came_from = d_map["came_from"]
	cur_square = from_square
	path = []
	while cur_square != to_square:
		cur_square = came_from[cur_square]
		path.append(cur_square)
	return path


def get_move(gamemap, square, exclude=set(), target=None):
	if square.strength == 0:
		return [Move(square, STILL)]
	if isinstance(target, Square):
		if target.owner != my_id:
			combo_move = find_combo_move(gamemap, square, target, my_id, exclude=exclude)
			if combo_move is not None:
				return [combo_move]
		elif square.strength > 10:
			return [Move(square, get_relative_position(gamemap, square, target))]
		return [Move(square, STILL)]

	attacking_squares = [neighbor for neighbor in gamemap.neighbors(square) if neighbor.owner != my_id and neighbor.strength == 0]

	if len(attacking_squares) > 0:
		target = max(attacking_squares, key=lambda attacking_square: heuristic(gamemap, attacking_square))
		return get_move(gamemap, square, exclude=exclude, target=target)

	target, direction = max(((neighbor, direction) for direction, neighbor in enumerate(gamemap.neighbors(square))
							 if neighbor.owner != my_id),
							default=(None, None),
							key=lambda t: heuristic(gamemap, t[0], depth=2))

	if target is not None and target.strength < square.strength:
		return [Move(square, direction)]

	if square.strength <= square.production * 5:
		return [Move(square, STILL)]

	border = any(neighbor.owner != my_id for neighbor in gamemap.neighbors(square))
	
	enemy_present, nearest_target_direction = find_nearest_target_direction(gamemap, square)

	new_square = gamemap.get_target(square, nearest_target_direction)
	new_square_strength = new_square.strength + square.strength
	opp_cost_move = max(0, new_square_strength - 255)

	if enemy_present == True or not border:
		if new_square.owner == my_id and opp_cost_move > 0:
			return [Move(square, nearest_target_direction), Move(new_square, nearest_target_direction)]
		return [Move(square, nearest_target_direction)]
	else:
		return [Move(square, STILL)]


def run_game(gamemap, attack_path=None, simulate_game=False, num_moves=float("inf"), stop_after_attack_path=False):
	num_move = 0
	moves = []
	if simulate:
		gamemap = copy.deepcopy(gamemap)

	while num_move < num_moves:
		num_move += 1
		if not simulate_game:
			gamemap.get_frame()

		already_moved = set()
		already_targeted = False
		moves = []
		available = [square for square in gamemap if square.owner == my_id]
		attack_square = None

		for square in available:
			if square in already_moved:
				continue
			if attack_path is not None and len(attack_path) > 0:
				attack_squares = [gamemap.contents[target.y][target.x] for target in attack_path]
				attack_square = min(attack_squares[::-1], key=lambda target: abs(gamemap.get_distance(target, square) - 1))
				if attack_square == attack_squares[-1]:
					# end of the road...
					attack_path = None
					if stop_after_attack_path:
						return num_move

			new_moves = get_move(gamemap, square, exclude=already_moved, target=attack_square)
			for move in new_moves:
				if move.square not in already_moved:
					moves.append(move)
					if move.direction != STILL:
						already_moved.add(move.square)
		
		# if not simulate:
		future_strengths = {}
		moves.sort(key=lambda move: move.square.strength, reverse=True)
		for idx, move in enumerate(moves):
			if move.direction == STILL:
				future_strengths[move.square] = future_strengths.get(move.square,0) + move.square.strength
			else:
				future_square = gamemap.get_target(move.square, move.direction)
				if future_square.owner == my_id:
					new_strength = future_strengths.get(future_square, 0) + move.square.strength
					if new_strength > 255:
						moves[idx] = Move(move.square, STILL)
					else:
						future_strengths[future_square] = new_strength

		if simulate_game:
			gamemap = simulate.update_gamemap(gamemap, moves)
		else:
			hlt.send_frame(moves)
	return simulate.score_gamemap(gamemap, my_id)


start_square = [square for square in gamemap if square.owner == my_id][0]
closest_squares = get_closest_squares(gamemap, my_id)

enemy = [enemy for enemy in gamemap if enemy.owner not in [my_id, 0]][0]
d_map = dijkstra(gamemap, enemy)
attack_path = find_path(d_map, start_square, enemy)
num_sim_moves = run_game(gamemap, attack_path, simulate_game=True, stop_after_attack_path=True)

sim_time_start = time.time()
best_production = 0
_, _, best_production = run_game(gamemap, None, simulate_game=True, num_moves=num_sim_moves)

time_per_sim = time.time() - sim_time_start
closest_squares.sort(key=lambda square: eval_square(gamemap, square), reverse=True)
best = None

# # Simulations
reviewed = []
for close_square in closest_squares:
	sim_time_start = time.time()
	if time.time() - start_time + time_per_sim > 10:
		break  # running out of time

	if min([gamemap.get_distance(close_square, reviewed_square) for reviewed_square in reviewed] or [float("inf")]) < 3:
		continue  # already reviewed a neighbor

	d_map = dijkstra(gamemap, close_square, available=closest_squares)

	attack_path = find_path(d_map, start_square, close_square)
	t, s, p = run_game(gamemap, attack_path, simulate_game=True, num_moves=num_sim_moves)
	if p > best_production:
		best = close_square
		best_production = p

	reviewed.append(close_square)
	time_per_sim = max(time_per_sim, time.time() - sim_time_start)

# End simulations
if best is not None:
	d_map = dijkstra(gamemap, best, start_square, available=closest_squares)
	attack_path = find_path(d_map, start_square, best)
else:
	attack_path = None

hlt.send_init("NewBot_v28")
run_game(gamemap, attack_path)
