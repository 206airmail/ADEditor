"""Runtime-generated toolbar icons.

This module generates SVG data on the fly and converts it to wx objects.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

import wx
from wx.svg import SVGimage as SVGIMG


SIZE = 32


def _svg_base(body: str, accent: str = "#38bdf8") -> str:
    # Make glyphs darker for better contrast on the lighter modern background.
    body = body.replace("#f8fafc", "#0f172a")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" fill="none">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{SIZE}" y2="{SIZE}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="0.48" stop-color="#dbeafe"/>
      <stop offset="1" stop-color="#93c5fd"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="{SIZE}" y2="{SIZE}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{accent}"/>
      <stop offset="1" stop-color="#0369a1"/>
    </linearGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="0" y2="{SIZE}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/>
      <stop offset="0.42" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="30" height="30" rx="6" fill="url(#bg)"/>
  <rect x="1" y="1" width="30" height="30" rx="6" fill="url(#shine)"/>
  {body}
</svg>
"""


def _pin_shape(stroke: str = "url(#accent)") -> str:
    return (
        f'<path d="M16 7.5c-3.1 0-5.6 2.5-5.6 5.6 0 4.4 5.6 10.8 5.6 10.8s5.6-6.4 5.6-10.8c0-3.1-2.5-5.6-5.6-5.6Z" '
        f'stroke="{stroke}" stroke-width="2" stroke-linejoin="round"/>'
        '<circle cx="16" cy="13.1" r="1.9" fill="#f8fafc"/>'
    )


def build_ID_NEW() -> str:
    body = """
  <path d="M10 7.5h8l4 4V24.5a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 9 24.5V9a1.5 1.5 0 0 1 1-1.5Z" stroke="url(#accent)" stroke-width="2" stroke-linejoin="round"/>
  <path d="M18 7.5V12h4" stroke="#f8fafc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <line x1="15" y1="15" x2="15" y2="21" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
  <line x1="12" y1="18" x2="18" y2="18" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#38bdf8")


def build_ID_OPEN() -> str:
    body = """
  <path d="M8 11.5h5l2 2h9a1.5 1.5 0 0 1 1.4 1.9l-2.2 7a1.5 1.5 0 0 1-1.4 1H9.2a1.5 1.5 0 0 1-1.4-1l-1.4-8A1.5 1.5 0 0 1 8 11.5Z" stroke="url(#accent)" stroke-width="2" stroke-linejoin="round"/>
  <path d="M15.5 9.5H24" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
  <path d="M19.5 7l2.5 2.5-2.5 2.5" stroke="#f8fafc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
"""
    return _svg_base(body, accent="#22d3ee")


def build_ID_SAVE() -> str:
    body = """
  <path d="M9.5 7.5h12l2 2v14a1.5 1.5 0 0 1-1.5 1.5H10a1.5 1.5 0 0 1-1.5-1.5V9a1.5 1.5 0 0 1 1-1.5Z" stroke="url(#accent)" stroke-width="2" stroke-linejoin="round"/>
  <rect x="12" y="8.5" width="7" height="4" rx="1" fill="#f8fafc"/>
  <rect x="12" y="16.5" width="8" height="6" rx="1.2" stroke="#f8fafc" stroke-width="1.8"/>
"""
    return _svg_base(body, accent="#34d399")


def build_ID_SAVEAS() -> str:
    body = """
  <path d="M8.8 7.5h10.8l2 2v14a1.5 1.5 0 0 1-1.5 1.5H9.3a1.5 1.5 0 0 1-1.5-1.5V9a1.5 1.5 0 0 1 1-1.5Z" stroke="url(#accent)" stroke-width="2" stroke-linejoin="round"/>
  <rect x="11.2" y="8.5" width="6.4" height="4" rx="1" fill="#f8fafc"/>
  <path d="M22 12.5h6M25 9.5v6" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#10b981")


def build_ID_UNDO() -> str:
    body = """
  <path d="M13.5 11.5H9v-4" stroke="url(#accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M9 11.5c2.2-2.4 5-3.5 8.3-3.1 4.1.5 6.7 3.6 6.7 7.2 0 3.6-2.8 6.7-7.1 7.1" stroke="#f8fafc" stroke-width="2.2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#a78bfa")


def build_ID_REDO() -> str:
    body = """
  <path d="M18.5 11.5H23v-4" stroke="url(#accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M23 11.5c-2.2-2.4-5-3.5-8.3-3.1-4.1.5-6.7 3.6-6.7 7.2 0 3.6 2.8 6.7 7.1 7.1" stroke="#f8fafc" stroke-width="2.2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#8b5cf6")


def build_ID_PREFERENCES() -> str:
    body = """
  <circle cx="16" cy="16" r="3.1" fill="#f8fafc"/>
  <path d="M16 8.2v2.2M16 21.6v2.2M23.8 16h-2.2M10.4 16H8.2M21.5 10.5l-1.6 1.6M12.1 19.9l-1.6 1.6M21.5 21.5l-1.6-1.6M12.1 12.1l-1.6-1.6" stroke="url(#accent)" stroke-width="2" stroke-linecap="round"/>
  <circle cx="16" cy="16" r="7.2" stroke="#f8fafc" stroke-width="1.5" opacity="0.8"/>
"""
    return _svg_base(body, accent="#38bdf8")


def build_ID_ABOUT() -> str:
    body = """
  <circle cx="16" cy="16" r="8.5" stroke="url(#accent)" stroke-width="2.2"/>
  <circle cx="16" cy="11.5" r="1.3" fill="#f8fafc"/>
  <path d="M16 14v6.5" stroke="#f8fafc" stroke-width="2.2" stroke-linecap="round"/>
  <line x1="14.4" y1="20.5" x2="17.6" y2="20.5" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#f59e0b")


def build_ID_ZOOM_IN() -> str:
    body = """
  <circle cx="13" cy="13" r="6.2" stroke="url(#accent)" stroke-width="2.4"/>
  <line x1="17.7" y1="17.7" x2="23" y2="23" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
  <line x1="13" y1="10.2" x2="13" y2="15.8" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
  <line x1="10.2" y1="13" x2="15.8" y2="13" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#22d3ee")


def build_ID_ZOOM_OUT() -> str:
    body = """
  <circle cx="13" cy="13" r="6.2" stroke="url(#accent)" stroke-width="2.4"/>
  <line x1="17.7" y1="17.7" x2="23" y2="23" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
  <line x1="10.2" y1="13" x2="15.8" y2="13" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#60a5fa")


def build_ID_ZOOM_FIT() -> str:
    body = """
  <rect x="9.5" y="9.5" width="13" height="13" rx="2.3" stroke="url(#accent)" stroke-width="2"/>
  <path d="M7 12V7h5M25 12V7h-5M7 20v5h5M25 20v5h-5" stroke="#f8fafc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
"""
    return _svg_base(body, accent="#a78bfa")


def build_ID_ZOOM_RECT() -> str:
    body = """
  <rect x="7.5" y="8.2" width="14" height="11.8" rx="2" stroke="url(#accent)" stroke-width="2" stroke-dasharray="3 2"/>
  <line x1="19.2" y1="18.2" x2="23.5" y2="22.5" stroke="#f8fafc" stroke-width="2.2" stroke-linecap="round"/>
  <circle cx="16.8" cy="15.8" r="4.2" stroke="#f8fafc" stroke-width="1.8"/>
"""
    return _svg_base(body, accent="#f59e0b")


def build_ID_DELETE() -> str:
    body = """
  <path d="M10.5 11.5h11l-1 12a2 2 0 0 1-2 1.8h-5a2 2 0 0 1-2-1.8l-1-12Z" stroke="url(#accent)" stroke-width="2" stroke-linejoin="round"/>
  <path d="M9.5 10h13M13 10V8.2a1.2 1.2 0 0 1 1.2-1.2h3.6A1.2 1.2 0 0 1 19 8.2V10" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
  <line x1="14" y1="14" x2="14" y2="22" stroke="#f8fafc" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="18" y1="14" x2="18" y2="22" stroke="#f8fafc" stroke-width="1.8" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#ef4444")


def build_ID_ROUTE_SWAPDIR() -> str:
    body = """
  <path d="M7 12h13" stroke="url(#accent)" stroke-width="2.2" stroke-linecap="round"/>
  <path d="m17 9 3 3-3 3" stroke="url(#accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M25 20H12" stroke="#f8fafc" stroke-width="2.2" stroke-linecap="round"/>
  <path d="m15 17-3 3 3 3" stroke="#f8fafc" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
"""
    return _svg_base(body, accent="#34d399")


def build_ID_ROUTE_ADD() -> str:
    body = """
  <circle cx="9.5" cy="11.5" r="2.4" fill="#f8fafc"/>
  <circle cx="20.5" cy="18.5" r="2.4" fill="#f8fafc"/>
  <path d="M11.7 12.8c2 1.4 4.6 3 6.6 4.4" stroke="url(#accent)" stroke-width="2.2" stroke-linecap="round"/>
  <line x1="24.2" y1="9.5" x2="24.2" y2="14.5" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
  <line x1="21.7" y1="12" x2="26.7" y2="12" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#38bdf8")


def build_ID_MARKER_ADD() -> str:
    body = f"""
  {_pin_shape()}
  <line x1="24" y1="8.5" x2="24" y2="14.5" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
  <line x1="21" y1="11.5" x2="27" y2="11.5" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#22c55e")


def build_ID_MARKER_EDIT() -> str:
    body = f"""
  {_pin_shape()}
  <path d="M21.5 20.5 26 16l2 2-4.5 4.5-2.6.6.6-2.6Z" fill="#f8fafc"/>
  <path d="m25.8 16.2 1.7-1.7a1 1 0 0 1 1.4 0l.7.7a1 1 0 0 1 0 1.4l-1.7 1.7-2.1-2.1Z" fill="url(#accent)"/>
"""
    return _svg_base(body, accent="#f97316")


def build_ID_MARKER_DEL() -> str:
    body = f"""
  {_pin_shape()}
  <line x1="21" y1="11.5" x2="27" y2="11.5" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
"""
    return _svg_base(body, accent="#ef4444")


_ID_GENERATORS: Dict[str, Callable[[], str]] = {
    "ID_NEW": build_ID_NEW,
    "ID_OPEN": build_ID_OPEN,
    "ID_SAVE": build_ID_SAVE,
    "ID_SAVEAS": build_ID_SAVEAS,
    "ID_UNDO": build_ID_UNDO,
    "ID_REDO": build_ID_REDO,
    "ID_PREFERENCES": build_ID_PREFERENCES,
    "ID_ABOUT": build_ID_ABOUT,
    "ID_ZOOM_IN": build_ID_ZOOM_IN,
    "ID_ZOOM_OUT": build_ID_ZOOM_OUT,
    "ID_ZOOM_FIT": build_ID_ZOOM_FIT,
    "ID_ZOOM_AUTO": build_ID_ZOOM_FIT,
    "ID_ZOOM_RECT": build_ID_ZOOM_RECT,
    "ID_DELETE": build_ID_DELETE,
    "ID_ROUTE_SWAPDIR": build_ID_ROUTE_SWAPDIR,
    "ID_ROUTE_ADD": build_ID_ROUTE_ADD,
    "ID_MARKER_ADD": build_ID_MARKER_ADD,
    "ID_MARKER_EDIT": build_ID_MARKER_EDIT,
    "ID_MARKER_DEL": build_ID_MARKER_DEL,
}

_FILE_TO_ID: Dict[str, str] = {
    "new.svg": "ID_NEW",
    "open.svg": "ID_OPEN",
    "save.svg": "ID_SAVE",
    "save_as.svg": "ID_SAVEAS",
    "undo.svg": "ID_UNDO",
    "redo.svg": "ID_REDO",
    "preferences.svg": "ID_PREFERENCES",
    "about.svg": "ID_ABOUT",
    "zoom_in.svg": "ID_ZOOM_IN",
    "zoom_out.svg": "ID_ZOOM_OUT",
    "zoom_auto.svg": "ID_ZOOM_AUTO",
    "zoom_window.svg": "ID_ZOOM_RECT",
    "delete.svg": "ID_DELETE",
    "route_swapdir.svg": "ID_ROUTE_SWAPDIR",
    "route_add.svg": "ID_ROUTE_ADD",
    "marker_add.svg": "ID_MARKER_ADD",
    "marker_edit.svg": "ID_MARKER_EDIT",
    "marker_del.svg": "ID_MARKER_DEL",
}


def _normalize_icon_id(icon_id: str) -> str:
    key = str(icon_id).strip()
    if key.lower().endswith(".svg"):
        key = _FILE_TO_ID.get(key.lower(), key)
    key = key.replace("wx.", "").replace("self.", "")
    return key


def getToolbarSvg(icon_id: str) -> str:
    key = _normalize_icon_id(icon_id)
    fn = _ID_GENERATORS.get(key)
    if fn is None:
        raise KeyError(f"Unknown toolbar icon id: {icon_id}")
    return fn()


def getToolbarSvgBytes(icon_id: str, encoding: str = "utf-8") -> bytes:
    return getToolbarSvg(icon_id).encode(encoding)


def _make_disabled_image(image: wx.Image) -> wx.Image:
    # Use grayscale and slightly lower alpha for a clearer disabled look.
    disabled = image.ConvertToGreyscale(0.299, 0.587, 0.114)
    if disabled.HasAlpha():
        disabled = disabled.AdjustChannels(1.0, 1.0, 1.0, 0.75)
    return disabled


def getToolbarBitmaps(icon_id: str, size: Tuple[int, int] = (32, 32)) -> Tuple[wx.Bitmap, wx.Bitmap]:
    active = SVGIMG.CreateFromBytes(getToolbarSvgBytes(icon_id)).ConvertToScaledBitmap(size)
    disabled = wx.Bitmap(_make_disabled_image(active.ConvertToImage()))
    return active, disabled


def getToolbarBitmap(icon_id: str, size: Tuple[int, int] = (32, 32), enabled: bool = True) -> wx.Bitmap:
    active, disabled = getToolbarBitmaps(icon_id, size)
    return disabled if enabled else active


def getToolbarImages(icon_id: str, size: Tuple[int, int] = (32, 32)) -> Tuple[wx.Image, wx.Image]:
    active_bmp, disabled_bmp = getToolbarBitmaps(icon_id, size)
    return active_bmp.ConvertToImage(), disabled_bmp.ConvertToImage()


def getToolbarImage(icon_id: str, size: Tuple[int, int] = (32, 32), enabled: bool = True) -> wx.Image:
    active, disabled = getToolbarImages(icon_id, size)
    return disabled if enabled else active


def getToolbarIcons(icon_id: str, size: Tuple[int, int] = (32, 32)) -> Tuple[wx.Icon, wx.Icon]:
    active_bmp, disabled_bmp = getToolbarBitmaps(icon_id, size)
    active_icon = wx.Icon()
    active_icon.CopyFromBitmap(active_bmp)
    disabled_icon = wx.Icon()
    disabled_icon.CopyFromBitmap(disabled_bmp)
    return active_icon, disabled_icon


def getToolbarIcon(icon_id: str, size: Tuple[int, int] = (32, 32), enabled: bool = True) -> wx.Icon:
    active_bmp, disabled_bmp = getToolbarBitmaps(icon_id, size)
    icon = wx.Icon()
    icon.CopyFromBitmap(disabled_bmp if enabled else active_bmp)
    return icon


# Compatibility mapping for legacy code paths that expect raw SVG bytes by filename.
toolbarImages = {fname: getToolbarSvgBytes(icon_id) for fname, icon_id in _FILE_TO_ID.items()}
