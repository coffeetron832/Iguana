from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QPainter, QPixmap, QIcon
from PyQt6.QtSvg import QSvgRenderer

SVG_ICONS = {
    "play": '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3" fill="{color}"/></svg>',
    "pause": '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2"><rect x="6" y="4" width="4" height="16" fill="{color}"/><rect x="14" y="4" width="4" height="16" fill="{color}"/></svg>',
    "prev": '<svg viewBox="0 0 24 24" fill="{color}"><polygon points="11,6 2,12 11,18"/><polygon points="22,6 13,12 22,18"/></svg>',
    "next": '<svg viewBox="0 0 24 24" fill="{color}"><polygon points="13,6 22,12 13,18"/><polygon points="2,6 11,12 2,18"/></svg>',
    "eject": '<svg viewBox="0 0 24 24" fill="{color}"><polygon points="12,5 5,15 19,15"/><rect x="5" y="17" width="14" height="2"/></svg>',
    "volume": '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"><path d="M11 5L6 9H2v6h4l5 4V5z" fill="{color}"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
    "help": '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "close": '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
}

def create_svg_icon(symbol_type, color="#84cc16", size=16):
    svg_str = SVG_ICONS.get(symbol_type, "").format(color=color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)