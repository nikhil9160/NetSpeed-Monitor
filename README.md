<p align="center">
  <img src="logo.png" width="140" height="140" alt="NetSpeed Monitor Logo" style="border-radius: 28px;" />
</p>

# ⚡ NetSpeed Monitor

A modern, ultra-lightweight, and aesthetic real-time internet speed floating widget for Windows. Displays live download and upload speeds, session data totals, and real-time sparkline traffic graphs.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![RAM](https://img.shields.io/badge/RAM_Usage-<20MB-brightgreen.svg)

---

## ✨ Features

- 📌 **Always-On-Top (Taskbar & Fullscreen Proof)**: Stays reliably on top of all windows and prevents Windows taskbar from overlapping it (`HWND_TOPMOST` enforcement).
- 🗔 **Dual View Modes**:
  - **Mini Pill Mode**: Ultra-compact floating pill showing `↓ Download` and `↑ Upload` speeds.
  - **Expanded Graph Mode**: Detailed card with real-time gradient sparkline graph, network adapter tag, and session total bandwidth transferred.
  - *Double-click* the widget anywhere to toggle between modes.
- 🎨 **Multiple Visual Themes**:
  - **Dark Cyber** (Neon Cyan & Electric Magenta on deep navy glass)
  - **Light Clean** (Crystal clean light glass theme for light wallpapers & minimal setups)
  - **OLED Pure Black** (Pure `#000000` with high contrast neon)
  - **Nordic Slate** (Soft minimalist charcoal with pastel accents)
- 🧲 **Smart Edge Snapping**: Magnetically snaps to screen boundaries and taskbar edges for pixel-perfect placement.
- 🚀 **Windows Auto-Start**: Easily toggle *“Start with Windows”* directly from the right-click menu or system tray.
- 🔔 **System Tray & Hidden Icons**:
  - Resides quietly in the Windows notification area / hidden icons tray.
  - Live tooltip updates showing current speeds and transferred session data.
  - Left-click tray icon to show/hide the widget anytime.
- ⚡ **Speed Units & Adapters**:
  - Supports `MB/s`, `Mbps`, `KB/s`, and `Auto` dynamic scaling.
  - Select specific network adapters (Wi-Fi, Ethernet, VPNs) or monitor *All Interfaces* simultaneously.
- 🪶 **Ultra-Lightweight & Smooth**: Consumes `< 20MB RAM` and `~0.0% CPU`. High-DPI scaling enabled for 4K / retina displays.

---

## 🚀 Quick Start & Installation

### Option 1: Run with Python

1. **Clone or download the repository**:
   ```bash
   git clone https://github.com/your-username/speed-meter.git
   cd speed-meter
   ```

2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch**:
   - Double-click `run.bat` or run:
     ```bash
     python main.py
     ```
   - To run completely silently in the background (no console window), double-click `run_silently.vbs` or run `pythonw main.py`.

---

## 🖱️ Controls & Shortcuts

| Action | Function |
|---|---|
| **Left Click + Drag** | Move widget anywhere on screen (auto-snaps to edges) |
| **Double Click** | Toggle between **Mini Pill** and **Expanded Graph** mode |
| **Right Click** | Open quick settings menu (Units, Themes, Opacity, Auto-Start, Lock) |
| **Tray Icon Click** | Show / Hide widget from system tray |

---

## ⚙️ Configuration & Customization

Settings are automatically saved in `config.json` upon change:

```json
{
    "is_compact": true,
    "always_on_top": true,
    "opacity": 0.92,
    "unit_mode": "MB/s",
    "pos_x": 120,
    "pos_y": 120,
    "is_locked": false,
    "selected_interface": "All Interfaces",
    "theme": "dark_neon",
    "snap_to_edges": true,
    "start_with_windows": false,
    "refresh_rate_ms": 1000
}
```

---

## 📦 Building Standalone .EXE

To create a standalone `.exe` with icon embedded:

1. Run `build_exe.bat` or execute:
   ```bash
   pip install pyinstaller Pillow
   pyinstaller --onedir --windowed --name "NetSpeedMonitor" --icon="icon.ico" --add-data "icon.png;." main.py
   ```
2. Your standalone executable will be located in the `dist/NetSpeedMonitor/` directory.

---

## 🪶 Fallback / Zero-Dependency Version

If you need a super lightweight Tkinter version with zero extra GUI dependencies, you can run:
```bash
python tkinter_app.py
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
