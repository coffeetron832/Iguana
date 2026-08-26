import os
import mutagen
from mutagen.id3 import APIC
from mutagen.flac import Picture
from PyQt6.QtGui import QImage, QPixmap

def extract_cover_art(file_path):
    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return None
            
        if hasattr(audio, 'tags') and audio.tags:
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    img = QImage()
                    img.loadFromData(tag.data)
                    return QPixmap.fromImage(img)
                    
        if hasattr(audio, 'pictures') and audio.pictures:
            for pic in audio.pictures:
                if isinstance(pic, Picture):
                    img = QImage()
                    img.loadFromData(pic.data)
                    return QPixmap.fromImage(img)
    except Exception:
        pass
    return None

def get_track_info(file_path):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    info = {
        "title": base_name,
        "artist": "Desconocido",
        "album": "Desconocido",
        "date": "Desconocida",
        "track": "Desconocido",
        "genre": "Desconocido"
    }
    try:
        audio = mutagen.File(file_path, easy=True)
        if audio:
            if 'title' in audio and audio['title']:
                info["title"] = audio['title'][0]
            if 'artist' in audio and audio['artist']:
                info["artist"] = audio['artist'][0]
            if 'album' in audio and audio['album']:
                info["album"] = audio['album'][0]
            if 'date' in audio and audio['date']:
                info["date"] = audio['date'][0]
            elif 'year' in audio and audio['year']:
                info["date"] = str(audio['year'][0])
            if 'tracknumber' in audio and audio['tracknumber']:
                info["track"] = str(audio['tracknumber'][0])
            elif 'track' in audio and audio['track']:
                info["track"] = str(audio['track'][0])
            if 'genre' in audio and audio['genre']:
                genres = audio['genre']
                if isinstance(genres, list):
                    info["genre"] = ", ".join(str(g) for g in genres)
                else:
                    info["genre"] = str(genres)
    except Exception:
        pass
    return info

def get_track_duration(file_path):
    try:
        audio = mutagen.File(file_path)
        if audio and hasattr(audio, 'info') and hasattr(audio.info, 'length'):
            return max(1.0, float(audio.info.length))
    except Exception:
        pass
    return 180.0

def format_time(seconds):
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02d}:{secs:02d}"