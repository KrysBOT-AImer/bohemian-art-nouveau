#!/usr/bin/env python3
"""Pure-Python ASAR patcher for dynamic Linux titleBarOverlay support in Antigravity 2."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import struct
import sys
import tempfile
from typing import Any

DEFAULT_ASAR_PATH = Path("/opt/Antigravity/resources/app.asar")
DEFAULT_HOOK_PATH = Path("/etc/pacman.d/hooks/antigravity-titlebar-overlay.hook")
DEFAULT_SCRIPT_INSTALL_PATH = Path(
    "/usr/local/libexec/antigravity-patch-titlebar-overlay.py"
)

PATCH_MARKER = "/* AGY_LINUX_TITLEBAR_OVERLAY_PATCH_V3 */"
LEGACY_PATCH_MARKER_V2 = "/* AGY_LINUX_TITLEBAR_OVERLAY_PATCH_V2 */"
LEGACY_PATCH_MARKER_V1 = "/* AGY_LINUX_TITLEBAR_OVERLAY_PATCH_V1 */"
DEFAULT_INTEGRITY_BLOCK_SIZE = 4194304

IPC_HANDLERS_REL_PATH = "dist/ipcHandlers.js"
UTILS_REL_PATH = "dist/utils.js"

IPC_HANDLERS_ANCHOR = """\
    electron_1.ipcMain.handle('window:set-title-bar-overlay', async (event, options) => {
        const win = getTargetHubWindow(event?.sender);
        if (win && process.platform === 'win32') {
            win.setTitleBarOverlay({
                color: options.color,
                symbolColor: options.symbolColor,
                height: 30,
            });
        }
    });"""

IPC_HANDLERS_V1_REPLACEMENT = f"""\
    electron_1.ipcMain.handle('window:set-title-bar-overlay', async (event, options) => {{
        {LEGACY_PATCH_MARKER_V1}
        const win = getTargetHubWindow(event?.sender);
        const normalizeOverlayColor = (val) => {{
            if (typeof val !== 'string') {{
                return undefined;
            }}
            const trimmed = val.trim();
            if (/^#[0-9a-fA-F]{{6}}$/.test(trimmed)) {{
                return trimmed.toUpperCase();
            }}
            const shortHex = /^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$/.exec(trimmed);
            if (shortHex) {{
                return `#${{shortHex[1]}}${{shortHex[1]}}${{shortHex[2]}}${{shortHex[2]}}${{shortHex[3]}}${{shortHex[3]}}`.toUpperCase();
            }}
            const rgbMatch = /^rgba?\\(\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*[,\\s]\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*[,\\s]\\s*([+-]?\\d+(?:\\.\\d+)?)(?:\\s*[,/]\\s*([+-]?\\d*(?:\\.\\d+)?%?))?\\s*\\)$/i.exec(trimmed);
            if (rgbMatch) {{
                const toHex = (n) => Math.max(0, Math.min(255, Math.round(Number(n))))
                    .toString(16)
                    .padStart(2, '0')
                    .toUpperCase();
                return `#${{toHex(rgbMatch[1])}}${{toHex(rgbMatch[2])}}${{toHex(rgbMatch[3])}}`;
            }}
            return (0, utils_1.normalizeHexSurfaceColor)(trimmed);
        }};
        if (win && (process.platform === 'win32' || process.platform === 'linux') && options && typeof options === 'object') {{
            const overlayColor = normalizeOverlayColor(options.color);
            const overlaySymbolColor = normalizeOverlayColor(options.symbolColor);
            const resolvedColor = overlayColor ?? options.color;
            if (typeof win.setTitleBarOverlay === 'function' && typeof resolvedColor === 'string' && resolvedColor.trim().length > 0) {{
                try {{
                    win.setTitleBarOverlay({{
                        color: resolvedColor,
                        symbolColor: overlaySymbolColor ?? options.symbolColor,
                        height: 30,
                    }});
                }}
                catch {{
                    // Ignore platforms or windows without titleBarOverlay support.
                }}
            }}
            const updates = {{}};
            if (overlayColor) {{
                updates.titleBarOverlayColor = overlayColor;
            }}
            if (overlaySymbolColor) {{
                updates.titleBarOverlaySymbolColor = overlaySymbolColor;
            }}
            if (Object.keys(updates).length > 0) {{
                const surfaceColor = (0, utils_1.normalizeHexSurfaceColor)((0, utils_1.getHubCurtainColor)(win));
                if (surfaceColor) {{
                    updates.titleBarOverlaySurfaceColor = surfaceColor;
                }}
                await Promise.resolve(storageManager?.updateItems(updates)).catch(() => undefined);
            }}
        }}
    }});"""

IPC_HANDLERS_V2_REPLACEMENT = f"""\
    electron_1.ipcMain.handle('window:set-title-bar-overlay', async (event, options) => {{
        {LEGACY_PATCH_MARKER_V2}
        const win = getTargetHubWindow(event?.sender);
        if (win && process.platform === 'win32') {{
            win.setTitleBarOverlay({{
                color: options.color,
                symbolColor: options.symbolColor,
                height: 30,
            }});
        }}
        else if (win && process.platform === 'linux' && options && typeof options === 'object') {{
            const normalizeOverlayColor = (val) => {{
                if (typeof val !== 'string') {{
                    return undefined;
                }}
                const trimmed = val.trim();
                if (/^#[0-9a-fA-F]{{6}}$/.test(trimmed)) {{
                    return trimmed.toUpperCase();
                }}
                const shortHex = /^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$/.exec(trimmed);
                if (shortHex) {{
                    return `#${{shortHex[1]}}${{shortHex[1]}}${{shortHex[2]}}${{shortHex[2]}}${{shortHex[3]}}${{shortHex[3]}}`.toUpperCase();
                }}
                const rgbMatch = /^rgba?\\(\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*[,\\s]\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*[,\\s]\\s*([+-]?\\d+(?:\\.\\d+)?)(?:\\s*[,/]\\s*([+-]?\\d*(?:\\.\\d+)?%?))?\\s*\\)$/i.exec(trimmed);
                if (rgbMatch) {{
                    const toHex = (n) => Math.max(0, Math.min(255, Math.round(Number(n))))
                        .toString(16)
                        .padStart(2, '0')
                        .toUpperCase();
                    return `#${{toHex(rgbMatch[1])}}${{toHex(rgbMatch[2])}}${{toHex(rgbMatch[3])}}`;
                }}
                return (0, utils_1.normalizeHexSurfaceColor)(trimmed);
            }};
            const overlayColor = normalizeOverlayColor(options.color);
            const overlaySymbolColor = normalizeOverlayColor(options.symbolColor);
            const resolvedColor = overlayColor ?? options.color;
            if (typeof win.setTitleBarOverlay === 'function' && typeof resolvedColor === 'string' && resolvedColor.trim().length > 0) {{
                try {{
                    win.setTitleBarOverlay({{
                        color: resolvedColor,
                        symbolColor: overlaySymbolColor ?? options.symbolColor,
                        height: 30,
                    }});
                }}
                catch {{
                    // Ignore platforms or windows without titleBarOverlay support.
                }}
            }}
            const updates = {{}};
            if (overlayColor) {{
                updates.titleBarOverlayColor = overlayColor;
            }}
            if (overlaySymbolColor) {{
                updates.titleBarOverlaySymbolColor = overlaySymbolColor;
            }}
            if (Object.keys(updates).length > 0) {{
                const surfaceColor = (0, utils_1.normalizeHexSurfaceColor)((0, utils_1.getHubCurtainColor)(win));
                if (surfaceColor) {{
                    updates.titleBarOverlaySurfaceColor = surfaceColor;
                }}
                await Promise.resolve(storageManager?.updateItems(updates)).catch(() => undefined);
            }}
        }}
    }});"""

IPC_HANDLERS_REPLACEMENT = f"""\
    electron_1.ipcMain.handle('window:set-title-bar-overlay', async (event, options) => {{
        {PATCH_MARKER}
        const win = getTargetHubWindow(event?.sender);
        if (win && process.platform === 'win32') {{
            win.setTitleBarOverlay({{
                color: options.color,
                symbolColor: options.symbolColor,
                height: 30,
            }});
        }}
        else if (win && process.platform === 'linux' && options && typeof options === 'object') {{
            const normalizeOverlayColor = (val) => {{
                if (typeof val !== 'string') {{
                    return undefined;
                }}
                const trimmed = val.trim();
                if (/^#[0-9a-fA-F]{{6}}$/.test(trimmed)) {{
                    return trimmed.toUpperCase();
                }}
                const shortHex = /^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$/.exec(trimmed);
                if (shortHex) {{
                    return `#${{shortHex[1]}}${{shortHex[1]}}${{shortHex[2]}}${{shortHex[2]}}${{shortHex[3]}}${{shortHex[3]}}`.toUpperCase();
                }}
                const rgbMatch = /^rgba?\\(\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*[,\\s]\\s*([+-]?\\d+(?:\\.\\d+)?)\\s*[,\\s]\\s*([+-]?\\d+(?:\\.\\d+)?)(?:\\s*[,/]\\s*([+-]?\\d*(?:\\.\\d+)?%?))?\\s*\\)$/i.exec(trimmed);
                if (rgbMatch) {{
                    const toHex = (n) => Math.max(0, Math.min(255, Math.round(Number(n))))
                        .toString(16)
                        .padStart(2, '0')
                        .toUpperCase();
                    return `#${{toHex(rgbMatch[1])}}${{toHex(rgbMatch[2])}}${{toHex(rgbMatch[3])}}`;
                }}
                return (0, utils_1.normalizeHexSurfaceColor)(trimmed);
            }};
            const overlayColor = normalizeOverlayColor(options.color);
            const overlaySymbolColor = normalizeOverlayColor(options.symbolColor);
            const resolvedColor = overlayColor ?? options.color;
            if (typeof win.setTitleBarOverlay === 'function' && typeof resolvedColor === 'string' && resolvedColor.trim().length > 0) {{
                try {{
                    win.setTitleBarOverlay({{
                        color: resolvedColor,
                        symbolColor: overlaySymbolColor ?? options.symbolColor,
                        height: 30,
                    }});
                }}
                catch {{
                    // Ignore platforms or windows without titleBarOverlay support.
                }}
            }}
            const updates = {{}};
            if (overlayColor) {{
                updates.titleBarOverlayColor = overlayColor;
            }}
            if (overlaySymbolColor) {{
                updates.titleBarOverlaySymbolColor = overlaySymbolColor;
            }}
            if (Object.keys(updates).length > 0) {{
                const surfaceColor = (0, utils_1.normalizeHexSurfaceColor)((0, utils_1.getHubCurtainColor)(win));
                if (surfaceColor) {{
                    updates.titleBarOverlaySurfaceColor = surfaceColor;
                }}
                await Promise.resolve(storageManager?.updateItems(updates)).catch(() => undefined);
            }}
        }}
    }});"""

UTILS_BLOCK1_ANCHOR = """\
    const theme = getThemeMode().toUpperCase();
    const isLight = theme.includes('LIGHT');
    const backgroundColor = isLight ? '#FAFAFA' : '#131313';
    const foregroundColor = isLight ? '#383A42' : '#FAFAFA';"""

UTILS_BLOCK1_V1_REPLACEMENT = f"""\
    {LEGACY_PATCH_MARKER_V1}
    const theme = getThemeMode().toUpperCase();
    const isLight = theme.includes('LIGHT');
    const backgroundColor = isLight ? '#FAFAFA' : '#131313';
    const foregroundColor = isLight ? '#383A42' : '#FAFAFA';
    let overlayStorageItems = {{}};
    if (typeof storageManager?.getItemsSync === 'function') {{
        try {{
            overlayStorageItems = asRecord(storageManager.getItemsSync()) ?? {{}};
        }}
        catch {{
            overlayStorageItems = {{}};
        }}
    }}
    else {{
        overlayStorageItems = readAppStorageSync();
    }}
    const initialCurtainColor = getHubCurtainColor();
    const storedOverlayColor = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlayColor']);
    const storedOverlaySymbol = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlaySymbolColor']);
    const storedOverlaySurface = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlaySurfaceColor']);
    const surfaceMatches = !storedOverlaySurface || storedOverlaySurface === initialCurtainColor;
    const overlayColor = (storedOverlayColor && surfaceMatches) ? storedOverlayColor : initialCurtainColor;
    const computeContrastSymbolColor = (hexColor) => {{
        if (!/^#[0-9A-Fa-f]{{6}}$/.test(hexColor)) {{
            return foregroundColor;
        }}
        const clean = hexColor.slice(1);
        const toLinear = (offset) => {{
            const c = parseInt(clean.slice(offset, offset + 2), 16) / 255;
            return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        }};
        const lum = 0.2126 * toLinear(0) + 0.7152 * toLinear(2) + 0.0722 * toLinear(4);
        return lum > 0.179 ? '#383A42' : '#FAFAFA';
    }};
    const computedContrastSymbolColor = computeContrastSymbolColor(overlayColor);
    const overlaySymbolColor = (storedOverlaySymbol && surfaceMatches) ? storedOverlaySymbol : computedContrastSymbolColor;"""

UTILS_BLOCK1_V2_REPLACEMENT = f"""\
    {LEGACY_PATCH_MARKER_V2}
    const theme = getThemeMode().toUpperCase();
    const isLight = theme.includes('LIGHT');
    const backgroundColor = isLight ? '#FAFAFA' : '#131313';
    const foregroundColor = isLight ? '#383A42' : '#FAFAFA';
    let overlayColor = backgroundColor;
    let overlaySymbolColor = foregroundColor;
    if (process.platform === 'linux') {{
        let overlayStorageItems = {{}};
        if (typeof storageManager?.getItemsSync === 'function') {{
            try {{
                overlayStorageItems = asRecord(storageManager.getItemsSync()) ?? {{}};
            }}
            catch {{
                overlayStorageItems = {{}};
            }}
        }}
        else {{
            overlayStorageItems = readAppStorageSync();
        }}
        const initialCurtainColor = getHubCurtainColor();
        const storedOverlayColor = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlayColor']);
        const storedOverlaySymbol = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlaySymbolColor']);
        const storedOverlaySurface = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlaySurfaceColor']);
        const surfaceMatches = !storedOverlaySurface || storedOverlaySurface === initialCurtainColor;
        overlayColor = (storedOverlayColor && surfaceMatches) ? storedOverlayColor : initialCurtainColor;
        const computeContrastSymbolColor = (hexColor) => {{
            if (!/^#[0-9A-Fa-f]{{6}}$/.test(hexColor)) {{
                return foregroundColor;
            }}
            const clean = hexColor.slice(1);
            const toLinear = (offset) => {{
                const c = parseInt(clean.slice(offset, offset + 2), 16) / 255;
                return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
            }};
            const lum = 0.2126 * toLinear(0) + 0.7152 * toLinear(2) + 0.0722 * toLinear(4);
            return lum > 0.179 ? '#383A42' : '#FAFAFA';
        }};
        const computedContrastSymbolColor = computeContrastSymbolColor(overlayColor);
        overlaySymbolColor = (storedOverlaySymbol && surfaceMatches) ? storedOverlaySymbol : computedContrastSymbolColor;
    }}"""

UTILS_BLOCK1_REPLACEMENT = f"""\
    {PATCH_MARKER}
    const theme = getThemeMode().toUpperCase();
    const isLight = theme.includes('LIGHT');
    const backgroundColor = isLight ? '#FAFAFA' : '#131313';
    const foregroundColor = isLight ? '#383A42' : '#FAFAFA';
    let overlayColor = backgroundColor;
    let overlaySymbolColor = foregroundColor;
    if (process.platform === 'linux') {{
        let overlayStorageItems = {{}};
        if (typeof storageManager?.getItemsSync === 'function') {{
            try {{
                overlayStorageItems = asRecord(storageManager.getItemsSync()) ?? {{}};
            }}
            catch {{
                overlayStorageItems = {{}};
            }}
        }}
        else {{
            overlayStorageItems = readAppStorageSync();
        }}
        const fallbackSurfaceColor = isLight ? '#F3EFE8' : '#162B37';
        const fallbackOverlayColor = isLight ? '#F0E7D8' : '#193341';
        const fallbackSymbolColor = isLight ? '#162B37' : '#EFE4D2';
        const rawCurtainColor = normalizeHexSurfaceColor(getHubCurtainColor());
        const initialCurtainColor = rawCurtainColor ?? fallbackSurfaceColor;
        const storedOverlayColor = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlayColor']);
        const storedOverlaySymbol = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlaySymbolColor']);
        const storedOverlaySurface = normalizeHexSurfaceColor(overlayStorageItems['titleBarOverlaySurfaceColor']);
        const surfaceMatches = !storedOverlaySurface || storedOverlaySurface === initialCurtainColor;
        overlayColor = (storedOverlayColor && surfaceMatches) ? storedOverlayColor : (rawCurtainColor ?? fallbackOverlayColor);
        const computeContrastSymbolColor = (hexColor) => {{
            if (!/^#[0-9A-Fa-f]{{6}}$/.test(hexColor)) {{
                return fallbackSymbolColor;
            }}
            const clean = hexColor.slice(1);
            const toLinear = (offset) => {{
                const c = parseInt(clean.slice(offset, offset + 2), 16) / 255;
                return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
            }};
            const lum = 0.2126 * toLinear(0) + 0.7152 * toLinear(2) + 0.0722 * toLinear(4);
            return lum > 0.179 ? '#162B37' : '#EFE4D2';
        }};
        const computedContrastSymbolColor = computeContrastSymbolColor(overlayColor);
        overlaySymbolColor = (storedOverlaySymbol && surfaceMatches) ? storedOverlaySymbol : computedContrastSymbolColor;
    }}"""

UTILS_BLOCK2_ANCHOR = """\
        titleBarStyle: 'hidden',
        titleBarOverlay: isMacOS()
            ? false
            : {
                color: backgroundColor,
                symbolColor: foregroundColor,
                height: 30,
            },
        backgroundColor,"""

UTILS_BLOCK2_REPLACEMENT = """\
        titleBarStyle: 'hidden',
        titleBarOverlay: isMacOS()
            ? false
            : {
                color: overlayColor,
                symbolColor: overlaySymbolColor,
                height: 30,
            },
        backgroundColor,"""

UTILS_BLOCK2_V2_REPLACEMENT = UTILS_BLOCK2_REPLACEMENT
UTILS_BLOCK2_V1_REPLACEMENT = UTILS_BLOCK2_REPLACEMENT


class AsarError(RuntimeError):
    """Raised when an ASAR archive is malformed, corrupted, or missing entries."""


def _normalize_rel_path(rel_path: str) -> list[str]:
    """Split and validate a relative POSIX path inside an ASAR archive."""
    cleaned = rel_path.replace("\\", "/").strip("/")
    if not cleaned:
        raise AsarError("ASAR entry path must not be empty")
    parts = cleaned.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise AsarError(f"Invalid ASAR entry path: {rel_path!r}")
    return parts


def _lookup_asar_node(header: Mapping[str, Any], rel_path: str) -> dict[str, Any]:
    """Traverse the nested ASAR JSON header tree and return the target node."""
    parts = _normalize_rel_path(rel_path)
    current: Any = header
    for part in parts:
        if not isinstance(current, Mapping):
            raise AsarError(f"ASAR entry not found: {rel_path}")
        files = current.get("files")
        if not isinstance(files, Mapping) or part not in files:
            raise AsarError(f"ASAR entry not found: {rel_path}")
        current = files[part]
    if not isinstance(current, dict):
        raise AsarError(f"Invalid ASAR node for {rel_path}")
    return current


def _iter_asar_nodes(
    tree: Mapping[str, Any], prefix: str = ""
) -> list[tuple[str, dict[str, Any]]]:
    """Flatten all non-directory entries in an ASAR header tree."""
    files = tree.get("files")
    if not isinstance(files, Mapping):
        raise AsarError("ASAR directory node missing 'files' object")
    items: list[tuple[str, dict[str, Any]]] = []
    for name, node in files.items():
        if not isinstance(name, str) or not isinstance(node, dict):
            raise AsarError(f"Invalid ASAR node under {prefix or '/'}")
        rel_path = f"{prefix}/{name}" if prefix else name
        if "files" in node:
            items.extend(_iter_asar_nodes(node, rel_path))
        else:
            items.append((rel_path, node))
    return items


def read_asar_header(asar_path: Path) -> tuple[dict[str, Any], int]:
    """Read and validate the Chromium Pickle JSON header from an ASAR archive."""
    try:
        file_size = asar_path.stat().st_size
    except OSError as exc:
        raise AsarError(f"Unable to stat ASAR archive {asar_path}: {exc}") from exc

    if file_size < 16:
        raise AsarError(
            f"ASAR archive {asar_path} is too small ({file_size} bytes)"
        )

    with asar_path.open("rb") as handle:
        prefix = handle.read(16)
        if len(prefix) != 16:
            raise AsarError(f"Truncated ASAR header prefix in {asar_path}")
        u0, u1, u2, u3 = struct.unpack("<4I", prefix)
        if u0 != 4:
            raise AsarError(f"Invalid ASAR pickle outer size u32[0]={u0} (expected 4)")

        pad = (4 - (u3 % 4)) % 4
        expected_u2 = 4 + u3 + pad
        expected_u1 = 8 + u3 + pad
        if u2 != expected_u2 or u1 != expected_u1:
            raise AsarError(
                "Invalid ASAR pickle header lengths: "
                f"u32[1]={u1} (expected {expected_u1}), "
                f"u32[2]={u2} (expected {expected_u2}), u32[3]={u3}"
            )

        data_start = 8 + u1
        if data_start > file_size:
            raise AsarError(
                f"ASAR header end {data_start} exceeds file size {file_size}"
            )

        raw_json = handle.read(u3)
        if len(raw_json) != u3:
            raise AsarError(f"Truncated ASAR JSON header in {asar_path}")

    try:
        header = json.loads(raw_json.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AsarError(f"Corrupt ASAR JSON header in {asar_path}: {exc}") from exc

    if not isinstance(header, dict) or not isinstance(header.get("files"), dict):
        raise AsarError(f"ASAR JSON header in {asar_path} lacks root 'files' dict")

    return header, data_start


def read_asar_file(asar_path: Path, rel_path: str) -> bytes:
    """Read a packed file's raw bytes from an ASAR archive."""
    header, data_start = read_asar_header(asar_path)
    node = _lookup_asar_node(header, rel_path)
    if "files" in node:
        raise AsarError(f"ASAR entry is a directory: {rel_path}")
    if node.get("unpacked"):
        raise AsarError(f"ASAR entry is unpacked: {rel_path}")
    if "offset" not in node or "size" not in node:
        raise AsarError(f"ASAR entry lacks packed offset/size: {rel_path}")

    try:
        offset = int(node["offset"])
        size = int(node["size"])
    except (TypeError, ValueError) as exc:
        raise AsarError(f"Invalid offset/size metadata for {rel_path}") from exc

    if offset < 0 or size < 0:
        raise AsarError(f"Negative offset/size for {rel_path}")

    file_size = asar_path.stat().st_size
    if data_start + offset + size > file_size:
        raise AsarError(
            f"ASAR entry {rel_path} exceeds archive bounds "
            f"({data_start + offset + size} > {file_size})"
        )

    with asar_path.open("rb") as handle:
        handle.seek(data_start + offset)
        data = handle.read(size)
    if len(data) != size:
        raise AsarError(f"Short read for ASAR entry {rel_path}")
    return data


def compute_asar_integrity(
    data: bytes, block_size: int = DEFAULT_INTEGRITY_BLOCK_SIZE
) -> dict[str, Any]:
    """Compute Electron ASAR SHA-256 whole-file and block-level integrity metadata."""
    if block_size <= 0:
        raise ValueError(f"block_size must be positive, got {block_size}")

    file_hash = hashlib.sha256(data).hexdigest()
    if len(data) == 0:
        blocks = [hashlib.sha256(b"").hexdigest()]
    else:
        blocks = [
            hashlib.sha256(data[i : i + block_size]).hexdigest()
            for i in range(0, len(data), block_size)
        ]

    return {
        "algorithm": "SHA256",
        "hash": file_hash,
        "blockSize": block_size,
        "blocks": blocks,
    }


def encode_asar_bytes(header: Mapping[str, Any], payload: bytes) -> bytes:
    """Encode an ASAR header dictionary and packed payload into full archive bytes."""
    header_bytes = json.dumps(
        header, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    length = len(header_bytes)
    pad = (4 - (length % 4)) % 4
    pickle_prefix = struct.pack(
        "<4I", 4, 8 + length + pad, 4 + length + pad, length
    )
    return pickle_prefix + header_bytes + (b"\x00" * pad) + payload


def repack_asar_with_replacements(
    asar_path: Path, replacements: Mapping[str, bytes]
) -> bytes:
    """Rebuild an ASAR archive with updated packed file bytes, offsets, and hashes."""
    header, data_start = read_asar_header(asar_path)
    new_header = copy.deepcopy(header)
    file_size = asar_path.stat().st_size

    normalized_replacements: dict[str, bytes] = {}
    for raw_key, raw_bytes in replacements.items():
        norm_key = "/".join(_normalize_rel_path(raw_key))
        node = _lookup_asar_node(new_header, norm_key)
        if "files" in node:
            raise AsarError(f"Cannot replace directory entry: {norm_key}")
        if node.get("unpacked") or "offset" not in node or "size" not in node:
            raise AsarError(f"Target entry is not a packed file: {norm_key}")
        normalized_replacements[norm_key] = bytes(raw_bytes)

    all_nodes = _iter_asar_nodes(new_header)
    packed_nodes: list[tuple[int, str, dict[str, Any]]] = []
    for rel_path, node in all_nodes:
        if node.get("unpacked") or "offset" not in node:
            continue
        if "size" not in node:
            raise AsarError(f"Packed ASAR entry missing size: {rel_path}")
        try:
            old_offset = int(node["offset"])
            old_size = int(node["size"])
        except (TypeError, ValueError) as exc:
            raise AsarError(f"Invalid offset/size in {rel_path}") from exc
        if old_offset < 0 or old_size < 0:
            raise AsarError(f"Negative offset/size in {rel_path}")
        if data_start + old_offset + old_size > file_size:
            raise AsarError(f"Packed entry {rel_path} out of archive bounds")
        packed_nodes.append((old_offset, rel_path, node))

    packed_nodes.sort(key=lambda item: (item[0], item[1]))

    payload_parts: list[bytes] = []
    current_offset = 0
    with asar_path.open("rb") as handle:
        for old_offset, rel_path, node in packed_nodes:
            if rel_path in normalized_replacements:
                chunk = normalized_replacements[rel_path]
                node["size"] = len(chunk)
                existing_integrity = node.get("integrity")
                if isinstance(existing_integrity, dict):
                    raw_block_size = existing_integrity.get(
                        "blockSize", DEFAULT_INTEGRITY_BLOCK_SIZE
                    )
                    block_size = (
                        int(raw_block_size)
                        if isinstance(raw_block_size, int) and raw_block_size > 0
                        else DEFAULT_INTEGRITY_BLOCK_SIZE
                    )
                    node["integrity"] = compute_asar_integrity(
                        chunk, block_size=block_size
                    )
            else:
                old_size = int(node["size"])
                handle.seek(data_start + old_offset)
                chunk = handle.read(old_size)
                if len(chunk) != old_size:
                    raise AsarError(f"Short read copying packed entry {rel_path}")

            node["offset"] = str(current_offset)
            payload_parts.append(chunk)
            current_offset += len(chunk)

    return encode_asar_bytes(new_header, b"".join(payload_parts))


def verify_asar_integrity(asar_path: Path) -> dict[str, Any]:
    """Validate ASAR Pickle header math, bounds, non-overlap, and SHA-256 hashes."""
    header, data_start = read_asar_header(asar_path)
    file_size = asar_path.stat().st_size
    all_nodes = _iter_asar_nodes(header)

    packed_entries: list[tuple[int, int, str, dict[str, Any]]] = []
    unpacked_count = 0
    link_count = 0
    executable_count = 0

    for rel_path, node in all_nodes:
        if node.get("executable"):
            executable_count += 1
        if "link" in node and "offset" not in node:
            link_count += 1
            continue
        if node.get("unpacked"):
            unpacked_count += 1
            continue
        if "offset" not in node or "size" not in node:
            raise AsarError(f"Packed entry {rel_path} missing offset or size")
        try:
            offset = int(node["offset"])
            size = int(node["size"])
        except (TypeError, ValueError) as exc:
            raise AsarError(f"Invalid offset/size for {rel_path}") from exc
        if offset < 0 or size < 0:
            raise AsarError(f"Negative offset/size for {rel_path}")
        if data_start + offset + size > file_size:
            raise AsarError(
                f"Entry {rel_path} exceeds file bounds "
                f"({data_start + offset + size} > {file_size})"
            )
        packed_entries.append((offset, size, rel_path, node))

    packed_entries.sort(key=lambda item: (item[0], item[0] + item[1], item[2]))

    prev_end = 0
    verified_integrity = 0
    with asar_path.open("rb") as handle:
        for offset, size, rel_path, node in packed_entries:
            if offset < prev_end:
                raise AsarError(
                    f"Overlapping packed ASAR entry {rel_path}: "
                    f"offset {offset} < previous end {prev_end}"
                )
            prev_end = offset + size

            integrity = node.get("integrity")
            if integrity is None:
                continue
            if not isinstance(integrity, dict):
                raise AsarError(f"Invalid integrity metadata for {rel_path}")
            if integrity.get("algorithm") != "SHA256":
                raise AsarError(
                    f"Unsupported integrity algorithm for {rel_path}: "
                    f"{integrity.get('algorithm')!r}"
                )
            block_size = integrity.get("blockSize")
            expected_hash = integrity.get("hash")
            expected_blocks = integrity.get("blocks")
            if (
                not isinstance(block_size, int)
                or block_size <= 0
                or not isinstance(expected_hash, str)
                or not isinstance(expected_blocks, list)
                or not all(isinstance(b, str) for b in expected_blocks)
            ):
                raise AsarError(f"Malformed integrity fields for {rel_path}")

            handle.seek(data_start + offset)
            data = handle.read(size)
            if len(data) != size:
                raise AsarError(f"Short read verifying {rel_path}")

            actual = compute_asar_integrity(data, block_size=block_size)
            if actual["hash"] != expected_hash.lower():
                raise AsarError(
                    f"SHA-256 hash mismatch for {rel_path}: "
                    f"expected {expected_hash}, got {actual['hash']}"
                )
            if actual["blocks"] != [b.lower() for b in expected_blocks]:
                raise AsarError(f"SHA-256 block hash mismatch for {rel_path}")
            verified_integrity += 1

    return {
        "valid": True,
        "file_size": file_size,
        "data_start": data_start,
        "packed_files": len(packed_entries),
        "unpacked_files": unpacked_count,
        "verified_integrity_files": verified_integrity,
        "link_files": link_count,
        "executable_files": executable_count,
    }


def _classify_ipc_handlers(text: str) -> str:
    """Classify dist/ipcHandlers.js patch state."""
    if PATCH_MARKER in text:
        return "patched"
    if text.count(IPC_HANDLERS_V2_REPLACEMENT) == 1:
        return "patched_v2"
    if text.count(IPC_HANDLERS_V1_REPLACEMENT) == 1:
        return "patched_v1"
    if text.count(IPC_HANDLERS_ANCHOR) == 1:
        return "unpatched"
    return "incompatible"


def _classify_utils(text: str) -> str:
    """Classify dist/utils.js patch state."""
    if PATCH_MARKER in text:
        return "patched"
    if (
        text.count(UTILS_BLOCK1_V2_REPLACEMENT) == 1
        and text.count(UTILS_BLOCK2_V2_REPLACEMENT) == 1
    ):
        return "patched_v2"
    if (
        text.count(UTILS_BLOCK1_V1_REPLACEMENT) == 1
        and text.count(UTILS_BLOCK2_V1_REPLACEMENT) == 1
    ):
        return "patched_v1"
    if (
        text.count(UTILS_BLOCK1_ANCHOR) == 1
        and text.count(UTILS_BLOCK2_ANCHOR) == 1
    ):
        return "unpatched"
    return "incompatible"


def patch_ipc_handlers_js(text: str) -> str:
    """Apply or upgrade the titleBarOverlay patch in dist/ipcHandlers.js text."""
    state = _classify_ipc_handlers(text)
    if state == "patched":
        return text
    if state == "unpatched":
        return text.replace(IPC_HANDLERS_ANCHOR, IPC_HANDLERS_REPLACEMENT, 1)
    if state == "patched_v2":
        return text.replace(
            IPC_HANDLERS_V2_REPLACEMENT, IPC_HANDLERS_REPLACEMENT, 1
        )
    if state == "patched_v1":
        return text.replace(
            IPC_HANDLERS_V1_REPLACEMENT, IPC_HANDLERS_REPLACEMENT, 1
        )
    raise AsarError(
        f"Incompatible {IPC_HANDLERS_REL_PATH}: expected 1 anchor, V1, or V2 match, "
        f"found anchor={text.count(IPC_HANDLERS_ANCHOR)}"
    )


def patch_utils_js(text: str) -> str:
    """Apply or upgrade the titleBarOverlay startup patch in dist/utils.js text."""
    state = _classify_utils(text)
    if state == "patched":
        return text
    if state == "unpatched":
        patched = text.replace(UTILS_BLOCK1_ANCHOR, UTILS_BLOCK1_REPLACEMENT, 1)
        return patched.replace(UTILS_BLOCK2_ANCHOR, UTILS_BLOCK2_REPLACEMENT, 1)
    if state == "patched_v2":
        patched = text.replace(
            UTILS_BLOCK1_V2_REPLACEMENT, UTILS_BLOCK1_REPLACEMENT, 1
        )
        return patched.replace(
            UTILS_BLOCK2_V2_REPLACEMENT, UTILS_BLOCK2_REPLACEMENT, 1
        )
    if state == "patched_v1":
        patched = text.replace(
            UTILS_BLOCK1_V1_REPLACEMENT, UTILS_BLOCK1_REPLACEMENT, 1
        )
        return patched.replace(
            UTILS_BLOCK2_V1_REPLACEMENT, UTILS_BLOCK2_REPLACEMENT, 1
        )
    raise AsarError(
        f"Incompatible {UTILS_REL_PATH}: block1={text.count(UTILS_BLOCK1_ANCHOR)}, "
        f"block2={text.count(UTILS_BLOCK2_ANCHOR)}"
    )


def check_asar(asar_path: Path) -> dict[str, Any]:
    """Inspect an ASAR archive and report patch compatibility and status."""
    if not asar_path.is_file():
        return {
            "status": "incompatible",
            "asar_path": str(asar_path),
            "exists": False,
            "files": {},
            "integrity": None,
            "error": f"ASAR file not found: {asar_path}",
        }

    try:
        integrity = verify_asar_integrity(asar_path)
        ipc_text = read_asar_file(asar_path, IPC_HANDLERS_REL_PATH).decode("utf-8")
        utils_text = read_asar_file(asar_path, UTILS_REL_PATH).decode("utf-8")
    except (OSError, AsarError, UnicodeDecodeError) as exc:
        return {
            "status": "incompatible",
            "asar_path": str(asar_path),
            "exists": True,
            "files": {},
            "integrity": None,
            "error": str(exc),
        }

    ipc_state = _classify_ipc_handlers(ipc_text)
    utils_state = _classify_utils(utils_text)
    files_state = {
        IPC_HANDLERS_REL_PATH: ipc_state,
        UTILS_REL_PATH: utils_state,
    }

    if ipc_state == "patched" and utils_state == "patched":
        overall = "patched"
    elif ipc_state == "unpatched" and utils_state == "unpatched":
        overall = "unpatched"
    elif ipc_state == "patched_v2" and utils_state == "patched_v2":
        overall = "outdated_v2"
    elif ipc_state == "patched_v1" and utils_state == "patched_v1":
        overall = "outdated_v1"
    elif any(
        s in ("patched", "patched_v2", "patched_v1")
        for s in (ipc_state, utils_state)
    ):
        overall = "partially_patched"
    else:
        overall = "incompatible"

    return {
        "status": overall,
        "asar_path": str(asar_path),
        "exists": True,
        "files": files_state,
        "integrity": integrity,
        "error": None,
    }


def atomic_write_bytes(
    path: Path,
    data: bytes,
    *,
    default_mode: int = 0o644,
    mode: int | None = None,
) -> None:
    """Atomically write bytes to path with fsync and POSIX permission handling."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = (
        path.stat().st_mode & 0o777
        if os.name == "posix" and mode is None and path.exists()
        else None
    )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

        if os.name == "posix":
            target_mode = (
                mode
                if mode is not None
                else (existing_mode if existing_mode is not None else default_mode)
            )
            os.chmod(tmp_path, target_mode)
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise


def create_asar_backup(asar_path: Path) -> Path:
    """Create a UTC timestamped atomic .bak copy of asar_path."""
    if not asar_path.is_file():
        raise FileNotFoundError(f"Cannot back up missing ASAR: {asar_path}")
    utc_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = asar_path.with_name(f"{asar_path.name}.{utc_ts}.bak")
    existing_mode = asar_path.stat().st_mode & 0o777 if os.name == "posix" else 0o644
    atomic_write_bytes(
        backup_path, asar_path.read_bytes(), mode=existing_mode
    )
    return backup_path


def find_latest_backup(asar_path: Path) -> Path | None:
    """Return the newest UTC timestamped .bak file for asar_path, or None."""
    if not asar_path.parent.is_dir():
        return None
    backups = sorted(asar_path.parent.glob(f"{asar_path.name}.*.bak"))
    return backups[-1] if backups else None


def apply_patch(asar_path: Path, dry_run: bool = False) -> dict[str, Any]:
    """Dry-run or atomically apply the titleBarOverlay patch to asar_path."""
    check_info = check_asar(asar_path)
    status = check_info["status"]

    if status == "patched":
        return {
            "action": "apply",
            "status": "already_patched",
            "dry_run": dry_run,
            "asar_path": str(asar_path),
            "backup_path": None,
            "changed": False,
            "files": check_info["files"],
        }

    if status not in ("unpatched", "outdated_v1", "outdated_v2"):
        error_msg = check_info.get("error") or (
            f"Cannot apply patch: ASAR status is {status} ({check_info['files']})"
        )
        raise AsarError(error_msg)

    if status == "outdated_v2":
        upgraded_from = "v2"
    elif status == "outdated_v1":
        upgraded_from = "v1"
    else:
        upgraded_from = None

    ipc_text = read_asar_file(asar_path, IPC_HANDLERS_REL_PATH).decode("utf-8")
    utils_text = read_asar_file(asar_path, UTILS_REL_PATH).decode("utf-8")

    patched_ipc = patch_ipc_handlers_js(ipc_text).encode("utf-8")
    patched_utils = patch_utils_js(utils_text).encode("utf-8")

    repacked_bytes = repack_asar_with_replacements(
        asar_path,
        {
            IPC_HANDLERS_REL_PATH: patched_ipc,
            UTILS_REL_PATH: patched_utils,
        },
    )
    new_sha256 = hashlib.sha256(repacked_bytes).hexdigest()

    if dry_run:
        result: dict[str, Any] = {
            "action": "apply",
            "status": "dry_run_ready",
            "dry_run": True,
            "asar_path": str(asar_path),
            "backup_path": None,
            "changed": False,
            "files": check_info["files"],
            "new_size": len(repacked_bytes),
            "new_sha256": new_sha256,
        }
        if upgraded_from is not None:
            result["upgraded_from"] = upgraded_from
        return result

    backup_path = create_asar_backup(asar_path)
    try:
        atomic_write_bytes(asar_path, repacked_bytes, default_mode=0o644)
        integrity = verify_asar_integrity(asar_path)
    except Exception:
        if backup_path.is_file():
            atomic_write_bytes(
                asar_path, backup_path.read_bytes(), default_mode=0o644
            )
        raise

    result = {
        "action": "apply",
        "status": "patched",
        "dry_run": False,
        "asar_path": str(asar_path),
        "backup_path": str(backup_path),
        "changed": True,
        "files": {
            IPC_HANDLERS_REL_PATH: "patched",
            UTILS_REL_PATH: "patched",
        },
        "new_size": len(repacked_bytes),
        "new_sha256": new_sha256,
        "integrity": integrity,
    }
    if upgraded_from is not None:
        result["upgraded_from"] = upgraded_from
    return result


def restore_asar(asar_path: Path, dry_run: bool = False) -> dict[str, Any]:
    """Restore the newest verified .bak archive over asar_path."""
    backup_path = find_latest_backup(asar_path)
    if backup_path is None:
        raise FileNotFoundError(f"No backup found for {asar_path}")

    integrity = verify_asar_integrity(backup_path)
    if dry_run:
        return {
            "action": "restore",
            "status": "dry_run_ready",
            "dry_run": True,
            "asar_path": str(asar_path),
            "backup_path": str(backup_path),
            "restored": False,
            "integrity": integrity,
        }

    atomic_write_bytes(asar_path, backup_path.read_bytes(), default_mode=0o644)
    return {
        "action": "restore",
        "status": "restored",
        "dry_run": False,
        "asar_path": str(asar_path),
        "backup_path": str(backup_path),
        "restored": True,
        "integrity": integrity,
    }


def render_pacman_hook(
    asar_path: Path = DEFAULT_ASAR_PATH,
    script_install_path: Path = DEFAULT_SCRIPT_INSTALL_PATH,
) -> str:
    """Render the pacman PostTransaction hook content."""
    target = asar_path.as_posix().lstrip("/")
    exec_parts = [
        "/usr/bin/python3",
        shlex.quote(str(script_install_path)),
        "--apply",
        "--fail-safe",
    ]
    if asar_path.as_posix() != DEFAULT_ASAR_PATH.as_posix():
        exec_parts.extend(["--asar-path", shlex.quote(str(asar_path))])

    return (
        "[Trigger]\n"
        "Operation = Install\n"
        "Operation = Upgrade\n"
        "Type = Path\n"
        f"Target = {target}\n"
        "\n"
        "[Action]\n"
        "Description = Re-applying Antigravity Linux titleBarOverlay patch...\n"
        "When = PostTransaction\n"
        f"Exec = {' '.join(exec_parts)}\n"
    )


def install_hook(
    asar_path: Path = DEFAULT_ASAR_PATH,
    hook_path: Path = DEFAULT_HOOK_PATH,
    script_install_path: Path = DEFAULT_SCRIPT_INSTALL_PATH,
    dry_run: bool = False,
    source_script: Path | None = None,
) -> dict[str, Any]:
    """Install the patcher script and pacman PostTransaction hook atomically."""
    src = (source_script or Path(__file__)).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source script not found: {src}")

    hook_content = render_pacman_hook(
        asar_path=asar_path,
        script_install_path=script_install_path,
    )

    if not dry_run:
        atomic_write_bytes(script_install_path, src.read_bytes(), mode=0o755)
        atomic_write_bytes(
            hook_path, hook_content.encode("utf-8"), mode=0o644
        )

    return {
        "action": "install-hook",
        "status": "dry_run_ready" if dry_run else "installed",
        "dry_run": dry_run,
        "hook_path": str(hook_path),
        "script_install_path": str(script_install_path),
        "asar_path": str(asar_path),
        "hook_content": hook_content,
    }


def uninstall_hook(
    hook_path: Path = DEFAULT_HOOK_PATH,
    script_install_path: Path = DEFAULT_SCRIPT_INSTALL_PATH,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove the installed pacman hook and helper script idempotently."""
    hook_existed = hook_path.exists()
    script_existed = script_install_path.exists()

    if not dry_run:
        if hook_existed:
            hook_path.unlink()
        if script_existed:
            script_install_path.unlink()

    if not hook_existed and not script_existed:
        status = "already_absent"
    elif dry_run:
        status = "dry_run_ready"
    else:
        status = "uninstalled"

    return {
        "action": "uninstall-hook",
        "status": status,
        "dry_run": dry_run,
        "hook_path": str(hook_path),
        "script_install_path": str(script_install_path),
        "removed_hook": hook_existed and not dry_run,
        "removed_script": script_existed and not dry_run,
    }


def is_linux_platform() -> bool:
    """Return True when running on a Linux host."""
    return sys.platform.startswith("linux")


def _resolve_cli_action(args: argparse.Namespace) -> str:
    """Map parsed CLI flags to the canonical action name."""
    if args.check:
        return "check"
    if args.restore:
        return "restore"
    if args.install_hook:
        return "install-hook"
    if args.uninstall_hook:
        return "uninstall-hook"
    return "apply"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="patch_titlebar_overlay.py",
        description=(
            "Linux-only tool to inspect, dry-run, apply, and restore the dynamic "
            "Linux titleBarOverlay patch in Antigravity 2's app.asar, or manage a "
            "fail-safe pacman PostTransaction hook.\n\n"
            "Non-Linux hosts (Windows/macOS) are refused with 'unsupported_platform' "
            "(exit 1), or 'skipped_non_linux' (exit 0) when --fail-safe is set, "
            "without touching the filesystem.\n\n"
            "Exit codes:\n"
            "  0: Success (patched/already_patched/restored/installed, skipped_non_linux "
            "with --fail-safe, or any non-fatal condition when --fail-safe is set)\n"
            "  1: Unsupported non-Linux platform (unsupported_platform), operational "
            "error, incompatible ASAR, partially_patched, or missing backup "
            "(unless --fail-safe is set)\n"
            "  2: --check reports 'unpatched', 'outdated_v1', or 'outdated_v2' (unless --fail-safe is set)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--check",
        action="store_true",
        help="Read-only check of app.asar patch state (exit 0=patched, 2=unpatched/outdated_v1/outdated_v2, 1=partially_patched/incompatible/unsupported_platform).",
    )
    action.add_argument(
        "--apply",
        action="store_true",
        help="Back up and atomically patch app.asar (idempotent if already patched).",
    )
    action.add_argument(
        "--restore",
        action="store_true",
        help="Verify and restore the newest app.asar.*.bak backup.",
    )
    action.add_argument(
        "--install-hook",
        action="store_true",
        help="Install script to --script-install-path and pacman hook to --hook-path.",
    )
    action.add_argument(
        "--uninstall-hook",
        action="store_true",
        help="Remove installed pacman hook and helper script (idempotent).",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate changes without modifying disk (defaults to dry-run --apply when used alone).",
    )
    parser.add_argument(
        "--asar-path",
        type=Path,
        default=DEFAULT_ASAR_PATH,
        help=f"Path to Antigravity app.asar (default: {DEFAULT_ASAR_PATH}).",
    )
    parser.add_argument(
        "--hook-path",
        type=Path,
        default=DEFAULT_HOOK_PATH,
        help=f"Path to pacman hook file (default: {DEFAULT_HOOK_PATH}).",
    )
    parser.add_argument(
        "--script-install-path",
        type=Path,
        default=DEFAULT_SCRIPT_INSTALL_PATH,
        help=f"Path to installed helper script (default: {DEFAULT_SCRIPT_INSTALL_PATH}).",
    )
    parser.add_argument(
        "--fail-safe",
        action="store_true",
        help="Exit 0 on non-fatal warnings/incompatibilities/missing files (for pacman hooks).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output.",
    )
    return parser


def _emit_output(payload: Mapping[str, Any], as_json: bool, error: bool = False) -> None:
    """Print structured JSON or concise human-readable status output."""
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    stream = sys.stderr if error else sys.stdout
    action = payload.get("action", "status")
    status = payload.get("status", "unknown")
    detail = payload.get("error") or payload.get("backup_path") or payload.get("asar_path") or ""
    suffix = f" ({detail})" if detail else ""
    print(f"[{action}] {status}{suffix}", file=stream)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    has_explicit_action = any(
        (
            args.check,
            args.apply,
            args.restore,
            args.install_hook,
            args.uninstall_hook,
        )
    )
    if not has_explicit_action and not args.dry_run:
        parser.error(
            "one of the arguments --check --dry-run --apply --restore "
            "--install-hook --uninstall-hook is required"
        )

    action_name = _resolve_cli_action(args)

    if not is_linux_platform():
        exit_code = 0 if args.fail_safe else 1
        payload = {
            "action": action_name,
            "status": "skipped_non_linux" if args.fail_safe else "unsupported_platform",
            "platform": sys.platform,
            "dry_run": args.dry_run,
            "asar_path": str(args.asar_path),
            "fail_safe": args.fail_safe,
            "exit_code": exit_code,
            "error": (
                f"patch_titlebar_overlay.py is Linux-only (current platform: {sys.platform}); "
                "Windows natively supports titleBarOverlay and macOS uses native window chrome."
            ),
        }
        _emit_output(payload, args.json, error=(exit_code != 0))
        return exit_code

    exit_code = 0

    try:
        if args.check:
            check_result = check_asar(args.asar_path)
            status = check_result["status"]
            if status == "patched":
                exit_code = 0
            elif status in ("unpatched", "outdated_v1", "outdated_v2"):
                exit_code = 0 if args.fail_safe else 2
            else:
                exit_code = 0 if args.fail_safe else 1
            payload = {
                "action": "check",
                **check_result,
                "fail_safe": args.fail_safe,
                "exit_code": exit_code,
            }
            _emit_output(payload, args.json, error=(exit_code == 1))
            return exit_code

        if args.restore:
            payload = restore_asar(args.asar_path, dry_run=args.dry_run)
        elif args.install_hook:
            payload = install_hook(
                asar_path=args.asar_path,
                hook_path=args.hook_path,
                script_install_path=args.script_install_path,
                dry_run=args.dry_run,
            )
        elif args.uninstall_hook:
            payload = uninstall_hook(
                hook_path=args.hook_path,
                script_install_path=args.script_install_path,
                dry_run=args.dry_run,
            )
        else:
            payload = apply_patch(args.asar_path, dry_run=args.dry_run)

        payload["fail_safe"] = args.fail_safe
        payload["exit_code"] = 0
        _emit_output(payload, args.json, error=False)
        return 0

    except (AsarError, OSError, ValueError, FileNotFoundError) as exc:
        exit_code = 0 if args.fail_safe else 1
        payload = {
            "action": action_name,
            "status": "warning" if args.fail_safe else "error",
            "dry_run": args.dry_run,
            "asar_path": str(args.asar_path),
            "fail_safe": args.fail_safe,
            "exit_code": exit_code,
            "error": str(exc),
        }
        _emit_output(payload, args.json, error=(exit_code != 0))
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
