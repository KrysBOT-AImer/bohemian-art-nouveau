#!/usr/bin/env python3
"""Cross-platform unit tests for patch_titlebar_overlay.py."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

BUNDLE_DIR = Path(__file__).resolve().parent.parent
if str(BUNDLE_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_DIR))

import patch_titlebar_overlay as patcher  # noqa: E402


SYNTHETIC_IPC_HANDLERS_TEMPLATE = """\
"use strict";
const electron_1 = require("electron");
const utils_1 = require("./utils");
function registerIpcHandlers(storageManager, deps = {}) {
    const getTargetHubWindow = (sender) => deps.getWindow ? deps.getWindow(sender) : null;
    // Window
__ANCHOR__
}
exports.registerIpcHandlers = registerIpcHandlers;
"""

SYNTHETIC_UTILS_TEMPLATE = """\
"use strict";
const electron_1 = require("electron");
const path_1 = { default: require("path") };
const windowState_1 = require("./windowState");
const debugConsole_1 = require("./debugConsole");
const wsl_1 = require("./wsl");
const fs = require("fs");
const HEX_COLOR_6_RE = /^#[0-9A-Fa-f]{6}$/;
const asRecord = (v) => (v && typeof v === 'object' && !Array.isArray(v) ? v : undefined);
let mockAppStorage = {};
let mockThemeMode = 'DARK';
let mockCurtainColor = '#131313';
function setMockState(state) {
    if (state.appStorage !== undefined) mockAppStorage = state.appStorage;
    if (state.themeMode !== undefined) mockThemeMode = state.themeMode;
    if (state.curtainColor !== undefined) mockCurtainColor = state.curtainColor;
}
function isMacOS() {
    return process.platform === 'darwin';
}
function getThemeMode() {
    return mockThemeMode;
}
function startInactive() {
    return false;
}
function ensureAppIsInDock() {}
function ensureAppIsInDockInactive() {}
function getHubWindows() {
    return [];
}
function getFocusedHubWindow() {
    return undefined;
}
function readAppStorageSync() {
    return mockAppStorage;
}
function normalizeHexSurfaceColor(color) {
    const s = typeof color === 'string' ? color.trim() : '';
    return HEX_COLOR_6_RE.test(s) ? s.toUpperCase() : undefined;
}
function getHubCurtainColor() {
    return mockCurtainColor;
}
function createWindow(url, storageManager, options) {
    const inactive = startInactive();
    if (inactive) {
        ensureAppIsInDockInactive();
    }
    else {
        ensureAppIsInDock();
    }
    const existingWindows = options?.cascade && !options.initialState ? getHubWindows() : [];
    const initialWindowState = (0, windowState_1.resolveInitialWindowState)({
        state: options?.initialState,
        cascadeFromWindow: undefined,
    });
__BLOCK1__
    const badge = options?.titleSuffix ?? '';
    const builtInBrowser = options?.builtInBrowser ?? false;
    const additionalArguments = options?.additionalArguments ?? [];
    const windowOptions = {
        width: initialWindowState.width,
        height: initialWindowState.height,
        title: electron_1.app.getName() + badge,
        icon: path_1.default.join(__dirname, '..', 'icon.png'),
__BLOCK2__
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
    };
    return new electron_1.BrowserWindow(windowOptions);
}
module.exports = {
    createWindow,
    normalizeHexSurfaceColor,
    getHubCurtainColor,
    setMockState,
};
"""


def _build_synthetic_js(
    *,
    ipc_anchor: str = patcher.IPC_HANDLERS_ANCHOR,
    utils_block1: str = patcher.UTILS_BLOCK1_ANCHOR,
    utils_block2: str = patcher.UTILS_BLOCK2_ANCHOR,
) -> tuple[bytes, bytes]:
    ipc_js = SYNTHETIC_IPC_HANDLERS_TEMPLATE.replace("__ANCHOR__", ipc_anchor)
    utils_js = (
        SYNTHETIC_UTILS_TEMPLATE.replace("__BLOCK1__", utils_block1).replace(
            "__BLOCK2__", utils_block2
        )
    )
    return ipc_js.encode("utf-8"), utils_js.encode("utf-8")


def _insert_tree_entry(root: dict[str, object], rel_path: str, meta: dict[str, object]) -> None:
    parts = rel_path.split("/")
    curr = root
    for folder in parts[:-1]:
        files = curr.setdefault("files", {})
        assert isinstance(files, dict)
        curr = files.setdefault(folder, {"files": {}})
        assert isinstance(curr, dict)
    files = curr.setdefault("files", {})
    assert isinstance(files, dict)
    files[parts[-1]] = meta


def _build_synthetic_asar(
    asar_path: Path,
    *,
    ipc_bytes: bytes | None = None,
    utils_bytes: bytes | None = None,
    extra_tag: str = "",
    block_size: int = 4194304,
) -> dict[str, bytes]:
    """Create a realistic synthetic ASAR archive and return packed file payloads."""
    default_ipc, default_utils = _build_synthetic_js()
    packed_files: dict[str, bytes] = {
        "00_prelude.txt": b"bohemian-prelude-bytes\n",
        "empty.txt": b"",
        patcher.IPC_HANDLERS_REL_PATH: ipc_bytes if ipc_bytes is not None else default_ipc,
        patcher.UTILS_REL_PATH: utils_bytes if utils_bytes is not None else default_utils,
        "dist/zzz_after.bin": bytes(range(64)),
    }
    if extra_tag:
        packed_files[f"meta/{extra_tag}.txt"] = b"tag"

    header: dict[str, object] = {"files": {}}
    payload_parts: list[bytes] = []
    offset = 0

    for rel_path, content in packed_files.items():
        node: dict[str, object] = {
            "size": len(content),
            "offset": str(offset),
            "integrity": patcher.compute_asar_integrity(content, block_size=block_size),
        }
        if rel_path == "00_prelude.txt":
            node["executable"] = True
        _insert_tree_entry(header, rel_path, node)
        payload_parts.append(content)
        offset += len(content)

    _insert_tree_entry(
        header,
        "assets/native.node",
        {"size": 128, "unpacked": True},
    )

    archive_bytes = patcher.encode_asar_bytes(header, b"".join(payload_parts))
    asar_path.parent.mkdir(parents=True, exist_ok=True)
    asar_path.write_bytes(archive_bytes)
    return packed_files


def _find_js_runtime() -> tuple[list[str], dict[str, str]] | None:
    """Return command prefix + env for Node syntax/runtime checks if available."""
    node_bin = shutil.which("node")
    if node_bin:
        return [node_bin], os.environ.copy()
    agy_bin = Path("/opt/Antigravity/antigravity")
    if sys.platform.startswith("linux") and agy_bin.is_file():
        env = os.environ.copy()
        env["ELECTRON_RUN_AS_NODE"] = "1"
        return [str(agy_bin)], env
    return None


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        code = patcher.main(argv)
    return code, stdout_buf.getvalue(), stderr_buf.getvalue()


class PatchTitlebarOverlayTests(unittest.TestCase):
    """Test suite for ASAR binary engine, JS patcher, CLI lifecycle, and hook."""

    def test_asar_pickle_alignment_and_integrity_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # 1. Cover all 4 header JSON length remainders (L % 4 in {0, 1, 2, 3})
            seen_remainders: set[int] = set()
            for idx in range(16):
                asar_path = root / f"align_{idx}.asar"
                _build_synthetic_asar(asar_path, extra_tag="x" * idx)
                u0, u1, u2, u3 = struct.unpack("<4I", asar_path.read_bytes()[:16])
                rem = u3 % 4
                pad = (4 - rem) % 4
                self.assertEqual(u0, 4)
                self.assertEqual(u2, 4 + u3 + pad)
                self.assertEqual(u1, 8 + u3 + pad)
                seen_remainders.add(rem)
                summary = patcher.verify_asar_integrity(asar_path)
                self.assertTrue(summary["valid"])
                self.assertEqual(summary["unpacked_files"], 1)
                self.assertEqual(summary["executable_files"], 1)
                if len(seen_remainders) == 4:
                    break
            self.assertEqual(seen_remainders, {0, 1, 2, 3})

            # 2. Multi-block and empty-file integrity metadata
            empty_integrity = patcher.compute_asar_integrity(b"", block_size=16)
            self.assertEqual(empty_integrity["hash"], hashlib.sha256(b"").hexdigest())
            self.assertEqual(
                empty_integrity["blocks"], [hashlib.sha256(b"").hexdigest()]
            )

            sample = b"0123456789abcdef" * 2 + b"tail"
            multi = patcher.compute_asar_integrity(sample, block_size=16)
            self.assertEqual(multi["algorithm"], "SHA256")
            self.assertEqual(multi["blockSize"], 16)
            self.assertEqual(len(multi["blocks"]), 3)
            self.assertEqual(multi["blocks"][0], hashlib.sha256(sample[:16]).hexdigest())
            self.assertEqual(multi["blocks"][1], hashlib.sha256(sample[16:32]).hexdigest())
            self.assertEqual(multi["blocks"][2], hashlib.sha256(sample[32:]).hexdigest())

            # 3. Repacking shifts offsets and preserves unmodified files + metadata
            asar_path = root / "repack.asar"
            original_payloads = _build_synthetic_asar(asar_path, block_size=16)
            orig_header, _ = patcher.read_asar_header(asar_path)
            orig_after_offset = int(
                orig_header["files"]["dist"]["files"]["zzz_after.bin"]["offset"]
            )

            new_ipc = b"// patched placeholder\n" * 40
            repacked_bytes = patcher.repack_asar_with_replacements(
                asar_path, {patcher.IPC_HANDLERS_REL_PATH: new_ipc}
            )
            repacked_path = root / "repacked.asar"
            repacked_path.write_bytes(repacked_bytes)

            rep_summary = patcher.verify_asar_integrity(repacked_path)
            self.assertTrue(rep_summary["valid"])
            rep_header, _ = patcher.read_asar_header(repacked_path)
            rep_after_offset = int(
                rep_header["files"]["dist"]["files"]["zzz_after.bin"]["offset"]
            )
            delta = len(new_ipc) - len(original_payloads[patcher.IPC_HANDLERS_REL_PATH])
            self.assertEqual(rep_after_offset, orig_after_offset + delta)

            self.assertEqual(
                patcher.read_asar_file(repacked_path, "00_prelude.txt"),
                original_payloads["00_prelude.txt"],
            )
            self.assertEqual(patcher.read_asar_file(repacked_path, "empty.txt"), b"")
            self.assertEqual(
                patcher.read_asar_file(repacked_path, "dist/zzz_after.bin"),
                original_payloads["dist/zzz_after.bin"],
            )
            self.assertEqual(
                patcher.read_asar_file(repacked_path, patcher.IPC_HANDLERS_REL_PATH),
                new_ipc,
            )
            self.assertTrue(rep_header["files"]["00_prelude.txt"]["executable"])
            self.assertTrue(
                rep_header["files"]["assets"]["files"]["native.node"]["unpacked"]
            )
            self.assertEqual(
                rep_header["files"]["dist"]["files"]["ipcHandlers.js"]["integrity"][
                    "blockSize"
                ],
                16,
            )

            # 4. Corruption detection
            corrupted_payload = root / "corrupted_payload.asar"
            raw = bytearray(repacked_bytes)
            raw[-1] ^= 0xFF
            corrupted_payload.write_bytes(bytes(raw))
            with self.assertRaises(patcher.AsarError):
                patcher.verify_asar_integrity(corrupted_payload)

            truncated = root / "truncated.asar"
            truncated.write_bytes(repacked_bytes[:-10])
            with self.assertRaises(patcher.AsarError):
                patcher.verify_asar_integrity(truncated)

            bad_pickle = root / "bad_pickle.asar"
            bad_raw = bytearray(repacked_bytes)
            struct.pack_into("<I", bad_raw, 4, 999999)
            bad_pickle.write_bytes(bytes(bad_raw))
            with self.assertRaises(patcher.AsarError):
                patcher.verify_asar_integrity(bad_pickle)

    @mock.patch.object(patcher.sys, "platform", "linux")
    def test_check_statuses_and_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Unpatched -> exit 2
            unpatched = root / "unpatched.asar"
            _build_synthetic_asar(unpatched)
            code, out, err = _run_cli(
                ["--check", "--asar-path", str(unpatched), "--json"]
            )
            self.assertEqual(code, 2, err)
            data = json.loads(out)
            self.assertEqual(data["action"], "check")
            self.assertEqual(data["status"], "unpatched")
            self.assertEqual(data["exit_code"], 2)
            self.assertEqual(data["files"][patcher.IPC_HANDLERS_REL_PATH], "unpatched")
            self.assertEqual(data["files"][patcher.UTILS_REL_PATH], "unpatched")
            self.assertTrue(data["integrity"]["valid"])

            # Patched -> exit 0
            apply_code, _, _ = _run_cli(["--apply", "--asar-path", str(unpatched)])
            self.assertEqual(apply_code, 0)
            code, out, _ = _run_cli(
                ["--check", "--asar-path", str(unpatched), "--json"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "patched")

            # Partially patched (only ipcHandlers patched) -> exit 1
            partial = root / "partial.asar"
            default_ipc, default_utils = _build_synthetic_js()
            patched_ipc = patcher.patch_ipc_handlers_js(default_ipc.decode("utf-8")).encode(
                "utf-8"
            )
            _build_synthetic_asar(partial, ipc_bytes=patched_ipc, utils_bytes=default_utils)
            code, out, _ = _run_cli(["--check", "--asar-path", str(partial), "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["status"], "partially_patched")

            # Incompatible anchor -> exit 1
            incompatible = root / "incompatible.asar"
            bad_ipc, bad_utils = _build_synthetic_js(ipc_anchor="// changed upstream")
            _build_synthetic_asar(incompatible, ipc_bytes=bad_ipc, utils_bytes=bad_utils)
            code, out, _ = _run_cli(
                ["--check", "--asar-path", str(incompatible), "--json"]
            )
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["status"], "incompatible")

    @mock.patch.object(patcher.sys, "platform", "linux")
    def test_full_lifecycle_dry_run_apply_idempotency_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            asar_path = root / "app.asar"
            _build_synthetic_asar(asar_path)
            orig_bytes = asar_path.read_bytes()

            # Restore with no backup fails with exit 1
            code, out, err = _run_cli(["--restore", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 1)
            self.assertIn("No backup found", json.loads(out)["error"])
            code_txt, _, err_txt = _run_cli(["--restore", "--asar-path", str(asar_path)])
            self.assertEqual(code_txt, 1)
            self.assertIn("No backup found", err_txt)

            # --dry-run leaves disk untouched and creates no .bak
            code, out, _ = _run_cli(["--dry-run", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "dry_run_ready")
            self.assertEqual(asar_path.read_bytes(), orig_bytes)
            self.assertEqual(list(root.glob("app.asar.*.bak")), [])

            # --apply creates backup, patches, verifies integrity
            code, out, _ = _run_cli(["--apply", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0)
            apply_data = json.loads(out)
            self.assertEqual(apply_data["status"], "patched")
            self.assertTrue(apply_data["changed"])
            backup_path = Path(apply_data["backup_path"])
            self.assertTrue(backup_path.is_file())
            self.assertEqual(backup_path.read_bytes(), orig_bytes)
            self.assertTrue(patcher.verify_asar_integrity(asar_path)["valid"])

            patched_bytes = asar_path.read_bytes()
            self.assertNotEqual(patched_bytes, orig_bytes)

            # Second --apply is idempotent (no extra backup, no file modification)
            code, out, _ = _run_cli(["--apply", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0)
            second_data = json.loads(out)
            self.assertEqual(second_data["status"], "already_patched")
            self.assertFalse(second_data["changed"])
            self.assertEqual(len(list(root.glob("app.asar.*.bak"))), 1)
            self.assertEqual(asar_path.read_bytes(), patched_bytes)

            # --restore --dry-run leaves patched bytes untouched
            code, out, _ = _run_cli(
                ["--restore", "--dry-run", "--asar-path", str(asar_path), "--json"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "dry_run_ready")
            self.assertEqual(asar_path.read_bytes(), patched_bytes)

            # --restore recovers exact original bytes
            code, out, _ = _run_cli(["--restore", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0)
            restore_data = json.loads(out)
            self.assertEqual(restore_data["status"], "restored")
            self.assertTrue(restore_data["restored"])
            self.assertEqual(asar_path.read_bytes(), orig_bytes)

    @mock.patch.object(patcher.sys, "platform", "linux")
    def test_fail_safe_always_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Missing app.asar
            missing = root / "missing.asar"
            code, out, _ = _run_cli(
                ["--apply", "--fail-safe", "--asar-path", str(missing), "--json"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "warning")

            # Incompatible anchor
            incompatible = root / "incompatible.asar"
            bad_ipc, bad_utils = _build_synthetic_js(ipc_anchor="// unexpected")
            _build_synthetic_asar(incompatible, ipc_bytes=bad_ipc, utils_bytes=bad_utils)
            code, out, _ = _run_cli(
                ["--apply", "--fail-safe", "--asar-path", str(incompatible), "--json"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "warning")

            # Valid apply + second already-patched apply
            valid = root / "valid.asar"
            _build_synthetic_asar(valid)
            code1, out1, _ = _run_cli(
                ["--apply", "--fail-safe", "--asar-path", str(valid), "--json"]
            )
            self.assertEqual(code1, 0)
            self.assertEqual(json.loads(out1)["status"], "patched")

            code2, out2, _ = _run_cli(
                ["--apply", "--fail-safe", "--asar-path", str(valid), "--json"]
            )
            self.assertEqual(code2, 0)
            self.assertEqual(json.loads(out2)["status"], "already_patched")

    @mock.patch.object(patcher.sys, "platform", "linux")
    def test_pacman_hook_install_and_uninstall_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            hook_path = root / "hooks" / "antigravity-titlebar-overlay.hook"
            script_path = root / "libexec" / "antigravity-patch-titlebar-overlay.py"

            # Dry-run install touches nothing
            code, out, _ = _run_cli(
                [
                    "--install-hook",
                    "--dry-run",
                    "--hook-path",
                    str(hook_path),
                    "--script-install-path",
                    str(script_path),
                    "--json",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "dry_run_ready")
            self.assertFalse(hook_path.exists())
            self.assertFalse(script_path.exists())

            # Real install
            code, out, _ = _run_cli(
                [
                    "--install-hook",
                    "--hook-path",
                    str(hook_path),
                    "--script-install-path",
                    str(script_path),
                    "--json",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "installed")
            self.assertTrue(hook_path.is_file())
            self.assertTrue(script_path.is_file())
            self.assertEqual(
                script_path.read_bytes(), Path(patcher.__file__).read_bytes()
            )
            if os.name == "posix":
                self.assertEqual(script_path.stat().st_mode & 0o777, 0o755)
                self.assertEqual(hook_path.stat().st_mode & 0o777, 0o644)

            hook_text = hook_path.read_text(encoding="utf-8")
            self.assertIn("Target = opt/Antigravity/resources/app.asar", hook_text)
            self.assertIn("When = PostTransaction", hook_text)
            self.assertIn("--apply --fail-safe", hook_text)
            self.assertIn(str(script_path), hook_text)

            # Uninstall + idempotent repeat
            code, out, _ = _run_cli(
                [
                    "--uninstall-hook",
                    "--hook-path",
                    str(hook_path),
                    "--script-install-path",
                    str(script_path),
                    "--json",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "uninstalled")
            self.assertFalse(hook_path.exists())
            self.assertFalse(script_path.exists())

            code, out, _ = _run_cli(
                [
                    "--uninstall-hook",
                    "--hook-path",
                    str(hook_path),
                    "--script-install-path",
                    str(script_path),
                    "--json",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "already_absent")

    def test_non_linux_platforms_refused_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            asar_path = root / "app.asar"
            _build_synthetic_asar(asar_path)
            orig_asar_bytes = asar_path.read_bytes()

            bak_path = root / "app.asar.20260101T000000000000Z.bak"
            bak_bytes = b"sentinel-backup-bytes"
            bak_path.write_bytes(bak_bytes)

            new_hook_path = root / "new_hooks" / "antigravity.hook"
            new_script_path = root / "new_libexec" / "patcher.py"

            existing_hook_path = root / "existing_hooks" / "antigravity.hook"
            existing_script_path = root / "existing_libexec" / "patcher.py"
            existing_hook_path.parent.mkdir(parents=True, exist_ok=True)
            existing_script_path.parent.mkdir(parents=True, exist_ok=True)
            existing_hook_path.write_text("[Trigger]\n", encoding="utf-8")
            existing_script_path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            actions: list[tuple[str, list[str]]] = [
                ("check", ["--check", "--asar-path", str(asar_path)]),
                ("apply", ["--dry-run", "--asar-path", str(asar_path)]),
                ("apply", ["--apply", "--asar-path", str(asar_path)]),
                ("restore", ["--restore", "--asar-path", str(asar_path)]),
                (
                    "install-hook",
                    [
                        "--install-hook",
                        "--hook-path",
                        str(new_hook_path),
                        "--script-install-path",
                        str(new_script_path),
                    ],
                ),
                (
                    "uninstall-hook",
                    [
                        "--uninstall-hook",
                        "--hook-path",
                        str(existing_hook_path),
                        "--script-install-path",
                        str(existing_script_path),
                    ],
                ),
            ]

            for platform in ("win32", "darwin"):
                with mock.patch.object(patcher.sys, "platform", platform):
                    for expected_action, base_argv in actions:
                        code, out, err = _run_cli([*base_argv, "--json"])
                        self.assertEqual(code, 1, f"{platform} {base_argv}: {err}")
                        data = json.loads(out)
                        self.assertEqual(data["action"], expected_action)
                        self.assertEqual(data["status"], "unsupported_platform")
                        self.assertEqual(data["platform"], platform)
                        self.assertEqual(data["exit_code"], 1)
                        self.assertIn("Linux-only", data["error"])

                        code_fs, out_fs, err_fs = _run_cli(
                            [*base_argv, "--fail-safe", "--json"]
                        )
                        self.assertEqual(code_fs, 0, f"{platform} fail-safe: {err_fs}")
                        data_fs = json.loads(out_fs)
                        self.assertEqual(data_fs["action"], expected_action)
                        self.assertEqual(data_fs["status"], "skipped_non_linux")
                        self.assertEqual(data_fs["platform"], platform)
                        self.assertEqual(data_fs["exit_code"], 0)
                        self.assertIn("Linux-only", data_fs["error"])

                    # Plain text output check
                    code_txt, out_txt, err_txt = _run_cli(
                        ["--apply", "--asar-path", str(asar_path)]
                    )
                    self.assertEqual(code_txt, 1)
                    self.assertEqual(out_txt, "")
                    self.assertIn("unsupported_platform", err_txt)

                    code_fs_txt, out_fs_txt, err_fs_txt = _run_cli(
                        ["--apply", "--fail-safe", "--asar-path", str(asar_path)]
                    )
                    self.assertEqual(code_fs_txt, 0)
                    self.assertIn("skipped_non_linux", out_fs_txt)
                    self.assertEqual(err_fs_txt, "")

            # Confirm zero filesystem mutations occurred
            self.assertEqual(asar_path.read_bytes(), orig_asar_bytes)
            self.assertEqual(list(root.glob("app.asar.*.bak")), [bak_path])
            self.assertEqual(bak_path.read_bytes(), bak_bytes)
            self.assertFalse(new_hook_path.exists())
            self.assertFalse(new_script_path.exists())
            self.assertTrue(existing_hook_path.is_file())
            self.assertTrue(existing_script_path.is_file())
            self.assertEqual(existing_hook_path.read_text(encoding="utf-8"), "[Trigger]\n")
            self.assertEqual(
                existing_script_path.read_text(encoding="utf-8"),
                "#!/usr/bin/env python3\n",
            )

    @mock.patch.object(patcher.sys, "platform", "linux")
    def test_v1_to_v2_upgrade_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            asar_path = root / "v1_app.asar"
            v1_ipc, v1_utils = _build_synthetic_js(
                ipc_anchor=patcher.IPC_HANDLERS_V1_REPLACEMENT,
                utils_block1=patcher.UTILS_BLOCK1_V1_REPLACEMENT,
                utils_block2=patcher.UTILS_BLOCK2_V1_REPLACEMENT,
            )
            _build_synthetic_asar(asar_path, ipc_bytes=v1_ipc, utils_bytes=v1_utils)
            v1_bytes = asar_path.read_bytes()

            # --check reports outdated_v1 with exit 2 (0 under --fail-safe)
            code, out, err = _run_cli(["--check", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 2, err)
            check_data = json.loads(out)
            self.assertEqual(check_data["status"], "outdated_v1")
            self.assertEqual(check_data["exit_code"], 2)
            self.assertEqual(
                check_data["files"],
                {
                    patcher.IPC_HANDLERS_REL_PATH: "patched_v1",
                    patcher.UTILS_REL_PATH: "patched_v1",
                },
            )

            code_fs, out_fs, _ = _run_cli(
                ["--check", "--fail-safe", "--asar-path", str(asar_path), "--json"]
            )
            self.assertEqual(code_fs, 0)
            self.assertEqual(json.loads(out_fs)["status"], "outdated_v1")

            # --dry-run reports ready upgrade and touches nothing
            code, out, _ = _run_cli(["--dry-run", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0)
            dry_data = json.loads(out)
            self.assertEqual(dry_data["status"], "dry_run_ready")
            self.assertEqual(dry_data.get("upgraded_from"), "v1")
            self.assertEqual(asar_path.read_bytes(), v1_bytes)
            self.assertEqual(list(root.glob("v1_app.asar.*.bak")), [])

            # --apply creates backup and upgrades V1 -> V2
            code, out, err = _run_cli(["--apply", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0, err)
            apply_data = json.loads(out)
            self.assertEqual(apply_data["status"], "patched")
            self.assertEqual(apply_data.get("upgraded_from"), "v1")
            self.assertTrue(apply_data["changed"])
            backup_path = Path(apply_data["backup_path"])
            self.assertEqual(backup_path.read_bytes(), v1_bytes)
            self.assertTrue(patcher.verify_asar_integrity(asar_path)["valid"])

            upgraded_ipc = patcher.read_asar_file(
                asar_path, patcher.IPC_HANDLERS_REL_PATH
            ).decode("utf-8")
            upgraded_utils = patcher.read_asar_file(
                asar_path, patcher.UTILS_REL_PATH
            ).decode("utf-8")
            self.assertIn(patcher.PATCH_MARKER, upgraded_ipc)
            self.assertIn(patcher.PATCH_MARKER, upgraded_utils)
            self.assertNotIn(patcher.LEGACY_PATCH_MARKER_V1, upgraded_ipc)
            self.assertNotIn(patcher.LEGACY_PATCH_MARKER_V1, upgraded_utils)

            # Subsequent --check exits 0 ('patched') and second --apply is idempotent
            code, out, _ = _run_cli(["--check", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "patched")

            code, out, _ = _run_cli(["--apply", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0)
            second_data = json.loads(out)
            self.assertEqual(second_data["status"], "already_patched")
            self.assertFalse(second_data["changed"])
            self.assertEqual(len(list(root.glob("v1_app.asar.*.bak"))), 1)

            # --restore recovers exact pre-upgrade V1 bytes
            code, out, _ = _run_cli(["--restore", "--asar-path", str(asar_path), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "restored")
            self.assertEqual(asar_path.read_bytes(), v1_bytes)

            # Mixed V1 + V2 reports partially_patched (exit 1)
            mixed = root / "mixed.asar"
            _build_synthetic_asar(
                mixed,
                ipc_bytes=v1_ipc,
                utils_bytes=upgraded_utils.encode("utf-8"),
            )
            code, out, _ = _run_cli(["--check", "--asar-path", str(mixed), "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["status"], "partially_patched")

    @mock.patch.object(patcher.sys, "platform", "linux")
    def test_patched_js_syntax_and_runtime_behavior(self) -> None:
        runtime = _find_js_runtime()
        if runtime is None:
            self.skipTest("Neither node nor Antigravity Electron runtime is available")
        cmd_prefix, env = runtime

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            asar_path = root / "app.asar"
            _build_synthetic_asar(asar_path)
            code, _, err = _run_cli(["--apply", "--asar-path", str(asar_path)])
            self.assertEqual(code, 0, err)

            utils_file = root / "utils.js"
            ipc_file = root / "ipcHandlers.js"
            utils_file.write_bytes(
                patcher.read_asar_file(asar_path, patcher.UTILS_REL_PATH)
            )
            ipc_file.write_bytes(
                patcher.read_asar_file(asar_path, patcher.IPC_HANDLERS_REL_PATH)
            )

            for js_file in (utils_file, ipc_file):
                proc = subprocess.run(
                    [*cmd_prefix, "--check", str(js_file)],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    f"Syntax check failed for {js_file.name}: {proc.stderr}",
                )

            harness_js = f"""
const assert = require('assert');
const Module = require('module');

const ipcHandlersMap = new Map();
const overlayCalls = [];
const browserWindowArgs = [];
let shouldThrowOverlay = false;
let hasOverlayMethod = true;

class MockBrowserWindow {{
    constructor(opts) {{
        browserWindowArgs.push(opts);
    }}
}}

const utilsModulePath = {json.dumps(str(utils_file))};
const ipcModulePath = {json.dumps(str(ipc_file))};

const origLoad = Module._load;
let utilsExports = null;
Module._load = function(request, parent, isMain) {{
    if (request === 'electron') {{
        return {{
            app: {{ getName: () => 'Antigravity' }},
            BrowserWindow: MockBrowserWindow,
            ipcMain: {{
                handle: (channel, fn) => ipcHandlersMap.set(channel, fn),
            }},
        }};
    }}
    if (request === './utils') {{
        return utilsExports;
    }}
    if (request === './windowState') {{
        return {{ resolveInitialWindowState: () => ({{ width: 1280, height: 800 }}) }};
    }}
    if (request === './debugConsole') {{
        return {{ isDebugConsoleEnabled: () => false }};
    }}
    if (request === './wsl') {{
        return {{ getActiveWslDistro: () => undefined }};
    }}
    return origLoad.apply(this, arguments);
}};

utilsExports = require(utilsModulePath);
const ipcExports = require(ipcModulePath);

Object.defineProperty(process, 'platform', {{ configurable: true, value: 'linux' }});

const fakeWin = {{
    setTitleBarOverlay(arg) {{
        if (shouldThrowOverlay) {{
            throw new Error('unsupported');
        }}
        overlayCalls.push(arg);
    }},
}};
const storedUpdates = [];
let getItemsSyncCalls = 0;
const storageManager = {{
    getItemsSync() {{
        getItemsSyncCalls += 1;
        return utilsExports.__testStorage || {{}};
    }},
    async updateItems(obj) {{
        storedUpdates.push(obj);
    }},
}};

async function runTests() {{
    ipcExports.registerIpcHandlers(storageManager, {{ getWindow: () => fakeWin }});
    const handler = ipcHandlersMap.get('window:set-title-bar-overlay');
    assert.strictEqual(typeof handler, 'function');

    utilsExports.setMockState({{ curtainColor: '#162B37', themeMode: 'DARK', appStorage: {{}} }});
    await handler({{}}, {{ color: 'rgb(22, 43, 55)', symbolColor: '#efd' }});
    assert.deepStrictEqual(overlayCalls[0], {{
        color: '#162B37',
        symbolColor: '#EEFFDD',
        height: 30,
    }});
    assert.deepStrictEqual(storedUpdates[0], {{
        titleBarOverlayColor: '#162B37',
        titleBarOverlaySymbolColor: '#EEFFDD',
        titleBarOverlaySurfaceColor: '#162B37',
    }});

    // Throws and missing setTitleBarOverlay are ignored safely
    shouldThrowOverlay = true;
    await handler({{}}, {{ color: '#F3EFE8', symbolColor: '#162B37' }});
    shouldThrowOverlay = false;

    const noOverlayWin = {{}};
    ipcHandlersMap.clear();
    ipcExports.registerIpcHandlers(storageManager, {{ getWindow: () => noOverlayWin }});
    await ipcHandlersMap.get('window:set-title-bar-overlay')({{}}, {{ color: '#112233', symbolColor: '#ffffff' }});

    // Startup: matching surface uses persisted values
    storageManager.getItemsSync = () => {{
        getItemsSyncCalls += 1;
        return {{
            titleBarOverlayColor: '#1A3644',
            titleBarOverlaySymbolColor: '#EFE4D2',
            titleBarOverlaySurfaceColor: '#162B37',
        }};
    }};
    utilsExports.setMockState({{ curtainColor: '#162B37', themeMode: 'DARK' }});
    utilsExports.createWindow('about:blank', storageManager, {{}});
    assert.deepStrictEqual(browserWindowArgs[0].titleBarOverlay, {{
        color: '#1A3644',
        symbolColor: '#EFE4D2',
        height: 30,
    }});

    // Startup: mismatched surface falls back to curtainColor + WCAG contrast
    utilsExports.setMockState({{ curtainColor: '#F3EFE8', themeMode: 'LIGHT' }});
    utilsExports.createWindow('about:blank', storageManager, {{}});
    assert.deepStrictEqual(browserWindowArgs[1].titleBarOverlay, {{
        color: '#F3EFE8',
        symbolColor: '#383A42',
        height: 30,
    }});

    utilsExports.setMockState({{ curtainColor: '#162B37', themeMode: 'DARK' }});
    storageManager.getItemsSync = () => {{
        getItemsSyncCalls += 1;
        return {{
            titleBarOverlayColor: '#EFE4D2',
            titleBarOverlaySymbolColor: '#162B37',
            titleBarOverlaySurfaceColor: '#F3EFE8',
        }};
    }};
    utilsExports.createWindow('about:blank', storageManager, {{}});
    assert.deepStrictEqual(browserWindowArgs[2].titleBarOverlay, {{
        color: '#162B37',
        symbolColor: '#FAFAFA',
        height: 30,
    }});

    // Switch to win32: exact upstream behavior, zero storageManager reads/writes
    Object.defineProperty(process, 'platform', {{ configurable: true, value: 'win32' }});
    ipcHandlersMap.clear();
    ipcExports.registerIpcHandlers(storageManager, {{ getWindow: () => fakeWin }});
    const winHandler = ipcHandlersMap.get('window:set-title-bar-overlay');
    const updatesBeforeWin = storedUpdates.length;
    const overlayCallsBeforeWin = overlayCalls.length;
    await winHandler({{}}, {{ color: '#112233', symbolColor: '#abcdef' }});
    assert.strictEqual(overlayCalls.length, overlayCallsBeforeWin + 1);
    assert.deepStrictEqual(overlayCalls[overlayCalls.length - 1], {{
        color: '#112233',
        symbolColor: '#abcdef',
        height: 30,
    }});
    assert.strictEqual(storedUpdates.length, updatesBeforeWin);

    const syncCallsBeforeNonLinux = getItemsSyncCalls;
    utilsExports.setMockState({{ curtainColor: '#162B37', themeMode: 'DARK' }});
    utilsExports.createWindow('about:blank', storageManager, {{}});
    assert.strictEqual(getItemsSyncCalls, syncCallsBeforeNonLinux);
    assert.deepStrictEqual(browserWindowArgs[browserWindowArgs.length - 1].titleBarOverlay, {{
        color: '#131313',
        symbolColor: '#FAFAFA',
        height: 30,
    }});

    utilsExports.setMockState({{ curtainColor: '#F3EFE8', themeMode: 'LIGHT' }});
    utilsExports.createWindow('about:blank', storageManager, {{}});
    assert.strictEqual(getItemsSyncCalls, syncCallsBeforeNonLinux);
    assert.deepStrictEqual(browserWindowArgs[browserWindowArgs.length - 1].titleBarOverlay, {{
        color: '#FAFAFA',
        symbolColor: '#383A42',
        height: 30,
    }});

    // Switch to darwin: titleBarOverlay === false and IPC handler is a no-op
    Object.defineProperty(process, 'platform', {{ configurable: true, value: 'darwin' }});
    const overlayCallsBeforeMac = overlayCalls.length;
    const updatesBeforeMac = storedUpdates.length;
    await winHandler({{}}, {{ color: '#112233', symbolColor: '#abcdef' }});
    assert.strictEqual(overlayCalls.length, overlayCallsBeforeMac);
    assert.strictEqual(storedUpdates.length, updatesBeforeMac);

    utilsExports.setMockState({{ curtainColor: '#162B37', themeMode: 'DARK' }});
    utilsExports.createWindow('about:blank', storageManager, {{}});
    assert.strictEqual(getItemsSyncCalls, syncCallsBeforeNonLinux);
    assert.strictEqual(browserWindowArgs[browserWindowArgs.length - 1].titleBarOverlay, false);
}}

runTests().catch((err) => {{
    console.error(err);
    process.exit(1);
}});
"""
            proc = subprocess.run(
                [*cmd_prefix, "-e", harness_js],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                proc.returncode,
                0,
                f"JS runtime harness failed:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
