#!/usr/bin/env python3
"""Comprehensive verification suite for the Bohemian Art Nouveau Antigravity 2 theme."""

from __future__ import annotations

import contextlib
import getpass
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

BUNDLE_DIR = Path(__file__).resolve().parent.parent
if str(BUNDLE_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_DIR))

import apply_theme as theme_cli  # noqa: E402

PALETTE_HEX_ALLOWLIST = {
    # Core 60-25-10-5 (Day & Evening)
    "#F3EFE8", "#EFE4D2",
    "#1A3644", "#162B37",
    "#6C4F3D", "#7A4D33",
    "#C29B53", "#D4A853",
    "#C78A3A", "#D99330",
    "#B85D43", "#C66347",
    "#9E6B47", "#AD734A",
    "#5A3D4D", "#4E3242",
    # Architectural metalwork & cabinetry shading
    "#17303D", "#162E3B", "#12242E",
    "#DFBE7A", "#B38B40", "#946F2D",
    # Surface materials
    "#2A2C30", "#C8BEAF", "#E0D9CE", "#1F2023",
    # Botanical & pastel accents
    "#D6A692", "#E8BA9B", "#7B8C7E", "#A89FAD",
}

EXPECTED_SYNTAX_KEYS = {
    "comment",
    "punctuation",
    "property",
    "deleted",
    "inserted",
    "tag",
    "constant",
    "number",
    "string",
    "attrName",
    "builtin",
    "operator",
    "variable",
    "attrValue",
    "keyword",
    "function",
    "className",
    "regex",
}

EXPECTED_SEED_KEYS = {
    "background",
    "foreground",
    "primary",
    "primary_foreground",
    "code_foreground",
}

ALLOWED_PLUGIN_FIELDS = {
    "name",
    "displayName",
    "version",
    "description",
    "logo",
    "suggestedPrompts",
    "author",
    "homepage",
    "repository",
    "disabled",
}

HEX6_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
ANY_HEX_RE = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b")


def _srgb_channel_to_linear(channel_0_255: int) -> float:
    """Convert an 8-bit sRGB channel value to WCAG 2.1 linear luminance."""
    c = channel_0_255 / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """Compute WCAG 2.1 relative luminance for a #RRGGBB color."""
    clean = hex_color.lstrip("#")
    r = _srgb_channel_to_linear(int(clean[0:2], 16))
    g = _srgb_channel_to_linear(int(clean[2:4], 16))
    b = _srgb_channel_to_linear(int(clean[4:6], 16))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """Compute WCAG 2.1 contrast ratio between two #RRGGBB colors."""
    l1 = relative_luminance(hex_a)
    l2 = relative_luminance(hex_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class BohemianArtNouveauThemeTests(unittest.TestCase):
    """Automated test suite for plugin, themes, preview, CLI, and PII hygiene."""

    def test_plugin_manifest(self) -> None:
        manifest_path = BUNDLE_DIR / "plugin.json"
        self.assertTrue(manifest_path.is_file(), "plugin.json is missing")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIsInstance(manifest, dict)
        self.assertTrue(set(manifest.keys()).issubset(ALLOWED_PLUGIN_FIELDS))
        self.assertEqual(manifest.get("name"), "bohemian-art-nouveau")
        self.assertEqual(manifest.get("logo"), "assets/logo.svg")
        self.assertTrue(manifest.get("description"))

        logo_path = BUNDLE_DIR / manifest["logo"]
        self.assertTrue(logo_path.is_file(), "Referenced logo asset is missing")
        svg_root = ET.fromstring(logo_path.read_text(encoding="utf-8"))
        self.assertTrue(svg_root.tag.endswith("svg"))
        self.assertEqual(svg_root.attrib.get("viewBox"), "0 0 128 128")

    def test_theme_json_schemas(self) -> None:
        expected_modes = {
            "bohemian-art-nouveau-light.json": "light",
            "bohemian-art-nouveau-dark.json": "dark",
        }
        for filename, mode in expected_modes.items():
            theme_path = BUNDLE_DIR / "themes" / filename
            self.assertTrue(theme_path.is_file(), f"Missing {filename}")
            data = json.loads(theme_path.read_text(encoding="utf-8"))
            self.assertEqual(
                set(data.keys()),
                {"id", "label", "mode", "seeds", "syntax"},
                f"Unexpected top-level keys in {filename}",
            )
            self.assertEqual(data["mode"], mode)
            self.assertEqual(data["id"], f"bohemian-art-nouveau-{mode}")
            self.assertEqual(set(data["seeds"].keys()), EXPECTED_SEED_KEYS)
            self.assertEqual(set(data["syntax"].keys()), EXPECTED_SYNTAX_KEYS)

            for group_name in ("seeds", "syntax"):
                for key, value in data[group_name].items():
                    self.assertRegex(
                        value,
                        HEX6_RE,
                        f"Invalid hex value in {filename} {group_name}.{key}: {value!r}",
                    )

    def test_palette_only_hex_codes(self) -> None:
        strict_files = [
            BUNDLE_DIR / "themes" / "bohemian-art-nouveau-light.json",
            BUNDLE_DIR / "themes" / "bohemian-art-nouveau-dark.json",
            BUNDLE_DIR / "assets" / "logo.svg",
            BUNDLE_DIR / "apply_theme.py",
        ]
        for file_path in strict_files:
            content = file_path.read_text(encoding="utf-8")
            found = {m.upper() for m in ANY_HEX_RE.findall(content)}
            unexpected = found - PALETTE_HEX_ALLOWLIST
            self.assertEqual(
                unexpected,
                set(),
                f"Off-palette hex codes in {file_path.name}: {sorted(unexpected)}",
            )

        preview_html = (BUNDLE_DIR / "docs" / "bohemian-art-nouveau-preview.html").read_text(
            encoding="utf-8"
        )
        syntax_match = re.search(
            r"const\s+BOHEMIAN_SYNTAX\s*=\s*\{(?P<body>.*?)\n\s*\};",
            preview_html,
            re.DOTALL,
        )
        self.assertIsNotNone(syntax_match, "BOHEMIAN_SYNTAX block not found in preview HTML")
        syntax_hexes = {m.upper() for m in ANY_HEX_RE.findall(syntax_match.group("body"))}
        self.assertTrue(syntax_hexes, "No hex codes found in BOHEMIAN_SYNTAX block")
        self.assertEqual(
            syntax_hexes - PALETTE_HEX_ALLOWLIST,
            set(),
            "BOHEMIAN_SYNTAX contains off-palette hex codes",
        )

    def test_wcag_ui_contrasts(self) -> None:
        for mode in ("light", "dark"):
            theme_path = BUNDLE_DIR / "themes" / f"bohemian-art-nouveau-{mode}.json"
            seeds = json.loads(theme_path.read_text(encoding="utf-8"))["seeds"]

            fg_bg = contrast_ratio(seeds["foreground"], seeds["background"])
            pri_bg = contrast_ratio(seeds["primary"], seeds["background"])
            pf_pri = contrast_ratio(seeds["primary_foreground"], seeds["primary"])
            code_bg = contrast_ratio(seeds["code_foreground"], seeds["background"])

            self.assertGreaterEqual(fg_bg, 7.0, f"{mode} foreground/background={fg_bg:.2f}")
            self.assertGreaterEqual(pri_bg, 4.5, f"{mode} primary/background={pri_bg:.2f}")
            self.assertGreaterEqual(
                pf_pri, 4.5, f"{mode} primary_foreground/primary={pf_pri:.2f}"
            )
            self.assertGreaterEqual(
                code_bg, 4.5, f"{mode} code_foreground/background={code_bg:.2f}"
            )

    def test_apply_theme_cross_platform_and_lifecycle(self) -> None:
        fake_home = Path("/tmp/synthetic-home")

        # 1. Cross-platform path resolution
        self.assertEqual(
            theme_cli.get_default_config_path(home=fake_home),
            fake_home / ".gemini" / "config" / "config.json",
        )
        self.assertEqual(
            theme_cli.get_default_plugins_dir(home=fake_home),
            fake_home / ".gemini" / "config" / "plugins",
        )
        self.assertEqual(
            theme_cli.get_default_storage_path(platform="linux", env={}, home=fake_home),
            fake_home / ".config" / "Antigravity" / "app_storage.json",
        )
        self.assertEqual(
            theme_cli.get_default_storage_path(
                platform="linux",
                env={"XDG_CONFIG_HOME": "/tmp/custom-xdg"},
                home=fake_home,
            ),
            Path("/tmp/custom-xdg") / "Antigravity" / "app_storage.json",
        )
        self.assertEqual(
            theme_cli.get_default_storage_path(
                platform="win32",
                env={"APPDATA": "C:\\Users\\TestUser\\AppData\\Roaming"},
                home=fake_home,
            ),
            Path("C:\\Users\\TestUser\\AppData\\Roaming")
            / "Antigravity"
            / "app_storage.json",
        )
        self.assertEqual(
            theme_cli.get_default_storage_path(platform="win32", env={}, home=fake_home),
            fake_home / "AppData" / "Roaming" / "Antigravity" / "app_storage.json",
        )
        self.assertEqual(
            theme_cli.get_default_storage_path(platform="darwin", env={}, home=fake_home),
            fake_home
            / "Library"
            / "Application Support"
            / "Antigravity"
            / "app_storage.json",
        )

        # 2. Cross-platform process detection (Linux & Windows mocks)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            empty_proc = root / "empty_proc"
            empty_proc.mkdir()
            self.assertEqual(
                theme_cli.detect_running_antigravity("linux", proc_root=empty_proc),
                [],
            )

            fake_proc = root / "fake_proc"
            pid_dir = fake_proc / "999999"
            pid_dir.mkdir(parents=True)
            (pid_dir / "comm").write_text("antigravity\n", encoding="utf-8")
            (pid_dir / "cmdline").write_bytes(
                b"/opt/Antigravity/antigravity\x00--no-sandbox\x00"
            )
            detected_linux = theme_cli.detect_running_antigravity(
                "linux", proc_root=fake_proc
            )
            self.assertEqual(detected_linux, ["999999:antigravity"])

        win_running = subprocess.CompletedProcess(
            args=["tasklist", "/FO", "CSV", "/NH"],
            returncode=0,
            stdout='"Antigravity.exe","4321","Console","1","120,000 K"\n',
            stderr="",
        )
        with mock.patch.object(theme_cli.subprocess, "run", return_value=win_running):
            self.assertEqual(
                theme_cli.detect_running_antigravity("win32"),
                ["4321:Antigravity.exe"],
            )

        win_idle = subprocess.CompletedProcess(
            args=["tasklist", "/FO", "CSV", "/NH"],
            returncode=0,
            stdout='"explorer.exe","1024","Console","1","45,000 K"\n',
            stderr="",
        )
        with mock.patch.object(theme_cli.subprocess, "run", return_value=win_idle):
            self.assertEqual(theme_cli.detect_running_antigravity("win32"), [])

        # 3. Full isolated CLI/lifecycle checks
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config_path = tmp / "config" / "config.json"
            storage_path = tmp / "storage" / "app_storage.json"
            plugins_dir = tmp / "config" / "plugins"

            initial_config = {
                "userSettings": {
                    "themeMode": "THEME_MODE_DARK",
                    "customThemeSeedsLight": {"background": "#FFFFFF"},
                    "customThemeSeedsDark": {"background": "#000000"},
                },
                "permissionGrants": {"keep": True},
                "plugins": {"token-counter": {"enabled": True}},
            }
            initial_storage = {
                "theme-preset-light": "Default Light",
                "theme-preset-dark": "Default Dark",
                "customKey": "preserve",
            }
            config_path.parent.mkdir(parents=True, exist_ok=True)
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(initial_config, indent=2), encoding="utf-8")
            storage_path.write_text(
                json.dumps(initial_storage, indent=2), encoding="utf-8"
            )
            if os.name == "posix":
                os.chmod(config_path, 0o600)

            pre_config_text = config_path.read_text(encoding="utf-8")
            pre_storage_text = storage_path.read_text(encoding="utf-8")

            # Running-process guard blocks live apply (raises RuntimeError + CLI exit 2)
            with mock.patch.object(
                theme_cli, "detect_running_antigravity", return_value=["4321:antigravity"]
            ):
                with self.assertRaises(RuntimeError):
                    theme_cli.apply_theme(
                        BUNDLE_DIR,
                        config_path,
                        storage_path,
                        plugins_dir,
                        dry_run=False,
                        check_running=True,
                    )
                with contextlib.redirect_stderr(io.StringIO()):
                    exit_code = theme_cli.main(
                        [
                            "--apply",
                            "--bundle-dir",
                            str(BUNDLE_DIR),
                            "--config",
                            str(config_path),
                            "--storage",
                            str(storage_path),
                            "--plugins-dir",
                            str(plugins_dir),
                        ]
                    )
                self.assertEqual(exit_code, 2)
                self.assertEqual(config_path.read_text(encoding="utf-8"), pre_config_text)
                self.assertEqual(
                    storage_path.read_text(encoding="utf-8"), pre_storage_text
                )
                self.assertFalse(plugins_dir.exists())

                # --install-plugin succeeds even while Antigravity is running
                with contextlib.redirect_stdout(io.StringIO()):
                    install_code = theme_cli.main(
                        [
                            "--install-plugin",
                            "--bundle-dir",
                            str(BUNDLE_DIR),
                            "--config",
                            str(config_path),
                            "--storage",
                            str(storage_path),
                            "--plugins-dir",
                            str(plugins_dir),
                        ]
                    )
                self.assertEqual(install_code, 0)
                self.assertEqual(config_path.read_text(encoding="utf-8"), pre_config_text)
                self.assertEqual(
                    storage_path.read_text(encoding="utf-8"), pre_storage_text
                )

            # Remove installed plugin before dry-run test
            theme_cli.uninstall_plugin(plugins_dir, dry_run=False)
            self.assertFalse((plugins_dir / theme_cli.PLUGIN_SLUG).exists())

            # --dry-run leaves config, storage, and plugins_dir untouched
            dry_result = theme_cli.apply_theme(
                BUNDLE_DIR,
                config_path,
                storage_path,
                plugins_dir,
                dry_run=True,
                check_running=True,
            )
            self.assertTrue(dry_result["dry_run"])
            self.assertEqual(config_path.read_text(encoding="utf-8"), pre_config_text)
            self.assertEqual(storage_path.read_text(encoding="utf-8"), pre_storage_text)
            self.assertFalse((plugins_dir / theme_cli.PLUGIN_SLUG).exists())

            # Atomic --apply + sibling preservation + backup + POSIX 0600
            apply_result = theme_cli.apply_theme(
                BUNDLE_DIR,
                config_path,
                storage_path,
                plugins_dir,
                check_running=False,
            )
            self.assertFalse(apply_result["dry_run"])
            self.assertTrue(Path(apply_result["config_backup"]).is_file())
            self.assertTrue(Path(apply_result["storage_backup"]).is_file())

            applied_config = json.loads(config_path.read_text(encoding="utf-8"))
            applied_storage = json.loads(storage_path.read_text(encoding="utf-8"))

            self.assertEqual(applied_config["permissionGrants"], {"keep": True})
            self.assertEqual(
                applied_config["plugins"], {"token-counter": {"enabled": True}}
            )
            self.assertEqual(
                applied_config["userSettings"]["themeMode"], "THEME_MODE_DARK"
            )
            expected_camel_keys = {
                "background",
                "primary",
                "foregroundOverride",
                "primaryForegroundOverride",
                "codeForegroundOverride",
            }
            self.assertEqual(
                set(applied_config["userSettings"]["customThemeSeedsLight"].keys()),
                expected_camel_keys,
            )
            self.assertEqual(
                set(applied_config["userSettings"]["customThemeSeedsDark"].keys()),
                expected_camel_keys,
            )
            self.assertEqual(applied_storage["customKey"], "preserve")
            self.assertEqual(
                applied_storage["theme-preset-light"], "Gruvbox Material"
            )
            self.assertEqual(
                applied_storage["theme-preset-dark"], "Gruvbox Material"
            )
            self.assertEqual(
                applied_storage["hubSurfaceBackgroundColor"], "#162B37"
            )

            installed_dir = plugins_dir / theme_cli.PLUGIN_SLUG
            installed_files = {
                p.relative_to(installed_dir).as_posix()
                for p in installed_dir.rglob("*")
                if p.is_file()
            }
            self.assertEqual(installed_files, set(theme_cli.RUNTIME_PLUGIN_FILES))
            if os.name == "posix":
                self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)

            # --restore recovers exact pre-apply contents
            restore_result = theme_cli.restore_theme(
                config_path, storage_path, check_running=False
            )
            self.assertTrue(restore_result["restored_config"])
            self.assertTrue(restore_result["restored_storage"])
            self.assertEqual(config_path.read_text(encoding="utf-8"), pre_config_text)
            self.assertEqual(storage_path.read_text(encoding="utf-8"), pre_storage_text)

            # Re-apply then --uninstall
            theme_cli.apply_theme(
                BUNDLE_DIR,
                config_path,
                storage_path,
                plugins_dir,
                check_running=False,
            )
            uninstall_result = theme_cli.uninstall_theme(
                config_path,
                storage_path,
                plugins_dir,
                check_running=False,
            )
            self.assertTrue(uninstall_result["plugin_removed"])
            self.assertFalse(installed_dir.exists())

            uninstalled_config = json.loads(config_path.read_text(encoding="utf-8"))
            uninstalled_storage = json.loads(storage_path.read_text(encoding="utf-8"))
            self.assertEqual(uninstalled_config["permissionGrants"], {"keep": True})
            self.assertEqual(
                uninstalled_config["plugins"], {"token-counter": {"enabled": True}}
            )
            self.assertEqual(
                uninstalled_config["userSettings"]["customThemeSeedsLight"], {}
            )
            self.assertEqual(
                uninstalled_config["userSettings"]["customThemeSeedsDark"], {}
            )
            self.assertEqual(uninstalled_storage["customKey"], "preserve")
            self.assertEqual(
                uninstalled_storage["theme-preset-light"], "Default Light"
            )
            self.assertEqual(
                uninstalled_storage["theme-preset-dark"], "Default Dark"
            )

    def test_preview_html_offline(self) -> None:
        html_path = BUNDLE_DIR / "docs" / "bohemian-art-nouveau-preview.html"
        self.assertTrue(html_path.is_file(), "Preview HTML file is missing")
        html = html_path.read_text(encoding="utf-8")

        self.assertIsNone(
            re.search(r'(?:src|href)\s*=\s*["\']https?://', html, re.IGNORECASE),
            "Preview HTML must not reference external http(s) src or href URLs",
        )
        self.assertIsNone(
            re.search(r"url\(\s*['\"]?https?://", html, re.IGNORECASE),
            "Preview HTML must not reference external http(s) CSS url() assets",
        )
        self.assertIn("color-mix(in srgb", html)
        self.assertIn("BOHEMIAN_SYNTAX", html)
        self.assertIn("GA_GRUVBOX_SYNTAX", html)
        for token in EXPECTED_SYNTAX_KEYS:
            self.assertIn(token, html, f"Missing syntax token {token!r} in preview HTML")

    def test_no_pii_in_publishable_bundle(self) -> None:
        GENERIC_CI_USERNAMES = {
            "runner",
            "runneradmin",
            "root",
            "admin",
            "administrator",
            "user",
            "vscode",
            "codespace",
        }
        dynamic_tokens: set[str] = set()
        candidates = [
            getpass.getuser(),
            os.environ.get("USER", ""),
            os.environ.get("USERNAME", ""),
            str(Path.home()),
            Path.home().name,
        ]
        for item in candidates:
            cleaned = item.strip()
            if len(cleaned) >= 3 and cleaned.lower() not in GENERIC_CI_USERNAMES:
                dynamic_tokens.add(cleaned.lower())

        pii_patterns = [
            ("posix_home_path", re.compile("/" + r"home/[A-Za-z0-9._-]+")),
            ("macos_home_path", re.compile("/" + r"Users/[A-Za-z0-9._-]+")),
            (
                "windows_user_path",
                re.compile(r"[A-Za-z]:\\Users\\(?!<user>|YourUser|Test)[A-Za-z0-9._-]+"),
            ),
            (
                "email_address",
                re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
            ),
        ]

        findings: list[str] = []
        for path in sorted(BUNDLE_DIR.rglob("*")):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue

            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(BUNDLE_DIR).as_posix()
            lower_text = text.lower()

            for token in sorted(dynamic_tokens):
                if token in lower_text:
                    findings.append(f"{rel}: matched dynamic local token {token!r}")

            for label, pattern in pii_patterns:
                match = pattern.search(text)
                if match:
                    findings.append(f"{rel}: matched {label} ({match.group(0)!r})")

        self.assertEqual(findings, [], "PII leakage detected:\n" + "\n".join(findings))


if __name__ == "__main__":
    unittest.main()
