import sys
import os
import ctypes
import ctypes.wintypes
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSystemTrayIcon, QMenu, QPushButton, QFrame, QGraphicsDropShadowEffect,
    QAction, QActionGroup
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QEvent
from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap, QPainter, QBrush, QPen

from config import AppConfig, THEMES, set_windows_autostart, check_windows_autostart
from network_monitor import NetworkTracker, format_speed, format_bytes_human, get_network_interfaces
from sparkline import SparklineWidget

# Windows TopMost and Extended Style constants
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

def win32_setup_persistent_topmost(hwnd):
    """Configures OS-level extended window styles so Windows Shell 'Show Desktop' (Win+D / 3-finger swipe) does not minimize or hide this floating widget."""
    if sys.platform == "win32":
        try:
            hwnd_int = int(hwnd)
            cur_style = ctypes.windll.user32.GetWindowLongW(hwnd_int, GWL_EXSTYLE)
            new_style = cur_style | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            ctypes.windll.user32.SetWindowLongW(hwnd_int, GWL_EXSTYLE, new_style)
            ctypes.windll.user32.SetWindowPos(
                hwnd_int,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_FRAMECHANGED
            )
        except Exception:
            pass

def win32_force_topmost(hwnd):
    """Enforces absolute topmost Z-order above taskbar and all windows without stealing focus."""
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetWindowPos(
                int(hwnd),
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        except Exception:
            pass

def create_tray_icon_pixmap(dl_color="#00E676", ul_color="#D500F9"):
    """Generates a crisp 32x32 icon pixmap for Windows system tray."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Dark background circle
    painter.setBrush(QBrush(QColor(15, 23, 42)))
    painter.setPen(QPen(QColor(56, 189, 248), 1.5))
    painter.drawEllipse(2, 2, 28, 28)

    # Download arrow (Down)
    painter.setPen(QPen(QColor(dl_color), 2.2))
    painter.drawLine(11, 8, 11, 21)
    painter.drawLine(11, 21, 7, 17)
    painter.drawLine(11, 21, 15, 17)

    # Upload arrow (Up)
    painter.setPen(QPen(QColor(ul_color), 2.2))
    painter.drawLine(21, 23, 21, 10)
    painter.drawLine(21, 10, 17, 14)
    painter.drawLine(21, 10, 25, 14)

    painter.end()
    return pixmap

class NetSpeedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.tracker = NetworkTracker()
        self.tracker.set_interface(self.config.get("selected_interface", "All Interfaces"))

        self.drag_position = None
        self.is_compact = self.config.get("is_compact", True)
        self.user_hidden = False

        self.init_ui()
        self.apply_window_flags()

        # Update stats timer (1000ms default)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        refresh_rate = self.config.get("refresh_rate_ms", 1000)
        self.timer.start(refresh_rate)

        # High-frequency TopMost watchdog timer (200ms) to resist 3-finger swipe down / Win+D desktop toggle
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.timeout.connect(self.watchdog_check)
        self.watchdog_timer.start(200)

        # Restore position
        self.restore_position()

        # System tray setup
        self.setup_system_tray()
        
        # Apply theme and initial visibility
        self.update_mode_visibility()
        self.update_stats()

    def enforce_topmost(self):
        """Keeps the widget firmly on top of all windows including taskbar."""
        if self.config.get("always_on_top", True):
            win32_setup_persistent_topmost(self.winId())

    def watchdog_check(self):
        """Watchdog to ensure the widget is never minimized or hidden during 3-finger gestures or Show Desktop."""
        if self.config.get("always_on_top", True) and not self.user_hidden:
            if self.isMinimized():
                self.showNormal()
            if not self.isVisible():
                self.show()
                self.raise_()
            win32_force_topmost(self.winId())

    def nativeEvent(self, eventType, message):
        """Intercepts low-level Windows Shell messages to prevent minimize/hide when 3-finger swipe down occurs."""
        if sys.platform == "win32" and eventType == b"windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(message.__int__())
                WM_SYSCOMMAND = 0x0112
                SC_MINIMIZE = 0xF020
                WM_SHOWWINDOW = 0x0018

                # Block minimize commands sent by Windows Shell (Win+D / 3-finger gesture)
                if msg.message == WM_SYSCOMMAND:
                    if (msg.wParam & 0xFFF0) == SC_MINIMIZE:
                        return True, 0  # Swallow minimize command

                # Block shell hiding if not intentionally hidden by user
                if msg.message == WM_SHOWWINDOW and msg.wParam == 0:
                    if not self.user_hidden and self.config.get("always_on_top", True):
                        return True, 0  # Block hiding
            except Exception:
                pass
        return super().nativeEvent(eventType, message)

    def apply_window_flags(self):
        flags = Qt.FramelessWindowHint
        if self.config.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(self.config.get("opacity", 0.92))

    def showEvent(self, event):
        super().showEvent(event)
        self.enforce_topmost()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.ActivationChange, QEvent.WindowStateChange):
            if self.isMinimized() and not self.user_hidden:
                self.showNormal()
            self.enforce_topmost()

    def init_ui(self):
        self.setObjectName("MainWindow")
        
        # Root layout with 0 margins
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Container Frame
        self.container = QFrame(self)
        self.container.setObjectName("ContainerFrame")
        self.root_layout.addWidget(self.container)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # =========================================================================
        # 1. COMPACT PILL VIEW
        # =========================================================================
        self.compact_widget = QWidget(self.container)
        compact_layout = QHBoxLayout(self.compact_widget)
        compact_layout.setContentsMargins(10, 0, 3, 0)
        compact_layout.setSpacing(6)

        # Download Label
        self.compact_dl_label = QLabel("↓ 0.00 MB/s", self.compact_widget)
        self.compact_dl_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.compact_dl_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        # Separator
        self.compact_sep_label = QLabel("|", self.compact_widget)
        self.compact_sep_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.compact_sep_label.setAlignment(Qt.AlignCenter)

        # Upload Label
        self.compact_ul_label = QLabel("↑ 0.00 MB/s", self.compact_widget)
        self.compact_ul_label.setFont(QFont("Consolas", 9, QFont.Bold))
        self.compact_ul_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        # Expand Mode Button
        self.expand_btn = QPushButton("⤢", self.compact_widget)
        self.expand_btn.setFixedSize(18, 18)
        self.expand_btn.setToolTip("Expand to detailed graph view (Double-click widget)")
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.clicked.connect(self.toggle_mode)

        compact_layout.addWidget(self.compact_dl_label)
        compact_layout.addWidget(self.compact_sep_label)
        compact_layout.addWidget(self.compact_ul_label)
        compact_layout.addWidget(self.expand_btn)

        # =========================================================================
        # 2. EXPANDED DETAILED VIEW
        # =========================================================================
        self.expanded_widget = QWidget(self.container)
        expanded_layout = QVBoxLayout(self.expanded_widget)
        expanded_layout.setContentsMargins(4, 4, 4, 4)
        expanded_layout.setSpacing(5)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.header_title = QLabel("NET MONITOR", self.expanded_widget)
        self.header_title.setFont(QFont("Segoe UI", 8, QFont.Bold))

        self.iface_label = QLabel(self.tracker.selected_interface, self.expanded_widget)
        self.iface_label.setFont(QFont("Segoe UI", 7))

        self.collapse_btn = QPushButton("⤡", self.expanded_widget)
        self.collapse_btn.setFixedSize(18, 18)
        self.collapse_btn.setToolTip("Compact mini pill view (Double-click widget)")
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.clicked.connect(self.toggle_mode)

        header_layout.addWidget(self.header_title)
        header_layout.addWidget(self.iface_label)
        header_layout.addStretch()
        header_layout.addWidget(self.collapse_btn)

        # Speed Stats Display Row
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        # Download Box
        dl_box = QVBoxLayout()
        dl_box.setSpacing(1)
        self.dl_title = QLabel("DOWNLOAD", self.expanded_widget)
        self.dl_title.setFont(QFont("Segoe UI", 7, QFont.Bold))
        self.exp_dl_label = QLabel("↓ 0.00 MB/s", self.expanded_widget)
        self.exp_dl_label.setFont(QFont("Consolas", 10, QFont.Bold))
        dl_box.addWidget(self.dl_title)
        dl_box.addWidget(self.exp_dl_label)

        # Upload Box
        ul_box = QVBoxLayout()
        ul_box.setSpacing(1)
        self.ul_title = QLabel("UPLOAD", self.expanded_widget)
        self.ul_title.setFont(QFont("Segoe UI", 7, QFont.Bold))
        self.exp_ul_label = QLabel("↑ 0.00 MB/s", self.expanded_widget)
        self.exp_ul_label.setFont(QFont("Consolas", 10, QFont.Bold))
        ul_box.addWidget(self.ul_title)
        ul_box.addWidget(self.exp_ul_label)

        stats_layout.addLayout(dl_box)
        stats_layout.addStretch()
        stats_layout.addLayout(ul_box)

        # Sparkline Graph Widget
        self.sparkline = SparklineWidget(self.expanded_widget)
        self.sparkline.setFixedHeight(48)

        # Footer Row (Session Totals)
        self.total_label = QLabel("Session: ↓ 0 B | ↑ 0 B", self.expanded_widget)
        self.total_label.setFont(QFont("Consolas", 8))
        self.total_label.setAlignment(Qt.AlignCenter)

        expanded_layout.addLayout(header_layout)
        expanded_layout.addLayout(stats_layout)
        expanded_layout.addWidget(self.sparkline)
        expanded_layout.addWidget(self.total_label)

        # Add both to container layout
        self.container_layout.addWidget(self.compact_widget)
        self.container_layout.addWidget(self.expanded_widget)

    def apply_theme(self):
        theme = self.config.get_theme_data()
        dl_color = theme["dl_color"]
        ul_color = theme["ul_color"]
        text_pri = theme["text_primary"]
        text_sec = theme["text_secondary"]
        border_col = theme["border"]
        card_bg = theme["bg"].format(alpha="0.94" if not self.is_compact else "0.92")

        # Container styling
        radius = "16px" if self.is_compact else "12px"
        self.container.setStyleSheet(f"""
            #ContainerFrame {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: {radius};
            }}
        """)

        # Compact Labels
        self.compact_dl_label.setStyleSheet(f"color: {dl_color};")
        self.compact_ul_label.setStyleSheet(f"color: {ul_color};")
        self.compact_sep_label.setStyleSheet(f"color: {theme['sep_color']};")

        btn_css = f"""
            QPushButton {{
                background: rgba(128, 128, 128, 0.20);
                color: {text_sec};
                border: none;
                border-radius: 9px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {dl_color};
                color: #FFFFFF;
            }}
        """
        self.expand_btn.setStyleSheet(btn_css)
        self.collapse_btn.setStyleSheet(btn_css)

        self.header_title.setStyleSheet(f"color: {text_pri}; letter-spacing: 1px;")
        self.iface_label.setStyleSheet(f"color: {text_sec}; background: rgba(128,128,128,0.15); padding: 2px 5px; border-radius: 4px;")
        self.dl_title.setStyleSheet(f"color: {text_sec};")
        self.ul_title.setStyleSheet(f"color: {text_sec};")
        self.exp_dl_label.setStyleSheet(f"color: {dl_color};")
        self.exp_ul_label.setStyleSheet(f"color: {ul_color};")
        self.total_label.setStyleSheet(f"color: {text_sec};")

        # Sparkline Theme
        grid_col = QColor(255, 255, 255, 15) if "255" in theme["graph_grid"] else QColor(0, 0, 0, 15)
        self.sparkline.set_theme_colors(dl_color, ul_color, grid_col)

        # Tray Icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if not os.path.exists(icon_path) and hasattr(self, 'tray_icon'):
            self.tray_icon.setIcon(QIcon(create_tray_icon_pixmap(dl_color, ul_color)))

    def adjust_compact_size(self):
        if self.is_compact:
            w = self.compact_widget.sizeHint().width() + 2
            self.setFixedSize(max(226, w), 34)

    def update_mode_visibility(self):
        if self.is_compact:
            self.expanded_widget.hide()
            self.compact_widget.show()
            self.container_layout.setContentsMargins(0, 0, 0, 0)
            self.adjust_compact_size()
        else:
            self.compact_widget.hide()
            self.expanded_widget.show()
            self.container_layout.setContentsMargins(8, 6, 8, 6)
            self.setFixedSize(300, 165)
        
        self.apply_theme()
        if not self.user_hidden:
            self.show()
            self.raise_()
            self.enforce_topmost()

    def toggle_mode(self):
        self.is_compact = not self.is_compact
        self.config.set("is_compact", self.is_compact)
        self.update_mode_visibility()

    def update_stats(self):
        dl_speed, ul_speed = self.tracker.update()
        unit_mode = self.config.get("unit_mode", "MB/s")

        dl_str = f"↓ {format_speed(dl_speed, unit_mode)}"
        ul_str = f"↑ {format_speed(ul_speed, unit_mode)}"

        # Compact Labels
        self.compact_dl_label.setText(dl_str)
        self.compact_ul_label.setText(ul_str)
        if self.is_compact:
            self.adjust_compact_size()
        
        # Expanded Labels
        self.exp_dl_label.setText(dl_str)
        self.exp_ul_label.setText(ul_str)

        # Totals
        tot_dl = format_bytes_human(self.tracker.total_downloaded)
        tot_ul = format_bytes_human(self.tracker.total_uploaded)
        self.total_label.setText(f"Total:  ↓ {tot_dl}  |  ↑ {tot_ul}")

        # Sparkline
        if not self.is_compact:
            self.sparkline.set_data(self.tracker.dl_history, self.tracker.ul_history)

        # Update Tray Tooltip
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.setToolTip(f"NetSpeed Monitor ({unit_mode})\n{dl_str}  |  {ul_str}\nTotal: ↓ {tot_dl} | ↑ {tot_ul}")

        # Ensure Topmost
        if not self.user_hidden:
            self.enforce_topmost()

    # --- DRAGGING & EDGE SNAPPING ---
    def restore_position(self):
        pos_x = self.config.get("pos_x", 120)
        pos_y = self.config.get("pos_y", 120)
        
        # Bounds checking to guarantee widget stays visible on screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            pos_x = max(geo.left(), min(pos_x, geo.right() - 250))
            pos_y = max(geo.top(), min(pos_y, geo.bottom() - 40))
        self.move(pos_x, pos_y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.config.get("is_locked", False):
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            if not self.config.get("is_locked", False):
                new_pos = event.globalPos() - self.drag_position
                
                # Edge snapping
                if self.config.get("snap_to_edges", True):
                    screen = QApplication.primaryScreen()
                    if screen:
                        geo = screen.availableGeometry()
                        snap_margin = 16
                        x, y = new_pos.x(), new_pos.y()
                        w, h = self.width(), self.height()

                        if abs(x - geo.left()) < snap_margin:
                            x = geo.left()
                        elif abs(x + w - geo.right()) < snap_margin:
                            x = geo.right() - w

                        if abs(y - geo.top()) < snap_margin:
                            y = geo.top()
                        elif abs(y + h - geo.bottom()) < snap_margin:
                            y = geo.bottom() - h

                        new_pos = QPoint(x, y)

                self.move(new_pos)
                event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            self.config.set("pos_x", self.x())
            self.config.set("pos_y", self.y())
            self.enforce_topmost()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_mode()

    # --- CONTEXT MENU & SYSTEM TRAY ---
    def get_menu_stylesheet(self):
        theme = self.config.get_theme_data()
        return f"""
            QMenu {{
                background-color: {theme['menu_bg']};
                color: {theme['menu_text']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 26px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {theme['menu_hover']};
                color: {theme['dl_color']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {theme['sep_color']};
                margin: 4px 8px;
            }}
        """

    def build_app_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self.get_menu_stylesheet())

        # Toggle Mode
        mode_str = "⤢ Expand to Detailed Graph" if self.is_compact else "⤡ Switch to Mini Pill View"
        act_toggle = menu.addAction(mode_str)
        act_toggle.triggered.connect(self.toggle_mode)

        menu.addSeparator()

        # Always On Top
        act_top = QAction("📌 Always On Top", self)
        act_top.setCheckable(True)
        act_top.setChecked(self.config.get("always_on_top", True))
        act_top.triggered.connect(self.toggle_always_on_top)
        menu.addAction(act_top)

        # Lock Position
        act_lock = QAction("🔒 Lock Widget Position", self)
        act_lock.setCheckable(True)
        act_lock.setChecked(self.config.get("is_locked", False))
        act_lock.triggered.connect(self.toggle_lock_position)
        menu.addAction(act_lock)

        # Snap to Edges
        act_snap = QAction("🧲 Snap to Screen Edges", self)
        act_snap.setCheckable(True)
        act_snap.setChecked(self.config.get("snap_to_edges", True))
        act_snap.triggered.connect(self.toggle_snap_edges)
        menu.addAction(act_snap)

        # Run on Windows Startup
        act_startup = QAction("🚀 Start with Windows", self)
        act_startup.setCheckable(True)
        act_startup.setChecked(self.config.get("start_with_windows", False))
        act_startup.triggered.connect(self.toggle_autostart)
        menu.addAction(act_startup)

        menu.addSeparator()

        # Themes Submenu
        theme_menu = menu.addMenu("🎨 Themes & Appearance")
        theme_menu.setStyleSheet(self.get_menu_stylesheet())
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        current_theme = self.config.get("theme", "dark_neon")

        for t_key, t_info in THEMES.items():
            act_t = QAction(t_info["name"], self)
            act_t.setCheckable(True)
            act_t.setChecked(t_key == current_theme)
            act_t.triggered.connect(lambda checked, k=t_key: self.set_theme(k))
            theme_group.addAction(act_t)
            theme_menu.addAction(act_t)

        # Speed Unit Submenu
        unit_menu = menu.addMenu("⚡ Speed Unit")
        unit_menu.setStyleSheet(self.get_menu_stylesheet())
        unit_group = QActionGroup(self)
        unit_group.setExclusive(True)
        current_unit = self.config.get("unit_mode", "MB/s")
        for unit in ["MB/s", "Mbps", "KB/s", "Auto"]:
            act_u = QAction(unit, self)
            act_u.setCheckable(True)
            act_u.setChecked(unit == current_unit)
            act_u.triggered.connect(lambda checked, u=unit: self.set_unit_mode(u))
            unit_group.addAction(act_u)
            unit_menu.addAction(act_u)

        # Network Interface Submenu
        iface_menu = menu.addMenu("🌐 Network Adapter")
        iface_menu.setStyleSheet(self.get_menu_stylesheet())
        iface_group = QActionGroup(self)
        iface_group.setExclusive(True)
        current_iface = self.config.get("selected_interface", "All Interfaces")
        for iface in get_network_interfaces():
            act_i = QAction(iface, self)
            act_i.setCheckable(True)
            act_i.setChecked(iface == current_iface)
            act_i.triggered.connect(lambda checked, i=iface: self.set_interface(i))
            iface_group.addAction(act_i)
            iface_menu.addAction(act_i)

        # Opacity Submenu
        op_menu = menu.addMenu("👁 Transparency")
        op_menu.setStyleSheet(self.get_menu_stylesheet())
        op_group = QActionGroup(self)
        op_group.setExclusive(True)
        current_op = self.config.get("opacity", 0.92)
        for op_val, label in [(1.0, "100% Solid"), (0.92, "92% Standard Glass"), (0.75, "75% Translucent"), (0.50, "50% Ghost")]:
            act_o = QAction(label, self)
            act_o.setCheckable(True)
            act_o.setChecked(abs(current_op - op_val) < 0.05)
            act_o.triggered.connect(lambda checked, v=op_val: self.set_window_opacity(v))
            op_group.addAction(act_o)
            op_menu.addAction(act_o)

        menu.addSeparator()

        # Reset Position
        act_reset = menu.addAction("📍 Reset to Screen Center")
        act_reset.triggered.connect(self.reset_position)

        # Hide to Tray
        act_hide = menu.addAction("🗕 Hide to System Tray")
        act_hide.triggered.connect(self.hide_to_tray)

        # Exit
        act_exit = menu.addAction("❌ Exit Application")
        act_exit.triggered.connect(QApplication.instance().quit)

        return menu

    def contextMenuEvent(self, event):
        menu = self.build_app_menu()
        menu.exec_(event.globalPos())

    def toggle_always_on_top(self, checked):
        self.config.set("always_on_top", checked)
        self.apply_window_flags()
        self.show()
        self.enforce_topmost()

    def toggle_lock_position(self, checked):
        self.config.set("is_locked", checked)

    def toggle_snap_edges(self, checked):
        self.config.set("snap_to_edges", checked)

    def toggle_autostart(self, checked):
        self.config.set("start_with_windows", checked)

    def set_theme(self, theme_key):
        self.config.set("theme", theme_key)
        self.apply_theme()

    def set_unit_mode(self, unit):
        self.config.set("unit_mode", unit)
        self.update_stats()

    def set_interface(self, iface):
        self.config.set("selected_interface", iface)
        self.tracker.set_interface(iface)
        disp = iface if len(iface) <= 15 else iface[:13] + ".."
        self.iface_label.setText(disp)
        self.update_stats()

    def set_window_opacity(self, opacity):
        self.config.set("opacity", opacity)
        self.setWindowOpacity(opacity)

    def reset_position(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            new_x = geo.left() + (geo.width() - self.width()) // 2
            new_y = geo.top() + (geo.height() - self.height()) // 2
            self.move(new_x, new_y)
            self.config.set("pos_x", new_x)
            self.config.set("pos_y", new_y)

    def hide_to_tray(self):
        self.user_hidden = True
        self.hide()

    def show_from_tray(self):
        self.user_hidden = False
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        self.enforce_topmost()

    def setup_system_tray(self):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
        else:
            theme = self.config.get_theme_data()
            app_icon = QIcon(create_tray_icon_pixmap(theme["dl_color"], theme["ul_color"]))

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(app_icon)
        self.tray_icon.setToolTip("NetSpeed Monitor\nRunning in background")

        # Tray Context Menu
        self.tray_icon.setContextMenu(self.build_app_menu())
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide_to_tray()
            else:
                self.show_from_tray()

if __name__ == "__main__":
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keeps app running in system tray
    
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    widget = NetSpeedWidget()
    widget.show()

    sys.exit(app.exec_())
