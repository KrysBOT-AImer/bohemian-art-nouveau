#!/usr/bin/env python3
"""Cross-platform installer and theme applier for Bohemian Art Nouveau (Antigravity 2)."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

PLUGIN_SLUG = "bohemian-art-nouveau"
DEFAULT_PRESET = "Gruvbox Material"
RUNTIME_PLUGIN_FILES = (
    "plugin.json",
    "README.md",
    "LICENSE",
    "assets/logo.svg",
    "themes/bohemian-art-nouveau-light.json",
    "themes/bohemian-art-nouveau-dark.json",
)


class AntigravityRunningError(RuntimeError):
    """Raised when Antigravity 2 is running and a mutation requires it closed."""


def get_default_config_path(home: Path | None = None) -> Path:
    """Return the default Antigravity 2 config.json path."""
    return (home or Path.home()) / ".gemini" / "config" / "config.json"


def get_default_plugins_dir(home: Path | None = None) -> Path:
    """Return the default Antigravity 2 plugins directory."""
    return (home or Path.home()) / ".gemini" / "config" / "plugins"


def get_default_storage_path(
    platform: str | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return the platform-appropriate Antigravity app_storage.json path."""
    plat = (platform or sys.platform).lower()
    environ = env if env is not None else os.environ
    base_home = home or Path.home()

    if plat.startswith("win"):
        appdata = environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Antigravity" / "app_storage.json"
        return base_home / "AppData" / "Roaming" / "Antigravity" / "app_storage.json"

    if plat == "darwin":
        return (
            base_home
            / "Library"
            / "Application Support"
            / "Antigravity"
            / "app_storage.json"
        )

    xdg_config = environ.get("XDG_CONFIG_HOME")
    base_config = Path(xdg_config) if xdg_config else base_home / ".config"
    return base_config / "Antigravity" / "app_storage.json"


def _detect_windows_antigravity() -> list[str]:
    """Detect running Antigravity processes on Windows via tasklist."""
    try:
        proc = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return []

    if proc.returncode != 0 or not proc.stdout:
        return []

    matches: list[str] = []
    reader = csv.reader(io.StringIO(proc.stdout))
    for row in reader:
        if not row:
            continue
        image_name = row[0].strip()
        image_lower = image_name.lower()
        if image_lower.startswith("antigravity") or image_lower.startswith(
            "language_server"
        ):
            pid = row[1].strip() if len(row) > 1 else ""
            matches.append(f"{pid}:{image_name}" if pid else image_name)
    return matches


def _detect_linux_antigravity(proc_root: Path) -> list[str]:
    """Detect running Antigravity processes on Linux via /proc."""
    if not proc_root.is_dir():
        return []

    self_pid = os.getpid()
    parent_pid = os.getppid()
    matches: list[str] = []

    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return []

    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in (self_pid, parent_pid):
            continue

        try:
            comm = (entry / "comm").read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            comm = ""

        try:
            raw_cmdline = (entry / "cmdline").read_bytes()
        except OSError:
            raw_cmdline = b""

        if not comm and not raw_cmdline:
            continue

        cmdline_parts = [
            part
            for part in raw_cmdline.decode("utf-8", errors="replace").split("\x00")
            if part
        ]
        cmdline_str = " ".join(cmdline_parts)
        if "apply_theme.py" in cmdline_str or "test_theme.py" in cmdline_str:
            continue

        argv0_name = Path(cmdline_parts[0]).name.lower() if cmdline_parts else ""
        comm_lower = comm.lower()
        cmdline_lower = cmdline_str.lower()

        is_antigravity_bin = comm_lower in (
            "antigravity",
            "antigravity-2",
        ) or argv0_name in ("antigravity", "antigravity-2")
        is_lang_server = (
            comm_lower.startswith("language_server")
            or argv0_name.startswith("language_server")
        ) and (
            "/antigravity/" in cmdline_lower
            or "antigravity" in cmdline_lower
            or comm_lower.startswith("language_server")
        )

        if is_antigravity_bin or is_lang_server:
            label = comm or argv0_name
            matches.append(f"{pid}:{label}")

    return matches


def detect_running_antigravity(
    platform: str | None = None,
    proc_root: Path = Path("/proc"),
) -> list[str]:
    """Return a list of running Antigravity 2 process identifiers, if any."""
    plat = (platform or sys.platform).lower()
    if plat.startswith("win"):
        return _detect_windows_antigravity()
    if proc_root.is_dir():
        return _detect_linux_antigravity(proc_root)
    return []


def _extract_seed_value(raw_seeds: Mapping[str, Any], *keys: str) -> str:
    """Return the first present string value for candidate seed keys."""
    for key in keys:
        value = raw_seeds.get(key)
        if isinstance(value, str) and value:
            return value
    raise KeyError(f"Missing required theme seed key: {' / '.join(keys)}")


def load_theme_seeds(bundle_dir: Path) -> dict[str, dict[str, str]]:
    """Load light and dark theme JSONs and map them to config.json CustomThemeSeeds."""
    mapped: dict[str, dict[str, str]] = {}
    for mode in ("light", "dark"):
        theme_path = bundle_dir / "themes" / f"{PLUGIN_SLUG}-{mode}.json"
        data = json.loads(theme_path.read_text(encoding="utf-8"))
        raw_seeds = data["seeds"] if isinstance(data.get("seeds"), dict) else data
        mapped[mode] = {
            "background": _extract_seed_value(raw_seeds, "background"),
            "primary": _extract_seed_value(raw_seeds, "primary"),
            "foregroundOverride": _extract_seed_value(raw_seeds, "foreground"),
            "primaryForegroundOverride": _extract_seed_value(
                raw_seeds, "primary_foreground", "primaryForeground"
            ),
            "codeForegroundOverride": _extract_seed_value(
                raw_seeds, "code_foreground", "codeForeground"
            ),
        }
    return mapped


def atomic_write_json(
    path: Path,
    data: dict[str, Any],
    preserve_mode_0600: bool = False,
) -> None:
    """Atomically write JSON with UTF-8 encoding and optional POSIX 0600 permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = (
        path.stat().st_mode & 0o777 if os.name == "posix" and path.exists() else None
    )
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        if os.name == "posix" and (existing_mode is not None or preserve_mode_0600):
            os.chmod(
                tmp_path, existing_mode if existing_mode is not None else 0o600
            )
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise


def _atomic_copy_file(
    src: Path,
    dest: Path,
    preserve_mode_0600: bool = False,
) -> None:
    """Atomically copy a file into dest via a temp file in dest.parent."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing_mode = (
        dest.stat().st_mode & 0o777 if os.name == "posix" and dest.exists() else None
    )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(dest.parent),
            prefix=f".{dest.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(src.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "posix" and (existing_mode is not None or preserve_mode_0600):
            os.chmod(
                tmp_path, existing_mode if existing_mode is not None else 0o600
            )
        os.replace(tmp_path, dest)
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise


def create_backup(path: Path, preserve_mode_0600: bool = False) -> Path | None:
    """Create a UTC timestamped .bak copy of path if it exists."""
    if not path.exists():
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.{ts}.bak")
    shutil.copy2(path, backup)
    if os.name == "posix" and preserve_mode_0600:
        os.chmod(backup, 0o600)
    return backup


def find_latest_backup(path: Path) -> Path | None:
    """Return the most recent timestamped .bak file for path, or None."""
    if not path.parent.is_dir():
        return None
    backups = sorted(path.parent.glob(f"{path.name}.*.bak"))
    return backups[-1] if backups else None


def install_plugin(
    bundle_dir: Path,
    plugins_dir: Path,
    dry_run: bool = False,
) -> Path:
    """Install only the runtime plugin files into plugins_dir / PLUGIN_SLUG."""
    missing = [
        rel for rel in RUNTIME_PLUGIN_FILES if not (bundle_dir / rel).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"Missing required plugin bundle files in {bundle_dir}: {', '.join(missing)}"
        )

    dest = plugins_dir / PLUGIN_SLUG
    if not dry_run:
        for rel in RUNTIME_PLUGIN_FILES:
            src = bundle_dir / rel
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
    return dest


def uninstall_plugin(plugins_dir: Path, dry_run: bool = False) -> bool:
    """Remove the installed plugin directory if it exists."""
    dest = plugins_dir / PLUGIN_SLUG
    if not dest.exists():
        return False
    if not dry_run:
        shutil.rmtree(dest)
    return True


def _ensure_antigravity_stopped(check_running: bool, dry_run: bool) -> None:
    """Raise AntigravityRunningError if Antigravity 2 is running during a live edit."""
    if not check_running or dry_run:
        return
    running = detect_running_antigravity()
    if running:
        procs = ", ".join(running)
        raise AntigravityRunningError(
            "Antigravity 2 appears to be running "
            f"({procs}). Close Antigravity 2 before modifying config.json or "
            "app_storage.json (or use --install-plugin, which is safe while open)."
        )


def _read_json_dict(path: Path) -> dict[str, Any]:
    """Read a JSON object from path, or return an empty dict if missing."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def apply_theme(
    bundle_dir: Path,
    config_path: Path,
    storage_path: Path,
    plugins_dir: Path,
    mode: str = "both",
    preset: str = DEFAULT_PRESET,
    dry_run: bool = False,
    check_running: bool = True,
) -> dict[str, Any]:
    """Install plugin files and apply Bohemian Art Nouveau seeds + preset safely."""
    if mode not in ("light", "dark", "both"):
        raise ValueError(f"Unsupported mode: {mode}")

    _ensure_antigravity_stopped(check_running=check_running, dry_run=dry_run)

    seeds = load_theme_seeds(bundle_dir)
    plugin_dir = install_plugin(bundle_dir, plugins_dir, dry_run=dry_run)

    config_data = _read_json_dict(config_path)
    user_settings = config_data.get("userSettings")
    if not isinstance(user_settings, dict):
        user_settings = {}
        config_data["userSettings"] = user_settings

    apply_light = mode in ("light", "both")
    apply_dark = mode in ("dark", "both")

    if apply_light:
        user_settings["customThemeSeedsLight"] = seeds["light"]
    if apply_dark:
        user_settings["customThemeSeedsDark"] = seeds["dark"]

    storage_data = _read_json_dict(storage_path)
    if apply_light:
        storage_data["theme-preset-light"] = preset
    if apply_dark:
        storage_data["theme-preset-dark"] = preset

    theme_mode = user_settings.get("themeMode")
    if theme_mode == "THEME_MODE_LIGHT" and apply_light:
        storage_data["hubSurfaceBackgroundColor"] = seeds["light"]["background"]
    elif apply_dark:
        storage_data["hubSurfaceBackgroundColor"] = seeds["dark"]["background"]
    elif apply_light:
        storage_data["hubSurfaceBackgroundColor"] = seeds["light"]["background"]

    config_backup: Path | None = None
    storage_backup: Path | None = None
    if not dry_run:
        config_backup = create_backup(config_path, preserve_mode_0600=True)
        storage_backup = create_backup(storage_path, preserve_mode_0600=False)
        atomic_write_json(config_path, config_data, preserve_mode_0600=True)
        atomic_write_json(storage_path, storage_data, preserve_mode_0600=False)

    return {
        "dry_run": dry_run,
        "plugin_dir": str(plugin_dir),
        "config_path": str(config_path),
        "storage_path": str(storage_path),
        "config_backup": str(config_backup) if config_backup else None,
        "storage_backup": str(storage_backup) if storage_backup else None,
        "modes": ["light", "dark"] if mode == "both" else [mode],
        "preset": preset,
    }


def restore_theme(
    config_path: Path,
    storage_path: Path,
    dry_run: bool = False,
    check_running: bool = True,
) -> dict[str, Any]:
    """Restore the most recent backups of config.json and app_storage.json."""
    _ensure_antigravity_stopped(check_running=check_running, dry_run=dry_run)

    config_backup = find_latest_backup(config_path)
    storage_backup = find_latest_backup(storage_path)
    if config_backup is None and storage_backup is None:
        raise FileNotFoundError(
            f"No backups found for {config_path} or {storage_path}"
        )

    if not dry_run:
        if config_backup is not None:
            _atomic_copy_file(config_backup, config_path, preserve_mode_0600=True)
        if storage_backup is not None:
            _atomic_copy_file(storage_backup, storage_path, preserve_mode_0600=False)

    return {
        "dry_run": dry_run,
        "config_backup": str(config_backup) if config_backup else None,
        "storage_backup": str(storage_backup) if storage_backup else None,
        "restored_config": config_backup is not None,
        "restored_storage": storage_backup is not None,
    }


def uninstall_theme(
    config_path: Path,
    storage_path: Path,
    plugins_dir: Path,
    dry_run: bool = False,
    check_running: bool = True,
) -> dict[str, Any]:
    """Remove the plugin directory and reset custom theme seeds and presets."""
    _ensure_antigravity_stopped(check_running=check_running, dry_run=dry_run)

    plugin_removed = uninstall_plugin(plugins_dir, dry_run=dry_run)
    config_backup: Path | None = None
    storage_backup: Path | None = None
    config_updated = False
    storage_updated = False

    if config_path.exists():
        config_data = _read_json_dict(config_path)
        user_settings = config_data.get("userSettings")
        if not isinstance(user_settings, dict):
            user_settings = {}
            config_data["userSettings"] = user_settings
        user_settings["customThemeSeedsLight"] = {}
        user_settings["customThemeSeedsDark"] = {}
        config_updated = True
        if not dry_run:
            config_backup = create_backup(config_path, preserve_mode_0600=True)
            atomic_write_json(config_path, config_data, preserve_mode_0600=True)

    if storage_path.exists():
        storage_data = _read_json_dict(storage_path)
        storage_data["theme-preset-light"] = "Default Light"
        storage_data["theme-preset-dark"] = "Default Dark"
        storage_updated = True
        if not dry_run:
            storage_backup = create_backup(storage_path, preserve_mode_0600=False)
            atomic_write_json(storage_path, storage_data, preserve_mode_0600=False)

    return {
        "dry_run": dry_run,
        "plugin_removed": plugin_removed,
        "config_updated": config_updated,
        "storage_updated": storage_updated,
        "config_backup": str(config_backup) if config_backup else None,
        "storage_backup": str(storage_backup) if storage_backup else None,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="apply_theme.py",
        description=(
            "Install and apply the Bohemian Art Nouveau Light/Dark theme "
            "for Antigravity 2."
        ),
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--apply",
        action="store_true",
        help="Install plugin files and apply theme seeds + preset (default).",
    )
    action.add_argument(
        "--install-plugin",
        action="store_true",
        help="Copy runtime plugin files only (safe while Antigravity 2 is running).",
    )
    action.add_argument(
        "--restore",
        action="store_true",
        help="Restore the latest config.json and app_storage.json backups.",
    )
    action.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove installed plugin files and reset custom seeds and presets.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing or deleting any files.",
    )
    parser.add_argument(
        "--mode",
        choices=("light", "dark", "both"),
        default="both",
        help="Which theme mode(s) to apply (default: both).",
    )
    parser.add_argument(
        "--preset",
        default=DEFAULT_PRESET,
        help=f"Syntax preset name to set in app_storage.json (default: {DEFAULT_PRESET}).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Override path to Antigravity config.json.",
    )
    parser.add_argument(
        "--storage",
        type=Path,
        default=None,
        help="Override path to Antigravity app_storage.json.",
    )
    parser.add_argument(
        "--plugins-dir",
        type=Path,
        default=None,
        help="Override path to Antigravity plugins directory.",
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=None,
        help="Override path to the Bohemian Art Nouveau bundle directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    bundle_dir = (args.bundle_dir or Path(__file__).resolve().parent).resolve()
    config_path = args.config or get_default_config_path()
    storage_path = args.storage or get_default_storage_path()
    plugins_dir = args.plugins_dir or get_default_plugins_dir()

    try:
        if args.install_plugin:
            dest = install_plugin(
                bundle_dir=bundle_dir,
                plugins_dir=plugins_dir,
                dry_run=args.dry_run,
            )
            result: dict[str, Any] = {
                "action": "install-plugin",
                "dry_run": args.dry_run,
                "plugin_dir": str(dest),
            }
        elif args.restore:
            result = {
                "action": "restore",
                **restore_theme(
                    config_path=config_path,
                    storage_path=storage_path,
                    dry_run=args.dry_run,
                ),
            }
        elif args.uninstall:
            result = {
                "action": "uninstall",
                **uninstall_theme(
                    config_path=config_path,
                    storage_path=storage_path,
                    plugins_dir=plugins_dir,
                    dry_run=args.dry_run,
                ),
            }
        else:
            result = {
                "action": "apply",
                **apply_theme(
                    bundle_dir=bundle_dir,
                    config_path=config_path,
                    storage_path=storage_path,
                    plugins_dir=plugins_dir,
                    mode=args.mode,
                    preset=args.preset,
                    dry_run=args.dry_run,
                ),
            }
    except AntigravityRunningError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
