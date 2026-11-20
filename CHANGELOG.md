# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-20

### Added

- Paired **Light (`4000K Day`)** and **Dark (`2700K Evening`)** Antigravity 2 themes based on the 60-25-10-5 Bohemian Art Nouveau architectural palette.
- 5-seed UI configuration + future-ready 18-token `PluginThemeItem` JSON presets (`themes/bohemian-art-nouveau-light.json`, `themes/bohemian-art-nouveau-dark.json`) and vector plugin emblem (`assets/logo.svg`).
- Zero-dependency cross-platform Python 3 CLI (`apply_theme.py`) with `--dry-run`, `--apply`, `--install-plugin`, `--restore`, `--uninstall`, atomic JSON writes, POSIX `0600` preservation, timestamped `.bak` backups, and running-process safety guard.
- Offline HTML preview (`docs/bohemian-art-nouveau-preview.html`) and historical Czech design reference (`docs/nymburk_art_nouveau_palette.html`).
- Automated `unittest` suite covering manifest schema, palette hex allowlist, WCAG AAA/AA+ contrasts, CLI lifecycle, offline preview integrity, and PII hygiene, plus GitHub Actions CI for Linux and Windows.
- MIT License (`LICENSE`).
