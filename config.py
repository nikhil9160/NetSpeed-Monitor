import json
import os
import sys

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

THEMES = {
    "dark_neon": {
        "name": "Dark Cyber",
        "bg": "rgba(15, 23, 42, {alpha})",
        "border": "rgba(56, 189, 248, 0.5)",
        "card_bg": "#0F172A",
        "dl_color": "#00E676",   # Emerald Cyan
        "ul_color": "#D500F9",   # Electric Magenta
        "text_primary": "#F8FAFC",
        "text_secondary": "#94A3B8",
        "sep_color": "#334155",
        "graph_grid": "rgba(255, 255, 255, 0.08)",
        "menu_bg": "#0F172A",
        "menu_hover": "#1E293B",
        "menu_text": "#F8FAFC",
    },
    "light_clean": {
        "name": "Light Clean",
        "bg": "rgba(255, 255, 255, {alpha})",
        "border": "rgba(37, 99, 235, 0.45)",
        "card_bg": "#FFFFFF",
        "dl_color": "#059669",   # Emerald Green
        "ul_color": "#7C3AED",   # Purple Violet
        "text_primary": "#0F172A",
        "text_secondary": "#64748B",
        "sep_color": "#CBD5E1",
        "graph_grid": "rgba(0, 0, 0, 0.08)",
        "menu_bg": "#FFFFFF",
        "menu_hover": "#F1F5F9",
        "menu_text": "#0F172A",
    },
    "oled_black": {
        "name": "OLED Pure Black",
        "bg": "rgba(0, 0, 0, {alpha})",
        "border": "rgba(0, 230, 118, 0.6)",
        "card_bg": "#000000",
        "dl_color": "#00FF88",
        "ul_color": "#FF007F",
        "text_primary": "#FFFFFF",
        "text_secondary": "#A1A1AA",
        "sep_color": "#27272A",
        "graph_grid": "rgba(255, 255, 255, 0.12)",
        "menu_bg": "#121212",
        "menu_hover": "#242424",
        "menu_text": "#FFFFFF",
    },
    "nordic_slate": {
        "name": "Nordic Slate",
        "bg": "rgba(30, 41, 59, {alpha})",
        "border": "rgba(148, 163, 184, 0.4)",
        "card_bg": "#1E293B",
        "dl_color": "#38BDF8",   # Sky Blue
        "ul_color": "#F472B6",   # Rose Pink
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "sep_color": "#475569",
        "graph_grid": "rgba(255, 255, 255, 0.07)",
        "menu_bg": "#1E293B",
        "menu_hover": "#334155",
        "menu_text": "#F1F5F9",
    }
}

DEFAULT_CONFIG = {
    "is_compact": True,
    "always_on_top": True,
    "opacity": 0.92,
    "unit_mode": "MB/s",  # 'MB/s', 'Mbps', 'KB/s', or 'Auto'
    "pos_x": 120,
    "pos_y": 120,
    "is_locked": False,
    "selected_interface": "All Interfaces",
    "theme": "dark_neon",
    "snap_to_edges": True,
    "start_with_windows": False,
    "refresh_rate_ms": 1000
}

def get_startup_shortcut_command():
    """Returns the command to execute for auto-start."""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        python_exe = sys.executable
        # Try to use pythonw.exe to run without console window
        pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        if os.path.exists(pythonw):
            python_exe = pythonw
        main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        return f'"{python_exe}" "{main_script}"'

def set_windows_autostart(enabled=True):
    """Adds or removes the application from Windows Run registry key."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "NetSpeedMonitor"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = get_startup_shortcut_command()
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Auto-start registry error: {e}")
        return False

def check_windows_autostart():
    """Checks if the application is currently registered to start with Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "NetSpeedMonitor"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, app_name)
            return True
    except Exception:
        return False

class AppConfig:
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        self.load()
        # Sync autostart status with actual registry status
        if sys.platform == "win32":
            self.data["start_with_windows"] = check_windows_autostart()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.data[key] = value
        if key == "start_with_windows" and sys.platform == "win32":
            set_windows_autostart(bool(value))
        self.save()

    def get_theme_data(self):
        theme_key = self.get("theme", "dark_neon")
        return THEMES.get(theme_key, THEMES["dark_neon"])
