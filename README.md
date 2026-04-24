# ThermoQ

[English](#english) | [中文](#中文)

<img width="1024" height="1024" alt="logo" src="https://github.com/user-attachments/assets/6486eb41-5c75-4f08-9e41-05c480f2e39b" />

---

## English

ThermoQ is a desktop application for thermodynamic workflows (Pandat / Thermo-Calc data ingestion, batch computations, and rich visualization).

### Highlights

- **GUI-first** workflow with batch generators, extractors, and plotters.
- **Internationalization (i18n)**: switch UI language via **Help → Language** (English / 中文). Tool windows refresh after language change.
- **Pandat import**: load `P.xlsx`, `Ts.xlsx` (required) and `P-S.xlsx`, `Ts-S.xlsx` (optional).
- **Results viewer**: save results as **Excel / CSV / TXT / DAT**.

### Main workflows

- **Calculate → Single composition**
  - Compute **Qtrue**, **Q/P/Beta (components)**, **ΔT**, **ΔTs** from imported Pandat tables.
  - Scalar interpolation uses a **Newton forward-difference quadratic** scheme when enough points exist (linear fallback for <3 points).
- **Calculate → Composition space (batch)**
  - **Batch source**: **Equilibrium/Lever**, **Scheil**, or **All** (P + P-S together).
  - **Compute batch** shows progress while processing.
  - **Export columns**: select columns, then **Save CSV** / **Save Excel** to export *only selected columns*.
  - **Ternary corner fill**: for ternary systems, missing values in **Q/P/Beta** at composition edges can be filled using a Newton forward-difference extrapolation near \(w=0\).
  - **Quantity (Z)=All**: mass-generate plots for all numeric columns and plot types into the chosen output directory.

### Plot tools

- **Plot Phase Surfaces**: 2D heatmap, 3D static, 3D rotation GIF, Plotly 3D (interactive HTML).
- **Plot Qtrue Values**
- **Plot Liquidus Vectors**
- **Plot Solid-Liquid Partition Coefficients**
- **Plot T-zero Surface**
  - **Thermo-Calc** workflow: load `t_zero.xlsx` produced by **Extract Thermo-calc Results → T-zero**.
  - **Pandat** workflow: load `T0.xlsx` produced by **Extract Pandat Results → T-zero**.

### Tools

- **Composition Converter (wt% ↔ at%)**
- **Generate Thermo-calc Batch File** (`.tcm`)
- **Generate Pandat Batch File** (`.pbfx`)
  - **T-zero tab**: batch-generate `.pbfx` files from a template with element placeholders like `%LI%`.
  - **Gibbs tab**: supports both element placeholders `%X%` and a temperature placeholder `%T%`.
  - **Unit recognition**:
    - Composition base from `<unit name="n" value="w%|x%|w|x" />`:
      - `w%` / `x%` → balance total = **100**
      - `w` / `x` → balance total = **1**
    - Temperature token from `<unit name="T" value="K|C|F" />` (used for filename suffixes).
  - **Balancing the last element**:
    - Remove exactly **one** element row to make it the balance element: `balance = total − Σ(swept)`; or
    - Keep all rows and enable **balance last in list** to sweep the first \(n-1\) and compute the last.
  - **Default output filename pattern** preserves canonical element casing (e.g. `Si`, `Li`) instead of forcing upper-case.
- **Extract Thermo-calc Results**
  - **Melting Range**: scan `.exp` blocks and export liquidus/solidus/melting-range to Excel.
  - **T-zero**: extract `T0 (K)` vs composition and export `t_zero.xlsx`.
- **Extract Pandat Results**
  - **P/Ts (Lever/Scheil)**: read Pandat All table folders (`.csv` / `.dat`) and generate `P.xlsx`, `Ts.xlsx`, `P-S.xlsx`, `Ts-S.xlsx`; supports **Import to ThermoQ** for one-click import after extraction.
  - **T-zero**: read `All table_T0` and export `T0.xlsx` with normalized `w(Element)` columns.
  - **TriST Zone** (Pandat Gibbs):
    - Read `All table_Gibbs` and pair LIQUID + solid Gibbs energies at the same \(T\) and composition.
    - Export a TriST workbook: `Merged_Gibbs`, `T0_tie_1D`, `TriST_dG_le_0`.
    - **Visualize TriST**: Plotly 3D HTML, ternary projection \(x/y\), \(z=T\), color by \(dG\); A/B/C axes auto-populate from `w(…)` columns.

### Installation

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

- **图形界面**，流程直观（批处理生成 / 提取 / 绘图一体化）。
- **国际化 i18n**：通过 **Help → Language** 切换英文/中文；语言切换后工具窗口会刷新。
- **Pandat 导入**：支持 `P.xlsx`、`Ts.xlsx`（必需）和 `P-S.xlsx`、`Ts-S.xlsx`（可选）。
- **结果窗口**：支持保存 **Excel / CSV / TXT / DAT**。

### 主要工作流

- **Calculate → 单点成分**
  - 基于已导入 Pandat 表计算 **Qtrue**、**Q/P/Beta（分量）**、**ΔT**、**ΔTs**。
  - 标量插值在点数足够时使用 **Newton 前向差分二次插值**（不足 3 点则线性）。
- **Calculate → Composition space (batch)（成分空间·批量）**
  - **Batch source**：**Equilibrium/Lever**、**Scheil** 或 **All**（合并 P + P-S）。
  - **Compute batch** 会显示处理进度。
  - **Export columns**：选择列后用 **Save CSV / Save Excel** 导出（只导出勾选列）。
  - **三元角点填充**：三元体系下 **Q/P/Beta** 在边界 \(w=0\) 附近可用 Newton 前向差分外推进行填充。
  - **Quantity(Z)=All**：对所有数值列与多种图形类型批量输出到指定目录。

### Plot 绘图工具

- **Plot Phase Surfaces**：2D 热图、3D 静态、3D 旋转 GIF、Plotly 3D（交互 HTML）。
- **Plot Qtrue Values**
- **Plot Liquidus Vectors**
- **Plot Solid-Liquid Partition Coefficients**
- **Plot T-zero Surface**
  - **Thermo-Calc**：加载 **Extract Thermo-calc Results → T-zero** 生成的 `t_zero.xlsx`。
  - **Pandat**：加载 **Extract Pandat Results → T-zero** 生成的 `T0.xlsx`。

### Tools 工具集

- **Composition Converter（wt% ↔ at%）**
- **Generate Thermo-calc Batch File（.tcm）**
- **Generate Pandat Batch File（.pbfx）**
  - **T-zero 页**：从含 `%LI%` 等占位符的模板批量生成 `.pbfx`。
  - **Gibbs 页**：支持元素占位符 `%X%` 与温度占位符 `%T%`。
  - **单位识别**：
    - 成分基准来自 `<unit name="n" value="w%|x%|w|x" />`：`w%/x%` 总量 100；`w/x` 总量 1。
    - 温度单位来自 `<unit name="T" value="K|C|F" />`（用于文件名后缀）。
  - **平衡组元**：删除恰好 1 行作为平衡组元（`total − Σ`），或保留全部并勾选“按列表平衡最后一个”。
  - **默认文件名模式**保持规范元素大小写（如 `Si`、`Li`）。
- **Extract Thermo-calc Results**
  - **Melting Range**：扫描 `.exp` 数据块导出液相线/固相线/熔程。
  - **T-zero**：提取 `T0 (K)` 与成分，导出 `t_zero.xlsx`。
- **Extract Pandat Results**
  - **P/Ts (Lever/Scheil)**：读取 Pandat All table 文件夹（支持 `.csv/.dat`）生成 `P.xlsx`、`Ts.xlsx`、`P-S.xlsx`、`Ts-S.xlsx`；并支持 **Import to ThermoQ** 一键导入。
  - **T-zero**：读取 `All table_T0` 导出 `T0.xlsx`（`w(Element)` 列会规范化合并）。
  - **TriST Zone（Pandat Gibbs）**：
    - 读取 `All table_Gibbs`，在相同 \(T\) 与相同成分下配对 LIQUID 与固相 Gibbs 能。
    - 导出 TriST 工作簿：`Merged_Gibbs`、`T0_tie_1D`、`TriST_dG_le_0`。
    - **Visualize TriST**：Plotly 交互 3D（\(x/y\) 为三元投影，\(z=T\)，颜色 \(dG\)）；A/B/C 会自动从 `w(…)` 列填充。

### 安装与运行

- Python 3.6+

```bash
pip install -r requirements.txt
python main.py
```
