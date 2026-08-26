import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt6.QtGui import QPixmap, QTransform

from src.ui import IguanaWindow

def get_resource_path(relative_path: str) -> Path:
    """ Obtiene la ruta absoluta a los recursos, compatible con PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / relative_path

LOGO_PATH = get_resource_path("assets/logo.png")


class SplashScreen(QSplashScreen):
    def __init__(self, logo_path=None, size=(420, 420), rotation_angle=-90):
        target_path = Path(logo_path) if logo_path else LOGO_PATH
        pixmap = QPixmap(str(target_path))
        
        if not pixmap.isNull():
            # 1. Redimensionar
            pixmap = pixmap.scaled(
                size[0], size[1],
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            # 2. Aplicar rotación
            if rotation_angle != 0:
                transform = QTransform().rotate(rotation_angle)
                pixmap = pixmap.transformed(
                    transform, 
                    Qt.TransformationMode.SmoothTransformation
                )

        super().__init__(pixmap)
        
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(1.0)

    def fade_out(self, on_finished_callback=None):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(800)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        
        if on_finished_callback:
            self.animation.finished.connect(on_finished_callback)
            
        self.animation.finished.connect(self.close)
        self.animation.start()


def load_stylesheet(app):
    qss_path = get_resource_path("assets/styles.qss")
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_stylesheet(app)

    splash = SplashScreen(size=(420, 420), rotation_angle=-90)
    splash.show()
    app.processEvents()

    window = None

    def launch_main_window():
        global window
        window = IguanaWindow()
        window.show()

    QTimer.singleShot(2000, lambda: splash.fade_out(on_finished_callback=launch_main_window))

    sys.exit(app.exec())