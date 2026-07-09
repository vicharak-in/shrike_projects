import csv
import sys
import time
import traceback
import webbrowser
import base64
from datetime import datetime

from PyQt6.QtCore    import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                             QSize, QPoint, QRect)
from PyQt6.QtGui     import (QColor, QFont, QCursor, QPainter, QIcon,
                             QPixmap)
from PyQt6.QtSvg     import QSvgRenderer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QStatusBar, QCheckBox, QSizePolicy, QFileDialog, 
    QMessageBox, QApplication, QMenu, QGraphicsDropShadowEffect, QLineEdit,
)

try:
    import numpy as np
    import matplotlib, logging as _log
    matplotlib.use("QtAgg")
    _log.getLogger("matplotlib.font_manager").setLevel(_log.ERROR)
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavToolbar
    from matplotlib.figure import Figure
    import matplotlib.ticker as mticker
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

def _excepthook(et, ev, tb):
    print("=" * 60, file=sys.stderr)
    traceback.print_exception(et, ev, tb)
sys.excepthook = _excepthook

try:
    from port_scanner   import get_available_ports
    from serial_manager import SerialManager
    from packet_parser  import PacketParser
except ImportError as e:
    print(f"[IMPORT FALLBACK] {e}", file=sys.stderr)
    def get_available_ports(): return ["COM1", "COM3"]
    class SerialManager:
        def is_connected(self):   return False
        def connect(self, *a):    return False
        def disconnect(self):     pass
        def read_available(self): return []
    class PacketParser:
        def parse_line(self, l):  return []


# ══════════════════════════════════════════════════════════════
#  DYNAMIC PALETTE (BLACK MODE)
# ══════════════════════════════════════════════════════════════
THEME = {}
def set_theme(light=False):
    global THEME
    THEME.update({
        "MODE_NAME": "BLACK",
        "C_BG": "#000000", "C_SURFACE": "#0A0A0A", "C_SURFACE2": "#121212",
        "C_SURFACE3": "#1A1A1A", "C_BORDER": "#2A2A2A", "C_BORDER2": "#3A3A3A",
        "C_AMBER": "#FFB800", "C_BLUE": "#EAEAEA", "C_GREEN": "#00FF66",
        "C_RED": "#FF3333", "C_PURPLE": "#C77DFF", "C_SLATE": "#888888",
        "C_DIM": "#666666", "C_TEXT": "#FFFFFF", "C_WHITE": "#FFFFFF",
        "C_HDR": "#050505", "C_TEAL": "#00F0FF",
        "BADGE_BG_I2C": "#1A1A1A", "BADGE_BG_UART": "#0A1F0A",
        "BADGE_BG_SPI": "#1F0A1F", "BADGE_BG_PWM": "#1F1A0A",
        "BADGE_BG_ASCII": "#0A1F1F", "BADGE_BG_UNKNOWN": "#1F0A0A",
        "ARROW_COLOR": "FFFFFF", "BTN_HOVER_BG": "rgba(255, 255, 255, 0.08)"
    })
set_theme(False) # Init Dark Mode

def get_badge_bg(proto):
    cleaned = "I2C" if "I2C" in proto else proto
    return THEME.get(f"BADGE_BG_{cleaned}", THEME["BADGE_BG_UNKNOWN"])
def get_badge_fg(proto):
    cleaned = "I2C" if "I2C" in proto else proto
    m = {"I2C":THEME["C_BLUE"], "UART":THEME["C_GREEN"], "SPI":THEME["C_PURPLE"], "PWM":THEME["C_AMBER"], "ASCII":THEME["C_TEAL"]}
    return m.get(cleaned, THEME["C_RED"])
def get_event_fg(ev):
    m = {"START":THEME["C_GREEN"], "STOP":THEME["C_RED"], "ADDR":THEME["C_BLUE"], "DATA":THEME["C_AMBER"],
         "ACK":THEME["C_GREEN"], "NAK":THEME["C_RED"], "CHAR":THEME["C_SLATE"], "MESSAGE":THEME["C_AMBER"],
         "BYTES":THEME["C_SLATE"], "MOSI":THEME["C_AMBER"], "MISO":THEME["C_TEAL"]}
    return m.get(ev, THEME["C_DIM"])


# ══════════════════════════════════════════════════════════════
#  SVG ICON TEMPLATES
# ══════════════════════════════════════════════════════════════
_T_GITHUB = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{c}"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>'
_T_LINKEDIN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{c}"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>'
_T_GMAIL = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{c}"><path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.908 1.528-1.147C21.69 2.28 24 3.434 24 5.457z"/></svg>'
_T_WEB = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>'

_ICON_DIM_COLOR = "#4E6070"
_ICON_HOV_COLORS = {"github": ("#000000", None), "linkedin": ("#0A66C2", None), "gmail": ("#EA4335", None), "website": ("#20C8B0", None)}
_ICON_TEMPLATES = {"github": _T_GITHUB, "linkedin": _T_LINKEDIN, "gmail": _T_GMAIL, "website": _T_WEB}

def _svg_pixmap(svg_str: str, size: int) -> QPixmap:
    renderer = QSvgRenderer(svg_str.encode())
    px = QPixmap(size, size); px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p); p.end()
    return px

class IconLinkButton(QPushButton):
    def __init__(self, key: str, url: str, size: int = 40, parent=None):
        super().__init__(parent)
        self.setObjectName("icon_btn")
        self.setFixedSize(size, size)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.key = key; self._isz = size - 8; self.url = url
        self.clicked.connect(lambda: webbrowser.open(self.url))
        self._update_colors()

    def _update_colors(self):
        tmpl = _ICON_TEMPLATES[self.key]
        self._dim_svg = tmpl.format(c=THEME["C_SLATE"])
        hc, _ = _ICON_HOV_COLORS[self.key]
        self._hov_svg = tmpl.format(c=hc if THEME["C_BG"]=="#F0F4F8" and hc=="#000000" else THEME["C_TEXT"] if hc=="#000000" else hc)
        self._set(False)

    def _set(self, hov: bool):
        px = _svg_pixmap(self._hov_svg if hov else self._dim_svg, self._isz)
        self.setIcon(QIcon(px)); self.setIconSize(px.size())

    def enterEvent(self, e): super().enterEvent(e); self._set(True)
    def leaveEvent(self, e): super().leaveEvent(e); self._set(False)


# ══════════════════════════════════════════════════════════════
#  SCROLLING FOOTER TICKER
# ══════════════════════════════════════════════════════════════
class ScrollingTicker(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # We use two labels to create an infinite seamless scroll
        self.label1 = QLabel(self)
        self.label1.setOpenExternalLinks(True)
        self.label1.setWordWrap(False)
        self.label1.setStyleSheet("background: transparent; border: none;")
        
        self.label2 = QLabel(self)
        self.label2.setOpenExternalLinks(True)
        self.label2.setWordWrap(False)
        self.label2.setStyleSheet("background: transparent; border: none;")

        self.x1 = 0.0
        self.x2 = 0.0
        self.gap = 50  # Gap between the two labels
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scroll_text)
        self.timer.start(30) # ~33 fps
        self.is_hovered = False

    def enterEvent(self, event):
        self.is_hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        super().leaveEvent(event)

    def update_html(self, html_content):
        self.label1.setText(html_content)
        self.label2.setText(html_content)
        self.label1.adjustSize()
        self.label2.adjustSize()
        self.x1 = 0.0
        self.x2 = float(self.label1.width() + self.gap)
        self.label1.move(int(self.x1), 0)
        self.label2.move(int(self.x2), 0)

    def scroll_text(self):
        if self.is_hovered: return # Pause so user can click links!

        self.x1 -= 1.0
        self.x2 -= 1.0

        w1 = self.label1.width()
        w2 = self.label2.width()

        # Wrap around
        if self.x1 < -(w1 + self.gap):
            self.x1 = self.x2 + w2 + self.gap
        if self.x2 < -(w2 + self.gap):
            self.x2 = self.x1 + w1 + self.gap

        # Offset slightly down for vertical centering in the widget
        self.label1.move(int(self.x1), 4)
        self.label2.move(int(self.x2), 4)


# ══════════════════════════════════════════════════════════════
#  PULSE DOT  (animated live indicator)
# ══════════════════════════════════════════════════════════════
class PulseDot(QLabel):
    def __init__(self, parent=None):
        super().__init__("●  OFFLINE", parent)
        self._pulse = QTimer(); self._pulse.setInterval(700)
        self._pulse.timeout.connect(self._toggle)
        self._state = False; self._online = False
        self._update_style()

    def set_online(self, v: bool):
        self._online = v
        if v: self._pulse.start()
        else: self._pulse.stop()
        self._state = True
        self._update_style()

    def _toggle(self):
        self._state = not self._state; self._update_style()

    def _update_style(self):
        if self._online:
            alpha = "FF" if self._state else "88"
            self.setText("●  LIVE")
            self.setStyleSheet(f"color:#{alpha}E878;font-size:11px;font-weight:800;letter-spacing:0.06em;")
        else:
            self.setText("●  OFFLINE")
            self.setStyleSheet(f"color:{THEME['C_RED']};font-size:11px;font-weight:800;letter-spacing:0.06em;")


# ══════════════════════════════════════════════════════════════
#  MATPLOTLIB WAVEFORM HELPERS
# ══════════════════════════════════════════════════════════════
def _apply_mpl_style():
    import matplotlib as mpl
    mpl.rcParams.update({
        "figure.facecolor": THEME["C_BG"],
        "axes.facecolor": THEME["C_HDR"],
        "axes.edgecolor": THEME["C_BORDER2"],
        "axes.labelcolor": THEME["C_SLATE"],
        "xtick.color": THEME["C_SLATE"], "ytick.color": THEME["C_SLATE"],
        "xtick.labelcolor": THEME["C_SLATE"], "ytick.labelcolor": THEME["C_SLATE"],
        "grid.color": THEME["C_BORDER"], "grid.linewidth": 0.5, "grid.alpha": 0.9,
        "lines.linewidth": 2.0,
        "font.family": ["Consolas", "DejaVu Sans Mono", "monospace"],
        "font.size": 9,
    })

I2C_US_PER_BIT  = 10.0
UART_US_PER_BIT = 104.17
SPI_US_PER_BIT  = 10.0

def _style_ax(ax, ylabel, color, show_xticks=False):
    ax.set_facecolor(THEME["C_HDR"])
    for sp in ax.spines.values(): sp.set_color(THEME["C_BORDER2"]); sp.set_linewidth(0.8)
    ax.tick_params(colors=THEME["C_SLATE"], labelsize=8, length=3, width=0.8, labelcolor=THEME["C_SLATE"])
    ax.set_ylabel(ylabel, color=color, fontsize=10, fontweight="bold", rotation=0, labelpad=44, va="center")
    ax.set_ylim(-0.4, 2.0)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["LOW", "HIGH"], color=THEME["C_SLATE"], fontsize=7.5)
    ax.grid(True, axis="x", color=THEME["C_BORDER"], lw=0.5, alpha=0.9)
    ax.grid(True, axis="y", color=THEME["C_BORDER"], lw=0.3, alpha=0.5)
    ax.axhline(0, color=THEME["C_BORDER2"], lw=0.7, zorder=0)
    ax.axhline(1, color=THEME["C_BORDER2"], lw=0.7, zorder=0)

def _gen_i2c(events):
    T, SCL, SDA = [], [], []; t = [0.0]
    def push(dt, sv, dv):
        T.extend([t[0], t[0]+dt]); SCL.extend([sv, sv]); SDA.extend([dv, dv]); t[0]+=dt
    def bit(d): push(.25,0,d); push(.5,1,d); push(.25,0,d)
    def byte_send(v):
        for i in range(7,-1,-1): bit((v>>i)&1)
        bit(0)
    push(1,1,1); push(.5,1,1); push(.3,1,0); push(.2,0,0)
    for ev in events:
        e,d = ev.get("event",""), ev.get("details","")
        if e in ("START","SEPARATOR"): continue
        elif e=="ADDR":
            p=d.split()
            try: byte_send((int(p[0],16)<<1)|(0 if len(p)>1 and "W" in p[1].upper() else 1))
            except: byte_send(0)
        elif e=="DATA":
            p=d.split()
            try: byte_send(int(p[0],16))
            except: byte_send(0)
        elif e=="STOP":
            push(.2,0,0); push(.3,1,0); push(.3,1,1); push(.7,1,1)
    push(1,1,1)
    return np.array(T), np.array(SCL), np.array(SDA)

def _gen_uart(message):
    T, SIG = [], []; t = [0.0]
    def push(dt,v): T.extend([t[0],t[0]+dt]); SIG.extend([v,v]); t[0]+=dt
    push(2,1)
    for ch in message:
        b=ord(ch)&0xFF; push(1,0)
        for i in range(8): push(1,(b>>i)&1)
        push(1,1); push(1,1)
    push(2,1)
    return np.array(T), np.array(SIG)

def _gen_spi(events):
    T, SCLK, MOSI, MISO, CS = [], [], [], [], []; t = [0.0]
    def push(dt, sclk_val, mosi_val, miso_val, cs_val):
        T.extend([t[0], t[0]+dt])
        SCLK.extend([sclk_val, sclk_val])
        MOSI.extend([mosi_val, mosi_val])
        MISO.extend([miso_val, miso_val])
        CS.extend([cs_val, cs_val])
        t[0]+=dt

    def bit(mosi_b, miso_b):
        push(0.5, 1, mosi_b, miso_b, 0)
        push(0.5, 0, mosi_b, miso_b, 0)

    def byte_send(mosi_byte, miso_byte):
        for i in range(7, -1, -1):
            bit((mosi_byte >> i) & 1, (miso_byte >> i) & 1)

    push(1.0, 0, 0, 0, 1)
    push(0.5, 0, 0, 0, 0)

    mosi_bytes = []
    miso_bytes = []
    has_new_format = False

    for ev in events:
        e, d = ev.get("event",""), ev.get("details","")
        if e == "MOSI":
            for x in d.split():
                try:
                    mosi_bytes.append(int(x, 16))
                    has_new_format = True
                except ValueError: pass
        elif e == "MISO":
            for x in d.split():
                try:
                    miso_bytes.append(int(x, 16))
                    has_new_format = True
                except ValueError: pass

    if has_new_format:
        length = max(len(mosi_bytes), len(miso_bytes))
        mosi_bytes += [0] * (length - len(mosi_bytes))
        miso_bytes += [0] * (length - len(miso_bytes))
        for mosi_b, miso_b in zip(mosi_bytes, miso_bytes):
            byte_send(mosi_b, miso_b)
            push(0.5, 0, 0, 0, 0)
    else:
        for ev in events:
            e, d = ev.get("event",""), ev.get("details","")
            if e in ("START", "SEPARATOR", "STOP"): continue
            elif e == "DATA":
                mosi_val, miso_val = 0, 0
                parts = d.split()
                for p in parts:
                    if p.startswith("MOSI="):
                        try: mosi_val = int(p.split("=")[1], 16)
                        except: pass
                    elif p.startswith("MISO="):
                        try: miso_val = int(p.split("=")[1], 16)
                        except: pass
                byte_send(mosi_val, miso_val)
                push(0.5, 0, 0, 0, 0)

    push(0.5, 0, 0, 0, 1)
    push(1.0, 0, 0, 0, 1)
    return np.array(T), np.array(SCLK), np.array(MOSI), np.array(MISO), np.array(CS)


# ══════════════════════════════════════════════════════════════
#  WAVEFORM CANVAS
# ══════════════════════════════════════════════════════════════
class WaveformCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        self._zoom_level = 1.0   
        self._cur_xlim   = None  
        self._cur_tx     = None
        self._cur_proto  = None

        if not HAS_MPL:
            lbl = QLabel("⚠  Install matplotlib+numpy:\n\npip install matplotlib numpy")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{THEME['C_AMBER']};font-size:13px;")
            outer.addWidget(lbl); return

        _apply_mpl_style()
        self._fig = Figure(facecolor=THEME["C_BG"])
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        top_row = QHBoxLayout(); top_row.setContentsMargins(0,0,0,0); top_row.setSpacing(0)
        self._nav = NavToolbar(self._canvas, self)
        self._nav.setObjectName("nav_toolbar")
        self._nav.setIconSize(QSize(20, 20))
        top_row.addWidget(self._nav)
        top_row.addStretch()

        self.zoom_btns = []
        for sym, tip, slot in [("+","Zoom In",self._zoom_in),("-","Zoom Out",self._zoom_out),("⟳","Reset Zoom",self._zoom_reset)]:
            btn = QPushButton(sym); btn.setToolTip(tip); btn.setFixedSize(32, 28); btn.setObjectName("zoom_btn")
            btn.clicked.connect(slot); top_row.addWidget(btn)
            self.zoom_btns.append(btn)
        top_row.addSpacing(6)

        self.toolbar_widget = QWidget()
        self.toolbar_widget.setLayout(top_row)
        self.toolbar_widget.setFixedHeight(32)

        self._cursor_lbl = QLabel("  Move cursor over waveform to read time and logic level.")
        self._cursor_lbl.setObjectName("cursor_lbl")
        self._canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self._canvas.mpl_connect("scroll_event", self._on_scroll)

        outer.addWidget(self.toolbar_widget)
        outer.addWidget(self._canvas, stretch=1)
        outer.addWidget(self._cursor_lbl)
        self._idle()
        self.update_theme()

    def update_theme(self):
        if not HAS_MPL: return
        self.toolbar_widget.setStyleSheet(f"background:{THEME['C_SURFACE2']};border-bottom:1px solid {THEME['C_BORDER2']};")
        self._nav.setStyleSheet(f"background:{THEME['C_SURFACE2']};color:{THEME['C_SLATE']};padding:1px 4px;")
        self._cursor_lbl.setStyleSheet(f"color:{THEME['C_TEXT']};font-family:Consolas,monospace;font-size:12px;font-weight:bold;background:{THEME['C_SURFACE2']};padding:6px 12px;border-top:1px solid {THEME['C_BORDER']};")
        for btn in self.zoom_btns:
            btn.setStyleSheet(f"background:{THEME['C_SURFACE3']};color:{THEME['C_AMBER']};border:1px solid {THEME['C_BORDER2']};border-radius:3px;font-size:18px;font-weight:900;padding:0;")
        
        _apply_mpl_style()
        if self._cur_proto == "I2C": self.show_i2c(self._cur_tx)
        elif self._cur_proto == "UART": self.show_uart(self._cur_tx)
        elif self._cur_proto == "SPI": self.show_spi(self._cur_tx)
        else: self._idle()

    def _on_mouse_move(self, event):
        if not HAS_MPL: return
        if event.inaxes and event.xdata is not None:
            logic = "HIGH" if (event.ydata or 0) > 0.5 else "LOW"
            us = event.xdata * self._us_per_bit
            self._cursor_lbl.setText(f"  t = {us:.2f} µs  ({event.xdata:.3f} bit-periods)    Logic = {logic}")
        else:
            self._cursor_lbl.setText("  Move cursor over waveform to read time and logic level.")

    def _on_scroll(self, event):
        if not HAS_MPL or self._cur_xlim is None: return
        if event.button == "up": self._zoom_in()
        elif event.button == "down": self._zoom_out()

    def _zoom_in(self): self._zoom_level = min(self._zoom_level * 1.5, 32.0); self._apply_zoom()
    def _zoom_out(self): self._zoom_level = max(self._zoom_level / 1.5, 1.0); self._apply_zoom()
    def _zoom_reset(self): self._zoom_level = 1.0; self._apply_zoom()

    def _apply_zoom(self):
        if not HAS_MPL or self._cur_xlim is None: return
        full_min, full_max = self._cur_xlim
        span = (full_max - full_min) / self._zoom_level
        mid  = (full_min + full_max) / 2
        for ax in self._fig.axes:
            ax.set_xlim(mid - span/2, mid + span/2)
        self._canvas.draw_idle()

    def _idle(self):
        if not HAS_MPL: return
        self._us_per_bit = I2C_US_PER_BIT; self._cur_xlim = None; self._cur_proto = None
        self._fig.clear(); self._fig.patch.set_facecolor(THEME["C_BG"])
        ax = self._fig.add_subplot(111)
        ax.set_facecolor(THEME["C_BG"]); ax.set_axis_off()
        ax.text(0.5, 0.5, "Select a transaction row in the Stream tab\nto render its protocol waveform here.", transform=ax.transAxes, ha="center", va="center", fontsize=12, color=THEME["C_DIM"], fontfamily="Consolas")
        self._canvas.draw()

    def show_idle(self):
        if HAS_MPL: self._idle()

    def show_i2c(self, tx):
        if not HAS_MPL: return
        self._cur_tx = tx; self._cur_proto = "I2C"
        self._us_per_bit = I2C_US_PER_BIT; self._zoom_level = 1.0
        events = tx.get("events", [])
        t, scl, sda = _gen_i2c(events)
        t_us = t * I2C_US_PER_BIT
        self._cur_xlim = (float(t_us.min()), float(t_us.max()))

        self._fig.clear(); self._fig.patch.set_facecolor(THEME["C_BG"])
        gs = self._fig.add_gridspec(2, 1, hspace=0.08, left=0.12, right=0.97, top=0.88, bottom=0.07)
        ax1 = self._fig.add_subplot(gs[0]); ax2 = self._fig.add_subplot(gs[1])
        _style_ax(ax1, "SCL", THEME["C_BLUE"]); _style_ax(ax2, "SDA", THEME["C_AMBER"], show_xticks=True)

        ax1.step(t_us, scl, color=THEME["C_BLUE"],  linewidth=1.8, where="post")
        ax2.step(t_us, sda, color=THEME["C_AMBER"], linewidth=1.8, where="post")
        ax1.fill_between(t_us, 0, scl, step="post", alpha=0.07, color=THEME["C_BLUE"])
        ax2.fill_between(t_us, 0, sda, step="post", alpha=0.07, color=THEME["C_AMBER"])

        BIT_US = I2C_US_PER_BIT; BYTE_US = 9 * BIT_US
        tc_us = (1.0 + 0.5 + 0.3 + 0.2) * BIT_US
        ax1.axvline(tc_us, color=THEME["C_GREEN"], ls="--", lw=0.9, alpha=0.7)
        ax1.text(tc_us, 1.66, "START", color=THEME["C_GREEN"], fontsize=7, ha="center", fontfamily="Consolas")
        for ev in events:
            ek, ed = ev.get("event",""), ev.get("details","")
            if ek in ("START","SEPARATOR","STOP","ACK","NAK"): continue
            mid_us = tc_us + BYTE_US / 2
            col = THEME["C_BLUE"] if ek == "ADDR" else THEME["C_AMBER"]
            ax2.text(mid_us, 1.66, f"{ek}\n{ed.split()[0] if ed else ''}", color=col, fontsize=6.5, ha="center", va="bottom", fontfamily="Consolas")
            ax2.axvline(tc_us, color=THEME["C_BORDER2"], ls=":", lw=0.6, alpha=0.7)
            tc_us += BYTE_US

        ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f} µs"))
        ax2.set_xlabel("Time (µs)  —  I²C 100 kHz, 10 µs/bit", color=THEME["C_SLATE"], fontsize=8, fontfamily="Consolas")
        ax2.tick_params(axis="x", labelsize=8, rotation=30)
        self._fig.suptitle(f"I²C Transaction #{tx.get('tx_num',1)}  ·  SCL / SDA  ·  100 kHz", color=THEME["C_BLUE"], fontsize=11, fontweight="bold", y=0.96)
        self._canvas.draw()

    def show_spi(self, tx):
        if not HAS_MPL: return
        self._cur_tx = tx; self._cur_proto = "SPI"
        self._us_per_bit = SPI_US_PER_BIT; self._zoom_level = 1.0
        events = tx.get("events", [])
        t, sclk, mosi, miso, cs = _gen_spi(events)
        t_us = t * SPI_US_PER_BIT
        self._cur_xlim = (float(t_us.min()), float(t_us.max()))

        self._fig.clear(); self._fig.patch.set_facecolor(THEME["C_BG"])
        gs = self._fig.add_gridspec(4, 1, hspace=0.15, left=0.12, right=0.97, top=0.90, bottom=0.07)
        ax_cs   = self._fig.add_subplot(gs[0])
        ax_sclk = self._fig.add_subplot(gs[1])
        ax_mosi = self._fig.add_subplot(gs[2])
        ax_miso = self._fig.add_subplot(gs[3])

        _style_ax(ax_cs,   "CS",   THEME["C_RED"])
        _style_ax(ax_sclk, "SCLK", THEME["C_PURPLE"])
        _style_ax(ax_mosi, "MOSI", THEME["C_AMBER"])
        _style_ax(ax_miso, "MISO", THEME["C_TEAL"], show_xticks=True)

        ax_cs.step(t_us,   cs,   color=THEME["C_RED"],    linewidth=1.8, where="post")
        ax_sclk.step(t_us, sclk, color=THEME["C_PURPLE"], linewidth=1.8, where="post")
        ax_mosi.step(t_us, mosi, color=THEME["C_AMBER"],  linewidth=1.8, where="post")
        ax_miso.step(t_us, miso, color=THEME["C_TEAL"],   linewidth=1.8, where="post")

        ax_cs.fill_between(t_us,   0, cs,   step="post", alpha=0.07, color=THEME["C_RED"])
        ax_sclk.fill_between(t_us, 0, sclk, step="post", alpha=0.07, color=THEME["C_PURPLE"])
        ax_mosi.fill_between(t_us, 0, mosi, step="post", alpha=0.07, color=THEME["C_AMBER"])
        ax_miso.fill_between(t_us, 0, miso, step="post", alpha=0.07, color=THEME["C_TEAL"])

        BIT_US = SPI_US_PER_BIT; BYTE_US = 8 * BIT_US
        tc_us = 1.5 * BIT_US
        
        ax_cs.axvline(1.0 * BIT_US, color=THEME["C_RED"], ls="--", lw=0.9, alpha=0.7)
        ax_cs.text(1.0 * BIT_US, 1.66, "START", color=THEME["C_RED"], fontsize=7, ha="center", fontfamily="Consolas")
        
        mosi_bytes = []
        miso_bytes = []
        has_new_format = False
        for ev in events:
            ek, ed = ev.get("event",""), ev.get("details","")
            if ek == "MOSI":
                for x in ed.split():
                    try:
                        int(x, 16)
                        mosi_bytes.append(x)
                        has_new_format = True
                    except ValueError: pass
            elif ek == "MISO":
                for x in ed.split():
                    try:
                        int(x, 16)
                        miso_bytes.append(x)
                        has_new_format = True
                    except ValueError: pass

        if has_new_format:
            length = max(len(mosi_bytes), len(miso_bytes))
            while len(mosi_bytes) < length: mosi_bytes.append("00")
            while len(miso_bytes) < length: miso_bytes.append("00")
            for mosi_str, miso_str in zip(mosi_bytes, miso_bytes):
                mid_us = tc_us + BYTE_US / 2
                ax_mosi.text(mid_us, 1.66, mosi_str, color=THEME["C_AMBER"], fontsize=7, ha="center", va="bottom", fontfamily="Consolas")
                ax_miso.text(mid_us, 1.66, miso_str, color=THEME["C_TEAL"], fontsize=7, ha="center", va="bottom", fontfamily="Consolas")
                ax_mosi.axvline(tc_us, color=THEME["C_BORDER2"], ls=":", lw=0.6, alpha=0.7)
                ax_miso.axvline(tc_us, color=THEME["C_BORDER2"], ls=":", lw=0.6, alpha=0.7)
                tc_us += BYTE_US + 0.5 * BIT_US
        else:
            for ev in events:
                ek, ed = ev.get("event",""), ev.get("details","")
                if ek in ("START", "SEPARATOR", "STOP"): continue
                elif ek == "DATA":
                    mid_us = tc_us + BYTE_US / 2
                    
                    mosi_str, miso_str = "", ""
                    parts = ed.split()
                    for p in parts:
                        if p.startswith("MOSI="): mosi_str = p.split("=")[1]
                        elif p.startswith("MISO="): miso_str = p.split("=")[1]
                    
                    ax_mosi.text(mid_us, 1.66, mosi_str, color=THEME["C_AMBER"], fontsize=7, ha="center", va="bottom", fontfamily="Consolas")
                    ax_miso.text(mid_us, 1.66, miso_str, color=THEME["C_TEAL"], fontsize=7, ha="center", va="bottom", fontfamily="Consolas")
                    
                    ax_mosi.axvline(tc_us, color=THEME["C_BORDER2"], ls=":", lw=0.6, alpha=0.7)
                    ax_miso.axvline(tc_us, color=THEME["C_BORDER2"], ls=":", lw=0.6, alpha=0.7)
                    
                    tc_us += BYTE_US + 0.5 * BIT_US
        
        stop_us = tc_us - 0.5 * BIT_US + 0.5 * BIT_US
        ax_cs.axvline(stop_us, color=THEME["C_RED"], ls="--", lw=0.9, alpha=0.7)
        ax_cs.text(stop_us, 1.66, "STOP", color=THEME["C_RED"], fontsize=7, ha="center", fontfamily="Consolas")

        ax_miso.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f} µs"))
        ax_miso.set_xlabel("Time (µs)", color=THEME["C_SLATE"], fontsize=8, fontfamily="Consolas")
        ax_miso.tick_params(axis="x", labelsize=8, rotation=30)
        
        self._fig.suptitle(f"SPI Transaction #{tx.get('tx_num',1)}  ·  CS / SCLK / MOSI / MISO", color=THEME["C_PURPLE"], fontsize=11, fontweight="bold", y=0.97)
        self._canvas.draw()

    def show_uart(self, tx):
        if not HAS_MPL: return
        self._cur_tx = tx; self._cur_proto = "UART"
        self._us_per_bit = UART_US_PER_BIT; self._zoom_level = 1.0
        msg = tx.get("message","")
        t, sig = _gen_uart(msg)
        t_us = t * UART_US_PER_BIT
        self._cur_xlim = (float(t_us.min()), float(t_us.max()))

        self._fig.clear(); self._fig.patch.set_facecolor(THEME["C_BG"])
        ax = self._fig.add_subplot(111, position=[0.10, 0.14, 0.86, 0.68])
        _style_ax(ax, "TX", THEME["C_GREEN"], show_xticks=True)
        ax.step(t_us, sig, color=THEME["C_GREEN"], linewidth=1.8, where="post")
        ax.fill_between(t_us, 0, sig, step="post", alpha=0.06, color=THEME["C_GREEN"])

        FRAME_US = 11.0 * UART_US_PER_BIT; tc_us = 2.0 * UART_US_PER_BIT
        for ch in msg:
            mid_us = tc_us + FRAME_US / 2
            ax.text(mid_us, 1.66, repr(ch), color=THEME["C_AMBER"], fontsize=9, ha="center", va="bottom", fontweight="bold", fontfamily="Consolas")
            ax.axvline(tc_us, color=THEME["C_BORDER2"], ls=":", lw=0.7, alpha=0.6)
            tc_us += FRAME_US

        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f} µs"))
        ax.set_xlabel("Time (µs)  —  UART 9600 baud, 104 µs/bit  (8N1)", color=THEME["C_SLATE"], fontsize=8, fontfamily="Consolas")
        ax.tick_params(axis="x", labelsize=8, rotation=30)
        ax.text(0.01, 0.03, "Format: 8 data bits, No parity, 1 stop bit", transform=ax.transAxes, color=THEME["C_DIM"], fontsize=8, fontfamily="Consolas", va="bottom")
        self._fig.suptitle(f"UART Message #{tx.get('tx_num',1)}  ·  TX  ·  9600 baud  8N1", color=THEME["C_GREEN"], fontsize=11, fontweight="bold", y=0.97)
        self._canvas.draw()


# ══════════════════════════════════════════════════════════════
#  STAT CARD
# ══════════════════════════════════════════════════════════════
class StatCard(QFrame):
    def __init__(self, label, accent_key, parent=None):
        super().__init__(parent); self.setObjectName("stat_card")
        self._accent_key = accent_key
        v = QVBoxLayout(self); v.setContentsMargins(14, 5, 14, 5); v.setSpacing(2)
        self._lbl = QLabel(label.upper()); self._lbl.setObjectName("stat_label")
        self._val = QLabel("0"); self._val.setObjectName("stat_value")
        v.addWidget(self._lbl); v.addWidget(self._val)
        self.update_theme()
        
    def set_value(self, v): self._val.setText(str(v))
    def update_theme(self):
        self._val.setStyleSheet(f"color:{THEME[self._accent_key]};font-size:24px;font-weight:700;font-family:'Consolas','JetBrains Mono',monospace;")
        self.setStyleSheet(f"#stat_card {{ background: {THEME['C_SURFACE3']}; border: 1px solid {THEME['C_BORDER2']}; border-top: 2px solid {THEME[self._accent_key]}; border-radius: 5px; }}")


# ══════════════════════════════════════════════════════════════
#  EXPORT HELPERS
# ══════════════════════════════════════════════════════════════
def _export_csv(tbl: QTableWidget, path: str):
    cols = tbl.columnCount()
    headers = [tbl.horizontalHeaderItem(c).text() for c in range(cols)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in range(tbl.rowCount()):
            w.writerow([(tbl.item(row,c).text() if tbl.item(row,c) else "") for c in range(cols)])

def _export_pdf(tbl: QTableWidget, path: str):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Peripheral Analyzer Sniffer — Capture Export", styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}",styles["Normal"]))
    story.append(Spacer(1, 5*mm))
    cols = tbl.columnCount()
    headers = [tbl.horizontalHeaderItem(c).text() for c in range(cols)]
    data = [headers]
    for row in range(tbl.rowCount()):
        data.append([(tbl.item(row,c).text() if tbl.item(row,c) else "") for c in range(cols)])
    t = Table(data, colWidths=[28*mm,22*mm,22*mm,None], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.black),
        ("TEXTCOLOR",(0,0),(-1,0), colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),
        ("FONTNAME",(0,1),(-1,-1),"Courier"),("FONTSIZE",(0,1),(-1,-1),8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F0F0F0")]),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#888888")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("TEXTCOLOR",(0,1),(-1,-1),colors.black),
    ]))
    story.append(t)
    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=16*mm, bottomMargin=14*mm)
    doc.build(story)


# ══════════════════════════════════════════════════════════════
#  STYLESHEET GENERATOR
# ══════════════════════════════════════════════════════════════
def generate_qss(t):
    return f"""
    * {{ font-family:"Inter","Segoe UI",sans-serif; font-size:13px; color:{t['C_TEXT']}; }}
    QMainWindow, QWidget#root_widget {{ background:{t['C_BG']}; }}

    #toolbar {{
        background: {t['C_SURFACE']};
        border-bottom: 1px solid {t['C_BORDER']};
    }}

    QFrame#combo_box_frame {{
        background: {t['C_SURFACE3']};
        border: 1px solid {t['C_BORDER2']};
        border-radius: 4px;
    }}
    QFrame#combo_box_frame:hover {{ border-color: {t['C_BLUE']}; }}

    QComboBox {{
        border: none; background: transparent; color: {t['C_TEXT']}; padding: 4px 6px; font-weight: 600; font-size: 13px;
    }}
    QComboBox::drop-down {{ border: none; width: 24px; border-left: 1px solid {t['C_BORDER2']}; }}
    QComboBox::down-arrow {{
        image: url("data:image/svg+xml;utf8,<svg viewBox='0 0 24 24' fill='none' stroke='%23{t['ARROW_COLOR']}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' xmlns='http://www.w3.org/2000/svg'><polyline points='6 9 12 15 18 9'></polyline></svg>");
        width: 16px; height: 16px;
    }}
    QComboBox QAbstractItemView {{
        background: {t['C_SURFACE2']}; color: {t['C_TEXT']}; border: 1px solid {t['C_BORDER2']};
        selection-background-color: {t['BTN_HOVER_BG']}; selection-color: {t['C_TEXT']};
    }}

    QTabWidget::pane {{ border:none; background:{t['C_BG']}; }}
    QTabBar {{ background:{t['C_HDR']}; border-bottom:1px solid {t['C_BORDER2']}; }}
    QTabBar::tab {{
        background:transparent; color:{t['C_DIM']}; padding:10px 30px; font-size:11px; font-weight:700; letter-spacing:0.09em;
        border-bottom:2px solid transparent; margin-right:2px;
    }}
    QTabBar::tab:selected {{ color:{t['C_TEXT']}; border-bottom:2px solid {t['C_TEXT']}; background:{t['BTN_HOVER_BG']}; }}
    QTabBar::tab:hover:!selected {{ color:{t['C_TEXT']}; background:rgba(255,255,255,0.05); }}

    QPushButton {{
        background: {t['C_SURFACE3']}; color: {t['C_TEXT']}; border: 1px solid {t['C_BORDER2']}; border-radius: 4px;
        padding: 5px 14px; font-weight: 600; font-size: 13px;
    }}
    QPushButton:hover {{ border-color: {t['C_TEXT']}; background: {t['BTN_HOVER_BG']}; color: {t['C_TEXT']}; }}
    QPushButton:pressed {{ background: rgba(255,255,255,0.1); }}

    QPushButton#btn_connect {{ color: {t['C_GREEN']}; border: 1px solid {t['C_GREEN']}; background: transparent; }}
    QPushButton#btn_connect:hover {{ background: {t['C_GREEN']}; color: #000; }}
    QPushButton#btn_disconnect {{ color: {t['C_RED']}; border: 1px solid {t['C_RED']}; background: transparent; }}
    QPushButton#btn_disconnect:hover {{ background: {t['C_RED']}; color: #fff; }}

    QPushButton#btn_clear {{ color: #fff; border-color: rgba(255, 51, 51, 0.5); background: {t['C_RED']}; font-weight: 700; }}
    QPushButton#btn_clear:hover {{ background: #ff4444; border-color: #ff4444; }}

    QPushButton#btn_export {{ color: {t['C_TEXT']}; border-color: {t['C_BORDER2']}; background: {t['C_SURFACE3']}; font-weight: 700; }}
    QPushButton#btn_export:hover {{ background: {t['C_TEXT']}; color: #000; border-color: {t['C_TEXT']}; }}

    QPushButton#btn_autoscroll {{
        color: {t['C_TEXT']};
        border-color: {t['C_BORDER2']};
        background: {t['C_SURFACE3']};
    }}
    QPushButton#btn_autoscroll:hover {{
        color: {t['C_TEXT']};
        border-color: {t['C_TEXT']};
        background: {t['BTN_HOVER_BG']};
    }}
    QPushButton#btn_autoscroll:checked {{
        color: {t['C_TEXT']};
        border-color: {t['C_TEXT']};
        background: {t['BTN_HOVER_BG']};
        font-weight: bold;
    }}
    QPushButton#btn_autoscroll:checked:hover {{
        background: rgba(255, 255, 255, 0.12);
    }}

    QCheckBox {{ color:{t['C_TEXT']}; spacing:8px; font-weight:500; font-size:13px; background: transparent; }}
    
    QLineEdit#search_box {{
        background: {t['C_SURFACE2']}; color: {t['C_TEXT']}; border: 1px solid {t['C_BORDER2']}; border-radius: 4px;
        padding: 4px 10px; font-size: 12px; font-weight: 600;
    }}
    QLineEdit#search_box:focus {{ border-color: {t['C_TEXT']}; }}
    
    #stats_bar {{ background: {t['C_SURFACE']}; border-bottom: 1px solid {t['C_BORDER2']}; }}
    #stat_card {{
        background: {t['C_SURFACE3']}; border: 1px solid {t['C_BORDER2']};
        border-top: 2px solid {t['C_BORDER2']}; border-radius: 5px;
    }}
    QLabel#stat_label {{ color:{t['C_DIM']}; font-size:10px; font-weight:700; letter-spacing:0.12em; background: transparent; }}

    QTableWidget {{
        background:{t['C_BG']}; gridline-color:transparent; border:none;
        selection-background-color:{t['C_SURFACE3']}; selection-color:{t['C_TEXT']};
        font-family:"Consolas","JetBrains Mono",monospace; font-size:13px;
    }}
    QTableWidget::item {{ border-bottom:1px solid {t['C_SURFACE2']}; padding:3px 8px; }}
    QTableWidget::item:selected {{ background:{t['C_SURFACE3']}; color:{t['C_TEXT']}; }}
    QTableWidget {{ alternate-background-color:{t['C_SURFACE']}; }}
    QHeaderView::section {{
        background:{t['C_HDR']}; color:{t['C_SLATE']}; padding:8px 10px; border:none; border-right:1px solid {t['C_BORDER']};
        border-bottom:2px solid {t['C_BORDER2']}; font-size:11px; font-weight:700; letter-spacing:0.09em;
    }}

    QLabel#section_title {{ color:{t['C_TEXT']}; font-size:11px; font-weight:700; letter-spacing:0.18em; background: transparent; }}
    QLabel#wave_hint {{ color:{t['C_DIM']}; font-size:12px; font-family:Consolas; background: transparent; }}

    #footer {{ background: {t['C_HDR']}; border-top: 1px solid {t['C_BORDER2']}; }}
    QLabel#foot_name  {{ color:{t['C_TEXT']}; font-size:15px; font-weight:700; background: transparent; }}
    QLabel#foot_dept  {{ color:{t['C_DIM']};   font-size:10px; background: transparent; }}
    QLabel#foot_inst  {{ color:{t['C_SLATE']}; font-size:10px; font-weight:600; background: transparent; }}

    QPushButton#icon_btn {{ background:{t['C_SURFACE2']}; border:1px solid {t['C_BORDER2']}; border-radius:7px; padding:0; }}
    QPushButton#icon_btn:hover {{ border-color:{t['C_TEXT']}; background:{t['C_SURFACE3']}; }}

    QScrollBar:vertical {{ background:{t['C_SURFACE']}; width:6px; border-radius:3px; }}
    QScrollBar::handle:vertical {{ background:{t['C_BORDER2']}; border-radius:3px; min-height:20px; }}
    QScrollBar::handle:vertical:hover {{ background:{t['C_SLATE']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}

    QStatusBar {{ background:{t['C_HDR']}; color:{t['C_SLATE']}; font-size:11px; border-top:1px solid {t['C_BORDER2']}; }}
    #clock_lbl {{ color:{t['C_TEXT']}; font-size:15px; font-weight:700; font-family:"Consolas",monospace; letter-spacing:0.08em; padding:0 10px; background: transparent; }}
    QLabel, QCheckBox {{ background: transparent; }}
    """


# ══════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════
class AutoRefreshComboBox(QComboBox):
    def __init__(self, refresh_cb, parent=None):
        super().__init__(parent)
        self.refresh_cb = refresh_cb

    def showPopup(self):
        if self.refresh_cb:
            self.refresh_cb()
        super().showPopup()

class MainWindow(QMainWindow):
    LINKS = {
        "github":   "https://github.com/upadhyaypranjal/Peripheral_Analyzer_Sniffer",
        "linkedin": "https://linkedin.com/in/pranjalupadhyay0142",
        "gmail":    "mailto:pranjal2004upadhyay@gmail.com",
        "website":  "https://pranjalupadhyay.netlify.app",
    }
    BAUD_RATES = ["1200","2400","4800","9600","19200","38400","57600","115200","230400","460800","921600"]
    PROTOCOLS  = ["Auto-Detect","I2C","UART","SPI","PWM"]

    def __init__(self):
        super().__init__()
        try:
            self._init_state()
            self._build_ui()
            self._apply_theme()
        except Exception:
            traceback.print_exc(); raise

    def _init_state(self):
        self.serial_manager = SerialManager()
        self.packet_parser  = PacketParser()
        self._stats         = {"uart":0,"i2c":0,"spi":0,"pwm":0,"errors":0}
        self._start_time    = None
        self._protocol_filter = "Auto-Detect"
        self._capture_active = False
        self._is_light_mode = False
        
        self._i2c_open = False; self._i2c_tx_count=0; self._i2c_hdr_row=-1; self._cur_i2c_idx=-1
        self._spi_open = False; self._spi_tx_count=0; self._spi_hdr_row=-1; self._cur_spi_idx=-1
        self._uart_char_rows: list[int] = []
        self._uart_msg_count = 0       
        self._uart_msg_serial = 0      
        self._tx_log:    list[dict] = []
        self._row_to_tx: dict[int,int] = {}
        
        self._timer = QTimer(); self._timer.setInterval(50); self._timer.timeout.connect(self._drain)
        self._clock_timer = QTimer(); self._clock_timer.setInterval(500); self._clock_timer.timeout.connect(self._tick_clock)
        self._runtime_timer = QTimer(); self._runtime_timer.setInterval(1000); self._runtime_timer.timeout.connect(self._tick_runtime)
        self.setWindowTitle("FPGA based Multi Protocol Analyzer Sniffer")
        self.resize(1480, 940); self.setMinimumSize(1080, 700)
        self._footer_status_timer = QTimer(); self._footer_status_timer.setSingleShot(True)
        self._footer_status_timer.timeout.connect(self._clear_footer_status)

        self._in_transition = False
        self._spinner_angle = 0
        self._transition_timer = QTimer()
        self._transition_timer.setSingleShot(True)
        self._transition_timer.timeout.connect(self._on_transition_timeout)
        self._spinner_timer = QTimer()
        self._spinner_timer.setInterval(40)
        self._spinner_timer.timeout.connect(self._update_spinner)

    def _build_ui(self):
        root = QWidget(); root.setObjectName("root_widget"); self.setCentralWidget(root)
        vbox = QVBoxLayout(root); vbox.setContentsMargins(0,0,0,0); vbox.setSpacing(0)
        vbox.addWidget(self._mk_toolbar())
        vbox.addWidget(self._mk_stats_bar())
        self._tabs = QTabWidget()
        self._tabs.addTab(self._mk_stream_tab(),   "📡  Stream")
        self._tabs.addTab(self._mk_waveform_tab(), "〰  Waveform")
        vbox.addWidget(self._tabs, stretch=1)
        vbox.addWidget(self._mk_footer())
        self._sb = QStatusBar(); self.setStatusBar(self._sb)
        self._sb.showMessage("Instrument Status:  Disconnected  —  Select a port and click Connect.")
        self._clock_timer.start()

    def _mk_combo_box(self, label_text: str, combo: QComboBox):
        frame = QFrame(); frame.setObjectName("combo_box_frame")
        layout = QHBoxLayout(frame); layout.setContentsMargins(10, 0, 0, 0); layout.setSpacing(0)
        lbl = QLabel(label_text + ":")
        lbl.setStyleSheet(f"font-size:11px;font-weight:700;border:none;background:transparent;")
        layout.addWidget(lbl); layout.addWidget(combo)
        return frame

    def _mk_toolbar(self):
        bar = QWidget(); bar.setObjectName("toolbar"); bar.setFixedHeight(110)
        v_main = QVBoxLayout(bar); v_main.setContentsMargins(16, 12, 16, 12); v_main.setSpacing(12)

        r1 = QHBoxLayout(); r1.setSpacing(8)
        self._title_lbl = QLabel("FPGA based Multi Protocol Analyzer Sniffer")
        self._title_lbl.setStyleSheet("font-size:15px;font-weight:800;letter-spacing:0.04em;")
        r1.addWidget(self._title_lbl); r1.addStretch()
        self._dot = PulseDot(); r1.addWidget(self._dot)
        r1.addWidget(self._vsep(16))
        self._clock_lbl = QLabel("00:00:00"); self._clock_lbl.setObjectName("clock_lbl"); r1.addWidget(self._clock_lbl)

        r2 = QHBoxLayout(); r2.setSpacing(12)
        self._port_cb = AutoRefreshComboBox(self._reload_ports); self._port_cb.setFixedWidth(130); self._reload_ports()
        r2.addWidget(self._mk_combo_box("PORT", self._port_cb))
        r2.addWidget(self._vsep(22))

        self._baud_cb = QComboBox(); self._baud_cb.addItems(self.BAUD_RATES); self._baud_cb.setCurrentText("9600"); self._baud_cb.setFixedWidth(110)
        r2.addWidget(self._mk_combo_box("BAUD", self._baud_cb))
        r2.addWidget(self._vsep(22))

        self._proto_cb = QComboBox(); self._proto_cb.addItems(self.PROTOCOLS); self._proto_cb.setFixedWidth(120); self._proto_cb.currentTextChanged.connect(self._protocol_changed)
        r2.addWidget(self._mk_combo_box("PROTOCOL", self._proto_cb))
        r2.addWidget(self._vsep(22))

        self._btn_con = QPushButton("Connect"); self._btn_con.setObjectName("btn_connect"); self._btn_con.setFixedWidth(100); self._btn_con.setFixedHeight(30)
        self._btn_con.setIconSize(QSize(16, 16))
        self._btn_con.clicked.connect(self._toggle_connect); r2.addWidget(self._btn_con)
        r2.addWidget(self._vsep(22))

        self._btn_stop = QPushButton("⏸ Pause"); self._btn_stop.setFixedWidth(90); self._btn_stop.setFixedHeight(30)
        self._btn_stop.clicked.connect(self._toggle_capture); self._btn_stop.setObjectName("btn_export"); self._btn_stop.setEnabled(False)
        r2.addWidget(self._btn_stop)
        r2.addWidget(self._vsep(22))

        self._btn_scroll = QPushButton("Auto Scroll")
        self._btn_scroll.setObjectName("btn_autoscroll")
        self._btn_scroll.setCheckable(True)
        self._btn_scroll.setChecked(True)
        self._btn_scroll.setFixedHeight(30)
        self._btn_scroll.toggled.connect(self._on_auto_scroll_toggled)
        r2.addWidget(self._btn_scroll); r2.addStretch()

        btn_exp = QPushButton("Export ↓"); btn_exp.setObjectName("btn_export"); btn_exp.setFixedHeight(30); btn_exp.setFixedWidth(90)
        export_menu = QMenu(self)
        export_menu.setObjectName("export_menu")
        csv_action = export_menu.addAction("Export as CSV"); pdf_action = export_menu.addAction("Export as PDF")
        csv_action.triggered.connect(lambda: self._do_export("CSV")); pdf_action.triggered.connect(lambda: self._do_export("PDF"))
        btn_exp.setMenu(export_menu); r2.addWidget(btn_exp); r2.addWidget(self._vsep(22))

        btn_clr = QPushButton("⊘  Clear"); btn_clr.setObjectName("btn_clear"); btn_clr.setFixedHeight(30); btn_clr.setFixedWidth(84); btn_clr.clicked.connect(self._clear)
        r2.addWidget(btn_clr)

        v_main.addLayout(r1); v_main.addLayout(r2)
        return bar

    def _mk_stats_bar(self):
        bar = QWidget(); bar.setObjectName("stats_bar"); bar.setFixedHeight(72)
        h = QHBoxLayout(bar); h.setContentsMargins(16,8,16,8); h.setSpacing(10)
        self._c_uart    = StatCard("UART Messages", "C_GREEN")
        self._c_i2c     = StatCard("I2C Events",    "C_BLUE")
        self._c_spi     = StatCard("SPI Events",    "C_PURPLE")
        self._c_pwm     = StatCard("PWM Signals",   "C_AMBER")
        self._c_errs    = StatCard("Frame Errors",   "C_RED")
        self._c_runtime = StatCard("Session Runtime", "C_AMBER")
        for c in [self._c_uart, self._c_i2c, self._c_spi, self._c_pwm, self._c_errs, self._c_runtime]: h.addWidget(c, stretch=1)
        return bar

    def _mk_stream_tab(self):
        wrap = QWidget(); v = QVBoxLayout(wrap); v.setContentsMargins(16,10,16,8); v.setSpacing(4)
        row_h = QHBoxLayout(); row_h.setSpacing(12)
        lbl = QLabel("LIVE HARDWARE PACKET STREAM"); lbl.setObjectName("section_title")
        row_h.addWidget(lbl)

        # Re-add Stream Search Box
        self._search_box = QLineEdit()
        self._search_box.setObjectName("search_box")
        self._search_box.setPlaceholderText("Filter Stream...")
        self._search_box.setFixedWidth(180)
        self._search_box.textChanged.connect(self._filter_stream)
        row_h.addWidget(self._search_box)
        
        row_h.addStretch()
        
        self._stream_hint = QLabel("Click any row  →  view waveform")
        self._stream_hint.setObjectName("wave_hint"); row_h.addWidget(self._stream_hint); v.addLayout(row_h)
        self._tbl = QTableWidget(0, 4)
        self._tbl.setHorizontalHeaderLabels(["Timestamp","Protocol","Event","Details"])
        hdr = self._tbl.horizontalHeader()
        for i, m in enumerate([QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.Stretch]):
            hdr.setSectionResizeMode(i, m)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setShowGrid(False); self._tbl.setAlternatingRowColors(True)
        self._tbl.cellClicked.connect(self._row_clicked); v.addWidget(self._tbl)
        return wrap

    def _mk_waveform_tab(self):
        wrap = QWidget(); v = QVBoxLayout(wrap); v.setContentsMargins(16,10,16,10); v.setSpacing(8)
        info = QHBoxLayout(); info.setSpacing(12)
        self._wave_badge = QLabel("  ···  "); self._wave_badge.setFixedHeight(24)
        self._wave_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wave_title = QLabel("Select a row in the Stream tab to render its waveform.")
        self._wave_title.setObjectName("wave_hint")
        self._wave_meta = QLabel(""); self._wave_meta.setObjectName("wave_hint")
        info.addWidget(self._wave_badge); info.addWidget(self._wave_title, stretch=1); info.addWidget(self._wave_meta); v.addLayout(info)
        self._wave_sep = QFrame(); self._wave_sep.setFrameShape(QFrame.Shape.HLine)
        v.addWidget(self._wave_sep)
        self._wave_canvas = WaveformCanvas(); v.addWidget(self._wave_canvas, stretch=1)
        return wrap

    def _mk_footer(self):
        foot = QWidget(); foot.setObjectName("footer"); foot.setFixedHeight(50)
        h = QHBoxLayout(foot); h.setContentsMargins(20,10,20,10); h.setSpacing(16)
        col = QVBoxLayout(); col.setSpacing(2)
        n = QLabel("Pranjal Upadhyay"); n.setObjectName("foot_name")
        col.addWidget(n)
        h.addLayout(col); h.addStretch()

        self._footer_status = QLabel(""); self._footer_status.setObjectName("footer_status"); self._footer_status.setFixedHeight(28)
        self._footer_status.setAlignment(Qt.AlignmentFlag.AlignCenter); self._footer_status.setStyleSheet("background: transparent; border: none;")
        self._footer_status.hide()
        h.addWidget(self._footer_status)
        h.addStretch()

        right = QVBoxLayout(); right.setSpacing(4); right.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._ver_lbl = QLabel(); right.addWidget(self._ver_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        h.addLayout(right)
        
        self._icons = []
        icons_layout = QHBoxLayout(); icons_layout.setSpacing(10); icons_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        for k, url in self.LINKS.items():
            btn = IconLinkButton(k, url, size=26); icons_layout.addWidget(btn); self._icons.append(btn)
        h.addLayout(icons_layout)
        return foot



    def _vsep(self, h=22):
        f = QFrame(); f.setFixedSize(1, h)
        f.setObjectName("vsep_frame")
        return f

    def _on_auto_scroll_toggled(self, checked):
        if checked:
            self._show_footer_msg("Auto Scroll Enabled", "info")
        else:
            self._show_footer_msg("Auto Scroll Disabled", "info")

    def _apply_theme(self):
        self.setStyleSheet(generate_qss(THEME))
        self._title_lbl.setStyleSheet(f"color:{THEME['C_TEXT']};font-size:15px;font-weight:800;letter-spacing:0.04em;")
        self._wave_badge.setStyleSheet(f"background:{THEME['C_SURFACE3']};border:1px solid {THEME['C_BORDER2']};border-radius:3px;padding:0 10px;font-weight:700;font-size:10px;")
        self._wave_sep.setStyleSheet(f"background:{THEME['C_BORDER2']};border:none;max-height:1px;")
        self._ver_lbl.setStyleSheet(f"color:{THEME['C_DIM']};font-size:9px;font-family:Consolas;")
        
        for f in self.findChildren(QFrame, "vsep_frame"):
            f.setStyleSheet(f"background:{THEME['C_BORDER2']};border:none;")
        for menu in self.findChildren(QMenu, "export_menu"):
            menu.setStyleSheet(f"QMenu {{ background-color: {THEME['C_SURFACE2']}; color: {THEME['C_TEXT']}; border: 1px solid {THEME['C_BORDER2']}; border-radius: 4px; padding: 4px 0px; }} QMenu::item {{ padding: 6px 20px; background-color: transparent; }} QMenu::item:selected {{ background-color: {THEME['C_BLUE']}; color: #fff; }}")
        
        for c in [self._c_uart, self._c_i2c, self._c_spi, self._c_pwm, self._c_errs, self._c_runtime]: c.update_theme()
        for icon in self._icons: icon._update_colors()
        self._wave_canvas.update_theme()
        self._recolor_table()
        
        if self._footer_status.text() != "":
            self._footer_status.setStyleSheet(self._footer_status.styleSheet().replace("color: ", f"color: {THEME['C_TEXT']}"))

    def _recolor_table(self):
        for r in range(self._tbl.rowCount()):
            it0, it1, it2, it3 = self._tbl.item(r, 0), self._tbl.item(r, 1), self._tbl.item(r, 2), self._tbl.item(r, 3)
            if not it0: continue
            if it0.text().strip() == "":
                bg = QColor(THEME["C_SURFACE2"])
                if "▶" in it3.text():
                    for c in range(4): self._tbl.item(r, c).setBackground(bg)
                    if "SPI" in it3.text():
                        it3.setForeground(QColor(THEME["C_PURPLE"]))
                    else:
                        it3.setForeground(QColor(THEME["C_BLUE"]))
                elif "──" in it3.text():
                    for c in range(4): self._tbl.item(r, c).setBackground(bg)
                    it3.setForeground(QColor(THEME["C_GREEN"]))
                elif "─" in it3.text():
                    for c in range(4): self._tbl.item(r, c).setBackground(QColor(THEME["C_BORDER"]))
                    it3.setForeground(QColor(THEME["C_BORDER2"]))
            else:
                proto = it1.text().strip()
                ev = it2.text().strip()
                it0.setForeground(QColor(THEME["C_SLATE"]))
                it1.setForeground(QColor(get_badge_fg(proto)))
                it1.setBackground(QColor(get_badge_bg(proto)))
                it2.setForeground(QColor(get_event_fg(ev)))
                it3.setForeground(QColor(THEME["C_TEXT"]))

    def _clear_footer_status(self):
        self._footer_status.setText("")
        self._footer_status.setStyleSheet("background: transparent; border: none;")
        self._footer_status.hide()

    def _show_footer_msg(self, msg: str, kind: str):
        self._footer_status_timer.stop()
        bg, fg, border = "", "", ""
        if kind in ("connected", "success"):
            bg, fg, border = "rgba(0, 255, 102, 0.15)", THEME["C_GREEN"], THEME["C_GREEN"]
        elif kind in ("disconnected", "error"):
            bg, fg, border = "rgba(255, 51, 51, 0.15)", THEME["C_RED"], THEME["C_RED"]
        elif kind == "warning":
            bg, fg, border = "rgba(255, 184, 0, 0.15)", THEME["C_AMBER"], THEME["C_AMBER"]
        else: # info
            bg, fg, border = "rgba(234, 234, 234, 0.15)", THEME["C_TEXT"], THEME["C_TEXT"]

        self._footer_status.setText(msg)
        self._footer_status.setStyleSheet(f"""
            QLabel#footer_status {{ background-color: {bg}; color: {fg}; border: 1px solid {border}; border-radius: 14px; padding: 0 16px; font-size: 11px; font-weight: bold; letter-spacing: 0.04em; }}
        """)
        self._footer_status.show()
        self._footer_status_timer.start(5000)

    def _reload_ports(self):
        self._port_cb.clear()
        try:   ports = get_available_ports()
        except: ports = []
        self._port_cb.addItems(ports if ports else ["No Ports Detected"])

    def _protocol_changed(self, proto: str):
        self._protocol_filter = proto
        if hasattr(self, "packet_parser"):
            self.packet_parser._active_protocol = "UNKNOWN" if proto == "Auto-Detect" else proto

    def _draw_spinner(self, angle, size=16, color_key="C_BLUE"):
        color = QColor(THEME.get(color_key, "#4A9EFF"))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = painter.pen()
        pen.setWidth(2)
        pen.setColor(color)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        painter.drawArc(2, 2, size - 4, size - 4, int(angle * 16), int(270 * 16))
        painter.end()
        return QIcon(pixmap)

    def _update_spinner(self):
        self._spinner_angle = (self._spinner_angle - 15) % 360
        color_key = "C_RED" if self.serial_manager.is_connected() else "C_GREEN"
        icon = self._draw_spinner(self._spinner_angle, size=16, color_key=color_key)
        self._btn_con.setIcon(icon)

    def _connect_actual(self):
        self._in_transition = False
        self._spinner_timer.stop()
        self._btn_con.setIcon(QIcon())
        self._btn_con.setFixedWidth(100)
        
        port = self._port_cb.currentText()
        if not port or "No Ports" in port:
            self._show_footer_msg("⚠  No valid port selected.", "warning"); return
        if self.serial_manager.is_connected():
            self._show_footer_msg(f"⚠  Already Connected  —  {port}", "warning"); return
        baud = int(self._baud_cb.currentText())
        try:   ok = self.serial_manager.connect(port, baud)
        except: traceback.print_exc(); ok = False
        if ok:
            self._start_time = time.time(); self._timer.start(); self._runtime_timer.start(); self._dot.set_online(True)
            self._sb.showMessage(f"Instrument Status:  Connected  —  {port}  @  {baud} baud  |  Protocol: {self._protocol_filter}")
            self._show_footer_msg(f"✔  Connected  —  {port}", "connected")
            self._btn_con.setText("Disconnect"); self._btn_con.setObjectName("btn_disconnect")
            self._btn_con.style().unpolish(self._btn_con); self._btn_con.style().polish(self._btn_con)
            self._capture_active = True; self._btn_stop.setEnabled(True)
            self._btn_stop.setText("⏸ Pause")
        else:
            self._sb.showMessage("Instrument Status:  Connection failed.")
            self._show_footer_msg(f"✖  Connection Failed  —  {port}", "error")
            self._btn_con.setText("Connect"); self._btn_con.setObjectName("btn_connect")
            self._btn_con.style().unpolish(self._btn_con); self._btn_con.style().polish(self._btn_con)
            self._capture_active = False; self._btn_stop.setEnabled(False)

    def _disconnect_actual(self):
        self._in_transition = False
        self._spinner_timer.stop()
        self._btn_con.setIcon(QIcon())
        self._btn_con.setFixedWidth(100)
        
        if not self.serial_manager.is_connected():
            self._show_footer_msg("⚠  No active connection.", "warning"); return
        port = self._port_cb.currentText()
        self._timer.stop(); self._runtime_timer.stop()
        if self._i2c_open: self._close_i2c()
        if self._spi_open: self._close_spi()
        try:   self.serial_manager.disconnect()
        except: traceback.print_exc()
        self._start_time = None; self._dot.set_online(False)
        self._sb.showMessage("Instrument Status:  Disconnected.")
        self._show_footer_msg(f"✖  Disconnected  —  {port}", "disconnected")
        self._btn_con.setText("Connect"); self._btn_con.setObjectName("btn_connect")
        self._btn_con.style().unpolish(self._btn_con); self._btn_con.style().polish(self._btn_con)
        self._capture_active = False; self._btn_stop.setEnabled(False)

    def _on_transition_timeout(self):
        if self.serial_manager.is_connected():
            self._disconnect_actual()
        else:
            self._connect_actual()

    def _toggle_connect(self):
        if self._in_transition:
            return
            
        port = self._port_cb.currentText()
        if not self.serial_manager.is_connected():
            if not port or "No Ports" in port:
                self._show_footer_msg("⚠  No valid port selected.", "warning"); return
            self._in_transition = True
            self._btn_con.setFixedWidth(220)
            self._btn_con.setText(f"Connecting to {port} ....")
            self._sb.showMessage(f"Instrument Status:  Connecting to {port} ....")
            self._show_footer_msg(f"Connecting to {port} ....", "info")
            self._spinner_angle = 0
            self._spinner_timer.start()
            self._transition_timer.start(1200)
        else:
            self._in_transition = True
            self._btn_con.setFixedWidth(240)
            self._btn_con.setText(f"Disconnecting from {port} ....")
            self._sb.showMessage(f"Instrument Status:  Disconnecting from {port} ....")
            self._show_footer_msg(f"Disconnecting from {port} ....", "info")
            self._spinner_angle = 0
            self._spinner_timer.start()
            self._transition_timer.start(1200)

    def _toggle_capture(self):
        if self._capture_active:
            self._capture_active = False
            self._btn_stop.setText("▶ Resume")
            self._show_footer_msg("⏸  Capture Paused", "warning")
        else:
            if not self.serial_manager.is_connected(): return
            self._capture_active = True
            self._btn_stop.setText("⏸ Pause")
            self._show_footer_msg("▶  Capture Running", "success")

    def _drain(self):
        try:   lines = self.serial_manager.read_available()
        except: traceback.print_exc(); return
        for line in lines:
            line = line.strip()
            if not line: continue
            
            try:   packets = self.packet_parser.parse_line(line)
            except: traceback.print_exc(); packets = []

            if getattr(self, "_capture_active", False):
                for pkt in packets:
                    try:   self._ingest(pkt)
                    except: traceback.print_exc()

    def _ingest(self, pkt: dict):
        proto = pkt.get("protocol","UNKNOWN")
        event = pkt.get("event","")
        
        # Normalize protocol for filtering (e.g. "I2C SLAVE" -> "I2C")
        norm_proto = "I2C" if "I2C" in proto else proto
        if self._protocol_filter != "Auto-Detect" and norm_proto != self._protocol_filter and norm_proto != "ASCII": return

        if proto == "" and event == "":
            self._add_row(pkt, indent=False)
            if self._btn_scroll.isChecked(): self._tbl.scrollToBottom()
            self._filter_stream(self._search_box.text())
            return

        if proto == "I2C":
            if event == "SEPARATOR": return
            self._stats["i2c"] += 1; self._refresh_stats()
            if event == "START":
                if self._i2c_open: self._close_i2c()
                self._i2c_tx_count += 1
                tx = {"type":"I2C","tx_num":self._i2c_tx_count,"events":[pkt],"rows":[]}
                self._cur_i2c_idx = len(self._tx_log); self._tx_log.append(tx)
                hdr = self._insert_i2c_hdr(self._i2c_tx_count)
                tx["rows"].append(hdr); self._row_to_tx[hdr] = self._cur_i2c_idx
                self._i2c_hdr_row = hdr; self._i2c_open = True
                row = self._add_row(pkt, indent=True)
                tx["rows"].append(row); self._row_to_tx[row] = self._cur_i2c_idx
            elif event == "STOP":
                if not self._i2c_open:
                    self._i2c_tx_count += 1
                    tx = {"type":"I2C","tx_num":self._i2c_tx_count,"events":[],"rows":[]}
                    self._cur_i2c_idx = len(self._tx_log); self._tx_log.append(tx)
                    hdr = self._insert_i2c_hdr(self._i2c_tx_count)
                    tx["rows"].append(hdr); self._row_to_tx[hdr] = self._cur_i2c_idx; self._i2c_open = True
                if self._cur_i2c_idx >= 0: self._tx_log[self._cur_i2c_idx]["events"].append(pkt)
                row = self._add_row(pkt, indent=True)
                if self._cur_i2c_idx >= 0:
                    self._tx_log[self._cur_i2c_idx]["rows"].append(row); self._row_to_tx[row] = self._cur_i2c_idx
                self._close_i2c()
            else:
                if not self._i2c_open:
                    self._i2c_tx_count += 1
                    tx = {"type":"I2C","tx_num":self._i2c_tx_count,"events":[],"rows":[]}
                    self._cur_i2c_idx = len(self._tx_log); self._tx_log.append(tx)
                    hdr = self._insert_i2c_hdr(self._i2c_tx_count)
                    tx["rows"].append(hdr); self._row_to_tx[hdr] = self._cur_i2c_idx; self._i2c_open = True
                if self._cur_i2c_idx >= 0: self._tx_log[self._cur_i2c_idx]["events"].append(pkt)
                row = self._add_row(pkt, indent=True)
                if self._cur_i2c_idx >= 0:
                    self._tx_log[self._cur_i2c_idx]["rows"].append(row); self._row_to_tx[row] = self._cur_i2c_idx

        elif proto == "UART" or proto == "I2C SLAVE":
            if event == "SEPARATOR": return
            if event == "CHAR":
                row = self._add_row(pkt); self._uart_char_rows.append(row)
            elif event == "MESSAGE":
                self._remove_rows(self._uart_char_rows); self._uart_char_rows = []
                self._uart_msg_count += 1; self._uart_msg_serial += 1; self._stats["uart"] += 1; self._refresh_stats()
                tx = {"type":proto,"tx_num":self._uart_msg_count,"message":pkt.get("details",""),"events":[pkt],"rows":[]}
                tx_idx = len(self._tx_log); self._tx_log.append(tx)
                msg_row = self._add_row(pkt); tx["rows"].append(msg_row); self._row_to_tx[msg_row] = tx_idx
                sep_color = THEME["C_BLUE"] if "I2C" in proto else THEME["C_GREEN"]
                sep_row = self._add_sep(f"  ── Message #{self._uart_msg_count} complete  ·  {len(pkt.get('details',''))} chars  ·  Next message will start at #1  ──", sep_color)
                tx["rows"].append(sep_row); self._uart_msg_count = 0
            else: self._add_row(pkt)

        elif proto == "SPI":
            if event == "SEPARATOR": return
            self._stats["spi"] += 1; self._refresh_stats()
            if event == "START":
                if self._spi_open: self._close_spi()
                self._spi_tx_count += 1
                tx = {"type":"SPI","tx_num":self._spi_tx_count,"events":[pkt],"rows":[]}
                self._cur_spi_idx = len(self._tx_log); self._tx_log.append(tx)
                hdr = self._insert_spi_hdr(self._spi_tx_count)
                tx["rows"].append(hdr); self._row_to_tx[hdr] = self._cur_spi_idx
                self._spi_hdr_row = hdr; self._spi_open = True
                row = self._add_row(pkt, indent=True)
                tx["rows"].append(row); self._row_to_tx[row] = self._cur_spi_idx
            elif event == "STOP":
                if not self._spi_open:
                    self._spi_tx_count += 1
                    tx = {"type":"SPI","tx_num":self._spi_tx_count,"events":[],"rows":[]}
                    self._cur_spi_idx = len(self._tx_log); self._tx_log.append(tx)
                    hdr = self._insert_spi_hdr(self._spi_tx_count)
                    tx["rows"].append(hdr); self._row_to_tx[hdr] = self._cur_spi_idx; self._spi_open = True
                if self._cur_spi_idx >= 0: self._tx_log[self._cur_spi_idx]["events"].append(pkt)
                row = self._add_row(pkt, indent=True)
                if self._cur_spi_idx >= 0:
                    self._tx_log[self._cur_spi_idx]["rows"].append(row); self._row_to_tx[row] = self._cur_spi_idx
                self._close_spi()
            else:
                if not self._spi_open:
                    self._spi_tx_count += 1
                    tx = {"type":"SPI","tx_num":self._spi_tx_count,"events":[],"rows":[]}
                    self._cur_spi_idx = len(self._tx_log); self._tx_log.append(tx)
                    hdr = self._insert_spi_hdr(self._spi_tx_count)
                    tx["rows"].append(hdr); self._row_to_tx[hdr] = self._cur_spi_idx; self._spi_open = True
                if self._cur_spi_idx >= 0: self._tx_log[self._cur_spi_idx]["events"].append(pkt)
                row = self._add_row(pkt, indent=True)
                if self._cur_spi_idx >= 0:
                    self._tx_log[self._cur_spi_idx]["rows"].append(row); self._row_to_tx[row] = self._cur_spi_idx

        else:
            if event == "SEPARATOR": return
            if proto == "PWM":
                self._stats["pwm"] += 1
                self._refresh_stats()
            elif proto == "UNKNOWN":
                self._stats["errors"] += 1
                self._refresh_stats()
            
            indent = (proto == "ASCII" and (self._spi_open or self._i2c_open))
            row = self._add_row(pkt, indent=indent)
            
            if proto == "ASCII":
                if self._spi_open and self._cur_spi_idx >= 0:
                    self._tx_log[self._cur_spi_idx]["events"].append(pkt)
                    self._tx_log[self._cur_spi_idx]["rows"].append(row)
                    self._row_to_tx[row] = self._cur_spi_idx
                elif self._i2c_open and self._cur_i2c_idx >= 0:
                    self._tx_log[self._cur_i2c_idx]["events"].append(pkt)
                    self._tx_log[self._cur_i2c_idx]["rows"].append(row)
                    self._row_to_tx[row] = self._cur_i2c_idx

        if self._btn_scroll.isChecked(): self._tbl.scrollToBottom()
        self._filter_stream(self._search_box.text())

    def _insert_i2c_hdr(self, n):
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        bg = QColor(THEME["C_SURFACE2"])
        for col in range(4):
            it = QTableWidgetItem(""); it.setBackground(bg)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable); self._tbl.setItem(row,col,it)
        hdr = QTableWidgetItem(f"  ▶  I2C TRANSACTION  #{n}")
        hdr.setForeground(QColor(THEME["C_BLUE"])); hdr.setFont(QFont("Consolas",11,QFont.Weight.Bold)); hdr.setBackground(bg)
        hdr.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable); hdr.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
        self._tbl.setItem(row,3,hdr); self._tbl.setRowHeight(row,26)
        return row

    def _close_i2c(self): self._insert_hairline(); self._i2c_open=False; self._i2c_hdr_row=-1

    def _insert_spi_hdr(self, n):
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        bg = QColor(THEME["C_SURFACE2"])
        for col in range(4):
            it = QTableWidgetItem(""); it.setBackground(bg)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable); self._tbl.setItem(row,col,it)
        hdr = QTableWidgetItem(f"  ▶  SPI TRANSACTION  #{n}")
        hdr.setForeground(QColor(THEME["C_PURPLE"])); hdr.setFont(QFont("Consolas",11,QFont.Weight.Bold)); hdr.setBackground(bg)
        hdr.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable); hdr.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
        self._tbl.setItem(row,3,hdr); self._tbl.setRowHeight(row,26)
        return row

    def _close_spi(self): self._insert_hairline(); self._spi_open=False; self._spi_hdr_row=-1

    def _insert_hairline(self):
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        for col in range(4):
            it = QTableWidgetItem(""); it.setBackground(QColor(THEME["C_BORDER"]))
            it.setFlags(Qt.ItemFlag.ItemIsEnabled); self._tbl.setItem(row,col,it)
        rule = QTableWidgetItem("  " + "─"*110)
        rule.setForeground(QColor(THEME["C_BORDER2"])); rule.setBackground(QColor(THEME["C_BORDER"]))
        rule.setFont(QFont("Consolas",5)); rule.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._tbl.setItem(row,3,rule); self._tbl.setRowHeight(row,5)

    def _add_row(self, pkt: dict, indent: bool = False) -> int:
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        proto = pkt.get("protocol","UNKNOWN"); event = pkt.get("event","")
        ts = pkt.get("timestamp",""); det = ("   " if indent else "") + pkt.get("details","")

        ts_it = QTableWidgetItem(ts); ts_it.setForeground(QColor(THEME["C_SLATE"])); ts_it.setFont(QFont("Consolas",13)); ts_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
        
        if proto:
            bg_it = QTableWidgetItem(f"  {proto}  "); bg_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); bg_it.setForeground(QColor(get_badge_fg(proto))); bg_it.setBackground(QColor(get_badge_bg(proto))); bg_it.setFont(QFont("Consolas",12,QFont.Weight.Bold))
        else:
            bg_it = QTableWidgetItem("")
            
        ev_it = QTableWidgetItem(event); ev_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
        if event:
            ev_it.setForeground(QColor(get_event_fg(event))); ev_it.setFont(QFont("Consolas",13,QFont.Weight.Bold))
            
        det_it = QTableWidgetItem(det); det_it.setForeground(QColor(THEME["C_TEXT"])); det_it.setFont(QFont("Consolas",13)); det_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)

        for col, it in enumerate([ts_it,bg_it,ev_it,det_it]): self._tbl.setItem(row,col,it)
        self._tbl.setRowHeight(row,28)
        return row

    def _add_sep(self, text, color) -> int:
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        bg = QColor(THEME["C_SURFACE2"])
        for col in range(4):
            it = QTableWidgetItem(""); it.setBackground(bg)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled); self._tbl.setItem(row,col,it)
        sep = QTableWidgetItem(text)
        sep.setForeground(QColor(color)); sep.setFont(QFont("Consolas",10,QFont.Weight.Bold)); sep.setBackground(bg)
        sep.setFlags(Qt.ItemFlag.ItemIsEnabled); sep.setTextAlignment(Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft)
        self._tbl.setItem(row,3,sep); self._tbl.setRowHeight(row,22)
        return row

    def _remove_rows(self, rows: list):
        for r in sorted(rows, reverse=True):
            self._tbl.removeRow(r)
            new_map = {}
            for k, v in self._row_to_tx.items():
                if k == r: continue
                new_map[k if k < r else k-1] = v
            self._row_to_tx = new_map

    def _filter_stream(self, text: str):
        query = text.lower()
        for i in range(self._tbl.rowCount()):
            if not query:
                self._tbl.setRowHidden(i, False)
                continue
            match = False
            for c in range(self._tbl.columnCount()):
                item = self._tbl.item(i, c)
                if item and query in item.text().lower():
                    match = True
                    break
            self._tbl.setRowHidden(i, not match)

    def _row_clicked(self, row: int, _col: int):
        tx_idx = self._row_to_tx.get(row)
        if tx_idx is None: return
        tx = self._tx_log[tx_idx]; proto=tx["type"]; num=tx.get("tx_num",1)
        self._wave_badge.setText(f"  {proto}  #{num}  ")
        self._wave_badge.setStyleSheet(f"background:{get_badge_bg(proto)};color:{get_badge_fg(proto)};border:1px solid {get_badge_fg(proto)};border-radius:3px;padding:0 10px;font-weight:700;font-size:10px;font-family:Consolas,monospace;")
        if proto=="I2C":
            ne=len([e for e in tx["events"] if e["event"] not in("SEPARATOR",)])
            self._wave_title.setText(f"I²C Transaction #{num}"); self._wave_title.setStyleSheet(f"color:{THEME['C_BLUE']};font-size:12px;font-weight:700;font-family:Consolas,monospace;")
            self._wave_meta.setText(f"{ne} event{'s' if ne!=1 else ''}")
            self._wave_canvas.show_i2c(tx)
        elif proto=="SPI":
            ne=len([e for e in tx["events"] if e["event"] not in("SEPARATOR",)])
            self._wave_title.setText(f"SPI Transaction #{num}"); self._wave_title.setStyleSheet(f"color:{THEME['C_PURPLE']};font-size:12px;font-weight:700;font-family:Consolas,monospace;")
            self._wave_meta.setText(f"{ne} event{'s' if ne!=1 else ''}")
            self._wave_canvas.show_spi(tx)
        else:
            msg = tx.get("message","")
            title_text = f"I2C SLAVE Message #{num}" if "I2C" in proto else f"UART Message #{num}"
            title_color = THEME["C_BLUE"] if "I2C" in proto else THEME["C_GREEN"]
            self._wave_title.setText(title_text); self._wave_title.setStyleSheet(f"color:{title_color};font-size:12px;font-weight:700;font-family:Consolas,monospace;")
            self._wave_meta.setText(f'"{msg}"  ·  {len(msg)} char{"s" if len(msg)!=1 else ""}')
            self._wave_canvas.show_uart(tx)
        self._tabs.setCurrentIndex(1)

    def _do_export(self, fmt="CSV"):
        if self._tbl.rowCount() == 0:
            self._show_footer_msg("⚠  No data to export.", "warning"); return
        if fmt == "CSV":
            path, _ = QFileDialog.getSaveFileName(self, "Export as CSV", f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "CSV Files (*.csv)")
            if not path: return
            try:
                _export_csv(self._tbl, path)
                self._show_footer_msg("✔  CSV Exported successfully.", "success")
            except Exception as ex:
                traceback.print_exc(); QMessageBox.critical(self, "Export Failed", str(ex))
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Export as PDF", f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", "PDF Files (*.pdf)")
            if not path: return
            try:
                _export_pdf(self._tbl, path)
                self._show_footer_msg("✔  PDF Exported successfully.", "success")
            except Exception as ex:
                traceback.print_exc(); QMessageBox.critical(self, "Export Failed", str(ex))

    def _refresh_stats(self):
        self._c_uart.set_value(self._stats["uart"])
        self._c_i2c.set_value(self._stats["i2c"])
        if hasattr(self, "_c_spi") and self._c_spi:
            self._c_spi.set_value(self._stats["spi"])
        if hasattr(self, "_c_pwm") and self._c_pwm:
            self._c_pwm.set_value(self._stats["pwm"])
        self._c_errs.set_value(self._stats["errors"])

    def _tick_clock(self): self._clock_lbl.setText(datetime.now().strftime("%H:%M:%S"))

    def _tick_runtime(self):
        if self._start_time is None: return
        e = int(time.time() - self._start_time)
        self._c_runtime.set_value(f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}")

    def _clear(self):
        self._tbl.setRowCount(0)
        self._i2c_open=False; self._i2c_tx_count=0; self._i2c_hdr_row=-1; self._cur_i2c_idx=-1
        self._spi_open=False; self._spi_tx_count=0; self._spi_hdr_row=-1; self._cur_spi_idx=-1
        self._uart_char_rows=[]; self._uart_msg_count=0; self._uart_msg_serial=0
        self._tx_log=[]; self._row_to_tx={}
        self._stats={"uart":0,"i2c":0,"spi":0,"pwm":0,"errors":0}; self._refresh_stats()
        self._wave_canvas.show_idle()
        self._wave_badge.setText("  ···  "); self._wave_badge.setStyleSheet(f"background:{THEME['C_SURFACE3']};border:1px solid {THEME['C_BORDER2']};border-radius:3px;padding:0 10px;font-weight:700;font-size:10px;")
        self._wave_title.setText("Select a row in the Stream tab to render its waveform."); self._wave_title.setStyleSheet(f"color:{THEME['C_DIM']};font-size:12px;font-family:Consolas,monospace;")
        self._wave_meta.setText("")
        self._show_footer_msg("ℹ  Capture stream cleared.", "info")

    def closeEvent(self, e):
        try:
            self._timer.stop(); self._runtime_timer.stop(); self._clock_timer.stop()
            self._transition_timer.stop(); self._spinner_timer.stop()
            if self.serial_manager.is_connected(): self.serial_manager.disconnect()
        except Exception: traceback.print_exc()
        e.accept()
