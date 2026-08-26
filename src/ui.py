import math
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMenu, QApplication,
    QWidgetAction, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QLineF, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QAction, QBrush, QCursor

from .player import MusicPlayer
from .icons import create_svg_icon
from .utils import extract_cover_art, get_track_info, get_track_duration, format_time
from .widgets import TrackInfoLabel, CoverArtWidget, JumpSlider
from .dialogs import HelpAboutDialog


class IguanaWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.player = MusicPlayer()
        self.playlist = []        
        self.tracks_metadata = [] 
        self.current_index = -1
        self.track_duration = 180.0
        self.progress = 0.0
        self.metadata_view_mode = 0
        
        self.drag_mode_enabled = False
        self._drag_pos = QPoint()

        # Temporizador para restaurar la información tras ajustar volumen / avisos
        self.vol_timer = QTimer(self)
        self.vol_timer.setSingleShot(True)
        self.vol_timer.timeout.connect(self.restore_info_after_volume)
        self._was_marquee_active = False

        # Temporizador con retardo de 3 segundos para el scroll de canciones
        self.scroll_debounce_timer = QTimer(self)
        self.scroll_debounce_timer.setSingleShot(True)
        self.scroll_debounce_timer.setInterval(3000)
        self.scroll_debounce_timer.timeout.connect(self._on_scroll_debounce_timeout)

        # Temporizador de progreso de reproducción
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_progress)

        self.player.track_ended.connect(self.handle_track_ended)

        self.init_ui()

        self.welcome_text = "    ¡Te damos la bienvenida! Carga tus canciones para disfrutar    "
        self.marquee_timer = QTimer(self)
        self.marquee_timer.setInterval(160)
        self.marquee_timer.timeout.connect(self._scroll_welcome_text)
        self.marquee_timer.start()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(600, 38)

        self.setStyleSheet("""
            IguanaWindow {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_style = """
            QPushButton {
                background: transparent; 
                border: none; 
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(132, 204, 22, 0.2);
            }
        """

        self.cover_widget = CoverArtWidget(self)
        layout.addWidget(self.cover_widget)

        self.btn_eject = QPushButton()
        self.btn_eject.setIcon(create_svg_icon("eject", color="#84cc16", size=15))
        self.btn_eject.setFixedSize(22, 22)
        self.btn_eject.setToolTip("Cargar música")
        self.btn_eject.setStyleSheet(btn_style)
        self.btn_eject.clicked.connect(self.show_load_menu)
        layout.addWidget(self.btn_eject)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(create_svg_icon("prev", color="#84cc16", size=15))
        self.btn_prev.setFixedSize(22, 22)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(self.play_prev_track)
        layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton()
        self.btn_play.setIcon(create_svg_icon("play", color="#84cc16", size=15))
        self.btn_play.setFixedSize(22, 22)
        self.btn_play.setStyleSheet(btn_style)
        self.btn_play.clicked.connect(self.toggle_play)
        layout.addWidget(self.btn_play)

        self.btn_next = QPushButton()
        self.btn_next.setIcon(create_svg_icon("next", color="#84cc16", size=15))
        self.btn_next.setFixedSize(22, 22)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(self.play_next_track)
        layout.addWidget(self.btn_next)

        self.lbl_info = TrackInfoLabel(self)
        self.lbl_info.setStyleSheet("color: #f3f4f6; font-size: 11px; font-weight: bold;")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_info.setMaximumWidth(280)
        layout.addWidget(self.lbl_info, 1)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: #84cc16; font-size: 10px; font-weight: bold;")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.lbl_time)

        self.vol_container = QWidget()
        self.vol_container.setStyleSheet("background: transparent;")
        vol_layout = QHBoxLayout(self.vol_container)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.setSpacing(2)
        vol_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_vol = QLabel()
        self.lbl_vol.setPixmap(create_svg_icon("volume", color="#84cc16", size=11).pixmap(11, 11))
        self.lbl_vol.setFixedWidth(11)
        self.lbl_vol.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.vol_slider = JumpSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.setFixedWidth(22)
        self.vol_slider.valueChanged.connect(self.change_volume)

        vol_layout.addWidget(self.lbl_vol)
        vol_layout.addWidget(self.vol_slider)
        vol_container_width = 35
        self.vol_container.setFixedWidth(vol_container_width)
        layout.addWidget(self.vol_container)

        self.btn_help = QPushButton()
        self.btn_help.setIcon(create_svg_icon("help", color="#84cc16", size=13))
        self.btn_help.setFixedSize(22, 22)
        self.btn_help.setToolTip("Atajos de teclado y Acerca de")
        self.btn_help.setStyleSheet(btn_style)
        self.btn_help.clicked.connect(self.show_help_dialog)
        layout.addWidget(self.btn_help)

        self.btn_close = QPushButton()
        self.btn_close.setIcon(create_svg_icon("close", color="#84cc16", size=13))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setToolTip("Cerrar")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent; 
                border: none; 
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
            }
        """)
        self.btn_close.clicked.connect(QApplication.instance().quit)
        layout.addWidget(self.btn_close)

        self.player.set_volume(0.7)

    def show_load_menu(self):
        """Despliega el menú con las dos opciones de carga."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { 
                background-color: #080a0f; 
                color: #f3f4f6; 
                border: 1px solid #84cc16; 
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QMenu::item:selected { background-color: rgba(132, 204, 22, 0.2); color: #84cc16; }
        """)

        file_action = QAction("Subir música (Archivos)", self)
        file_action.triggered.connect(self.add_tracks)
        menu.addAction(file_action)

        folder_action = QAction("Subir carpeta", self)
        folder_action.triggered.connect(self.add_folder)
        menu.addAction(folder_action)

        button_pos = self.btn_eject.mapToGlobal(QPoint(0, self.btn_eject.height()))
        menu.exec(button_pos)

    def add_tracks(self):
        """Añade archivos individuales seleccionados."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Cargar Música", "", "Audio (*.mp3 *.wav *.ogg *.flac *.m4a)"
        )
        if files:
            self._append_audio_files(files)

    def add_folder(self):
        """Escanea una carpeta y añade todos los archivos de audio compatibles."""
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con música")
        if folder:
            extensions = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}
            folder_path = Path(folder)
            found_files = [
                str(p) for p in folder_path.rglob("*") 
                if p.is_file() and p.suffix.lower() in extensions
            ]
            found_files.sort()
            if found_files:
                self._append_audio_files(found_files)

    def _append_audio_files(self, file_paths):
        """Procesa y agrega la lista de rutas a la playlist."""
        initial_empty = len(self.playlist) == 0
        for f in file_paths:
            self.playlist.append(f)
            self.tracks_metadata.append(get_track_info(f))
        
        if initial_empty:
            self.current_index = 0
            pixmap = extract_cover_art(file_paths[0])
            self.cover_widget.set_cover(pixmap)

    def _scroll_welcome_text(self):
        self.welcome_text = self.welcome_text[-1] + self.welcome_text[:-1]
        self.lbl_info.setText(self.welcome_text)

    def _stop_welcome_marquee(self):
        self._was_marquee_active = False
        if self.marquee_timer.isActive():
            self.marquee_timer.stop()

    def show_help_dialog(self):
        dialog = HelpAboutDialog(self)
        dialog.exec()

    def toggle_drag_mode(self):
        self.drag_mode_enabled = not self.drag_mode_enabled
        if self.marquee_timer.isActive():
            self._was_marquee_active = True
            self.marquee_timer.stop()

        if self.drag_mode_enabled:
            self.lbl_info.setText(" Modo Arrastre Activado ")
        else:
            self.lbl_info.setText(" Modo Arrastre Desactivado ")

        self.vol_timer.stop()
        self.vol_timer.start(2000)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width() - 2
        h = self.height() - 2

        painter.setBrush(QBrush(QColor("#080a0f")))
        painter.setPen(QPen(QColor("#1f2937"), 1))
        painter.drawRoundedRect(QRectF(1, 1, w, h), 4, 4)

        if self.progress > 0:
            perimeter = 2 * (w + h)
            drawn_length = perimeter * self.progress

            pen_fg = QPen(QColor("#84cc16"), 1.5)
            painter.setPen(pen_fg)

            top_len = min(drawn_length, w)
            if top_len > 0:
                painter.drawLine(QLineF(1, 1, 1 + top_len, 1))
            
            if drawn_length > w:
                right_len = min(drawn_length - w, h)
                painter.drawLine(QLineF(1 + w, 1, 1 + w, 1 + right_len))

            if drawn_length > (w + h):
                bottom_len = min(drawn_length - (w + h), w)
                painter.drawLine(QLineF(1 + w, 1 + h, 1 + w - bottom_len, 1 + h))

            if drawn_length > (2 * w + h):
                left_len = min(drawn_length - (2 * w + h), h)
                painter.drawLine(QLineF(1, 1 + h, 1, 1 + h - left_len))

    def wheelEvent(self, event):
        """Ignora el evento de la rueda a nivel de ventana para evitar interferencias."""
        event.ignore()

    def handle_track_scroll(self, event):
        """Navega entre canciones al hacer scroll sobre TrackInfoLabel con un retardo de 3s antes de reproducir."""
        if not self.playlist:
            return

        delta = event.angleDelta().y()
        if delta == 0:
            return

        step = -1 if delta > 0 else 1
        new_index = max(0, min(self.current_index + step, len(self.playlist) - 1))

        if new_index != self.current_index:
            self._stop_welcome_marquee()
            self.current_index = new_index
            self.metadata_view_mode = 0
            
            self.update_metadata_display()
            pixmap = extract_cover_art(self.playlist[self.current_index])
            self.cover_widget.set_cover(pixmap)

            # Reinicia el temporizador de 3 segundos para posponer la reproducción
            self.scroll_debounce_timer.stop()
            self.scroll_debounce_timer.start(3000)

    def _on_scroll_debounce_timeout(self):
        """Se ejecuta cuando finalizan los 3 segundos de inactividad tras el scroll."""
        if self.player.is_playing() and self.current_index >= 0:
            self.play_track_by_index(self.current_index)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_mode_enabled:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu_style = """
            QMenu { 
                background-color: #080a0f; 
                color: #f3f4f6; 
                border: 1px solid #84cc16; 
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QMenu::item:selected { background-color: rgba(132, 204, 22, 0.2); color: #84cc16; }
            QMenu::item:disabled { color: #4b5563; }
            QMenu::item:checked { color: #84cc16; font-weight: bold; }
        """
        menu.setStyleSheet(menu_style)
        
        # Submenú Cargar Música
        load_sub = menu.addMenu("Cargar música")
        load_sub.setStyleSheet(menu_style)
        
        file_action = QAction("Archivos de audio...", self)
        file_action.triggered.connect(self.add_tracks)
        load_sub.addAction(file_action)

        folder_action = QAction("Carpeta de audio...", self)
        folder_action.triggered.connect(self.add_folder)
        load_sub.addAction(folder_action)

        # Opción Modo Arrastre
        drag_action = QAction("Modo Arrastre (Mover ventana)", self)
        drag_action.setCheckable(True)
        drag_action.setChecked(self.drag_mode_enabled)
        drag_action.triggered.connect(self.toggle_drag_mode)
        menu.addAction(drag_action)

        # Submenú Salidas de Audio
        devices_menu = menu.addMenu("Salida de audio")
        devices_menu.setStyleSheet(menu_style)

        devices = self.player.get_audio_devices()
        current_dev_id = self.player.get_current_device_id()

        for dev in devices:
            action_name = dev.description()
            dev_action = QAction(action_name, self)
            dev_action.setCheckable(True)
            if dev.id() == current_dev_id:
                dev_action.setChecked(True)

            dev_action.triggered.connect(lambda chk, d=dev: self._change_audio_device(d))
            devices_menu.addAction(dev_action)

        # Submenú con Scroll para la Lista de reproducción
        if self.playlist:
            menu.addSeparator()
            playlist_menu = menu.addMenu(f"Lista de reproducción ({len(self.playlist)})")
            playlist_menu.setStyleSheet(menu_style)

            # Crear widget con QListWidget embebido para permitir Scroll
            list_widget = QListWidget()
            list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #080a0f;
                    color: #f3f4f6;
                    border: none;
                    outline: 0;
                    font-size: 11px;
                }
                QListWidget::item {
                    padding: 5px 8px;
                    border-radius: 2px;
                }
                QListWidget::item:hover {
                    background-color: rgba(132, 204, 22, 0.2);
                    color: #84cc16;
                }
                QListWidget::item:selected {
                    background-color: rgba(132, 204, 22, 0.3);
                    color: #84cc16;
                    font-weight: bold;
                }
                QScrollBar:vertical {
                    background: #080a0f;
                    width: 6px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #84cc16;
                    min-height: 15px;
                    border-radius: 3px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)

            # Llenar la lista con las canciones
            for idx, meta in enumerate(self.tracks_metadata):
                prefix = "▶ " if idx == self.current_index else "   "
                item_text = f"{prefix}{idx + 1}. {meta['title']} - {meta['artist']}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, idx)
                list_widget.addItem(item)
                if idx == self.current_index:
                    item.setSelected(True)

            # Dimensiones ajustadas: ancho mayor (420px) y alto de 10 elementos
            visible_count = min(10, len(self.playlist))
            row_height = 26
            list_widget.setFixedHeight(visible_count * row_height + 4)
            list_widget.setFixedWidth(420)

            # Posicionar el scroll automáticamente en la canción actual
            if self.current_index >= 0:
                list_widget.scrollToItem(list_widget.item(self.current_index), QListWidget.ScrollHint.PositionAtCenter)

            # Conectar click de elementos
            def on_item_clicked(item):
                self.scroll_debounce_timer.stop()
                idx = item.data(Qt.ItemDataRole.UserRole)
                self.play_track_by_index(idx)
                menu.close()

            list_widget.itemClicked.connect(on_item_clicked)

            # Incrustar la QListWidget en el menú mediante QWidgetAction
            widget_action = QWidgetAction(playlist_menu)
            widget_action.setDefaultWidget(list_widget)
            playlist_menu.addAction(widget_action)

        menu.exec(pos)

    def _change_audio_device(self, device):
        self.player.set_audio_device(device)
        if self.marquee_timer.isActive():
            self._was_marquee_active = True
            self.marquee_timer.stop()
            
        self.lbl_info.setText(f" Audio: {device.description()[:30]} ")
        self.vol_timer.stop()
        self.vol_timer.start(2000)

    def cycle_metadata_view(self):
        if not self.playlist:
            return
        self.vol_timer.stop()
        if self.marquee_timer.isActive():
            self._stop_welcome_marquee()
            self.current_index = 0
            self.metadata_view_mode = 0
            self.update_metadata_display()
            return

        if self.current_index < 0:
            self.current_index = 0

        self.metadata_view_mode = (self.metadata_view_mode + 1) % 5
        self.update_metadata_display()

    def update_metadata_display(self):
        if not self.playlist or self.current_index < 0:
            return
        meta = self.tracks_metadata[self.current_index]
        idx_str = f"[{self.current_index + 1}/{len(self.playlist)}]"

        if self.metadata_view_mode == 0:
            text = f"{idx_str} {meta['title']} - {meta['artist']}"
        elif self.metadata_view_mode == 1:
            text = f"{idx_str} Fecha: {meta['date']}"
        elif self.metadata_view_mode == 2:
            text = f"{idx_str} Álbum: {meta['album']}"
        elif self.metadata_view_mode == 3:
            text = f"{idx_str} Pista: {meta['track']}"
        elif self.metadata_view_mode == 4:
            text = f"{idx_str} Género: {meta['genre']}"

        self.lbl_info.setText(text)

    def change_volume(self, val):
        vol = val / 100.0
        self.player.set_volume(vol)

        if self.marquee_timer.isActive():
            self._was_marquee_active = True
            self.marquee_timer.stop()

        self.lbl_info.setText(f"Volumen: {val}%")

        self.vol_timer.stop()
        self.vol_timer.start(1500)

    def restore_info_after_volume(self):
        if self._was_marquee_active and (not self.playlist or self.current_index < 0):
            self.marquee_timer.start()
        else:
            self.update_metadata_display()

    def play_track_by_index(self, index):
        if not self.playlist or index < 0 or index >= len(self.playlist):
            return

        self.scroll_debounce_timer.stop()
        self.vol_timer.stop()
        self._stop_welcome_marquee()
        self.current_index = index
        self.metadata_view_mode = 0
        track_path = self.playlist[index]
        
        pixmap = extract_cover_art(track_path)
        self.cover_widget.set_cover(pixmap)

        self.track_duration = get_track_duration(track_path)
        self.progress = 0.0

        self.player.load_track(track_path)
        self.player.play()

        self.btn_play.setIcon(create_svg_icon("pause", color="#84cc16", size=15))
        self.update_metadata_display()
        self.timer.start()

    def toggle_play(self):
        if not self.playlist:
            self.show_load_menu()
            return

        if self.current_index < 0:
            self.current_index = 0

        track_path = self.playlist[self.current_index]

        if self.player.is_playing() and self.player.current_track == track_path:
            self.player.pause()
            self.timer.stop()
            self.btn_play.setIcon(create_svg_icon("play", color="#84cc16", size=15))
        elif self.player.is_paused and self.player.current_track == track_path:
            self.player.play()
            self.timer.start()
            self.btn_play.setIcon(create_svg_icon("pause", color="#84cc16", size=15))
        else:
            self.play_track_by_index(self.current_index)

    def play_next_track(self):
        if not self.playlist:
            return
        next_idx = (self.current_index + 1) % len(self.playlist)
        self.play_track_by_index(next_idx)

    def play_prev_track(self):
        if not self.playlist:
            return
        prev_idx = (self.current_index - 1) if self.current_index > 0 else len(self.playlist) - 1
        self.play_track_by_index(prev_idx)

    def handle_track_ended(self):
        self.play_next_track()

    def update_progress(self):
        elapsed = self.player.get_pos()
        if self.track_duration > 0:
            self.progress = min(1.0, elapsed / self.track_duration)
        else:
            self.progress = 0.0

        self.lbl_time.setText(f"{format_time(elapsed)} / {format_time(self.track_duration)}")
        self.update()