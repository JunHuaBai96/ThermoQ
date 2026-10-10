# ThermoQ v1.0.2 — Release notes (vs v1.0.1)

**Tag:** `v1.0.2`  
**Installer:** `ThermoQ-1.0.2-Windows-Setup.exe`  
**Requires:** Windows 10/11 64-bit — **no Python install needed**

## What's new since v1.0.1

### Tools — TriST Zone (Pandat & Thermo-Calc Gibbs)
- **Thermodynamic criterion**: TriST region = `{ΔG ≤ 0}` with `ΔG = Gs − Gl` (solid-stable / T0-interior side).
- **T0 as check standard**: primary T0 is sheet `T0_lines` (2D `ΔG = 0` contours). `T0_tie_1D` is an auxiliary per-temperature summary derived from `T0_lines` (fixes empty TC aux tables).
- **Solid phase selection**: default = lowest `Gs` at each `(T, C*)`; optional prefer **FCC / BCC / HCP**.
- **Coordinates**: prefer mole fractions `x(*)` when available; composition simplex masking; no nearest-neighbor projection onto the simplex.
- **Workbook quality**: `TriST_meta` + Status report Hausdorff distance (`T0_lines` vs `TriST_boundaries`) and mask⊂T0 checks; mask flag renamed to `below_T0_dG_le_0`.
- **Visualize TriST**: default **Overlay T0_lines (check standard)**; optional geometric-tangent field demoted (not μ-based).
- **Numerics / performance**: NaN-safe grids, remask after RGI (no sentinel fill), contourpy-friendly paths.

### Docs / packaging
- User manuals (EN/ZH) updated for TriST / T0 menu settings; cover shows **Version 1.0.2**.
- Windows installer and file version resources bumped to **1.0.2**.

### Upgrade from v1.0.1
1. Uninstall ThermoQ 1.0.1 (optional) or install over the same folder.
2. Run `ThermoQ-1.0.2-Windows-Setup.exe`.
3. Existing `Documents\ThermoQ` plot outputs are unchanged.
4. Re-run **Extract → TriST Zone** if you need the new sheets/columns (`TriST_meta`, `below_T0_dG_le_0`, filled `T0_tie_1D`). Older TriST workbooks still open for visualization.

## Publish checklist (GitHub)
```text
1. Commit version bumps + manuals + packaging + TriST fixes
2. git tag v1.0.2 && git push origin v1.0.2
   (or attach dist\ThermoQ-1.0.2-Windows-Setup.exe to a manual Release)
3. Release title: ThermoQ 1.0.2 Windows Setup
4. Paste this file as the release body (or summarize in Chinese/English)
```

---

## 相对 v1.0.1 的升级说明（中文摘要）

- **TriST 判据**：区域 = `{ΔG≤0}`，`ΔG=Gs−Gl`（固稳侧 / T0 内侧）。
- **T0 检查标准**：主标准为 `T0_lines`；`T0_tie_1D` 由其汇总；Status / `TriST_meta` 含 Hausdorff 与 mask⊂T0 检查。
- **固相选择**：默认最低 `Gs`，可选优先 FCC/BCC/HCP；坐标优先 `x(*)`。
- **可视化**：默认叠加 `T0_lines`；掩码列更名为 `below_T0_dG_le_0`。
- **说明书 / 安装包**：中英文 PDF 与 `ThermoQ-1.0.2-Windows-Setup.exe`（无需 Python）。
- **升级方式**：卸载或覆盖安装 1.0.1；旧 TriST 工作簿仍可可视化，需新列/检查时请重新提取。
