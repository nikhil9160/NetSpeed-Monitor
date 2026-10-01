from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPainterPath

class SparklineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dl_history = []
        self.ul_history = []
        self.dl_color = QColor(0, 230, 118)
        self.ul_color = QColor(213, 0, 249)
        self.grid_color = QColor(255, 255, 255, 20)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def set_theme_colors(self, dl_hex, ul_color_hex, grid_qcolor):
        self.dl_color = QColor(dl_hex)
        self.ul_color = QColor(ul_color_hex)
        self.grid_color = grid_qcolor
        self.update()

    def set_data(self, dl_history, ul_history):
        self.dl_history = list(dl_history)
        self.ul_history = list(ul_history)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        if w <= 10 or h <= 10:
            return

        # Background grid subtle lines
        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, int(h / 2), int(w), int(h / 2))

        if not self.dl_history and not self.ul_history:
            return

        max_val = max(
            max(self.dl_history) if self.dl_history else 0,
            max(self.ul_history) if self.ul_history else 0,
            1024 * 10.0  # Min scale baseline 10 KB/s
        )

        def draw_series(history, stroke_color, alpha_fill):
            if len(history) < 2:
                return

            n = len(history)
            dx = w / (n - 1)

            path = QPainterPath()
            fill_path = QPainterPath()
            fill_path.moveTo(0, h)

            for i, val in enumerate(history):
                x = i * dx
                norm_val = min(val / max_val, 1.0)
                y = h - (norm_val * (h - 8)) - 3

                if i == 0:
                    path.moveTo(x, y)
                    fill_path.lineTo(x, y)
                else:
                    path.lineTo(x, y)
                    fill_path.lineTo(x, y)

            fill_path.lineTo(w, h)
            fill_path.closeSubpath()

            # Fill gradient under line
            gradient = QLinearGradient(0, 0, 0, h)
            grad_color = QColor(stroke_color)
            grad_color.setAlpha(alpha_fill)
            gradient.setColorAt(0.0, grad_color)
            gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillPath(fill_path, QBrush(gradient))

            # Draw smooth stroke line
            pen = QPen(stroke_color, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)

        # Draw Upload first
        draw_series(self.ul_history, self.ul_color, 40)

        # Draw Download on top
        draw_series(self.dl_history, self.dl_color, 50)
