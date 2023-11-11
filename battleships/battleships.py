from battleships.ai import AIState, RandomState
from common import clear
from enum import Enum
from types import UnionType
from typing import Optional, Type, Iterator, Self
from vec2 import Vec2, vec_scalar_multiply, vec_add, vec_invert
from random import randint, choice
from time import sleep


class User:
    def __init__(self) -> None:
        self.board: MainBoard = new_board(SquareState.EMPTY, BOARD_HEIGHT, BOARD_WIDTH)
        self.ships: list[Ship] = []
        self.knowledge: KnowledgeBoard = new_board(
            KnowledgeSquareState.UNKNOWN, BOARD_HEIGHT, BOARD_WIDTH
        )


class Ship:
    def __init__(self, squares: list[Vec2]) -> None:
        self.hits: int = 0
        self.sunk: bool = False
        self.squares: list[Vec2] = squares

    def hit(self) -> bool:
        # Returns True if ship is sunk
        self.hits += 1
        if self.hits == len(self.squares):
            self.sunk = True
            return True
        return False


class Orientation(Enum):
    N = Vec2(0, -1)
    E = Vec2(1, 0)
    S = Vec2(0, 1)
    W = Vec2(-1, 0)


class SquareState(Enum):
    EMPTY = " "
    SHIP = "#"
    MISS = "·"
    HIT = "X"


class KnowledgeSquareState(Enum):
    UNKNOWN = " "
    MISS = "·"
    HIT = "X"


# Constants
LOOP_MAX = 100000
BOARD_WIDTH = 10
BOARD_HEIGHT = 10
SHIP_LENGTHS = [5, 4, 3, 3, 2]
# Types
MainBoard: Type = list[list[SquareState]]
KnowledgeBoard: Type = list[list[KnowledgeSquareState]]
Board: UnionType = MainBoard | KnowledgeBoard


def new_board(default, height, width) -> Board:
    return [[default for _ in range(width)] for _ in range(height)]


def square_in_board(square: Vec2, board: Board) -> bool:
    width = len(board[0])
    height = len(board)
    return 0 <= square.x < width and 0 <= square.y < height


def extend(origin: Vec2, direction: Vec2, length: int) -> Vec2:
    return vec_add(origin, vec_scalar_multiply(direction, length))


def new_valid_ship(
    origin: Vec2, orientation: Orientation, length: int, owner: User
) -> Optional[Ship]:
    squares = [extend(origin, orientation.value, i) for i in range(length)]
    # Confirm all squares are in the board
    if not all(square_in_board(square, owner.board) for square in squares):
        return None
    # Check if any already placed ships' squares overlap with our squares
    if any(
        len([s for s in squares if s in existing_ship.squares]) > 0
        for existing_ship in owner.ships
    ):
        return None

    new_ship = Ship(squares)
    owner.ships.append(new_ship)
    for square in new_ship.squares:
        owner.board[square.y][square.x] = SquareState.SHIP

    return new_ship


class FireResult(Enum):
    HIT = 1
    MISS = 2
    FAIL = 3
    SUNK = 4


def fire_missile(coord: Vec2, source: User, target: User) -> FireResult:
    # If already fired at this square
    if source.knowledge[coord.y][coord.x] != KnowledgeSquareState.UNKNOWN:
        return FireResult.FAIL
    # Check if shot is a hit or a miss
    for ship in target.ships:
        if coord in ship.squares:
            sunk = ship.hit()
            target.board[coord.y][coord.x] = SquareState.HIT
            source.knowledge[coord.y][coord.x] = KnowledgeSquareState.HIT
            return FireResult.SUNK if sunk else FireResult.HIT
    else:
        source.knowledge[coord.y][coord.x] = KnowledgeSquareState.MISS
        target.board[coord.y][coord.x] = SquareState.MISS
        return FireResult.MISS


def display_board(board: Board) -> None:
    height = len(board)
    width = len(board[0])
    print("│   " + " ".join([str(i) for i in range(width)]) + "   │")
    for i in range(height):
        print(f"│ {chr(i + 65)} ", end="")
        print(*[square.value for square in board[i]], sep=" ", end="   │\n")


def display_boards(*boards: Board) -> None:
    clear()
    board_width = len(boards[0][0])
    line_width = board_width * 2 + 5
    print("┌" + "─" * line_width + "┐")
    for i, board in enumerate(boards):
        display_board(board)
        if i < len(boards) - 1:
            print("├" + "─" * line_width + "┤")
        elif i == len(boards) - 1:
            print("└" + "─" * line_width + "┘")


def print_message(text: str, *boards: Board) -> None:
    display_boards(*boards)
    print(text)
    sleep(len(text.split(" ")) / 4 + 0.5)


def decode_notation(text: str, board: Board) -> Optional[Vec2]:
    if len(text) != 2:
        return None
    try:
        # "a" = 0
        row = ord(text.lower()[0]) - 97
        column = int(text[1])
        if not square_in_board(Vec2(column, row), board):
            return None
    except ValueError:
        return None

    return Vec2(column, row)


def random_square(board: Board, matching: SquareState | KnowledgeSquareState) -> Vec2:
    board_height = len(board)
    board_width = len(board[0])
    for _ in range(LOOP_MAX):
        coord = Vec2(randint(0, board_width - 1), randint(0, board_height - 1))
        if board[coord.y][coord.x] == matching:
            return coord
    exit(1)


def battleships() -> None:
    # AI ship placement
    ai = User()
    for length in SHIP_LENGTHS:
        new_ship = None
        while new_ship is None:
            new_ship = new_valid_ship(
                random_square(ai.board, SquareState.EMPTY),
                choice(list(Orientation)),
                length,
                ai,
            )

    # Player ship placement
    player = User()
    available_ship_lengths = SHIP_LENGTHS
    # --------------- TEST ----------
    ships: list[tuple[Vec2, Orientation, int]] = [
        (Vec2(1, 1), Orientation.E, 2),
        (Vec2(1, 3), Orientation.E, 3),
        (Vec2(4, 5), Orientation.E, 4),
        (Vec2(9, 2), Orientation.S, 5),
        (Vec2(0, 7), Orientation.S, 3),
    ]
    [new_valid_ship(s[0], s[1], s[2], player) for s in ships]
    available_ship_lengths = []
    # ----------------- END TEST -------------
    default_boards = [ai.board, player.knowledge, player.board]
    while len(available_ship_lengths) > 0:
        display_boards(*default_boards)

        inp = input("Enter start/end points of a ship to place it (e.g. c0 c2): ")
        if inp == "exit":
            return
        point_a, point_b = (decode_notation(i, player.board) for i in inp.split(" "))
        if point_a is None or point_b is None:
            print_message(
                "Error: One or more points invalid", player.knowledge, player.board
            )
            continue

        if point_a.y == point_b.y:
            displacement = point_b.x - point_a.x
            orientation = Orientation.E if displacement > 0 else Orientation.W
        elif point_a.x == point_b.x:
            displacement = point_b.y - point_a.y
            orientation = Orientation.S if displacement > 0 else Orientation.N
        else:
            # Diagonal
            continue

        length = abs(displacement) + 1
        if length in available_ship_lengths:
            new_ship = new_valid_ship(point_a, orientation, length, player)
            if new_ship is not None:
                available_ship_lengths.remove(length)
        else:
            print_message(
                "Error: Ship length not available", player.knowledge, player.board
            )

    # Main game loop
    ai_state: AIState = RandomState()
    while True:
        # Player turn
        result = FireResult.FAIL
        while result == FireResult.FAIL:
            display_boards(*default_boards)
            inp = input("Enter square to fire missile (e.g. c4): ")
            square = decode_notation(inp, player.board)
            if square is None:
                print_message("Error: invalid square", *default_boards)
                continue
            result = fire_missile(square, player, ai)
            match result:
                case FireResult.SUNK:
                    print_message("Enemy: You sunk my battleship!", *default_boards)
                case FireResult.MISS:
                    print_message("Enemy: Miss!", *default_boards)
                case FireResult.HIT:
                    print_message("Enemy: Hit...", *default_boards)
                case FireResult.FAIL:
                    print_message("Error: Already fired there", *default_boards)

        # AI turn
        state = ai_state.update(ai, player)
        if state is not None:
            ai_state = state

        # Win condition
        if all(ship.sunk for ship in player.ships):
            display_boards(*default_boards)
            input("You LOST! Press enter...")
            break
        if all(ship.sunk for ship in ai.ships):
            display_boards(*default_boards)
            input("You WON! Press enter...")
            break


if __name__ == "__main__":
    while True:
        battleships()
