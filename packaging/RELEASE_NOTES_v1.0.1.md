# ThermoQ v1.0.1 — Release notes (vs v1.0.0)

**Tag:** `v1.0.1`  
**Installer:** `ThermoQ-1.0.1-Windows-Setup.exe`  
**Requires:** Windows 10/11 64-bit — **no Python install needed**

## What's new since v1.0.0

### Tools — Thermo-Calc Batch Data File generator
- New menu: **Tools → Generate Thermo-Calc Batch Data File** (before Extract Thermo-calc Results).
- Builds Property Model Calculator batch **Data Files** (`.xlsx` / `.csv`) with Thermo-Calc English headers.
- **General Models** presets: Coarsening, CET, Crack Susceptibility, Driving Force, Equilibrium, Freeze-in, Interfacial Energy, Liquidus/Solidus, Phase Transition, Scheil, Spinodal, T-Zero, Yield Strength.
- **Custom / Diffusion** mode: `Temperature` column layout (e.g. `Ti-Al-Mn-1173K.xlsx`).
- Temperature grid → model-specific `Param …` columns (Evaluation / Annealing / Start temperature, etc.).
- Sample under `Example/Generate Thermo-Calc Batch Data File/`.

### UI / packaging polish
- CAE-style theme and **Help → Language** i18n continue to refresh open tool windows (including the new Data File tool).
- In-window **plot preview** (Save As… / Open) across Plot tools and batch plots.
- User manuals (EN/ZH) updated with expanded menu table and §1.1 for Batch Data File; cover shows **Version 1.0.1**.
- Packaging includes `tc_batch_datafile.py`; installer / CI paths use `1.0.1`.

### Upgrade from v1.0.0
1. Uninstall ThermoQ 1.0.0 (optional but recommended) or install over the same folder.
2. Run `ThermoQ-1.0.1-Windows-Setup.exe`.
3. Existing Documents\ThermoQ plot outputs are unchanged.
4. New feature appears under **Tools**; no change to Pandat import / extract file formats.

## Publish checklist (GitHub)
```text
1. Commit version bumps + manuals + packaging
2. git tag v1.0.1 && git push origin v1.0.1
   (or attach dist\ThermoQ-1.0.1-Windows-Setup.exe to a manual Release)
3. Release title: ThermoQ 1.0.1 Windows Setup
4. Paste this file as the release body (or summarize in Chinese/English)
```

---

## 相对 v1.0.0 的升级说明（中文摘要）

- **新工具**：Tools → 生成 Thermo-Calc 批处理 Data File（位于提取结果之前），支持全部 General Models + 自定义/扩散 Temperature 列格式。
- **说明书**：中英文 PDF 更新菜单表与 §1.1 Data File 说明；封面标注 1.0.1。
- **安装包**：`ThermoQ-1.0.1-Windows-Setup.exe`（约 170+ MB），无需 Python。
- **升级方式**：卸载或覆盖安装 1.0.0；用户文档目录下的出图文件不受影响。
