# ThermoQ

[English](#english) | [中文](#中文)

<<<<<<< Updated upstream
<img width="1024" height="1024" alt="logo" src="https://github.com/user-attachments/assets/6486eb41-5c75-4f08-9e41-05c480f2e39b" />

## 功能特点
=======
---
>>>>>>> Stashed changes

## English

ThermoQ is a desktop application for thermodynamic workflows (Pandat / Thermo-Calc data ingestion, batch computations, and rich visualization).

### Highlights

- **GUI-first** workflow with batch generators, extractors, and plotters.
- **Pandat import**: load `P.xlsx`, `Ts.xlsx` (required) and `P-S.xlsx`, `Ts-S.xlsx` (optional).
- **Calculate**:
  - **Single composition**
  - **Composition space (batch)**: Lever / Scheil / All sources; export selected columns to **CSV/Excel**; batch plot generation.
- **Results viewer**: save results as **Excel / CSV / TXT / DAT**.
- **Language**: **Help → Language** switches UI between English and 中文.

### Tools (selected)

- **Generate Pandat Batch File** (`.pbfx`)
  - Placeholders `%X%` detect elements.
  - Composition base from `<unit name="n" value="w%|x%|w|x" />`: total = 100 for `%`, total = 1 for fractions.
  - Gibbs tab supports `%T%` and reads `<unit name="T" value="K|C|F" />` for filename suffixes.
  - Balance mode: remove exactly one element row (that element becomes `total - Σ(swept)`), or keep all rows and check “balance last in list”.
- **Extract Pandat Results**
  - **P/Ts (Lever/Scheil)**: generates `P.xlsx`, `Ts.xlsx`, `P-S.xlsx`, `Ts-S.xlsx` from Pandat All table folders (`.csv` / `.dat` supported).
  - **T-zero**: generates `T0.xlsx` from Pandat `All table_T0`.
  - **TriST Zone**: generates TriST workbook + Plotly visualization.

### Requirements

- **Python**: 3.6+
- Install dependencies:

```bash
pip install -r requirements.txt
```

Optional packages enable extra plots:
- `matplotlib` for 2D/3D static + GIF
- `plotly` for interactive 3D
- `scikit-learn` / `scipy` for smoothing/interpolation fallbacks

### Run

```bash
python main.py
```

---

## 中文

ThermoQ 是一个用于热力学计算工作流的桌面应用（支持 Pandat / Thermo-Calc 数据导入、批量计算与可视化）。

### 亮点功能

- 图形界面，流程直观。
- **Pandat 导入**：支持 `P.xlsx`、`Ts.xlsx`（必需）和 `P-S.xlsx`、`Ts-S.xlsx`（可选）。
- **Calculate**：
  - **单点成分**
  - **Composition space (batch)**：Lever / Scheil / All；选列导出 CSV/Excel；批量出图。
- 结果窗口支持保存 **Excel / CSV / TXT / DAT**。
- **Help → Language**：英文/中文切换。

### 依赖与运行

```bash
pip install -r requirements.txt
python main.py
```

