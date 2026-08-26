from pathlib import Path
import sys

from PyQt6.QtWidgets import (
    QLabel, QSlider, QStyleOptionSlider, QStyle,
    QSplashScreen, QApplication, QWidget
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, QPropertyAnimation, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QBrush

# Obtiene el directorio del script actual y la ruta por defecto al logo
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_LOGO_PATH = BASE_DIR / "assets" / "logo.png"


class SplashScreen(QSplashScreen):
    def __init__(self, logo_path=None):
        target_path = Path(logo_path) if logo_path else DEFAULT_LOGO_PATH
        if not target_path.exists():
            target_path = Path.cwd() / "assets" / "logo.png"

        pixmap = QPixmap(str(target_path))
        if pixmap.isNull():
            # Placeholder si no se encuentra la imagen
            pixmap = QPixmap(128, 128)
            pixmap.fill(QColor("#080a0f"))

        super().__init__(pixmap)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(1.0)

    def fade_out(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(1000)  # 1 segundo de desvanecimiento
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.close)
        self.animation.start()


class TrackInfoLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.main_window and hasattr(self.main_window, 'cycle_metadata_view'):
                self.main_window.cycle_metadata_view()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """Redirige el evento de scroll a la función de cambio de canción en la ventana principal."""
        main_win = self.window()
        if hasattr(main_win, 'handle_track_scroll'):
            main_win.handle_track_scroll(event)
            event.accept()
        else:
            super().wheelEvent(event)


class CoverArtOverlay(QLabel):
    """Overlay flotante independiente que se despliega adaptativamente según la posición en pantalla."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            background-color: #080a0f;
            border: 1px solid #84cc16;
            border-radius: 8px;
        """)
        self.setFixedSize(140, 140)
        self.hide()

    def set_cover_pixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                128, 128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)
        else:
            self.clear()


class CoverArtWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pixmap = None
        self.overlay = None

    def set_cover(self, pixmap: QPixmap):
        self.pixmap = pixmap
        if self.overlay:
            self.overlay.set_cover_pixmap(pixmap)
        self.update()

    def _ensure_overlay(self):
        if self.overlay is None:
            self.overlay = CoverArtOverlay(self)
            if self.pixmap:
                self.overlay.set_cover_pixmap(self.pixmap)

    def enterEvent(self, event):
        """Calcula la posición global y conmuta el despliegue hacia arriba o hacia abajo dinámicamente."""
        self._ensure_overlay()

        if self.pixmap and not self.pixmap.isNull():
            main_window = self.window()
            if main_window:
                global_pos = main_window.mapToGlobal(QPoint(0, 0))
                padding_x = 4
                padding_y = 4
                
                x = global_pos.x() + padding_x
                
                # Obtener la geometría disponible del monitor actual
                screen = main_window.screen()
                screen_top = screen.availableGeometry().top() if screen else 0
                
                # Calcular el espacio superior disponible respecto a la pantalla
                space_above = global_pos.y() - screen_top
                overlay_height = self.overlay.height()

                if space_above >= overlay_height + padding_y:
                    # Desplegar hacia arriba si hay espacio suficiente
                    y = global_pos.y() - overlay_height - padding_y
                else:
                    # Desplegar hacia abajo si el reproductor está pegado al borde superior
                    y = global_pos.y() + main_window.height() + padding_y

                self.overlay.move(x, y)
                self.overlay.show()
            
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Oculta el overlay emergente."""
        if self.overlay:
            self.overlay.hide()
        super().leaveEvent(event)

    def paintEvent(self, event):
        """Dibuja la miniatura (26x26) en la barra del reproductor."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.setBrush(QBrush(scaled))
        else:
            painter.setBrush(QBrush(QColor("#1f2937")))

        painter.setPen(QPen(QColor("#84cc16"), 1))
        painter.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 3, 3)


class JumpSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setStyleSheet("""
            QSlider {
                background: transparent;
            }
            QSlider::groove:horizontal {
                height: 0px;
                background: transparent;
            }
            QSlider::handle:horizontal {
                width: 0px;
                height: 0px;
                background: transparent;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            margin = 3.0
            available_width = max(1.0, float(self.width()) - (2 * margin))
            click_x = max(0.0, min(float(event.position().x()) - margin, available_width))
            
            range_val = self.maximum() - self.minimum()
            val = self.minimum() + int(round((click_x / available_width) * range_val))
            
            self.setValue(val)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        
        margin = 3.0
        track_width = rect.width() - (2 * margin)
        track_height = 2.0
        center_y = rect.height() / 2.0

        # Track de fondo
        track_x = margin
        track_y = center_y - (track_height / 2.0)
        track_rect = QRectF(track_x, track_y, track_width, track_height)

        painter.setBrush(QBrush(QColor("#1f2937")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(track_rect, 1, 1)

        # Relleno de volumen
        range_val = max(1, self.maximum() - self.minimum())
        vol_ratio = (self.value() - self.minimum()) / range_val
        fill_width = track_width * vol_ratio

        if fill_width > 0:
            green_rect = QRectF(track_x, track_y, fill_width, track_height)
            painter.setBrush(QBrush(QColor("#84cc16")))
            painter.drawRoundedRect(green_rect, 1, 1)

        # Tirador circular
        handle_x = track_x + fill_width
        handle_center = QPointF(handle_x, center_y)
        
        painter.setBrush(QBrush(QColor("#f9fafb")))
        painter.setPen(QPen(QColor("#84cc16"), 1))
        painter.drawEllipse(handle_center, 2.5, 2.5)