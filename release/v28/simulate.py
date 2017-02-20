from hlt import *
import copy

def score_gamemap(gamemap, my_id):
    """ Scores a frame by strength, production and territories controlled by players
    input: 
        board: Array, [owner, enemies, strengths, productions]
        players: (Optional) The players to score
    output:
        player territory + strength + production
    """
    territory = sum([1 for square in gamemap if square.owner == my_id])
    strength = sum([square.strength for square in gamemap if square.owner == my_id])
    prod = sum([square.production for square in gamemap if square.owner == my_id])
    # return "territory: {}, strength: {}, prod: {}".format(territory, strength, prod)
    return territory, strength, prod

def update_gamemap(gamemap, moves, accrue_production=True):
    """ Updates board in place to reflect move. Returns new position.
    Input:
        gamemap: GameMap
        moves: List, [Move(...),...]        
    """
    return_gamemap = gamemap
    exclude_from_production_coords = set()
    for move in moves:
        square, direction = return_gamemap.contents[move.square.y][move.square.x], move.direction
        if direction != STILL and square.owner != 0:
            new_square = return_gamemap.get_target(square, direction)
            exclude_from_production_coords.add((square.x, square.y))
            if new_square.owner == square.owner:
                    return_gamemap.contents[new_square.y][new_square.x] = Square(
                        x=new_square.x, y=new_square.y, owner=new_square.owner, strength=min(255, square.strength + new_square.strength), production=new_square.production)
            else:
                new_owner = square.owner if square.strength >= new_square.strength else new_square.owner
                if new_owner == square.owner:
                    exclude_from_production_coords.add((new_square.x, new_square.y))
                new_strength = max(square.strength, new_square.strength) - min(square.strength, new_square.strength)
                return_gamemap.contents[new_square.y][new_square.x] = Square(
                    x=new_square.x, y=new_square.y, owner=new_owner, strength=new_strength, production=new_square.production)

            return_gamemap.contents[square.y][square.x] = Square(
                    x=square.x, y=square.y, owner=square.owner, strength=0, production=square.production)
    if accrue_production:
        for square in return_gamemap:
            if square.owner != 0 and (square.x, square.y) not in exclude_from_production_coords:
                return_gamemap.contents[square.y][square.x] = Square(
                        x=square.x, y=square.y, owner=square.owner, strength=square.strength + square.production, production=square.production)
                return_gamemap.contents[square.y][square.x] = Square(
                        x=square.x, y=square.y, owner=square.owner, strength=min(255, square.strength + square.production), production=square.production)
    return return_gamemap
