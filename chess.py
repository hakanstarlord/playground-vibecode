from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

Color = str
Kind = str
Square = Tuple[int, int]


@dataclass(frozen=True)
class Piece:
    color: Color
    kind: Kind

    def symbol(self) -> str:
        symbols = {
            "P": ("♙", "♟"),
            "R": ("♖", "♜"),
            "N": ("♘", "♞"),
            "B": ("♗", "♝"),
            "Q": ("♕", "♛"),
            "K": ("♔", "♚"),
        }
        white, black = symbols[self.kind]
        return white if self.color == "w" else black


Board = Dict[Square, Piece]

FILES = "abcdefgh"


@dataclass
class GameState:
    board: Board
    current: Color
    castling_rights: Dict[Color, Dict[str, bool]]
    en_passant: Optional[Square]


def initial_board() -> Board:
    board: Board = {}
    for col in range(8):
        board[(6, col)] = Piece("w", "P")
        board[(1, col)] = Piece("b", "P")
    board[(7, 0)] = Piece("w", "R")
    board[(7, 7)] = Piece("w", "R")
    board[(0, 0)] = Piece("b", "R")
    board[(0, 7)] = Piece("b", "R")
    board[(7, 1)] = Piece("w", "N")
    board[(7, 6)] = Piece("w", "N")
    board[(0, 1)] = Piece("b", "N")
    board[(0, 6)] = Piece("b", "N")
    board[(7, 2)] = Piece("w", "B")
    board[(7, 5)] = Piece("w", "B")
    board[(0, 2)] = Piece("b", "B")
    board[(0, 5)] = Piece("b", "B")
    board[(7, 3)] = Piece("w", "Q")
    board[(0, 3)] = Piece("b", "Q")
    board[(7, 4)] = Piece("w", "K")
    board[(0, 4)] = Piece("b", "K")
    return board


def initial_state() -> GameState:
    return GameState(
        board=initial_board(),
        current="w",
        castling_rights={"w": {"K": True, "Q": True}, "b": {"K": True, "Q": True}},
        en_passant=None,
    )


def in_bounds(square: Square) -> bool:
    row, col = square
    return 0 <= row < 8 and 0 <= col < 8


def is_opponent(piece: Piece, other: Piece) -> bool:
    return piece.color != other.color


def sliding_moves(
    board: Board, start: Square, deltas: Iterable[Tuple[int, int]], piece: Piece
) -> List[Square]:
    moves: List[Square] = []
    for dr, dc in deltas:
        row, col = start
        while True:
            row += dr
            col += dc
            next_sq = (row, col)
            if not in_bounds(next_sq):
                break
            occupant = board.get(next_sq)
            if occupant:
                if is_opponent(piece, occupant):
                    moves.append(next_sq)
                break
            moves.append(next_sq)
    return moves


def pawn_moves(state: GameState, start: Square, piece: Piece) -> List[Square]:
    moves: List[Square] = []
    board = state.board
    direction = -1 if piece.color == "w" else 1
    row, col = start
    one_step = (row + direction, col)
    if in_bounds(one_step) and one_step not in board:
        moves.append(one_step)
        start_row = 6 if piece.color == "w" else 1
        two_step = (row + 2 * direction, col)
        if row == start_row and two_step not in board:
            moves.append(two_step)
    for dc in (-1, 1):
        capture = (row + direction, col + dc)
        if in_bounds(capture):
            occupant = board.get(capture)
            if occupant and is_opponent(piece, occupant):
                moves.append(capture)
    if state.en_passant:
        ep_row, ep_col = state.en_passant
        if ep_row == row + direction and abs(ep_col - col) == 1:
            moves.append(state.en_passant)
    return moves


def knight_moves(board: Board, start: Square, piece: Piece) -> List[Square]:
    moves: List[Square] = []
    deltas = [
        (-2, -1),
        (-2, 1),
        (-1, -2),
        (-1, 2),
        (1, -2),
        (1, 2),
        (2, -1),
        (2, 1),
    ]
    for dr, dc in deltas:
        square = (start[0] + dr, start[1] + dc)
        if not in_bounds(square):
            continue
        occupant = board.get(square)
        if occupant is None or is_opponent(piece, occupant):
            moves.append(square)
    return moves


def king_moves(board: Board, start: Square, piece: Piece) -> List[Square]:
    moves: List[Square] = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            square = (start[0] + dr, start[1] + dc)
            if not in_bounds(square):
                continue
            occupant = board.get(square)
            if occupant is None or is_opponent(piece, occupant):
                moves.append(square)
    return moves


def find_king(board: Board, color: Color) -> Optional[Square]:
    for square, piece in board.items():
        if piece.color == color and piece.kind == "K":
            return square
    return None


def attacks(board: Board, color: Color) -> List[Square]:
    squares: List[Square] = []
    for square, piece in board.items():
        if piece.color != color:
            continue
        if piece.kind == "P":
            direction = -1 if color == "w" else 1
            for dc in (-1, 1):
                target = (square[0] + direction, square[1] + dc)
                if in_bounds(target):
                    squares.append(target)
            continue
        if piece.kind == "N":
            squares.extend(knight_moves(board, square, piece))
            continue
        if piece.kind == "B":
            squares.extend(sliding_moves(board, square, [(-1, -1), (-1, 1), (1, -1), (1, 1)], piece))
            continue
        if piece.kind == "R":
            squares.extend(sliding_moves(board, square, [(-1, 0), (1, 0), (0, -1), (0, 1)], piece))
            continue
        if piece.kind == "Q":
            squares.extend(
                sliding_moves(
                    board,
                    square,
                    [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
                    piece,
                )
            )
            continue
        if piece.kind == "K":
            squares.extend(king_moves(board, square, piece))
    return squares


def is_in_check(state: GameState, color: Color) -> bool:
    king_square = find_king(state.board, color)
    if king_square is None:
        return False
    opponent = "b" if color == "w" else "w"
    return king_square in attacks(state.board, opponent)


def piece_moves(state: GameState, start: Square, piece: Piece) -> List[Square]:
    if piece.kind == "P":
        return pawn_moves(state, start, piece)
    if piece.kind == "N":
        return knight_moves(state.board, start, piece)
    if piece.kind == "B":
        return sliding_moves(state.board, start, [(-1, -1), (-1, 1), (1, -1), (1, 1)], piece)
    if piece.kind == "R":
        return sliding_moves(state.board, start, [(-1, 0), (1, 0), (0, -1), (0, 1)], piece)
    if piece.kind == "Q":
        return sliding_moves(
            state.board,
            start,
            [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
            piece,
        )
    if piece.kind == "K":
        return king_moves(state.board, start, piece)
    return []


def castling_moves(state: GameState, start: Square, piece: Piece) -> List[Square]:
    if piece.kind != "K":
        return []
    if is_in_check(state, piece.color):
        return []
    row = 7 if piece.color == "w" else 0
    if start != (row, 4):
        return []
    moves: List[Square] = []
    opponent = "b" if piece.color == "w" else "w"
    attacked = set(attacks(state.board, opponent))
    rights = state.castling_rights[piece.color]

    if rights.get("K"):
        squares = [(row, 5), (row, 6)]
        if all(square not in state.board for square in squares):
            if all(square not in attacked for square in squares):
                moves.append((row, 6))
    if rights.get("Q"):
        squares = [(row, 3), (row, 2), (row, 1)]
        if all(square not in state.board for square in squares):
            if all(square not in attacked for square in [(row, 3), (row, 2)]):
                moves.append((row, 2))
    return moves


def legal_moves(state: GameState, color: Color) -> List[Tuple[Square, Square]]:
    moves: List[Tuple[Square, Square]] = []
    for square, piece in state.board.items():
        if piece.color != color:
            continue
        for target in piece_moves(state, square, piece) + castling_moves(state, square, piece):
            candidate = apply_move(state, square, target, promotion_choice=None)
            if not is_in_check(candidate, color):
                moves.append((square, target))
    return moves


def apply_move(
    state: GameState,
    start: Square,
    end: Square,
    promotion_choice: Optional[str],
) -> GameState:
    board = dict(state.board)
    piece = board.pop(start)
    captured = board.get(end)

    # En passant capture
    if piece.kind == "P" and state.en_passant and end == state.en_passant and end not in state.board:
        direction = -1 if piece.color == "w" else 1
        captured_square = (end[0] + (-direction), end[1])
        board.pop(captured_square, None)

    # Castling move
    if piece.kind == "K" and abs(end[1] - start[1]) == 2:
        row = start[0]
        if end[1] == 6:
            rook_start = (row, 7)
            rook_end = (row, 5)
        else:
            rook_start = (row, 0)
            rook_end = (row, 3)
        rook = board.pop(rook_start)
        board[rook_end] = rook

    board[end] = piece

    # Promotion
    if piece.kind == "P":
        if (piece.color == "w" and end[0] == 0) or (piece.color == "b" and end[0] == 7):
            promoted = promotion_choice or "Q"
            board[end] = Piece(piece.color, promoted)

    new_castling = {"w": dict(state.castling_rights["w"]), "b": dict(state.castling_rights["b"])}

    # Update castling rights on king/rook move or capture
    if piece.kind == "K":
        new_castling[piece.color]["K"] = False
        new_castling[piece.color]["Q"] = False
    if piece.kind == "R":
        if start == (7, 0):
            new_castling["w"]["Q"] = False
        if start == (7, 7):
            new_castling["w"]["K"] = False
        if start == (0, 0):
            new_castling["b"]["Q"] = False
        if start == (0, 7):
            new_castling["b"]["K"] = False
    if captured and captured.kind == "R":
        if end == (7, 0):
            new_castling["w"]["Q"] = False
        if end == (7, 7):
            new_castling["w"]["K"] = False
        if end == (0, 0):
            new_castling["b"]["Q"] = False
        if end == (0, 7):
            new_castling["b"]["K"] = False

    # Update en passant target
    new_en_passant = None
    if piece.kind == "P" and abs(end[0] - start[0]) == 2:
        mid_row = (start[0] + end[0]) // 2
        new_en_passant = (mid_row, start[1])

    return GameState(
        board=board,
        current="b" if state.current == "w" else "w",
        castling_rights=new_castling,
        en_passant=new_en_passant,
    )


def square_name(square: Square) -> str:
    row, col = square
    return f"{FILES[col]}{8 - row}"


class ChessGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Satranç")
        self.state = initial_state()
        self.selected: Optional[Square] = None
        self.highlighted: List[Square] = []
        self.pending_move: Optional[Tuple[Square, Square]] = None

        self.canvas = tk.Canvas(root, width=640, height=640, bg="#d9d9d9", highlightthickness=0)
        self.canvas.pack(side=tk.TOP, padx=10, pady=10)

        self.status_var = tk.StringVar(value="Beyaz başlar.")
        status = tk.Label(root, textvariable=self.status_var)
        status.pack(side=tk.TOP, pady=(0, 10))

        self.canvas.bind("<Button-1>", self.on_click)
        self.draw_board()

    def draw_board(self) -> None:
        self.canvas.delete("all")
        size = 80
        for row in range(8):
            for col in range(8):
                x0 = col * size
                y0 = row * size
                x1 = x0 + size
                y1 = y0 + size
                fill = "#f0d9b5" if (row + col) % 2 == 0 else "#b58863"
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=fill)
        for square in self.highlighted:
            row, col = square
            x0 = col * size
            y0 = row * size
            x1 = x0 + size
            y1 = y0 + size
            self.canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                outline="#66ccff",
                width=4,
            )
        if self.selected:
            row, col = self.selected
            x0 = col * size
            y0 = row * size
            x1 = x0 + size
            y1 = y0 + size
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="#ffcc00", width=4)
        for square, piece in self.state.board.items():
            row, col = square
            x = col * size + size / 2
            y = row * size + size / 2
            self.canvas.create_text(
                x,
                y,
                text=piece.symbol(),
                font=("Arial", 36),
            )

    def prompt_promotion(self, color: Color) -> str:
        choice = tk.StringVar(value="Q")
        window = tk.Toplevel(self.root)
        window.title("Terfi Seçimi")
        tk.Label(window, text="Piyon terfi: seçiniz").pack(padx=10, pady=10)

        def set_choice(kind: str) -> None:
            choice.set(kind)
            window.destroy()

        for kind, label in [("Q", "Vezir"), ("R", "Kale"), ("B", "Fil"), ("N", "At")]:
            tk.Button(window, text=label, command=lambda k=kind: set_choice(k)).pack(
                padx=10, pady=4, fill=tk.X
            )
        window.grab_set()
        window.wait_window()
        return choice.get()

    def apply_selected_move(self, start: Square, end: Square) -> None:
        piece = self.state.board.get(start)
        promotion_choice: Optional[str] = None
        if piece and piece.kind == "P":
            if (piece.color == "w" and end[0] == 0) or (piece.color == "b" and end[0] == 7):
                promotion_choice = self.prompt_promotion(piece.color)
        self.state = apply_move(self.state, start, end, promotion_choice)

    def on_click(self, event: tk.Event) -> None:
        size = 80
        col = event.x // size
        row = event.y // size
        if not in_bounds((row, col)):
            return
        square = (row, col)
        piece = self.state.board.get(square)
        if self.selected is None:
            if piece is None or piece.color != self.state.current:
                return
            self.selected = square
            self.highlighted = [
                end for start, end in legal_moves(self.state, self.state.current) if start == square
            ]
            self.draw_board()
            return

        if square == self.selected:
            self.selected = None
            self.highlighted = []
            self.draw_board()
            return

        if (self.selected, square) in legal_moves(self.state, self.state.current):
            self.apply_selected_move(self.selected, square)
            self.selected = None
            self.highlighted = []
            player = "Beyaz" if self.state.current == "w" else "Siyah"
            self.status_var.set(f"Sıra: {player}")
            self.draw_board()
            return

        if piece and piece.color == self.state.current:
            self.selected = square
            self.highlighted = [
                end for start, end in legal_moves(self.state, self.state.current) if start == square
            ]
            self.draw_board()


def main() -> None:
    root = tk.Tk()
    ChessGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()