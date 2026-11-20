# Bohemian Art Nouveau (`bohemian-art-nouveau`)

[![Version](https://img.shields.io/badge/version-v1.0.0-1A3644)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-7B8C7E)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-6C4F3D)](#seamless-1-command-installation-linux--windows)
[![Antigravity](https://img.shields.io/badge/Antigravity-2.33.0%2B-D4A853)](#compatibility-note-antigravity-2-v2330)
[![CI](https://github.com/KrysBOT-AImer/bohemian-art-nouveau/actions/workflows/ci.yml/badge.svg)](https://github.com/KrysBOT-AImer/bohemian-art-nouveau/actions/workflows/ci.yml)

Paired **Light (4000K Day)** and **Dark (2700K Evening)** themes for **Antigravity 2**, built strictly on the architectural **60-25-10-5** color balance:

- **60% Canvas & Surfaces**: Warm parchment (`#F3EFE8`) for daytime clarity; deep Prussian petrol (`#162B37`) for low-glare evening focus.
- **25% Primary Typography & Structural Ink**: High-contrast Prussian ink (`#162B37`) in Light mode; warm vellum (`#EFE4D2`) in Dark mode.
- **10% Accents & Interactive Focus**: Deep teal-slate (`#1A3644`) in Light mode; antique burnished gold (`#D4A853`) in Dark mode.
- **5% Semantic & Syntax Highlights**: Botanical sage, terracotta, ochre, and plum accents tuned for readable code and diffs.

---

## Compatibility Note (Antigravity 2 v2.33.0)

- **Works Immediately Today (Linux & Windows)**: Custom UI seeds (`Background`, `Foreground`, `Accent`, plus `primaryForegroundOverride` and `codeForegroundOverride`) paired with the built-in **`Gruvbox Material`** syntax preset work out of the box in Antigravity 2 v2.33.0.
- **Future-Ready 18-Token Plugin Preset**: The full 18-token custom syntax presets in `themes/bohemian-art-nouveau-light.json` and `themes/bohemian-art-nouveau-dark.json` adhere strictly to Antigravity 2's native `PluginThemeItem` schema. Running the installer automatically copies the runtime plugin bundle into `~/.gemini/config/plugins/bohemian-art-nouveau/` (or `%USERPROFILE%\.gemini\config\plugins\bohemian-art-nouveau\` on Windows) so it becomes selectable directly from **Settings → Appearance → Preset** as soon as Antigravity 2 enables `enablePluginThemes` for general users.

---

## Getting the Theme

1. **Download from GitHub Releases**: Download and extract `bohemian-art-nouveau-v1.0.0.zip` (or `.tar.gz`) from [GitHub Releases](https://github.com/KrysBOT-AImer/bohemian-art-nouveau/releases/latest).
2. **Or Clone the Repository**:
   ```bash
   git clone https://github.com/KrysBOT-AImer/bohemian-art-nouveau.git && cd bohemian-art-nouveau
   ```

---

## Seamless 1-Command Installation (Linux & Windows)

`apply_theme.py` uses only the Python 3 standard library (no `pip` packages required), creates timestamped `.bak` backups before modifying any file, writes JSON atomically, and refuses to edit `config.json` or `app_storage.json` while Antigravity 2 is running.

### Linux

```bash
# 1. Preview changes without modifying any files
python3 apply_theme.py --dry-run

# 2. Close Antigravity 2, then apply both Light & Dark themes + install plugin
python3 apply_theme.py --apply
```

### Windows (PowerShell / CMD)

```powershell
# 1. Preview changes without modifying any files
py apply_theme.py --dry-run

# 2. Close Antigravity 2, then apply both Light & Dark themes + install plugin
py apply_theme.py --apply
```

### Other Useful Commands

| Command | Behavior | Safe While Antigravity Is Open? |
| --- | --- | --- |
| `python3 apply_theme.py --install-plugin` | Copies only runtime plugin files (`plugin.json`, `README.md`, `LICENSE`, `assets/logo.svg`, `themes/*.json`) into the plugins directory | Yes |
| `python3 apply_theme.py --apply --mode light` | Applies Light theme seeds & preset only | No (close Antigravity 2 first) |
| `python3 apply_theme.py --apply --mode dark` | Applies Dark theme seeds & preset only | No (close Antigravity 2 first) |
| `python3 apply_theme.py --restore` | Atomically restores the latest `.bak` backups of `config.json` and `app_storage.json` | No (close Antigravity 2 first) |
| `python3 apply_theme.py --uninstall` | Removes the installed plugin directory and resets custom seeds and presets to defaults | No (close Antigravity 2 first) |

### Configuration & Plugin Paths

| File / Directory | Linux | Windows |
| --- | --- | --- |
| User Config | `~/.gemini/config/config.json` | `%USERPROFILE%\.gemini\config\config.json` |
| Plugins Directory | `~/.gemini/config/plugins/bohemian-art-nouveau/` | `%USERPROFILE%\.gemini\config\plugins\bohemian-art-nouveau\` |
| App Storage | `~/.config/Antigravity/app_storage.json` (or `$XDG_CONFIG_HOME/Antigravity/app_storage.json`) | `%APPDATA%\Antigravity\app_storage.json` |

---

## 30-Second Manual Setup (Settings → Appearance)

> **Warning:** **Always select the `Gruvbox Material` Preset FIRST before entering custom hex codes.** Changing the Preset in Antigravity 2 resets your custom UI seed fields.

1. Open **Settings → Appearance**.
2. Set **Preset** to **`Gruvbox Material`** first.
3. Enter the copy-paste values below for Light and/or Dark mode:

| Mode | Background (`background`) | Foreground (`foregroundOverride`) | Accent (`primary`) |
| --- | --- | --- | --- |
| **Light (4000K Day)** | `#F3EFE8` | `#162B37` | `#1A3644` |
| **Dark (2700K Evening)** | `#162B37` | `#EFE4D2` | `#D4A853` |

> **Note:** The CLI installer (`apply_theme.py --apply`) also populates `primaryForegroundOverride` (`#F3EFE8` Light / `#162B37` Dark) and `codeForegroundOverride` (`#6C4F3D` Light / `#DFBE7A` Dark) in `config.json`, which are not exposed as separate inputs in the Appearance UI.

---

## Palette & WCAG Contrast Table

| Role | Light Mode | Dark Mode | Light Contrast | Dark Contrast |
| --- | --- | --- | --- | --- |
| **Primary Text on Canvas** | `#162B37` on `#F3EFE8` | `#EFE4D2` on `#162B37` | `12.77:1` (AAA) | `11.64:1` (AAA) |
| **Accent on Canvas** | `#1A3644` on `#F3EFE8` | `#D4A853` on `#162B37` | `11.07:1` (AAA) | `6.64:1` (AA+) |
| **Button Text on Accent** | `#F3EFE8` on `#1A3644` | `#162B37` on `#D4A853` | `11.07:1` (AAA) | `6.64:1` (AA+) |
| **Inline Code on Canvas** | `#6C4F3D` on `#F3EFE8` | `#DFBE7A` on `#162B37` | `6.49:1` (AA+) | `8.21:1` (AAA) |

---

## 18-Token Custom Syntax Reference

Defined in [bohemian-art-nouveau-light.json](themes/bohemian-art-nouveau-light.json) and [bohemian-art-nouveau-dark.json](themes/bohemian-art-nouveau-dark.json):

| Token | Light (`4000K Day`) | Dark (`2700K Evening`) |
| --- | --- | --- |
| `comment` | `#7B8C7E` | `#7B8C7E` |
| `punctuation` | `#6C4F3D` | `#C8BEAF` |
| `property` | `#9E6B47` | `#C29B53` |
| `deleted` | `#B85D43` | `#C66347` |
| `inserted` | `#7B8C7E` | `#7B8C7E` |
| `tag` | `#4E3242` | `#D6A692` |
| `constant` | `#B85D43` | `#C78A3A` |
| `number` | `#B85D43` | `#D99330` |
| `string` | `#6C4F3D` | `#E8BA9B` |
| `attrName` | `#9E6B47` | `#D6A692` |
| `builtin` | `#946F2D` | `#B38B40` |
| `operator` | `#2A2C30` | `#E0D9CE` |
| `variable` | `#162B37` | `#EFE4D2` |
| `attrValue` | `#7A4D33` | `#E8BA9B` |
| `keyword` | `#5A3D4D` | `#A89FAD` |
| `function` | `#1A3644` | `#D4A853` |
| `className` | `#946F2D` | `#DFBE7A` |
| `regex` | `#7A4D33` | `#AD734A` |

---

## Offline Preview & Design Reference

- [`docs/bohemian-art-nouveau-preview.html`](docs/bohemian-art-nouveau-preview.html): Offline interactive Light/Dark UI & syntax preview.
- [`docs/nymburk_art_nouveau_palette.html`](docs/nymburk_art_nouveau_palette.html): Original Czech "Nymburk 1902" Bohemian Art Nouveau interior palette reference.

---

## Repository Structure

```text
bohemian-art-nouveau/
├── .github/workflows/ci.yml   # Linux & Windows unit test CI
├── assets/logo.svg            # Vector plugin emblem
├── docs/                      # Offline HTML preview & palette reference
├── tests/test_theme.py        # Schema, palette, WCAG, lifecycle & PII tests
├── themes/                    # Light & Dark PluginThemeItem JSON presets
├── CHANGELOG.md               # Release history
├── LICENSE                    # MIT License
├── README.md                  # Documentation
├── apply_theme.py             # Cross-platform CLI installer & theme applier
└── plugin.json                # Antigravity 2 plugin manifest
```

---

## Running Tests

```bash
python3 -B -m unittest discover -s tests -v
```

---

## License

Licensed under the [MIT License](LICENSE) (Copyright 2026 `KrysBOT-AImer`). See [`CHANGELOG.md`](CHANGELOG.md) for release notes.
