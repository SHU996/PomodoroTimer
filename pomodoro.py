import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import winsound
from datetime import datetime, date
from pathlib import Path

DATA_FILE = Path(__file__).parent / "pomodoro_stats.json"
CONFIG_FILE = Path(__file__).parent / "pomodoro_config.json"

DEFAULT_CONFIG = {
    "work_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "rounds_until_long_break": 4,
}

COLOR_BG = "#2d2d3a"
COLOR_PANEL = "#3a3a4d"
COLOR_WORK = "#e74c3c"
COLOR_BREAK = "#27ae60"
COLOR_TEXT = "#f5f5f5"
COLOR_ACCENT = "#f39c12"


def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(default, dict):
                merged = dict(default)
                merged.update(data)
                return merged
            return data
        except (json.JSONDecodeError, OSError):
            return default
    return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Failed to save {path}: {e}")


class PomodoroApp:
    MODE_WORK = "work"
    MODE_SHORT_BREAK = "short_break"
    MODE_LONG_BREAK = "long_break"

    def __init__(self, root):
        self.root = root
        self.root.title("番茄钟")
        self.root.geometry("420x520")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)

        self.config = load_json(CONFIG_FILE, DEFAULT_CONFIG)
        self.stats = load_json(DATA_FILE, {})

        self.mode = self.MODE_WORK
        self.remaining = self.config["work_minutes"] * 60
        self.running = False
        self.completed_rounds = 0
        self.timer_job = None

        self._build_ui()
        self._update_display()

    def _build_ui(self):
        title = tk.Label(
            self.root, text="🍅 番茄钟", font=("Microsoft YaHei", 22, "bold"),
            bg=COLOR_BG, fg=COLOR_TEXT,
        )
        title.pack(pady=(20, 10))

        self.mode_label = tk.Label(
            self.root, text="工作时间", font=("Microsoft YaHei", 14),
            bg=COLOR_BG, fg=COLOR_ACCENT,
        )
        self.mode_label.pack()

        self.timer_frame = tk.Frame(self.root, bg=COLOR_WORK, width=280, height=160)
        self.timer_frame.pack(pady=20)
        self.timer_frame.pack_propagate(False)

        self.time_label = tk.Label(
            self.timer_frame, text="25:00", font=("Consolas", 56, "bold"),
            bg=COLOR_WORK, fg=COLOR_TEXT,
        )
        self.time_label.pack(expand=True)

        btn_frame = tk.Frame(self.root, bg=COLOR_BG)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(
            btn_frame, text="开始", width=8, font=("Microsoft YaHei", 11),
            bg=COLOR_ACCENT, fg="white", bd=0, activebackground="#d68910",
            command=self.toggle_start,
        )
        self.start_btn.grid(row=0, column=0, padx=5)

        self.reset_btn = tk.Button(
            btn_frame, text="重置", width=8, font=("Microsoft YaHei", 11),
            bg=COLOR_PANEL, fg=COLOR_TEXT, bd=0, activebackground="#4a4a5d",
            command=self.reset,
        )
        self.reset_btn.grid(row=0, column=1, padx=5)

        self.skip_btn = tk.Button(
            btn_frame, text="跳过", width=8, font=("Microsoft YaHei", 11),
            bg=COLOR_PANEL, fg=COLOR_TEXT, bd=0, activebackground="#4a4a5d",
            command=self.skip,
        )
        self.skip_btn.grid(row=0, column=2, padx=5)

        self.settings_btn = tk.Button(
            btn_frame, text="设置", width=8, font=("Microsoft YaHei", 11),
            bg=COLOR_PANEL, fg=COLOR_TEXT, bd=0, activebackground="#4a4a5d",
            command=self.open_settings,
        )
        self.settings_btn.grid(row=0, column=3, padx=5)

        stats_frame = tk.Frame(self.root, bg=COLOR_PANEL)
        stats_frame.pack(pady=20, padx=20, fill="x")

        tk.Label(
            stats_frame, text="📊 统计", font=("Microsoft YaHei", 12, "bold"),
            bg=COLOR_PANEL, fg=COLOR_TEXT,
        ).pack(pady=(10, 5))

        self.today_label = tk.Label(
            stats_frame, text="今日完成: 0 个番茄", font=("Microsoft YaHei", 11),
            bg=COLOR_PANEL, fg=COLOR_TEXT,
        )
        self.today_label.pack(pady=2)

        self.total_label = tk.Label(
            stats_frame, text="累计完成: 0 个番茄", font=("Microsoft YaHei", 11),
            bg=COLOR_PANEL, fg=COLOR_TEXT,
        )
        self.total_label.pack(pady=(2, 10))

        self._refresh_stats()

    def _format_time(self, seconds):
        m, s = divmod(max(0, seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _mode_color(self):
        return COLOR_WORK if self.mode == self.MODE_WORK else COLOR_BREAK

    def _mode_text(self):
        return {
            self.MODE_WORK: "工作时间",
            self.MODE_SHORT_BREAK: "短休息",
            self.MODE_LONG_BREAK: "长休息",
        }[self.mode]

    def _update_display(self):
        self.time_label.config(text=self._format_time(self.remaining))
        color = self._mode_color()
        self.timer_frame.config(bg=color)
        self.time_label.config(bg=color)
        self.mode_label.config(text=self._mode_text())

    def toggle_start(self):
        if self.running:
            self.running = False
            self.start_btn.config(text="开始")
            if self.timer_job:
                self.root.after_cancel(self.timer_job)
                self.timer_job = None
        else:
            self.running = True
            self.start_btn.config(text="暂停")
            self._tick()

    def _tick(self):
        if not self.running:
            return
        if self.remaining <= 0:
            self._on_complete()
            return
        self.remaining -= 1
        self._update_display()
        self.timer_job = self.root.after(1000, self._tick)

    def _on_complete(self):
        self.running = False
        self.start_btn.config(text="开始")
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

        self._play_sound()

        if self.mode == self.MODE_WORK:
            self.completed_rounds += 1
            self._record_pomodoro()
            self._refresh_stats()
            if self.completed_rounds % self.config["rounds_until_long_break"] == 0:
                self._switch_mode(self.MODE_LONG_BREAK)
                msg = "工作完成！开始长休息 🎉"
            else:
                self._switch_mode(self.MODE_SHORT_BREAK)
                msg = "工作完成！开始短休息 ☕"
        else:
            self._switch_mode(self.MODE_WORK)
            msg = "休息结束！开始下一个番茄 🍅"

        messagebox.showinfo("番茄钟", msg)

    def _switch_mode(self, mode):
        self.mode = mode
        if mode == self.MODE_WORK:
            self.remaining = self.config["work_minutes"] * 60
        elif mode == self.MODE_SHORT_BREAK:
            self.remaining = self.config["short_break_minutes"] * 60
        else:
            self.remaining = self.config["long_break_minutes"] * 60
        self._update_display()

    def _play_sound(self):
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            self.root.bell()

    def reset(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.running = False
        self.start_btn.config(text="开始")
        self._switch_mode(self.mode)

    def skip(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self.remaining = 0
        self._on_complete()

    def _record_pomodoro(self):
        today = date.today().isoformat()
        self.stats[today] = self.stats.get(today, 0) + 1
        save_json(DATA_FILE, self.stats)

    def _refresh_stats(self):
        today = date.today().isoformat()
        today_count = self.stats.get(today, 0)
        total = sum(self.stats.values())
        self.today_label.config(text=f"今日完成: {today_count} 个番茄")
        self.total_label.config(text=f"累计完成: {total} 个番茄")

    def open_settings(self):
        SettingsDialog(self.root, self.config, self._on_config_saved)

    def _on_config_saved(self, new_config):
        self.config = new_config
        save_json(CONFIG_FILE, self.config)
        if not self.running:
            self._switch_mode(self.mode)


class SettingsDialog:
    def __init__(self, parent, config, on_save):
        self.config = config
        self.on_save = on_save

        self.win = tk.Toplevel(parent)
        self.win.title("设置")
        self.win.geometry("320x280")
        self.win.configure(bg=COLOR_BG)
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        tk.Label(
            self.win, text="⚙ 时间设置（分钟）",
            font=("Microsoft YaHei", 14, "bold"), bg=COLOR_BG, fg=COLOR_TEXT,
        ).pack(pady=15)

        self.entries = {}
        fields = [
            ("work_minutes", "工作时长"),
            ("short_break_minutes", "短休息时长"),
            ("long_break_minutes", "长休息时长"),
            ("rounds_until_long_break", "几轮后长休息"),
        ]

        form = tk.Frame(self.win, bg=COLOR_BG)
        form.pack(pady=5)

        for i, (key, label) in enumerate(fields):
            tk.Label(
                form, text=label, font=("Microsoft YaHei", 10),
                bg=COLOR_BG, fg=COLOR_TEXT, width=14, anchor="e",
            ).grid(row=i, column=0, padx=5, pady=5)
            entry = tk.Entry(form, width=8, font=("Consolas", 11), justify="center")
            entry.insert(0, str(config[key]))
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries[key] = entry

        btn_frame = tk.Frame(self.win, bg=COLOR_BG)
        btn_frame.pack(pady=15)

        tk.Button(
            btn_frame, text="保存", width=8, font=("Microsoft YaHei", 10),
            bg=COLOR_ACCENT, fg="white", bd=0, command=self._save,
        ).grid(row=0, column=0, padx=5)
        tk.Button(
            btn_frame, text="取消", width=8, font=("Microsoft YaHei", 10),
            bg=COLOR_PANEL, fg=COLOR_TEXT, bd=0, command=self.win.destroy,
        ).grid(row=0, column=1, padx=5)

    def _save(self):
        new_config = {}
        for key, entry in self.entries.items():
            try:
                value = int(entry.get())
                if value <= 0:
                    raise ValueError
                new_config[key] = value
            except ValueError:
                messagebox.showerror("错误", "请输入正整数", parent=self.win)
                return
        self.on_save(new_config)
        self.win.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()
