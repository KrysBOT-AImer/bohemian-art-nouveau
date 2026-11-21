# Bohemian Art Nouveau (`bohemian-art-nouveau`)

[![Version](https://img.shields.io/badge/version-v2.0.0-1A3644)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-7B8C7E)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-6C4F3D)](#seamless-1-command-installation-linux--windows)
[![Antigravity](https://img.shields.io/badge/Antigravity-2.33.0%2B-D4A853)](#compatibility-note-antigravity-2-v2330)
[![CI](https://github.com/KrysBOT-AImer/bohemian-art-nouveau/actions/workflows/ci.yml/badge.svg)](https://github.com/KrysBOT-AImer/bohemian-art-nouveau/actions/workflows/ci.yml)

Dual-lighting **4000K Daylight (Light)** and **2700K Warm Evening (Dark)** themes for **Antigravity 2**, built on **Bohemian Art Nouveau Design System v2.0.0** (**Crisp Flat-Tonal Minimalism**) and the architectural **60-25-10-5** color balance:

- **4000K Daylight (Light)**: **60%** Warm Chalk primary view (`#F3EFE8`), **25%** Stepped Alabaster surfaces & controls (`#F1EADD`–`#EFE4D2`), **10%** Midnight Petrol ink & active controls (`#162B37`–`#1A3644`), **5%** flat solid Warm Gold borders (`#C29B53`) + Smoked Walnut (`#6C4F3D`) & semantic accents.
- **2700K Warm Evening (Dark)**: **60%** Midnight Petrol canvas (`#162B37`), **25%** Stepped Midnight Petrol chrome/controls (`#18313E`–`#1A3644`), **10%** Soft Alabaster ink (`#EFE4D2`), **5%** flat solid Amber Gold selection/focus (`#D4A853`) + semantic accents.

---

## Compatibility Note (Antigravity 2 v2.33.0)

- **Works Immediately Today (Linux & Windows)**: Custom UI seeds (`Background`, `Foreground`, `Accent`, plus `primaryForegroundOverride` and `codeForegroundOverride`) paired with the built-in **`Gruvbox Material`** syntax preset work out of the box in Antigravity 2 v2.33.0.
- **Future-Ready 18-Token Plugin Preset**: The full 18-token custom syntax presets in `themes/bohemian-art-nouveau-light.json` and `themes/bohemian-art-nouveau-dark.json` adhere strictly to Antigravity 2's native `PluginThemeItem` schema. Running the installer automatically copies the runtime plugin bundle into `~/.gemini/config/plugins/bohemian-art-nouveau/` (or `%USERPROFILE%\.gemini\config\plugins\bohemian-art-nouveau\` on Windows) so it becomes selectable directly from **Settings → Appearance → Preset** as soon as Antigravity 2 enables `enablePluginThemes` for general users.

---

## Getting the Theme

1. **Download from GitHub Releases**: Download and extract `bohemian-art-nouveau-v2.0.0.zip` (or `.tar.gz`) from [GitHub Releases](https://github.com/KrysBOT-AImer/bohemian-art-nouveau/releases/latest).
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

## Linux Dynamic Titlebar Fix (`titleBarOverlay`)

> **Linux-only:** `patch_titlebar_overlay.py` is exclusively for Linux. Windows natively supports `titleBarOverlay` and macOS uses native window chrome, so the CLI safely refuses to run on non-Linux systems (`unsupported_platform` exit `1`, or `skipped_non_linux` exit `0` with `--fail-safe`) with zero filesystem changes. The injected `V3` patch supports seamless `V1`/`V2` → `V3` in-place upgrades and keeps upstream `win32`/`darwin` JS behavior 100% untouched.

On Linux, Antigravity 2 v2.33.0 gates Electron's `window:set-title-bar-overlay` IPC handler to `win32` and initializes `titleBarOverlay` with a hardcoded `#131313` dark / `#FAFAFA` light box behind the top-right window controls (`_ □ ×`).

`patch_titlebar_overlay.py` (`V3`) applies a pure-Python stdlib patch directly to `/opt/Antigravity/resources/app.asar` (creating a timestamped `.bak` backup and recalculating full SHA-256 ASAR integrity metadata) that aligns Linux startup fallback colors with Bohemian `Header` / `WM Active` titlebar surfaces (`#F0E7D8` background / `#162B37` symbols in Light; `#193341` background / `#EFE4D2` symbols in Dark) and dynamically updates both the titlebar overlay background and WCAG contrast-aware button symbols on theme switches with zero startup flash:

```bash
# 1. Inspect /opt/Antigravity/resources/app.asar and simulate the patch (read-only)
python3 patch_titlebar_overlay.py --check
python3 patch_titlebar_overlay.py --dry-run

# 2. Apply the patch (requires root for /opt/Antigravity), then restart Antigravity 2
sudo python3 patch_titlebar_overlay.py --apply

# 3. Optional (Arch Linux): install a fail-safe pacman PostTransaction hook
#    so future `antigravity` package upgrades automatically re-apply the patch
sudo python3 patch_titlebar_overlay.py --install-hook

# Restore the original app.asar backup or remove the pacman hook anytime
sudo python3 patch_titlebar_overlay.py --restore
sudo python3 patch_titlebar_overlay.py --uninstall-hook
```

---

## 30-Second Manual Setup (Settings → Appearance)

> **Warning:** **Always select the `Gruvbox Material` Preset FIRST before entering custom hex codes.** Changing the Preset in Antigravity 2 resets your custom UI seed fields.

1. Open **Settings → Appearance**.
2. Set **Preset** to **`Gruvbox Material`** first.
3. Enter the copy-paste values below for Light and/or Dark mode:

| Mode | Background (`background`) | Foreground (`foregroundOverride`) | Accent (`primary`) |
| --- | --- | --- | --- |
| **Light (4000K Daylight)** | `#F3EFE8` | `#162B37` | `#1A3644` |
| **Dark (2700K Warm Evening)** | `#162B37` | `#EFE4D2` | `#D4A853` |

> **Note:** The CLI installer (`apply_theme.py --apply`) also populates `primaryForegroundOverride` (`#F3EFE8` Light / `#162B37` Dark) and `codeForegroundOverride` (`#6C4F3D` Light / `#D4A853` Dark) in `config.json`, which are not exposed as separate inputs in the Appearance UI.

---

## Palette & WCAG Contrast Table

| Role | Light Mode | Dark Mode | Light Contrast | Dark Contrast |
| --- | --- | --- | --- | --- |
| **Primary Text on Canvas** | `#162B37` on `#F3EFE8` | `#EFE4D2` on `#162B37` | `12.77:1` (AAA) | `11.64:1` (AAA) |
| **Accent on Canvas** | `#1A3644` on `#F3EFE8` | `#D4A853` on `#162B37` | `11.07:1` (AAA) | `6.64:1` (AA) |
| **Button Text on Accent** | `#F3EFE8` on `#1A3644` | `#162B37` on `#D4A853` | `11.07:1` (AAA) | `6.64:1` (AA) |
| **Inline Code on Canvas** | `#6C4F3D` on `#F3EFE8` | `#D4A853` on `#162B37` | `6.49:1` (AA) | `6.64:1` (AA) |

---

## Design System v2.0.0 Reference

- **Design Direction**: **Crisp Flat-Tonal Minimalism** (sole heritage: calibrated 2700K–4000K color palette; flat solid `#C29B53` / `#D4A853`; zero gradients, zero fluting, zero Secessionist ornaments).
- **Typography**: `Newsreader` (Display & H1) · `Inter` (H2–H6 & UI) · `JetBrains Mono` (Code & Telemetry).
- **Modern Radii**: `--radius-sm: 4px`, `--radius-md: 6px`, `--radius-lg: 8px`, `--radius-xl: 10px`, `--radius-pill: 9999px`.

### Stepped Surface Ladders & Semantic Statuses

| Lighting System | Surface Ladder (`View` → Elevated) | Semantic Statuses & Links |
| --- | --- | --- |
| **4000K Daylight (Light)** | `#F3EFE8` → `#F1EADD` → `#F0E7D8` → `#EFE4D2` (+ Complementary Dark `#162B37` / `#18313E`) | Pos `#47634D` · Neu `#7A581B` · Neg `#9A412A` · Muted `#59656A` · Link `#6C4F3D` · Visited `#5A3D4D` |
| **2700K Warm Evening (Dark)** | `#162B37` → `#172E3A` → `#18313E` → `#193341` → `#1A3644` | Pos `#91A895` · Neu `#D99330` · Neg `#E6866B` · Muted `#9EA29D` · Link `#C29B53` · Visited `#A89FAD` |

### Core Guardrails

- **Warm Gold Restraint (4000K Light)**: Flat solid `#C29B53` is reserved strictly for subtle active indicators, hover borders, and hairline dividers—never for large surface fills, gradients, or body text on light surfaces.
- **Amber Gold Selection (2700K Dark)**: Flat solid `#D4A853` serves as the primary active selection fill, CTA background, and focus ring paired with `#162B37` ink (`6.64:1` AA).
- **Functional-Only Blue (4000K Light)**: `#1A3644` and `#162B37` are reserved strictly for primary CTAs, active selections, and dark Complementary navigation rails (never decorative light-page pills).
- **Strict Surface Bounds & Banned Colors**: All Light surfaces stay strictly inside `[#EFE4D2, #F3EFE8]` and all Dark surfaces inside `[#162B37, #1A3644]`, with zero gradients or ornamental chrome. The following 10 hex codes are strictly banned: `#FBFAF8`, `#1F333F`, `#213540`, `#233742`, `#2B414D`, `#1A2E3A`, `#244657`, `#1A4D66`, `#FFFFFF`, `#000000`.

---

## 18-Token Custom Syntax Reference

Defined in [bohemian-art-nouveau-light.json](themes/bohemian-art-nouveau-light.json) and [bohemian-art-nouveau-dark.json](themes/bohemian-art-nouveau-dark.json):

| Token | Light (`on #F3EFE8`) | Light Contrast | Dark (`on #162B37`) | Dark Contrast |
| --- | --- | --- | --- | --- |
| `comment` | `#7B8C7E` | `3.11:1` (AA Large / UI) | `#7B8C7E` | `4.11:1` (AA Large / UI) |
| `punctuation` | `#6C4F3D` | `6.49:1` (AA) | `#C8BEAF` | `7.97:1` (AAA) |
| `property` | `#9E6B47` | `3.94:1` (AA Large / UI) | `#C29B53` | `5.65:1` (AA) |
| `deleted` | `#B85D43` | `3.91:1` (AA Large / UI) | `#C66347` | `3.68:1` (AA Large / UI) |
| `inserted` | `#7B8C7E` | `3.11:1` (AA Large / UI) | `#7B8C7E` | `4.11:1` (AA Large / UI) |
| `tag` | `#4E3242` | `9.86:1` (AAA) | `#D6A692` | `6.78:1` (AA) |
| `constant` | `#B85D43` | `3.91:1` (AA Large / UI) | `#C78A3A` | `4.97:1` (AA) |
| `number` | `#B85D43` | `3.91:1` (AA Large / UI) | `#D99330` | `5.69:1` (AA) |
| `string` | `#6C4F3D` | `6.49:1` (AA) | `#E8BA9B` | `8.31:1` (AAA) |
| `attrName` | `#9E6B47` | `3.94:1` (AA Large / UI) | `#D6A692` | `6.78:1` (AA) |
| `builtin` | `#946F2D` | `4.01:1` (AA Large / UI) | `#B38B40` | `4.66:1` (AA) |
| `operator` | `#2A2C30` | `12.20:1` (AAA) | `#E0D9CE` | `10.44:1` (AAA) |
| `variable` | `#162B37` | `12.77:1` (AAA) | `#EFE4D2` | `11.64:1` (AAA) |
| `attrValue` | `#7A4D33` | `6.24:1` (AA) | `#E8BA9B` | `8.31:1` (AAA) |
| `keyword` | `#5A3D4D` | `8.29:1` (AAA) | `#A89FAD` | `5.73:1` (AA) |
| `function` | `#1A3644` | `11.07:1` (AAA) | `#D4A853` | `6.64:1` (AA) |
| `className` | `#946F2D` | `4.01:1` (AA Large / UI) | `#DFBE7A` | `8.21:1` (AAA) |
| `regex` | `#7A4D33` | `6.24:1` (AA) | `#AD734A` | `3.71:1` (AA Large / UI) |

---

## 24-Color Terminal ANSI Reference

- **4000K Daylight Terminal**: Background `#F3EFE8`, Foreground `#162B37` (`12.77:1` AAA)
- **2700K Warm Evening Terminal**: Background `#162B37`, Foreground `#EFE4D2` (`11.64:1` AAA)

| ANSI Slot | Light Normal | Light Intense | Light Faint | Dark Normal | Dark Intense | Dark Faint |
| --- | --- | --- | --- | --- | --- | --- |
| `Color0` (Black) | `#162B37` | `#59656A` | `#374851` | `#1A3644` | `#7B8C7E` | `#172E3A` |
| `Color1` (Red) | `#9A412A` | `#B85D43` | `#8A5042` | `#E07A5F` | `#EC967E` | `#B0624E` |
| `Color2` (Green) | `#47634D` | `#5D7A63` | `#516456` | `#91A895` | `#ABC2AF` | `#718675` |
| `Color3` (Yellow) | `#7A581B` | `#946F2D` | `#6D5B39` | `#D4A853` | `#DFBE7A` | `#A38242` |
| `Color4` (Blue) | `#1A3644` | `#28556B` | `#384E57` | `#6FA3B8` | `#8FC0D4` | `#578091` |
| `Color5` (Magenta) | `#5A3D4D` | `#785368` | `#5A4D55` | `#B5A8BE` | `#CCC1D4` | `#8D8294` |
| `Color6` (Cyan) | `#2E5E63` | `#3D767C` | `#436165` | `#7DB5A8` | `#9BCBC0` | `#618E83` |
| `Color7` (White) | `#6C4F3D` | `#85644E` | `#64574D` | `#C8BEAF` | `#EFE4D2` | `#9B9386` |

---

## Offline Preview & Design Reference

- [`docs/bohemian-art-nouveau-preview.html`](docs/bohemian-art-nouveau-preview.html): Offline interactive Light/Dark UI & syntax preview.
- [`docs/nymburk_art_nouveau_palette.html`](docs/nymburk_art_nouveau_palette.html): Original Czech "Nymburk 1902" Bohemian Art Nouveau interior palette reference.

---

## Repository Structure

```text
bohemian-art-nouveau/
├── .github/workflows/ci.yml                 # Linux & Windows unit test CI
├── assets/logo.svg                          # Vector plugin emblem
├── docs/                                    # Offline HTML preview & palette reference
├── tests/test_patch_titlebar_overlay.py     # Cross-platform ASAR patcher & JS tests
├── tests/test_theme.py                      # Schema, palette, WCAG, lifecycle & PII tests
├── themes/                                  # Light & Dark PluginThemeItem JSON presets
├── CHANGELOG.md                             # Release history
├── LICENSE                                  # MIT License
├── README.md                                # Documentation
├── apply_theme.py                           # Cross-platform CLI installer & theme applier
├── patch_titlebar_overlay.py                # Pure-Python ASAR patcher & pacman hook CLI
└── plugin.json                              # Antigravity 2 plugin manifest
```

---

## Running Tests

```bash
python3 -B -m unittest discover -s tests -v
```

---

## License

Licensed under the [MIT License](LICENSE) (Copyright 2026 `KrysBOT-AImer`). See [`CHANGELOG.md`](CHANGELOG.md) for release notes.
