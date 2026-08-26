from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTabWidget, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

# Obtiene la ruta base del archivo actual y define la ubicación por defecto de la mascota/logo
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_LOGO_PATH = BASE_DIR / "assets" / "logo.png"


class HelpAboutDialog(QDialog):
    def __init__(self, parent=None, logo_path=None):
        super().__init__(parent)
        self.setWindowTitle("Ayuda")
        self.setFixedSize(380, 240)

        # Resolver la ruta de la imagen
        target_path = Path(logo_path) if logo_path else DEFAULT_LOGO_PATH
        if not target_path.exists():
            target_path = Path.cwd() / "assets" / "logo.png"

        self.setStyleSheet("""
            QDialog { 
                background-color: #080a0f; 
                border: 1px solid #84cc16; 
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QTabWidget::pane { border: 1px solid #1f2937; background: #0d1117; }
            QTabBar::tab { background: #111827; color: #9ca3af; padding: 4px 10px; }
            QTabBar::tab:selected {
                background: #0d1117; color: #84cc16; font-weight: bold;
                border: 1px solid #84cc16; border-bottom: none;
            }
            QLabel { color: #f3f4f6; }
            QPushButton {
                background-color: #111827; color: #84cc16;
                border: 1px solid #84cc16; border-radius: 4px; padding: 3px 12px;
            }
            QPushButton:hover { background-color: #84cc16; color: #080a0f; }
        """)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # Pestaña Atajos
        tab_shortcuts = QWidget()
        shortcuts_layout = QVBoxLayout(tab_shortcuts)
        lbl_shortcuts = QLabel("""
        <div style='font-size: 11px;'>
            <p><b style='color:#84cc16;'>Espacio:</b> Reproducir / Pausar</p>
            <p><b style='color:#84cc16;'>Flecha Izq/Der:</b> Pistas Anterior / Siguiente</p>
            <p><b style='color:#84cc16;'>Scroll / Rueda:</b> Navegar en cola (Delay 3s)</p>
            <p><b style='color:#84cc16;'>Clic Título:</b> Ciclar metadatos</p>
            <p><b style='color:#84cc16;'>Clic Derecho:</b> Menú (Playlist / Modo Arrastre)</p>
        </div>
        """)
        lbl_shortcuts.setTextFormat(Qt.TextFormat.RichText)
        shortcuts_layout.addWidget(lbl_shortcuts)
        tabs.addTab(tab_shortcuts, "Atajos")

        # Pestaña Acerca de (con Logo/Mascota)
        tab_about = QWidget()
        about_layout = QHBoxLayout(tab_about)
        about_layout.setContentsMargins(12, 12, 12, 12)
        about_layout.setSpacing(14)

        lbl_logo = QLabel()
        lbl_logo.setFixedSize(64, 64)
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(str(target_path))
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            lbl_logo.setPixmap(scaled_pixmap)

        lbl_about = QLabel("""
        <div style='font-size: 11px;'>
            <h3 style='color:#84cc16; margin-bottom: 2px;'>Iguana Music Player</h3>
            <p style='color:#9ca3af; margin-top: 0;'>Versión 1.0</p>
            <p>Friedrich Nietzsche - "Sin música, la vida sería un error".</p>
        </div>
        """)
        lbl_about.setTextFormat(Qt.TextFormat.RichText)
        lbl_about.setWordWrap(True)

        about_layout.addWidget(lbl_logo)
        about_layout.addWidget(lbl_about, stretch=1)
        tabs.addTab(tab_about, "Acerca de")

        layout.addWidget(tabs)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)