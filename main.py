
import json
import random
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, ttk

DATA_FILE = Path(__file__).with_name("memory_data.json")


FIELD_SIZES = [(2, 2), (2, 3), (3, 4), (4, 4), (4, 5), (5, 6), (6, 6)]

SYMBOL_SETS = {
    "Эмодзи": ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨",
               "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🐦"],
    "Буквы": list("ABCDEFGHIJKLMNOPQR"),
    "Числа": [str(i) for i in range(1, 19)],
}

COLOR_CLOSED = "#4a6fa5"
COLOR_OPEN = "#ffffff"
COLOR_MATCHED = "#8fd19e"

MISMATCH_DELAY_MS = 800
MIN_WIN_W, MAX_WIN_W = 400, 1600
MIN_WIN_H, MAX_WIN_H = 400, 1200

DEFAULT_SETTINGS = {
    "rows": 4,
    "cols": 4,
    "symbols": "Эмодзи",
    "width": 640,
    "height": 720,
}


def field_label(rows, cols):
    return f"{rows}×{cols}"


def format_time(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class MemoryModel:

    CLOSED, OPEN, MATCHED = "closed", "open", "matched"

    def __init__(self, rows, cols, symbols):
        total = rows * cols
        if total % 2 != 0:
            raise ValueError("Число клеток должно быть чётным")
        pairs = total // 2
        if pairs > len(symbols):
            raise ValueError("Недостаточно символов для такого поля")
        chosen = random.sample(symbols, pairs)
        self.cards = chosen * 2
        random.shuffle(self.cards)
        self.state = [self.CLOSED] * total
        self.first = None
        self.moves = 0
        self.matched_pairs = 0
        self.total_pairs = pairs

    def open_card(self, index):

        if not 0 <= index < len(self.cards):
            return "ignored", None
        if self.state[index] != self.CLOSED:
            return "ignored", None
        self.state[index] = self.OPEN
        if self.first is None:
            self.first = index
            return "first", None
        other = self.first
        self.first = None
        self.moves += 1
        if self.cards[index] == self.cards[other]:
            self.state[index] = self.state[other] = self.MATCHED
            self.matched_pairs += 1
            return "match", other
        return "mismatch", other

    def close_cards(self, *indexes):
        for i in indexes:
            if self.state[i] == self.OPEN:
                self.state[i] = self.CLOSED

    @property
    def is_won(self):
        return self.matched_pairs == self.total_pairs


class DataStore:

    def __init__(self, path):
        self.path = path
        self.settings = dict(DEFAULT_SETTINGS)
        self.records = {}
        self.load_error = None

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as file:
                data = json.load(file)
            settings = data.get("settings", {})
            records = data.get("records", {})
            if isinstance(settings, dict):
                for key, default in DEFAULT_SETTINGS.items():
                    value = settings.get(key, default)
                    if isinstance(value, type(default)):
                        self.settings[key] = value
            if isinstance(records, dict):
                self.records = {
                    k: v for k, v in records.items()
                    if isinstance(v, dict)
                    and isinstance(v.get("moves"), int)
                    and isinstance(v.get("time"), int)
                }
        except FileNotFoundError:
            pass
        except (OSError, ValueError, AttributeError) as err:
            self.load_error = str(err)

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump({"settings": self.settings,
                           "records": self.records},
                          file, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    def update_record(self, rows, cols, moves, seconds):
        key = f"{rows}x{cols}"
        old = self.records.get(key)
        if old is None or (moves, seconds) < (old["moves"], old["time"]):
            self.records[key] = {"moves": moves, "time": seconds}
            return True
        return False


class SettingsDialog(tk.Toplevel):

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.title("Настройки")
        self.resizable(False, False)
        self.transient(parent)
        self.result = None

        frame = ttk.Frame(self, padding=15)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="Размер поля:").grid(row=0, column=0,
                                                   sticky="w", pady=4)
        self.field_var = tk.StringVar(
            value=field_label(settings["rows"], settings["cols"]))
        ttk.Combobox(frame, textvariable=self.field_var, state="readonly",
                     values=[field_label(r, c) for r, c in FIELD_SIZES],
                     width=10).grid(row=0, column=1, pady=4)

        ttk.Label(frame, text="Символы:").grid(row=1, column=0,
                                               sticky="w", pady=4)
        self.symbols_var = tk.StringVar(value=settings["symbols"])
        ttk.Combobox(frame, textvariable=self.symbols_var, state="readonly",
                     values=list(SYMBOL_SETS), width=10).grid(row=1, column=1,
                                                              pady=4)

        ttk.Label(frame, text="Ширина окна:").grid(row=2, column=0,
                                                   sticky="w", pady=4)
        self.width_var = tk.StringVar(value=str(settings["width"]))
        ttk.Entry(frame, textvariable=self.width_var,
                  width=12).grid(row=2, column=1, pady=4)

        ttk.Label(frame, text="Высота окна:").grid(row=3, column=0,
                                                   sticky="w", pady=4)
        self.height_var = tk.StringVar(value=str(settings["height"]))
        ttk.Entry(frame, textvariable=self.height_var,
                  width=12).grid(row=3, column=1, pady=4)

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(buttons, text="Применить",
                   command=self._on_apply).pack(side="left", padx=5)
        ttk.Button(buttons, text="Отмена",
                   command=self.destroy).pack(side="left", padx=5)

        self.bind("<Return>", lambda e: self._on_apply())
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.wait_window(self)

    def _on_apply(self):
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
        except ValueError:
            messagebox.showerror("Ошибка",
                                 "Ширина и высота должны быть целыми числами.",
                                 parent=self)
            return
        if not (MIN_WIN_W <= width <= MAX_WIN_W
                and MIN_WIN_H <= height <= MAX_WIN_H):
            messagebox.showerror(
                "Ошибка",
                f"Ширина: {MIN_WIN_W}-{MAX_WIN_W}, "
                f"высота: {MIN_WIN_H}-{MAX_WIN_H}.", parent=self)
            return
        rows, cols = next((r, c) for r, c in FIELD_SIZES
                          if field_label(r, c) == self.field_var.get())
        self.result = {"rows": rows, "cols": cols,
                       "symbols": self.symbols_var.get(),
                       "width": width, "height": height}
        self.destroy()


class MemoryApp:

    def __init__(self, root):
        self.root = root
        self.store = DataStore(DATA_FILE)
        self.store.load()
        self.settings = self.store.settings

        self.model = None
        self.cards = []
        self.locked = False
        self.start_time = None
        self.elapsed = 0
        self.timer_id = None
        self.hide_id = None

        root.title("Найди пару")
        root.minsize(MIN_WIN_W, MIN_WIN_H)
        root.geometry(f"{self.settings['width']}x{self.settings['height']}")
        root.report_callback_exception = self._on_callback_error
        root.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.card_font = tkfont.Font(size=24, weight="bold")
        self._build_menu()
        self._build_widgets()
        if self.store.load_error:
            messagebox.showwarning(
                "Предупреждение",
                "Не удалось прочитать файл настроек, "
                "используются значения по умолчанию.")
        self.new_game()

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        game_menu = tk.Menu(menubar, tearoff=0)
        game_menu.add_command(label="Новая игра", accelerator="F2",
                              command=self.new_game)
        game_menu.add_command(label="Рекорды", command=self.show_records)
        game_menu.add_separator()
        game_menu.add_command(label="Выход", command=self.exit_app)
        menubar.add_cascade(label="Игра", menu=game_menu)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Настройки...",
                                  command=self.open_settings)
        menubar.add_cascade(label="Настройки", menu=settings_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Правила", command=self.show_rules)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)

        self.root.config(menu=menubar)
        self.root.bind("<F2>", lambda e: self.new_game())

    def _build_widgets(self):
        info = ttk.Frame(self.root, padding=(10, 8))
        info.pack(side="top", fill="x")
        self.moves_var = tk.StringVar()
        self.time_var = tk.StringVar()
        self.record_var = tk.StringVar()
        ttk.Label(info, textvariable=self.moves_var).pack(side="left")
        ttk.Label(info, textvariable=self.time_var).pack(side="left",
                                                         padx=20)
        ttk.Label(info, textvariable=self.record_var).pack(side="right")

        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var, relief="sunken",
                  anchor="w", padding=(6, 2)).pack(side="bottom", fill="x")

        self.board = tk.Frame(self.root, padx=6, pady=6)
        self.board.pack(side="top", fill="both", expand=True)
        self.board.bind("<Configure>", self._on_board_resize)

    def _build_board(self):
        for widget in self.board.winfo_children():
            widget.destroy()
        self.cards = []
        rows, cols = self.settings["rows"], self.settings["cols"]
        for r in range(rows):
            self.board.rowconfigure(r, weight=1, uniform="row")
        for c in range(cols):
            self.board.columnconfigure(c, weight=1, uniform="col")
        for r in range(rows, 10):
            self.board.rowconfigure(r, weight=0, uniform="")
        for c in range(cols, 10):
            self.board.columnconfigure(c, weight=0, uniform="")

        for index in range(rows * cols):
            card = tk.Label(self.board, text="?", font=self.card_font,
                            bg=COLOR_CLOSED, fg="white", relief="raised",
                            bd=3, cursor="hand2")
            card.grid(row=index // cols, column=index % cols,
                      sticky="nsew", padx=3, pady=3)
            card.bind("<Button-1>", lambda e, i=index: self.on_card_click(i))
            self.cards.append(card)
        self._on_board_resize()

    def _on_board_resize(self, event=None):
        try:
            width = self.board.winfo_width()
            height = self.board.winfo_height()
            rows, cols = self.settings["rows"], self.settings["cols"]
            size = int(min(width / cols, height / rows) * 0.35)
            self.card_font.configure(size=max(8, size))
        except (tk.TclError, ZeroDivisionError):
            pass

    def new_game(self):
        self._cancel_timers()
        try:
            symbols = SYMBOL_SETS[self.settings["symbols"]]
            self.model = MemoryModel(self.settings["rows"],
                                     self.settings["cols"], symbols)
        except (KeyError, ValueError) as err:
            messagebox.showerror("Ошибка",
                                 f"Не удалось создать игру: {err}\n"
                                 "Будут восстановлены настройки по умолчанию.")
            self.settings.update(DEFAULT_SETTINGS)
            self.model = MemoryModel(self.settings["rows"],
                                     self.settings["cols"],
                                     SYMBOL_SETS[self.settings["symbols"]])
        self.locked = False
        self.start_time = None
        self.elapsed = 0
        self._build_board()
        self._update_info()
        self.status_var.set("Откройте любую карточку, чтобы начать.")

    def on_card_click(self, index):
        if self.locked or self.model is None or self.model.is_won:
            return
        if self.start_time is None:
            self.start_time = time.time()
            self._tick()
        result, other = self.model.open_card(index)
        if result == "ignored":
            return
        self._show_card(index)
        if result == "first":
            self.status_var.set("Выберите вторую карточку.")
        elif result == "match":
            self._show_card(other)
            self.status_var.set("Пара найдена!")
            if self.model.is_won:
                self._on_win()
        elif result == "mismatch":
            self.status_var.set("Не совпало. Запомните карточки!")
            self.locked = True
            self.hide_id = self.root.after(
                MISMATCH_DELAY_MS, lambda: self._hide_pair(other, index))
        self._update_info()

    def _hide_pair(self, first, second):
        self.hide_id = None
        if self.model is None:
            return
        self.model.close_cards(first, second)
        self._show_card(first)
        self._show_card(second)
        self.locked = False

    def _show_card(self, index):
        state = self.model.state[index]
        card = self.cards[index]
        if state == MemoryModel.CLOSED:
            card.config(text="?", bg=COLOR_CLOSED, fg="white",
                        relief="raised", cursor="hand2")
        elif state == MemoryModel.OPEN:
            card.config(text=self.model.cards[index], bg=COLOR_OPEN,
                        fg="black", relief="sunken", cursor="arrow")
        else:
            card.config(text=self.model.cards[index], bg=COLOR_MATCHED,
                        fg="black", relief="flat", cursor="arrow")

    def _on_win(self):
        self._cancel_timers()
        self._update_elapsed()
        rows, cols = self.settings["rows"], self.settings["cols"]
        is_record = self.store.update_record(rows, cols, self.model.moves,
                                             self.elapsed)
        if is_record and not self.store.save():
            messagebox.showwarning("Предупреждение",
                                   "Не удалось сохранить рекорд в файл.")
        self._update_info()
        text = (f"Вы нашли все пары!\nХодов: {self.model.moves}\n"
                f"Время: {format_time(self.elapsed)}")
        if is_record:
            text += "\nНовый рекорд!"
        self.status_var.set("Победа!")
        if messagebox.askyesno("Победа", text + "\n\nСыграть ещё раз?"):
            self.new_game()


    def _update_elapsed(self):
        if self.start_time is not None:
            self.elapsed = int(time.time() - self.start_time)

    def _tick(self):
        self._update_elapsed()
        self.time_var.set(f"Время: {format_time(self.elapsed)}")
        self.timer_id = self.root.after(250, self._tick)

    def _cancel_timers(self):
        for name in ("timer_id", "hide_id"):
            after_id = getattr(self, name)
            if after_id is not None:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    pass
                setattr(self, name, None)

    def _update_info(self):
        moves = self.model.moves if self.model else 0
        self.moves_var.set(f"Ходы: {moves}")
        self.time_var.set(f"Время: {format_time(self.elapsed)}")
        key = f"{self.settings['rows']}x{self.settings['cols']}"
        record = self.store.records.get(key)
        if record:
            self.record_var.set(
                f"Рекорд {field_label(self.settings['rows'], self.settings['cols'])}: "
                f"{record['moves']} ход., {format_time(record['time'])}")
        else:
            self.record_var.set("Рекорда пока нет")


    def open_settings(self):
        dialog = SettingsDialog(self.root, self.settings)
        if dialog.result:
            self.settings.update(dialog.result)
            self.root.geometry(
                f"{self.settings['width']}x{self.settings['height']}")
            if not self.store.save():
                messagebox.showwarning("Предупреждение",
                                       "Не удалось сохранить настройки.")
            self.new_game()

    def show_records(self):
        window = tk.Toplevel(self.root)
        window.title("Рекорды")
        window.transient(self.root)
        tree = ttk.Treeview(window, columns=("field", "moves", "time"),
                            show="headings", height=8)
        for column, title, width in (("field", "Поле", 90),
                                     ("moves", "Ходы", 90),
                                     ("time", "Время", 90)):
            tree.heading(column, text=title)
            tree.column(column, width=width, anchor="center")
        for rows, cols in FIELD_SIZES:
            record = self.store.records.get(f"{rows}x{cols}")
            if record:
                tree.insert("", "end", values=(field_label(rows, cols),
                                               record["moves"],
                                               format_time(record["time"])))
        tree.pack(padx=10, pady=10)
        ttk.Button(window, text="Закрыть",
                   command=window.destroy).pack(pady=(0, 10))

    def show_rules(self):
        messagebox.showinfo(
            "Правила",
            "На поле лежат карточки рубашкой вверх.\n"
            "За ход нужно открыть две карточки.\n"
            "Если символы совпали - пара остаётся открытой,\n"
            "иначе карточки закрываются.\n"
            "Цель - найти все пары за наименьшее число ходов.")

    def show_about(self):
        messagebox.showinfo("О программе",
                            "Игра «Найди пару»\n"
                            "Лабораторная работа № 3, вариант 21\n"
                            "Python + Tkinter")

    def exit_app(self):
        if messagebox.askokcancel("Выход", "Закрыть игру?"):
            self._cancel_timers()
            self.root.destroy()

    def _on_callback_error(self, exc_type, exc_value, exc_tb):
        try:
            messagebox.showerror(
                "Непредвиденная ошибка",
                f"{exc_type.__name__}: {exc_value}\n\n"
                "Программа продолжит работу.")
        except tk.TclError:
            pass


def main():
    root = tk.Tk()
    MemoryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
