from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox
from typing import Dict, List, Optional, Tuple

Player = str  # "W" or "B"
PointIndex = int  # 1..24


@dataclass
class Point:
    owner: Optional[Player] = None
    count: int = 0


class BackgammonGame:
    def __init__(self) -> None:
        self.points: Dict[PointIndex, Point] = {i: Point() for i in range(1, 25)}
        self.bar: Dict[Player, int] = {"W": 0, "B": 0}
        self.borne_off: Dict[Player, int] = {"W": 0, "B": 0}
        self.current_player: Player = "W"
        self.selected_source: Optional[Tuple[str, int]] = None
        self.dice_values: List[int] = []
        self.setup_initial_position()

    def setup_initial_position(self) -> None:
        # Standard backgammon setup
        for p in self.points.values():
            p.owner = None
            p.count = 0
        self.place("W", 24, 2)
        self.place("W", 13, 5)
        self.place("W", 8, 3)
        self.place("W", 6, 5)

        self.place("B", 1, 2)
        self.place("B", 12, 5)
        self.place("B", 17, 3)
        self.place("B", 19, 5)

    def place(self, owner: Player, point: int, count: int) -> None:
        self.points[point].owner = owner
        self.points[point].count = count

    def roll_dice(self) -> List[int]:
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        if d1 == d2:
            self.dice_values = [d1] * 4
        else:
            self.dice_values = [d1, d2]
        return self.dice_values.copy()

    def direction(self, player: Player) -> int:
        return -1 if player == "W" else 1

    def home_range(self, player: Player) -> range:
        return range(1, 7) if player == "W" else range(19, 25)

    def entry_from_bar(self, die: int, player: Player) -> int:
        # White enters from 24 -> 19, Black enters from 1 -> 6
        return 25 - die if player == "W" else die

    def can_land(self, player: Player, point: int) -> bool:
        target = self.points[point]
        return target.owner in (None, player) or (target.owner != player and target.count == 1)

    def all_in_home(self, player: Player) -> bool:
        if self.bar[player] > 0:
            return False
        home = self.home_range(player)
        total_home = sum(self.points[p].count for p in home if self.points[p].owner == player)
        return total_home + self.borne_off[player] == 15

    def furthest_checker_point(self, player: Player) -> Optional[int]:
        positions = [i for i in range(1, 25) if self.points[i].owner == player and self.points[i].count > 0]
        if not positions:
            return None
        return max(positions) if player == "W" else min(positions)

    def can_bear_off_from(self, player: Player, src: int, die: int) -> bool:
        if not self.all_in_home(player):
            return False
        if player == "W":
            exact = src - die == 0
            if exact:
                return True
            if src - die < 0:
                furthest = self.furthest_checker_point(player)
                return furthest == src
            return False

        exact = src + die == 25
        if exact:
            return True
        if src + die > 25:
            furthest = self.furthest_checker_point(player)
            return furthest == src
        return False

    def legal_moves_for_source(self, source: Tuple[str, int], player: Player) -> List[Tuple[int, Optional[int]]]:
        moves: List[Tuple[int, Optional[int]]] = []
        location, src = source

        if self.bar[player] > 0 and location != "bar":
            return moves

        for die in sorted(set(self.dice_values)):
            if location == "bar":
                target = self.entry_from_bar(die, player)
                if self.can_land(player, target):
                    moves.append((die, target))
                continue

            step = die * self.direction(player)
            target = src + step
            if 1 <= target <= 24:
                if self.can_land(player, target):
                    moves.append((die, target))
            elif self.can_bear_off_from(player, src, die):
                moves.append((die, None))

        return moves

    def legal_sources(self, player: Player) -> List[Tuple[str, int]]:
        if self.bar[player] > 0:
            return [("bar", 0)] if self.legal_moves_for_source(("bar", 0), player) else []

        sources: List[Tuple[str, int]] = []
        for i in range(1, 25):
            point = self.points[i]
            if point.owner == player and point.count > 0:
                moves = self.legal_moves_for_source(("point", i), player)
                if moves:
                    sources.append(("point", i))
        return sources

    def use_die(self, die: int) -> None:
        self.dice_values.remove(die)

    def move_checker(self, source: Tuple[str, int], die: int, target: Optional[int], player: Player) -> bool:
        moves = self.legal_moves_for_source(source, player)
        if (die, target) not in moves:
            return False

        loc, src = source
        if loc == "bar":
            self.bar[player] -= 1
        else:
            self.points[src].count -= 1
            if self.points[src].count == 0:
                self.points[src].owner = None

        if target is None:
            self.borne_off[player] += 1
        else:
            dest = self.points[target]
            if dest.owner not in (None, player) and dest.count == 1:
                hit_player = dest.owner
                self.bar[hit_player] += 1
                dest.owner = None
                dest.count = 0

            if dest.owner is None:
                dest.owner = player
                dest.count = 1
            else:
                dest.count += 1

        self.use_die(die)
        return True


class BackgammonUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Tavla - 2 Oyuncu")
        self.game = BackgammonGame()
        self.point_polygons: Dict[int, Tuple[int, int, int, int]] = {}
        self.selected_moves: List[Tuple[int, Optional[int]]] = []

        self.canvas = tk.Canvas(root, width=1100, height=700, bg="#f7efe3", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.controls = tk.Frame(root, bg="#f7efe3")
        self.controls.pack(fill="x", padx=10, pady=6)

        self.status_label = tk.Label(self.controls, text="", font=("Arial", 13, "bold"), bg="#f7efe3")
        self.status_label.pack(side="left", padx=8)

        self.info_label = tk.Label(self.controls, text="", font=("Arial", 11), bg="#f7efe3")
        self.info_label.pack(side="left", padx=18)

        self.end_turn_btn = tk.Button(
            self.controls,
            text="Hamleyi Bitir",
            font=("Arial", 11, "bold"),
            command=self.confirm_end_turn,
            bg="#d2b48c",
            activebackground="#c49c72",
        )
        self.end_turn_btn.pack(side="right", padx=10)

        self.canvas.bind("<Button-1>", self.on_click)

        self.start_turn(initial=True)

    def start_turn(self, initial: bool = False) -> None:
        dice = self.game.roll_dice()
        player_name = "Beyaz" if self.game.current_player == "W" else "Siyah"
        self.game.selected_source = None
        self.selected_moves = []
        self.draw_board()

        if not initial:
            messagebox.showinfo("Yeni Zar", f"{player_name} için zar: {dice}")

        if not self.game.legal_sources(self.game.current_player):
            messagebox.showinfo("Hamle Yok", f"{player_name} için oynanabilir hamle yok. Tur geçiyor.")
            self.game.current_player = "B" if self.game.current_player == "W" else "W"
            self.start_turn()

    def board_coords(self) -> Tuple[int, int, int, int]:
        x0, y0, x1, y1 = 80, 60, 1020, 620
        return x0, y0, x1, y1

    def draw_board(self) -> None:
        self.canvas.delete("all")
        x0, y0, x1, y1 = self.board_coords()
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#d7a86e", outline="#5c3b1e", width=5)

        mid = (x0 + x1) // 2
        self.canvas.create_rectangle(mid - 35, y0, mid + 35, y1, fill="#bf8a4f", outline="#5c3b1e", width=3)

        self.point_polygons.clear()
        self.draw_points(x0, y0, x1, y1)
        self.draw_checkers(x0, y0, x1, y1)
        self.draw_side_areas(x0, y0, x1, y1)
        self.update_labels()

    def draw_points(self, x0: int, y0: int, x1: int, y1: int) -> None:
        colors = ["#8b5a2b", "#f5deb3"]
        triangle_w = (x1 - x0 - 70) // 12
        idx = 0

        # top: 13..24 left-to-right as viewed on board
        for point in list(range(13, 19)) + list(range(19, 25)):
            col = idx if idx < 6 else idx + 2
            left = x0 + col * triangle_w
            right = left + triangle_w
            cx = (left + right) // 2
            self.canvas.create_polygon(left, y0, right, y0, cx, y0 + 220, fill=colors[idx % 2], outline="#5c3b1e")
            self.point_polygons[point] = (left, y0, right, y0 + 220)
            self.canvas.create_text(cx, y0 + 235, text=str(point), font=("Arial", 10, "bold"))
            idx += 1

        idx = 0
        # bottom: 12..1 left-to-right
        for point in list(range(12, 6, -1)) + list(range(6, 0, -1)):
            col = idx if idx < 6 else idx + 2
            left = x0 + col * triangle_w
            right = left + triangle_w
            cx = (left + right) // 2
            self.canvas.create_polygon(left, y1, right, y1, cx, y1 - 220, fill=colors[idx % 2], outline="#5c3b1e")
            self.point_polygons[point] = (left, y1 - 220, right, y1)
            self.canvas.create_text(cx, y1 - 235, text=str(point), font=("Arial", 10, "bold"))
            idx += 1

    def draw_checkers(self, x0: int, y0: int, x1: int, y1: int) -> None:
        r = 17
        for point in range(1, 25):
            owner = self.game.points[point].owner
            count = self.game.points[point].count
            if not owner or count == 0:
                continue

            left, top, right, bottom = self.point_polygons[point]
            cx = (left + right) // 2
            top_half = point >= 13
            for i in range(min(count, 5)):
                cy = (top + 20 + i * (2 * r + 2)) if top_half else (bottom - 20 - i * (2 * r + 2))
                self.draw_checker(cx, cy, owner)

            if count > 5:
                stack_text_y = top + 20 + 5 * (2 * r + 2) if top_half else bottom - 20 - 5 * (2 * r + 2)
                self.canvas.create_text(cx, stack_text_y, text=f"x{count}", fill="#111", font=("Arial", 10, "bold"))

    def draw_checker(self, cx: int, cy: int, owner: Player) -> None:
        color = "#ffffff" if owner == "W" else "#121212"
        outline = "#222" if owner == "W" else "#eee"
        self.canvas.create_oval(cx - 17, cy - 17, cx + 17, cy + 17, fill=color, outline=outline, width=2)

    def draw_side_areas(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self.canvas.create_text((x0 + x1) // 2, y0 - 22, text="BAR", font=("Arial", 14, "bold"))
        self.canvas.create_text((x0 + x1) // 2, y1 + 22, text="TOPLANAN", font=("Arial", 12, "bold"))

        self.canvas.create_text(x0 - 30, y0 + 70, text=f"Beyaz Bar: {self.game.bar['W']}", angle=90, font=("Arial", 10, "bold"))
        self.canvas.create_text(x1 + 30, y0 + 70, text=f"Siyah Bar: {self.game.bar['B']}", angle=270, font=("Arial", 10, "bold"))

        self.canvas.create_text(x0 - 50, y1 - 30, text=f"Beyaz Toplanan: {self.game.borne_off['W']}", font=("Arial", 10, "bold"))
        self.canvas.create_text(x1 + 50, y1 - 30, text=f"Siyah Toplanan: {self.game.borne_off['B']}", font=("Arial", 10, "bold"))

        self.highlight_selection()

    def update_labels(self) -> None:
        player_name = "Beyaz" if self.game.current_player == "W" else "Siyah"
        self.status_label.config(text=f"Sıra: {player_name}")
        self.info_label.config(text=f"Kalan Zarlar: {self.game.dice_values}")

    def point_at(self, x: int, y: int) -> Optional[int]:
        for point, (left, top, right, bottom) in self.point_polygons.items():
            if left <= x <= right and top <= y <= bottom:
                return point

        x0, y0, x1, y1 = self.board_coords()
        mid = (x0 + x1) // 2
        if mid - 35 <= x <= mid + 35 and y0 <= y <= y1:
            return 0  # bar

        return None

    def highlight_selection(self) -> None:
        if not self.game.selected_source:
            return

        loc, idx = self.game.selected_source
        if loc == "point":
            left, top, right, bottom = self.point_polygons[idx]
            self.canvas.create_rectangle(left, top, right, bottom, outline="#1e90ff", width=3)

        for _, target in self.selected_moves:
            if target is None:
                x0, y0, x1, y1 = self.board_coords()
                if self.game.current_player == "W":
                    self.canvas.create_rectangle(x0 - 90, y1 - 65, x0 - 10, y1 - 5, outline="#32cd32", width=3)
                else:
                    self.canvas.create_rectangle(x1 + 10, y1 - 65, x1 + 90, y1 - 5, outline="#32cd32", width=3)
                continue

            left, top, right, bottom = self.point_polygons[target]
            self.canvas.create_rectangle(left, top, right, bottom, outline="#32cd32", width=3)

    def on_click(self, event: tk.Event) -> None:
        if self.game.borne_off["W"] == 15 or self.game.borne_off["B"] == 15:
            return

        clicked = self.point_at(event.x, event.y)
        player = self.game.current_player

        if clicked is None:
            return

        if clicked == 0:
            if self.game.bar[player] > 0:
                self.select_source(("bar", 0))
            return

        if self.game.selected_source is None:
            if self.game.points[clicked].owner == player and self.game.points[clicked].count > 0:
                self.select_source(("point", clicked))
            return

        for die, target in self.selected_moves:
            if target == clicked:
                if self.game.move_checker(self.game.selected_source, die, target, player):
                    self.post_move_updates()
                return

        # bear-off click area
        x0, y0, x1, y1 = self.board_coords()
        if player == "W" and x0 - 90 <= event.x <= x0 - 10 and y1 - 65 <= event.y <= y1 - 5:
            self.try_bear_off_click()
            return
        if player == "B" and x1 + 10 <= event.x <= x1 + 90 and y1 - 65 <= event.y <= y1 - 5:
            self.try_bear_off_click()
            return

        if self.game.points[clicked].owner == player and self.game.points[clicked].count > 0:
            self.select_source(("point", clicked))

    def try_bear_off_click(self) -> None:
        if self.game.selected_source is None:
            return
        player = self.game.current_player
        for die, target in self.selected_moves:
            if target is None:
                if self.game.move_checker(self.game.selected_source, die, None, player):
                    self.post_move_updates()
                return

    def select_source(self, source: Tuple[str, int]) -> None:
        self.game.selected_source = source
        self.selected_moves = self.game.legal_moves_for_source(source, self.game.current_player)
        self.draw_board()

    def post_move_updates(self) -> None:
        winner = None
        if self.game.borne_off["W"] == 15:
            winner = "Beyaz"
        elif self.game.borne_off["B"] == 15:
            winner = "Siyah"

        self.game.selected_source = None
        self.selected_moves = []
        self.draw_board()

        if winner:
            messagebox.showinfo("Oyun Bitti", f"Kazanan: {winner}")
            return

        if not self.game.dice_values or not self.game.legal_sources(self.game.current_player):
            self.confirm_end_turn(auto=True)

    def confirm_end_turn(self, auto: bool = False) -> None:
        player_name = "Beyaz" if self.game.current_player == "W" else "Siyah"
        if not auto:
            if not messagebox.askyesno("Hamle Onayı", f"{player_name}, hamlen bitti mi?"):
                return

        self.game.current_player = "B" if self.game.current_player == "W" else "W"
        self.start_turn()


def main() -> None:
    root = tk.Tk()
    BackgammonUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
