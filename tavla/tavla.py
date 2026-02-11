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
        self.last_roll_pair: Tuple[int, int] = (1, 1)
        self.setup_initial_position()

    def snapshot(self) -> dict:
        return {
            "points": {idx: Point(p.owner, p.count) for idx, p in self.points.items()},
            "bar": copy.deepcopy(self.bar),
            "borne_off": copy.deepcopy(self.borne_off),
            "current_player": self.current_player,
            "dice_values": self.dice_values.copy(),
            "last_roll_pair": self.last_roll_pair,
        }

    def restore(self, data: dict) -> None:
        self.points = {idx: Point(p.owner, p.count) for idx, p in data["points"].items()}
        self.bar = data["bar"].copy()
        self.borne_off = data["borne_off"].copy()
        self.current_player = data["current_player"]
        self.dice_values = data["dice_values"].copy()
        self.last_roll_pair = data["last_roll_pair"]

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
        self.last_roll_pair = (d1, d2)
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
        self.selected_combo_moves: List[Tuple[int, int, int, int]] = []  # final_target, die1, die2, mid_target
        self.point_boxes: Dict[int, Tuple[int, int, int, int]] = {}
        self.bar_click_box: Optional[Tuple[int, int, int, int]] = None

        self.turn_start_snapshot: Optional[dict] = None
        self.moves_this_turn = 0
        self.dice_animating = False

        self.canvas = tk.Canvas(root, width=1400, height=780, bg="#1f3a3a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", self.on_resize)

        self.panel = tk.Frame(root, bg="#2c4b4b")
        self.panel.pack(fill="x", padx=8, pady=(0, 8))

        self.turn_label = tk.Label(self.panel, text="", font=("Arial", 13, "bold"), fg="#f5d77e", bg="#2c4b4b")
        self.turn_label.pack(side="left", padx=10)

        self.info_label = tk.Label(self.panel, text="", font=("Arial", 11), fg="#d8f0f0", bg="#2c4b4b")
        self.info_label.pack(side="left", padx=(6, 10))

        self.dice_canvas = tk.Canvas(self.panel, width=176, height=64, bg="#2c4b4b", highlightthickness=0)
        self.dice_canvas.pack(side="left", padx=8)

        self.end_turn_btn = tk.Button(
            self.panel,
            text="HAMLELERİ ONAYLA",
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

    def on_resize(self, _event: tk.Event) -> None:
        self.draw()

    @staticmethod
    def player_text(player: Player) -> str:
        return "Beyaz" if player == "W" else "Siyah"

    def board_rect(self) -> Tuple[int, int, int, int]:
        width = max(self.canvas.winfo_width(), 1200)
        height = max(self.canvas.winfo_height(), 680)

        board_w = 1020
        board_h = 620
        x0 = (width - board_w) // 2
        y0 = max(40, (height - board_h) // 2 - 20)
        return x0, y0, x0 + board_w, y0 + board_h

    def start_turn(self, initial: bool = False) -> None:
        player = self.game.current_player
        self.game.roll_dice()
        self.turn_start_snapshot = self.game.snapshot()
        self.moves_this_turn = 0
        self.selected_source = None
        self.selected_moves = []
        self.selected_combo_moves = []
        self.draw()

        self.animate_dice_then_show(self.game.last_roll_pair)

        if not initial:
            self.info_label.config(text=f"{self.player_text(player)} için zar atıldı: {self.game.last_roll_pair[0]} - {self.game.last_roll_pair[1]}")
        else:
            self.info_label.config(text="Oyun başladı. Zarlar otomatik atılır.")

        if not self.game.legal_sources(player):
            self.info_label.config(text=f"{self.player_text(player)} için oynanabilir hamle yok. Tur otomatik geçti.")
            self.switch_turn()

    def animate_dice_then_show(self, final_pair: Tuple[int, int], frame_count: int = 10) -> None:
        self.dice_animating = True

        def step(frame: int) -> None:
            if frame < frame_count:
                random_pair = (random.randint(1, 6), random.randint(1, 6))
                self.draw_dice_pair(random_pair)
                self.root.after(70, lambda: step(frame + 1))
                return

            self.draw_dice_pair(final_pair)
            self.dice_animating = False

        step(0)

    def switch_turn(self) -> None:
        self.game.current_player = "B" if self.game.current_player == "W" else "W"
        self.start_turn()

    def draw(self) -> None:
        self.canvas.delete("all")
        x0, y0, x1, y1 = self.board_rect()

        self.canvas.create_rectangle(x0 - 22, y0 - 22, x1 + 22, y1 + 22, fill="#5b2f12", outline="#8a4f1f", width=4)
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#c88f55", outline="#76421d", width=4)

        center = (x0 + x1) // 2
        self.canvas.create_rectangle(center - 30, y0, center + 30, y1, fill="#9d6738", outline="#6e3d1b", width=2)
        self.bar_click_box = (center - 30, y0, center + 30, y1)

        self.point_boxes.clear()
        self.draw_triangles(x0, y0, x1, y1)
        self.draw_checkers()
        self.draw_bar_checkers(x0, y0, x1, y1)
        self.draw_highlights()
        self.update_labels()

    def draw_triangles(self, x0: int, y0: int, x1: int, y1: int) -> None:
        gap_cols = 2
        tri_w = (x1 - x0 - 2 * 30) // (12 + gap_cols)
        top_colors = ["#6e3b1c", "#e5b176"]

        idx = 0
        for point in list(range(13, 19)) + list(range(19, 25)):
            col = idx if idx < 6 else idx + gap_cols
            left = x0 + col * tri_w
            right = left + tri_w
            cx = (left + right) // 2
            self.canvas.create_polygon(left, y0, right, y0, cx, y0 + 240, fill=top_colors[idx % 2], outline="")
            self.point_boxes[point] = (left, y0, right, y0 + 240)
            idx += 1

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

    def draw_bar_checkers(self, x0: int, y0: int, x1: int, y1: int) -> None:
        center = (x0 + x1) // 2

        # white hit checkers in lower half of center bar
        for i in range(min(self.game.bar["W"], 6)):
            self.paint_checker(center, y1 - 32 - i * 34, "W", 14)
        if self.game.bar["W"] > 6:
            self.canvas.create_text(center, y1 - 32 - 6 * 34, text=f"x{self.game.bar['W']}", fill="#fff", font=("Arial", 9, "bold"))

        # black hit checkers in upper half of center bar
        for i in range(min(self.game.bar["B"], 6)):
            self.paint_checker(center, y0 + 32 + i * 34, "B", 14)
        if self.game.bar["B"] > 6:
            self.canvas.create_text(center, y0 + 32 + 6 * 34, text=f"x{self.game.bar['B']}", fill="#fff", font=("Arial", 9, "bold"))

    def paint_checker(self, cx: int, cy: int, owner: Player, r: int) -> None:
        fill = "#f1f1f1" if owner == "W" else "#171717"
        outline = "#8a8a8a" if owner == "W" else "#c0c0c0"
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=outline, width=2)
        self.canvas.create_oval(cx - r + 5, cy - r + 5, cx + r - 5, cy + r - 5, outline=outline, width=1)

    def update_labels(self) -> None:
        self.turn_label.config(text=f"Sıra: {self.player_text(self.game.current_player)} | Hamle: {self.moves_this_turn}")

    def draw_dice_pair(self, pair: Tuple[int, int]) -> None:
        self.dice_canvas.delete("all")
        self.draw_die_face(10, 3, pair[0])
        self.draw_die_face(94, 3, pair[1])

    def draw_die_face(self, x: int, y: int, value: int) -> None:
        size = 58
        self.dice_canvas.create_rectangle(x, y, x + size, y + size, fill="#f7f7f7", outline="#333", width=2)

        pip_map = {
            1: [(0.5, 0.5)],
            2: [(0.25, 0.25), (0.75, 0.75)],
            3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
            4: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)],
            5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
            6: [(0.25, 0.22), (0.75, 0.22), (0.25, 0.5), (0.75, 0.5), (0.25, 0.78), (0.75, 0.78)],
        }

        r = 4
        for px, py in pip_map[value]:
            cx = x + int(px * size)
            cy = y + int(py * size)
            self.dice_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#111", outline="#111")

    def point_at(self, x: int, y: int) -> Optional[int]:
        for point, (left, top, right, bottom) in self.point_boxes.items():
            if left <= x <= right and top <= y <= bottom:
                return point

        if self.bar_click_box:
            bx0, by0, bx1, by1 = self.bar_click_box
            if bx0 <= x <= bx1 and by0 <= y <= by1:
                return 0

        return None


    def combined_moves_for_source(self, source: Source) -> List[Tuple[int, int, int, int]]:
        player = self.game.current_player
        dice = self.game.dice_values.copy()
        if len(dice) < 2:
            return []

        combos: Dict[int, Tuple[int, int, int, int]] = {}
        for i in range(len(dice)):
            for j in range(i + 1, len(dice)):
                first_die = dice[i]
                second_die = dice[j]
                orders = [(first_die, second_die)]
                if first_die != second_die:
                    orders.append((second_die, first_die))

                for d1, d2 in orders:
                    first_options = [(die, target) for die, target in self.game.legal_moves_for_source(source, player) if die == d1]
                    for _, mid_target in first_options:
                        if mid_target is None:
                            continue

                        sim_game = copy.deepcopy(self.game)
                        if not sim_game.move_checker(source, d1, mid_target, player):
                            continue

                        second_source: Source = ("point", mid_target)
                        second_options = [(die, target) for die, target in sim_game.legal_moves_for_source(second_source, player) if die == d2]
                        for _, final_target in second_options:
                            if final_target is None:
                                continue
                            combos.setdefault(final_target, (final_target, d1, d2, mid_target))

        return list(combos.values())

    def apply_combined_move(self, die1: int, die2: int, mid_target: int, final_target: int) -> None:
        if not self.selected_source:
            return
        player = self.game.current_player

        if not self.game.move_checker(self.selected_source, die1, mid_target, player):
            return

        if not self.game.move_checker(("point", mid_target), die2, final_target, player):
            return

        self.moves_this_turn += 2
        self.selected_source = None
        self.selected_moves = []
        self.selected_combo_moves = []
        self.draw()

        if self.game.borne_off["W"] == 15:
            messagebox.showinfo("Oyun Bitti", "Kazanan: Beyaz")
            return
        if self.game.borne_off["B"] == 15:
            messagebox.showinfo("Oyun Bitti", "Kazanan: Siyah")
            return

        if not self.game.dice_values or not self.game.legal_sources(player):
            self.ask_end_turn()

    def draw_highlights(self) -> None:
        if not self.selected_source:
            return

        loc, idx = self.selected_source
        if loc == "point":
            left, top, right, bottom = self.point_boxes[idx]
            self.canvas.create_rectangle(left, top, right, bottom, outline="#42a5ff", width=3)
        elif self.bar_click_box:
            bx0, by0, bx1, by1 = self.bar_click_box
            self.canvas.create_rectangle(bx0, by0, bx1, by1, outline="#42a5ff", width=3)

        for _, target in self.selected_moves:
            if target is None:
                x0, _, x1, y1 = self.board_rect()
                if self.game.current_player == "W":
                    self.canvas.create_rectangle(x0 - 90, y1 - 128, x0 - 8, y1 - 8, outline="#9aff5a", width=3)
                else:
                    self.canvas.create_rectangle(x1 + 8, y1 - 128, x1 + 90, y1 - 8, outline="#9aff5a", width=3)
                continue
            left, top, right, bottom = self.point_boxes[target]
            self.canvas.create_rectangle(left, top, right, bottom, outline="#9aff5a", width=3)

        for final_target, _, _, _ in self.selected_combo_moves:
            left, top, right, bottom = self.point_boxes[final_target]
            self.canvas.create_rectangle(left + 4, top + 4, right - 4, bottom - 4, outline="#ffb347", width=3)

    def on_click(self, event: tk.Event) -> None:
        if self.dice_animating:
            return
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

        for die, target in self.selected_moves:
            if target == clicked:
                self.apply_move(die, target)
                return

        for final_target, die1, die2, mid_target in self.selected_combo_moves:
            if final_target == clicked:
                self.apply_combined_move(die1, die2, mid_target, final_target)
                return

        x0, _, x1, y1 = self.board_rect()
        if player == "W" and x0 - 86 <= event.x <= x0 - 12 and y1 - 125 <= event.y <= y1 - 15:
            self.try_bear_off()
            return
        if player == "B" and x1 + 12 <= event.x <= x1 + 86 and y1 - 125 <= event.y <= y1 - 15:
            self.try_bear_off()
            return

        if self.game.points[clicked].owner == player and self.game.points[clicked].count > 0:
            self.select_source(("point", clicked))

    def select_source(self, source: Source) -> None:
        self.selected_source = source
        self.selected_moves = self.game.legal_moves_for_source(source, self.game.current_player)
        self.selected_combo_moves = self.combined_moves_for_source(source)
        self.draw()

    def try_bear_off(self) -> None:
        if not self.selected_source:
            return
        for die, target in self.selected_moves:
            if target is None:
                self.apply_move(die, None)
                return

    def apply_move(self, die: int, target: Optional[int]) -> None:
        if not self.selected_source:
            return
        player = self.game.current_player
        if self.game.move_checker(self.selected_source, die, target, player):
            self.moves_this_turn += 1
            self.selected_source = None
            self.selected_moves = []
            self.selected_combo_moves = []
            self.draw()
            if self.game.borne_off["W"] == 15:
                messagebox.showinfo("Oyun Bitti", "Kazanan: Beyaz")
                return
            if self.game.borne_off["B"] == 15:
                messagebox.showinfo("Oyun Bitti", "Kazanan: Siyah")
                return
            # Turu oyuncu sağ alttaki buton ile manuel onaylar.

    def ask_end_turn(self) -> None:
        # Pop-up onay olmadan, butona basınca tur direkt rakibe geçer.
        self.selected_source = None
        self.selected_moves = []
        self.selected_combo_moves = []
        self.draw()
        self.switch_turn()


def main() -> None:
    root = tk.Tk()
    BackgammonUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
