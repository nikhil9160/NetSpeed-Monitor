import os
import sys
import time
import json
import tkinter as tk
from tkinter import ttk
from collections import deque
import psutil
import ctypes

# Win32 TopMost enforcement helper
def set_topmost(hwnd):
    if sys.platform == "win32":
        try:
            # HWND_TOPMOST = -1, SWP_NOSIZE = 0x0001, SWP_NOMOVE = 0x0002, SWP_NOACTIVATE = 0x0010, SWP_SHOWWINDOW = 0x0040
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010 | 0x0040)
        except Exception:
            pass

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_tk.json")

DEFAULT_CONFIG = {
    "is_compact": True,
    "always_on_top": True,
    "unit_mode": "MB/s",
    "pos_x": 120,
    "pos_y": 120,
    "selected_interface": "All Interfaces",
    "theme": "dark"
}

THEMES = {
    "dark": {
        "bg": "#0f172a",
        "border": "#38bdf8",
        "card_bg": "#1e293b",
        "dl": "#00E676",
        "ul": "#D500F9",
        "text": "#f8fafc",
        "sub": "#94a3b8",
        "sep": "#475569"
    },
    "light": {
        "bg": "#ffffff",
        "border": "#2563eb",
        "card_bg": "#f1f5f9",
        "dl": "#059669",
        "ul": "#7c3aed",
        "text": "#0f172a",
        "sub": "#64748b",
        "sep": "#cbd5e1"
    }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def format_speed(bytes_sec, mode="MB/s"):
    if bytes_sec < 0:
        bytes_sec = 0.0
    if mode == "Mbps":
        bits_sec = bytes_sec * 8.0
        mbps = bits_sec / (1000.0 * 1000.0)
        if mbps >= 100:
            return f"{mbps:.1f} Mbps"
        else:
            return f"{mbps:.2f} Mbps"
    elif mode == "KB/s":
        kb_s = bytes_sec / 1024.0
        if kb_s >= 1000:
            return f"{kb_s:.0f} KB/s"
        return f"{kb_s:.1f} KB/s"
    elif mode == "MB/s":
        mb_s = bytes_sec / (1024.0 * 1024.0)
        if mb_s >= 100:
            return f"{mb_s:.1f} MB/s"
        else:
            return f"{mb_s:.2f} MB/s"
    else:  # Auto
        if bytes_sec < 1024:
            return f"{bytes_sec:.0f} B/s"
        elif bytes_sec < 1024 * 1024:
            return f"{bytes_sec / 1024.0:.1f} KB/s"
        else:
            return f"{bytes_sec / (1024.0 * 1024.0):.2f} MB/s"

def format_bytes_human(b):
    if b < 1024:
        return f"{b:.0f} B"
    elif b < 1024 * 1024:
        return f"{b / 1024.0:.1f} KB"
    elif b < 1024 * 1024 * 1024:
        return f"{b / (1024.0 * 1024.0):.1f} MB"
    else:
        return f"{b / (1024.0 * 1024.0 * 1024.0):.2f} GB"

class LightNetSpeedApp:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        
        self.selected_interface = self.config.get("selected_interface", "All Interfaces")
        self.unit_mode = self.config.get("unit_mode", "MB/s")
        self.is_compact = self.config.get("is_compact", True)
        self.theme_name = self.config.get("theme", "dark")

        self.last_bytes_recv = 0
        self.last_bytes_sent = 0
        self.last_time = time.time()
        self.total_dl = 0
        self.total_ul = 0

        self.dl_history = deque(maxlen=40)
        self.ul_history = deque(maxlen=40)

        self.drag_x = 0
        self.drag_y = 0

        self.init_counters()
        self.setup_ui()

        self.root.after(100, self.update_traffic)

    def init_counters(self):
        try:
            if self.selected_interface == "All Interfaces":
                c = psutil.net_io_counters(pernic=False)
            else:
                pernic = psutil.net_io_counters(pernic=True)
                c = pernic.get(self.selected_interface, psutil.net_io_counters(pernic=False))
            if c:
                self.last_bytes_recv = c.bytes_recv
                self.last_bytes_sent = c.bytes_sent
            self.last_time = time.time()
        except Exception:
            pass

    def setup_ui(self):
        t = THEMES.get(self.theme_name, THEMES["dark"])
        self.root.title("NetSpeed Monitor (Light)")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.config.get("always_on_top", True))
        self.root.config(bg=t["bg"])

        pos_x = self.config.get("pos_x", 120)
        pos_y = self.config.get("pos_y", 120)

        # Outer border frame
        self.outer_frame = tk.Frame(self.root, bg=t["border"], bd=1)
        self.outer_frame.pack(fill="both", expand=True)

        self.main_frame = tk.Frame(self.outer_frame, bg=t["bg"])
        self.main_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # --- COMPACT MINI FRAME ---
        self.compact_frame = tk.Frame(self.main_frame, bg=t["bg"], cursor="fleur")
        
        self.lbl_dl = tk.Label(self.compact_frame, text="↓ 0.00 MB/s", font=("Consolas", 10, "bold"), fg=t["dl"], bg=t["bg"])
        self.lbl_dl.pack(side="left", padx=4, pady=3)

        self.lbl_sep = tk.Label(self.compact_frame, text="|", font=("Consolas", 10, "bold"), fg=t["sep"], bg=t["bg"])
        self.lbl_sep.pack(side="left", padx=2)

        self.lbl_ul = tk.Label(self.compact_frame, text="↑ 0.00 MB/s", font=("Consolas", 10, "bold"), fg=t["ul"], bg=t["bg"])
        self.lbl_ul.pack(side="left", padx=4, pady=3)

        self.btn_toggle = tk.Label(self.compact_frame, text="⤢", font=("Segoe UI", 9, "bold"), fg=t["sub"], bg=t["card_bg"], width=2, cursor="hand2")
        self.btn_toggle.pack(side="right", padx=4, pady=3)
        self.btn_toggle.bind("<Button-1>", lambda e: self.toggle_mode())

        # --- EXPANDED DETAILED FRAME ---
        self.expanded_frame = tk.Frame(self.main_frame, bg=t["bg"])

        header = tk.Frame(self.expanded_frame, bg=t["bg"])
        header.pack(fill="x", padx=6, pady=(4, 2))

        self.lbl_title = tk.Label(header, text="NET MONITOR", font=("Segoe UI", 8, "bold"), fg=t["border"], bg=t["bg"])
        self.lbl_title.pack(side="left")

        self.btn_collapse = tk.Label(header, text="⤡", font=("Segoe UI", 9, "bold"), fg=t["sub"], bg=t["card_bg"], width=2, cursor="hand2")
        self.btn_collapse.pack(side="right")
        self.btn_collapse.bind("<Button-1>", lambda e: self.toggle_mode())

        # Speed Stats Row
        stats = tk.Frame(self.expanded_frame, bg=t["bg"])
        stats.pack(fill="x", padx=6, pady=2)

        self.lbl_exp_dl = tk.Label(stats, text="↓ 0.00 MB/s", font=("Consolas", 11, "bold"), fg=t["dl"], bg=t["bg"])
        self.lbl_exp_dl.pack(side="left")

        self.lbl_exp_ul = tk.Label(stats, text="↑ 0.00 MB/s", font=("Consolas", 11, "bold"), fg=t["ul"], bg=t["bg"])
        self.lbl_exp_ul.pack(side="right")

        # Sparkline Canvas Graph
        self.canvas = tk.Canvas(self.expanded_frame, height=40, bg=t["card_bg"], highlightthickness=0)
        self.canvas.pack(fill="x", padx=6, pady=4)

        # Totals label
        self.lbl_total = tk.Label(self.expanded_frame, text="Total: ↓ 0 B | ↑ 0 B", font=("Consolas", 8), fg=t["sub"], bg=t["bg"])
        self.lbl_total.pack(pady=(0, 4))

        # Event bindings for dragging
        for widget in [self.main_frame, self.compact_frame, self.lbl_dl, self.lbl_sep, self.lbl_ul, self.expanded_frame, stats, header, self.lbl_title]:
            widget.bind("<ButtonPress-1>", self.on_drag_start)
            widget.bind("<B1-Motion>", self.on_drag_motion)
            widget.bind("<ButtonRelease-1>", self.on_drag_stop)
            widget.bind("<Double-Button-1>", lambda e: self.toggle_mode())
            widget.bind("<Button-3>", self.show_context_menu)

        self.update_geometry(pos_x, pos_y)

    def apply_theme(self):
        t = THEMES.get(self.theme_name, THEMES["dark"])
        self.root.config(bg=t["bg"])
        self.outer_frame.config(bg=t["border"])
        self.main_frame.config(bg=t["bg"])
        self.compact_frame.config(bg=t["bg"])
        self.expanded_frame.config(bg=t["bg"])

        self.lbl_dl.config(fg=t["dl"], bg=t["bg"])
        self.lbl_sep.config(fg=t["sep"], bg=t["bg"])
        self.lbl_ul.config(fg=t["ul"], bg=t["bg"])
        self.btn_toggle.config(fg=t["sub"], bg=t["card_bg"])

        self.lbl_title.config(fg=t["border"], bg=t["bg"])
        self.btn_collapse.config(fg=t["sub"], bg=t["card_bg"])
        self.lbl_exp_dl.config(fg=t["dl"], bg=t["bg"])
        self.lbl_exp_ul.config(fg=t["ul"], bg=t["bg"])
        self.canvas.config(bg=t["card_bg"])
        self.lbl_total.config(fg=t["sub"], bg=t["bg"])

    def update_geometry(self, x=None, y=None):
        if x is None:
            x = self.root.winfo_x()
        if y is None:
            y = self.root.winfo_y()

        if self.is_compact:
            self.expanded_frame.pack_forget()
            self.compact_frame.pack(fill="both", expand=True)
            w, h = 260, 34
        else:
            self.compact_frame.pack_forget()
            self.expanded_frame.pack(fill="both", expand=True)
            w, h = 260, 140

        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.update_idletasks()
        if sys.platform == "win32" and self.config.get("always_on_top", True):
            set_topmost(self.root.winfo_id())

    def toggle_mode(self):
        self.is_compact = not self.is_compact
        self.config["is_compact"] = self.is_compact
        save_config(self.config)
        self.update_geometry()

    def on_drag_start(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def on_drag_motion(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_x)
        y = self.root.winfo_y() + (event.y - self.drag_y)
        self.root.geometry(f"+{x}+{y}")

    def on_drag_stop(self, event):
        self.config["pos_x"] = self.root.winfo_x()
        self.config["pos_y"] = self.root.winfo_y()
        save_config(self.config)
        if sys.platform == "win32" and self.config.get("always_on_top", True):
            set_topmost(self.root.winfo_id())

    def update_traffic(self):
        now = time.time()
        dt = now - self.last_time
        if dt <= 0:
            dt = 0.001

        try:
            if self.selected_interface == "All Interfaces":
                c = psutil.net_io_counters(pernic=False)
            else:
                pernic = psutil.net_io_counters(pernic=True)
                c = pernic.get(self.selected_interface, None)
                if not c:
                    c = psutil.net_io_counters(pernic=False)

            if c:
                delta_recv = max(0, c.bytes_recv - self.last_bytes_recv) if c.bytes_recv >= self.last_bytes_recv else 0
                delta_sent = max(0, c.bytes_sent - self.last_bytes_sent) if c.bytes_sent >= self.last_bytes_sent else 0

                dl_speed = delta_recv / dt
                ul_speed = delta_sent / dt

                self.total_dl += delta_recv
                self.total_ul += delta_sent

                self.last_bytes_recv = c.bytes_recv
                self.last_bytes_sent = c.bytes_sent
            else:
                dl_speed, ul_speed = 0.0, 0.0
        except Exception:
            dl_speed, ul_speed = 0.0, 0.0

        self.last_time = now
        self.dl_history.append(dl_speed)
        self.ul_history.append(ul_speed)

        dl_str = f"↓ {format_speed(dl_speed, self.unit_mode)}"
        ul_str = f"↑ {format_speed(ul_speed, self.unit_mode)}"

        self.lbl_dl.config(text=dl_str)
        self.lbl_ul.config(text=ul_str)

        if not self.is_compact:
            self.lbl_exp_dl.config(text=dl_str)
            self.lbl_exp_ul.config(text=ul_str)
            self.lbl_total.config(text=f"Total: ↓ {format_bytes_human(self.total_dl)} | ↑ {format_bytes_human(self.total_ul)}")
            self.draw_sparkline()

        # Enforce topmost on interval
        if self.config.get("always_on_top", True):
            set_topmost(self.root.winfo_id())

        self.root.after(1000, self.update_traffic)

    def draw_sparkline(self):
        t = THEMES.get(self.theme_name, THEMES["dark"])
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w <= 10 or h <= 10 or not self.dl_history:
            return

        max_val = max(max(self.dl_history), max(self.ul_history), 1024 * 10)
        n = len(self.dl_history)
        if n < 2:
            return

        dx = w / (n - 1)

        def get_coords(history):
            pts = []
            for i, val in enumerate(history):
                x = i * dx
                y = h - (min(val / max_val, 1.0) * (h - 6)) - 3
                pts.extend([x, y])
            return pts

        ul_pts = get_coords(self.ul_history)
        if len(ul_pts) >= 4:
            self.canvas.create_line(ul_pts, fill=t["ul"], width=2, smooth=True)

        dl_pts = get_coords(self.dl_history)
        if len(dl_pts) >= 4:
            self.canvas.create_line(dl_pts, fill=t["dl"], width=2, smooth=True)

    def show_context_menu(self, event):
        t = THEMES.get(self.theme_name, THEMES["dark"])
        menu = tk.Menu(self.root, tearoff=0, bg=t["bg"], fg=t["text"], activebackground=t["card_bg"], activeforeground=t["border"])

        menu.add_command(label="Toggle Mini / Expanded View", command=self.toggle_mode)
        menu.add_separator()

        # Unit selection
        unit_menu = tk.Menu(menu, tearoff=0, bg=t["bg"], fg=t["text"], activebackground=t["card_bg"], activeforeground=t["border"])
        for u in ["MB/s", "Mbps", "KB/s", "Auto"]:
            unit_menu.add_command(label=u, command=lambda u=u: self.set_unit(u))
        menu.add_cascade(label="Speed Unit", menu=unit_menu)

        # Theme selection
        theme_menu = tk.Menu(menu, tearoff=0, bg=t["bg"], fg=t["text"], activebackground=t["card_bg"], activeforeground=t["border"])
        theme_menu.add_command(label="Dark Neon", command=lambda: self.set_theme("dark"))
        theme_menu.add_command(label="Light Clean", command=lambda: self.set_theme("light"))
        menu.add_cascade(label="Themes", menu=theme_menu)

        # Always top toggle
        menu.add_command(label=f"Always On Top: {'[ON]' if self.config.get('always_on_top', True) else '[OFF]'}", command=self.toggle_always_top)

        menu.add_separator()
        menu.add_command(label="Exit", command=self.root.quit)

        menu.tk_popup(event.x_root, event.y_root)

    def set_unit(self, u):
        self.unit_mode = u
        self.config["unit_mode"] = u
        save_config(self.config)

    def set_theme(self, th):
        self.theme_name = th
        self.config["theme"] = th
        save_config(self.config)
        self.apply_theme()

    def toggle_always_top(self):
        top = not self.config.get("always_on_top", True)
        self.config["always_on_top"] = top
        self.root.attributes("-topmost", top)
        save_config(self.config)
        if sys.platform == "win32" and top:
            set_topmost(self.root.winfo_id())

if __name__ == "__main__":
    root = tk.Tk()
    app = LightNetSpeedApp(root)
    root.mainloop()
