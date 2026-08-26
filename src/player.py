import os
import mutagen
from mutagen.id3 import ID3, USLT
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices, QAudioDevice


class MusicPlayer(QObject):
    track_ended = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_track = None
        self._target_volume = 0.7
        self.is_paused = False
        self._cached_lyrics = None
        self._custom_device_selected = False

        # Configurar salida y reproductor de audio
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        # Escuchar cambios en los dispositivos de audio del sistema (ej. conectar Bluetooth)
        self.media_devices = QMediaDevices(self)
        self.media_devices.audioOutputsChanged.connect(self._on_audio_outputs_changed)

        # Conectar evento de fin de reproducción
        self.player.mediaStatusChanged.connect(self._handle_status_changed)

        self.set_volume(self._target_volume)

    def get_audio_devices(self):
        """Devuelve la lista de dispositivos de salida de audio disponibles."""
        return QMediaDevices.audioOutputs()

    def set_audio_device(self, device: QAudioDevice):
        """Cambia manualmente el dispositivo de salida de audio activo."""
        if device and not device.isNull():
            self.audio_output.setDevice(device)
            self._custom_device_selected = True

    def set_default_audio_device(self):
        """Vuelve a sincronizar con el dispositivo predeterminado del sistema."""
        self._custom_device_selected = False
        self._sync_audio_device()

    def get_current_device_id(self):
        """Devuelve el ID único del dispositivo de audio en uso."""
        current_dev = self.audio_output.device()
        return current_dev.id() if not current_dev.isNull() else None

    def _sync_audio_device(self):
        """Asigna el dispositivo predeterminado solo si el usuario no seleccionó uno manualmente."""
        if not self._custom_device_selected:
            default_device = QMediaDevices.defaultAudioOutput()
            if self.audio_output.device() != default_device:
                self.audio_output.setDevice(default_device)

    def _on_audio_outputs_changed(self):
        """Maneja el evento cuando se conecta o desconecta un dispositivo."""
        self._sync_audio_device()

    def load_track(self, file_path):
        """Carga una pista de audio y reinicia el estado interno."""
        if not file_path or not os.path.exists(file_path):
            return

        self._sync_audio_device()

        abs_path = os.path.abspath(file_path)
        if self.current_track != abs_path:
            self._cached_lyrics = None

        self.current_track = abs_path
        self.player.setSource(QUrl.fromLocalFile(abs_path))
        self.is_paused = False

    def play(self):
        if self.current_track:
            self._sync_audio_device()
            self.player.play()
            self.is_paused = False

    def pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.is_paused = True

    def stop(self):
        self.player.stop()
        self.is_paused = False
        self.current_track = None
        self._cached_lyrics = None

    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def get_pos(self):
        return max(0.0, self.player.position() / 1000.0)

    def set_volume(self, volume):
        self._target_volume = max(0.0, min(1.0, volume))
        self.audio_output.setVolume(self._target_volume)

    def get_lyrics(self):
        if not self.current_track or not os.path.exists(self.current_track):
            return "No hay archivo seleccionado."

        if self._cached_lyrics is not None:
            return self._cached_lyrics

        lyrics_found = "No hay letras incrustadas disponibles para esta pista."

        if self.current_track.lower().endswith('.mp3'):
            try:
                audio_id3 = ID3(self.current_track)
                for tag in audio_id3.values():
                    if isinstance(tag, USLT):
                        lyrics_found = tag.text
                        self._cached_lyrics = lyrics_found
                        return lyrics_found
            except Exception:
                pass

        try:
            audio = mutagen.File(self.current_track)
            if audio is not None:
                for key in ['lyrics', 'unsyncedlyrics', 'LYRICS', 'UNSYNCEDLYRICS', '©lyr']:
                    if key in audio:
                        val = audio[key]
                        if isinstance(val, list) and len(val) > 0:
                            lyrics_found = str(val[0])
                        else:
                            lyrics_found = str(val)
                        break
        except Exception:
            pass

        self._cached_lyrics = lyrics_found
        return lyrics_found

    def _handle_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.is_paused = False
            self.track_ended.emit()