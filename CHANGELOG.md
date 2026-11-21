# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-11-21

### Changed

- Synced Light (`4000K Daylight`) and Dark (`2700K Warm Evening`) theme presets, installers, Linux ASAR titlebar patcher, manifest, and documentation to **100% parity with Bohemian Art Nouveau Design System v2.0.0** (`8c020ea`, Crisp Flat-Tonal Minimalism):
  - Anchored Light `background` on `#F3EFE8` (Warm Chalk; `12.77:1` AAA primary text, `11.07:1` AAA accent, `6.49:1` AA inline code) stepping through `#F1EADD` → `#F0E7D8` → `#EFE4D2`.
  - Updated Dark `code_foreground` seed from `#DFBE7A` to `#D4A853` (Amber Gold; `6.64:1` AA on `#162B37`).
  - Updated `apply_theme.py` to align `hubSurfaceBackgroundColor` and `titleBarOverlay*` surface tiers with KDE Light/Dark ground truth (`#F3EFE8`/`#F0E7D8`/`#162B37` Light; `#162B37`/`#193341`/`#EFE4D2` Dark).
  - Upgraded `patch_titlebar_overlay.py` to `V3` with Bohemian Linux fallback colors (`#F0E7D8`/`#162B37` Light, `#193341`/`#EFE4D2` Dark) and seamless `V1`/`V2` → `V3` in-place upgrade support while keeping upstream anchors and `win32`/`darwin` behavior untouched.
  - Updated `assets/logo.svg` inner arch, inner diamond, and crown dot accents from `#F3EFE8` to `#EFE4D2` (2700K Soft Alabaster ink on `#162B37`).
  - Synced `docs/bohemian-art-nouveau-preview.html`, `README.md`, and `plugin.json` (`2.0.0`) to Crisp Flat-Tonal Minimalism (`Newsreader`, `Inter`, `JetBrains Mono`, modern `4px`–`10px` radii, flat solid `#C29B53`/`#D4A853`, and KDE v2.0.0 16-page ground truth); removed stale 17-page `docs/PNG of PDF/`.

### Added

- Added Design System v2.0.0 reference tables to `README.md`: Crisp Flat-Tonal Minimalism typography & radii, stepped surface ladders and semantic statuses, core guardrails and banned hex list, Light & Dark WCAG contrast ratios for all 18 syntax tokens, and the 24-color Terminal ANSI palette.

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
