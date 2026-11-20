# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-20

### Added

- Pure-Python stdlib Linux-only ASAR patcher (`patch_titlebar_overlay.py`) enabling dynamic `titleBarOverlay` updates and startup persistence in Antigravity 2 on Linux, with atomic writes, timestamped `.bak` backups, full SHA-256 ASAR integrity recalculation, and optional fail-safe Arch Linux `pacman` `PostTransaction` hook (`--install-hook` / `--uninstall-hook`).
- Cross-platform unit & Node runtime test suite (`tests/test_patch_titlebar_overlay.py`) covering ASAR Pickle alignment, integrity verification, non-Linux refusal, `V1` → `V2` upgrade, `pacman` hook lifecycle, and `linux` vs `win32`/`darwin` runtime behavior.

### Changed

- Strict Linux-only enforcement on both layers: the Python CLI cleanly refuses Windows and macOS (`unsupported_platform` exit `1`, or `skipped_non_linux` exit `0` under `--fail-safe`) with zero filesystem mutations; the injected JS (`V2`) gates all overlay persistence and startup overrides strictly on `process.platform === 'linux'` so upstream `win32` behavior remains 100% untouched, with seamless in-place `V1` → `V2` upgrade support (`--check` reports `outdated_v1` with exit `2`).

## [1.0.0] - 2026-11-20

### Added

- Paired **Light (`4000K Day`)** and **Dark (`2700K Evening`)** Antigravity 2 themes based on the 60-25-10-5 Bohemian Art Nouveau architectural palette.
- 5-seed UI configuration + future-ready 18-token `PluginThemeItem` JSON presets (`themes/bohemian-art-nouveau-light.json`, `themes/bohemian-art-nouveau-dark.json`) and vector plugin emblem (`assets/logo.svg`).
- Zero-dependency cross-platform Python 3 CLI (`apply_theme.py`) with `--dry-run`, `--apply`, `--install-plugin`, `--restore`, `--uninstall`, atomic JSON writes, POSIX `0600` preservation, timestamped `.bak` backups, and running-process safety guard.
- Offline HTML preview (`docs/bohemian-art-nouveau-preview.html`) and historical Czech design reference (`docs/nymburk_art_nouveau_palette.html`).
- Automated `unittest` suite covering manifest schema, palette hex allowlist, WCAG AAA/AA+ contrasts, CLI lifecycle, offline preview integrity, and PII hygiene, plus GitHub Actions CI for Linux and Windows.
- MIT License (`LICENSE`).
