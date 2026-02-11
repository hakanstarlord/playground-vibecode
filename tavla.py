from __future__ import annotations

import copy
import random
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox
from typing import Dict, List, Optional, Tuple

Player = str  # "W" or "B"
PointIndex = int  # 1..24
Source = Tuple[str, int]
MoveOption = Tuple[int, Optional[int]]


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
        self.dice_values: List[int] = []
        self.setup_initial_position()

    def snapshot(self) -> dict:
        return {
            "points": {idx: Point(p.owner, p.count) for idx, p in self.points.items()},
            "bar": copy.deepcopy(self.bar),
            "borne_off": copy.deepcopy(self.borne_off),
            "current_player": self.current_player,
            "dice_values": self.dice_values.copy(),
        }

    def restore(self, data: dict) -> None:
        self.points = {idx: Point(p.owner, p.count) for idx, p in data["points"].items()}
        self.bar = data["bar"].copy()
        self.borne_off = data["borne_off"].copy()
        self.current_player = data["current_player"]
        self.dice_values = data["dice_values"].copy()

    def setup_initial_position(self) -> None:
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
        self.dice_values = [d1] * 4 if d1 == d2 else [d1, d2]
        return self.dice_values.copy()

    @staticmethod
    def direction(player: Player) -> int:
        return -1 if player == "W" else 1

    @staticmethod
    def home_range(player: Player) -> range:
        return range(1, 7) if player == "W" else range(19, 25)

    @staticmethod
    def entry_from_bar(die: int, player: Player) -> int:
        return 25 - die if player == "W" else die

    def can_land(self, player: Player, point: int) -> bool:
        target = self.points[point]
        return target.owner in (None, player) or (target.owner != player and target.count == 1)

    def all_in_home(self, player: Player) -> bool:
        if self.bar[player] > 0:
            return False
        total_home = sum(self.points[p].count for p in self.home_range(player) if self.points[p].owner == player)
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
            if src - die == 0:
                return True
            if src - die < 0:
                return self.furthest_checker_point(player) == src
            return False

        if src + die == 25:
            return True
        if src + die > 25:
            return self.furthest_checker_point(player) == src
        return False

    def legal_moves_for_source(self, source: Source, player: Player) -> List[MoveOption]:
        moves: List[MoveOption] = []
        location, src = source

        if self.bar[player] > 0 and location != "bar":
            return moves

        for die in sorted(set(self.dice_values)):
            if location == "bar":
                target = self.entry_from_bar(die, player)
                if self.can_land(player, target):
                    moves.append((die, target))
                continue

            target = src + die * self.direction(player)
            if 1 <= target <= 24:
                if self.can_land(player, target):
                    moves.append((die, target))
            elif self.can_bear_off_from(player, src, die):
                moves.append((die, None))

        return moves

    def legal_sources(self, player: Player) -> List[Source]:
        if self.bar[player] > 0:
            return [("bar", 0)] if self.legal_moves_for_source(("bar", 0), player) else []

        sources: List[Source] = []
        for idx in range(1, 25):
            point = self.points[idx]
            if point.owner == player and point.count > 0 and self.legal_moves_for_source(("point", idx), player):
                sources.append(("point", idx))
        return sources

    def move_checker(self, source: Source, die: int, target: Optional[int], player: Player) -> bool:
        if (die, target) not in self.legal_moves_for_source(source, player):
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
                opponent = dest.owner
                self.bar[opponent] += 1
                dest.owner = None
                dest.count = 0

            if dest.owner is None:
                dest.owner = player
                dest.count = 1
            else:
                dest.count += 1

        self.dice_values.remove(die)
        return True


class BackgammonUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Tavla - 2 Oyuncu")
        self.root.configure(bg="#1f3a3a")

        self.game = BackgammonGame()
        self.selected_source: Optional[Source] = None
        self.selected_moves: List[MoveOption] = []
        self.point_boxes: Dict[int, Tuple[int, int, int, int]] = {}

        self.canvas = tk.Canvas(root, width=1080, height=720, bg="#1f3a3a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)

        self.panel = tk.Frame(root, bg="#2c4b4b")
        self.panel.pack(fill="x", padx=8, pady=(0, 8))

        self.turn_label = tk.Label(self.panel, text="", font=("Arial", 13, "bold"), fg="#f5d77e", bg="#2c4b4b")
        self.turn_label.pack(side="left", padx=10)

        self.dice_label = tk.Label(self.panel, text="", font=("Arial", 12), fg="#fff2c1", bg="#2c4b4b")
        self.dice_label.pack(side="left", padx=16)

        self.end_turn_btn = tk.Button(
            self.panel,
            text="HAMLEYİ BİTİR",
            command=self.ask_end_turn,
            font=("Arial", 11, "bold"),
            bg="#e0b715",
            activebackground="#cfaa10",
            relief="raised",
            padx=14,
        )
        self.end_turn_btn.pack(side="right", padx=10, pady=6)

        self.canvas.bind("<Button-1>", self.on_click)
        self.start_turn(initial=True)

    @staticmethod
    def player_text(player: Player) -> str:
        return "Beyaz" if player == "W" else "Siyah"

    def board_rect(self) -> Tuple[int, int, int, int]:
        return 90, 70, 990, 650

    def start_turn(self, initial: bool = False) -> None:
        player = self.game.current_player
        dice = self.game.roll_dice()
        self.selected_source = None
        self.selected_moves = []
        self.draw()

        if not initial:
            messagebox.showinfo("Yeni Tur", f"{self.player_text(player)} için zar: {dice}")

        if not self.game.legal_sources(player):
            messagebox.showinfo("Hamle Yok", f"{self.player_text(player)} için oynanabilir hamle yok.")
            self.switch_turn()

    def switch_turn(self) -> None:
        self.game.current_player = "B" if self.game.current_player == "W" else "W"
        self.start_turn()

    def draw(self) -> None:
        self.canvas.delete("all")
        x0, y0, x1, y1 = self.board_rect()

        # outer wooden frame
        self.canvas.create_rectangle(x0 - 22, y0 - 22, x1 + 22, y1 + 22, fill="#5b2f12", outline="#8a4f1f", width=4)
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#c88f55", outline="#76421d", width=4)

        # board center bar
        center = (x0 + x1) // 2
        self.canvas.create_rectangle(center - 28, y0, center + 28, y1, fill="#9d6738", outline="#6e3d1b", width=2)

        self.point_boxes.clear()
        self.draw_triangles(x0, y0, x1, y1)
        self.draw_checkers()
        self.draw_info_areas(x0, y0, x1, y1)
        self.draw_highlights()
        self.update_labels()

    def draw_triangles(self, x0: int, y0: int, x1: int, y1: int) -> None:
        gap_cols = 2
        tri_w = (x1 - x0 - 2 * 28) // (12 + gap_cols)
        top_colors = ["#6e3b1c", "#e5b176"]

        # top points 13..24
        idx = 0
        for point in list(range(13, 19)) + list(range(19, 25)):
            col = idx if idx < 6 else idx + gap_cols
            left = x0 + col * tri_w
            right = left + tri_w
            cx = (left + right) // 2
            self.canvas.create_polygon(left, y0, right, y0, cx, y0 + 240, fill=top_colors[idx % 2], outline="")
            self.point_boxes[point] = (left, y0, right, y0 + 240)
            idx += 1

        # bottom points 12..1
        idx = 0
        for point in list(range(12, 6, -1)) + list(range(6, 0, -1)):
            col = idx if idx < 6 else idx + gap_cols
            left = x0 + col * tri_w
            right = left + tri_w
            cx = (left + right) // 2
            self.canvas.create_polygon(left, y1, right, y1, cx, y1 - 240, fill=top_colors[idx % 2], outline="")
            self.point_boxes[point] = (left, y1 - 240, right, y1)
            idx += 1

    def draw_checkers(self) -> None:
        radius = 18
        for point in range(1, 25):
            stack = self.game.points[point]
            if stack.owner is None or stack.count == 0:
                continue

            left, top, right, bottom = self.point_boxes[point]
            cx = (left + right) // 2
            top_half = point >= 13

            for i in range(min(stack.count, 5)):
                cy = (top + 24 + i * 38) if top_half else (bottom - 24 - i * 38)
                self.paint_checker(cx, cy, stack.owner, radius)

            if stack.count > 5:
                ty = top + 24 + 5 * 38 if top_half else bottom - 24 - 5 * 38
                self.canvas.create_text(cx, ty, text=f"x{stack.count}", font=("Arial", 10, "bold"), fill="#2b1a0e")

    def paint_checker(self, cx: int, cy: int, owner: Player, r: int) -> None:
        fill = "#f1f1f1" if owner == "W" else "#171717"
        outline = "#8a8a8a" if owner == "W" else "#c0c0c0"
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=outline, width=2)
        self.canvas.create_oval(cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6, outline=outline, width=1)

    def draw_info_areas(self, x0: int, y0: int, x1: int, y1: int) -> None:
        center = (x0 + x1) // 2
        self.canvas.create_text(center, y0 - 26, text="BAR", fill="#ffd972", font=("Arial", 14, "bold"))

        self.canvas.create_rectangle(x0 - 82, y0 + 10, x0 - 12, y0 + 115, fill="#7a4a27", outline="#e7b676", width=2)
        self.canvas.create_text(x0 - 47, y0 + 40, text="W BAR", fill="#fff", font=("Arial", 10, "bold"))
        self.canvas.create_text(x0 - 47, y0 + 80, text=str(self.game.bar["W"]), fill="#ffe58a", font=("Arial", 18, "bold"))

        self.canvas.create_rectangle(x1 + 12, y0 + 10, x1 + 82, y0 + 115, fill="#7a4a27", outline="#e7b676", width=2)
        self.canvas.create_text(x1 + 47, y0 + 40, text="B BAR", fill="#fff", font=("Arial", 10, "bold"))
        self.canvas.create_text(x1 + 47, y0 + 80, text=str(self.game.bar["B"]), fill="#ffe58a", font=("Arial", 18, "bold"))

        self.canvas.create_rectangle(x0 - 82, y1 - 115, x0 - 12, y1 - 10, fill="#7a4a27", outline="#e7b676", width=2)
        self.canvas.create_text(x0 - 47, y1 - 85, text="W OFF", fill="#fff", font=("Arial", 10, "bold"))
        self.canvas.create_text(x0 - 47, y1 - 45, text=str(self.game.borne_off["W"]), fill="#ffe58a", font=("Arial", 18, "bold"))

        self.canvas.create_rectangle(x1 + 12, y1 - 115, x1 + 82, y1 - 10, fill="#7a4a27", outline="#e7b676", width=2)
        self.canvas.create_text(x1 + 47, y1 - 85, text="B OFF", fill="#fff", font=("Arial", 10, "bold"))
        self.canvas.create_text(x1 + 47, y1 - 45, text=str(self.game.borne_off["B"]), fill="#ffe58a", font=("Arial", 18, "bold"))

    def update_labels(self) -> None:
        player = self.game.current_player
        self.turn_label.config(text=f"Sıra: {self.player_text(player)}")
        self.dice_label.config(text=f"Kalan Zarlar: {self.game.dice_values}")

    def point_at(self, x: int, y: int) -> Optional[int]:
        for point, (left, top, right, bottom) in self.point_boxes.items():
            if left <= x <= right and top <= y <= bottom:
                return point

        x0, y0, x1, y1 = self.board_rect()
        center = (x0 + x1) // 2
        if center - 28 <= x <= center + 28 and y0 <= y <= y1:
            return 0
        return None

    def draw_highlights(self) -> None:
        if not self.selected_source:
            return

        loc, idx = self.selected_source
        if loc == "point":
            left, top, right, bottom = self.point_boxes[idx]
            self.canvas.create_rectangle(left, top, right, bottom, outline="#42a5ff", width=3)

        for _, target in self.selected_moves:
            if target is None:
                x0, _, x1, y1 = self.board_rect()
                if self.game.current_player == "W":
                    self.canvas.create_rectangle(x0 - 86, y1 - 118, x0 - 8, y1 - 6, outline="#9aff5a", width=3)
                else:
                    self.canvas.create_rectangle(x1 + 8, y1 - 118, x1 + 86, y1 - 6, outline="#9aff5a", width=3)
                continue
            left, top, right, bottom = self.point_boxes[target]
            self.canvas.create_rectangle(left, top, right, bottom, outline="#9aff5a", width=3)

    def on_click(self, event: tk.Event) -> None:
        if self.game.borne_off["W"] == 15 or self.game.borne_off["B"] == 15:
            return

        clicked = self.point_at(event.x, event.y)
        if clicked is None:
            return

        player = self.game.current_player
        if clicked == 0:
            if self.game.bar[player] > 0:
                self.select_source(("bar", 0))
            return

        if self.selected_source is None:
            if self.game.points[clicked].owner == player and self.game.points[clicked].count > 0:
                self.select_source(("point", clicked))
            return

        # destination selection
        for die, target in self.selected_moves:
            if target == clicked:
                self.try_move_with_confirmation(die, target)
                return

        # click bear-off zone if valid
        x0, _, x1, y1 = self.board_rect()
        if player == "W" and x0 - 82 <= event.x <= x0 - 12 and y1 - 115 <= event.y <= y1 - 10:
            self.try_bear_off()
            return
        if player == "B" and x1 + 12 <= event.x <= x1 + 82 and y1 - 115 <= event.y <= y1 - 10:
            self.try_bear_off()
            return

        # reselect source
        if self.game.points[clicked].owner == player and self.game.points[clicked].count > 0:
            self.select_source(("point", clicked))

    def select_source(self, source: Source) -> None:
        self.selected_source = source
        self.selected_moves = self.game.legal_moves_for_source(source, self.game.current_player)
        self.draw()

    def try_bear_off(self) -> None:
        if not self.selected_source:
            return
        for die, target in self.selected_moves:
            if target is None:
                self.try_move_with_confirmation(die, None)
                return

    def try_move_with_confirmation(self, die: int, target: Optional[int]) -> None:
        if not self.selected_source:
            return

        player = self.game.current_player
        before = self.game.snapshot()
        moved = self.game.move_checker(self.selected_source, die, target, player)
        if not moved:
            return

        self.draw()
        move_text = f"zar {die} ile {'toplamaya' if target is None else f'hane {target}e'} oynandı"
        ok = messagebox.askyesno("Hamle Onayı", f"{self.player_text(player)}: {move_text}.\nBu hamle son kararın mı?")

        if not ok:
            self.game.restore(before)
            self.draw()
            return

        self.selected_source = None
        self.selected_moves = []
        self.draw()
        self.post_move()

    def post_move(self) -> None:
        if self.game.borne_off["W"] == 15:
            messagebox.showinfo("Oyun Bitti", "Kazanan: Beyaz")
            return
        if self.game.borne_off["B"] == 15:
            messagebox.showinfo("Oyun Bitti", "Kazanan: Siyah")
            return

        if not self.game.dice_values or not self.game.legal_sources(self.game.current_player):
            self.ask_end_turn(auto=True)

    def ask_end_turn(self, auto: bool = False) -> None:
        player_name = self.player_text(self.game.current_player)
        if not auto:
            if not messagebox.askyesno("Tur Onayı", f"{player_name}, hamlen bitti mi?"):
                return
        self.switch_turn()


def main() -> None:
    root = tk.Tk()
    BackgammonUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
