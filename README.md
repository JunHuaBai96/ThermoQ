# ThermoQ

[English](#english) | [中文](#中文)

<img width="1024" height="1024" alt="logo" src="https://github.com/user-attachments/assets/6486eb41-5c75-4f08-9e41-05c480f2e39b" />

---

## English

ThermoQ is a desktop application for thermodynamic workflows (Pandat / Thermo-Calc data ingestion, batch computations, and rich visualization).

### Recent updates (after 2026-04-30)

- **Miscibility Gap workflow (Thermo-Calc)**
  - **Extract Thermo-calc Results → Miscibility Gap**: parse temperature-sweep `.exp` files; read axis labels from `XTEXT`/`YTEXT`; extract boundary points between `$ PLOTTED` … `BLOCKEND`; label curves by **Phase** (e.g. `LIQUID#1`); export **`miscibility_gap.xlsx`** (columns: `File`, `Temperature_K`, `Phase`, composition axes).
  - **Plot → Plot Miscibility Gap**: two pages — **At Temperature** (2D/3D boundary lines per Phase, with interpolation when the target *T* is missing) and **Temperature Surfaces** (single stacked smooth surface over all temperatures, **isotherm interval** labeling, *Z* clipped to data minimum temperature).
  - Default filename filter for miscibility-gap exports: temperature-style names such as `AlCuLi_800.exp` / `AlCuLi_300K.exp`.
- **Thermo-calc Batch File Generator**
  - Loop-body template supports **`%T%`** with UI temperature min / max / step (Cartesian product: compositions × temperatures).
  - When a generated loop iteration duplicates the **Template0 baseline** (`s-c t=…`, `s-c w(...)` / `s-c x(...)`), that entire loop block is **skipped** in the output `.tcm` (avoids double calculation at the same *T* or composition).
- **Extract Thermo-calc Results → Melting Range**
  - Optional **filename filter** (regex); default `*_np-T.exp`.
- **UI / i18n**
  - Miscibility Gap tools fully wired to **Help → Language** (EN / 中文).
  - Plot Miscibility Gap window: scrollable layout; plot buttons on the active tab only.

Sample data: `test/Liquid Miscibility Gap/`, `test/Fcc Miscibility Gap/`, `test/Generate Thermo-calc Batch File-np-T/`.

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
- **Plot Miscibility Gap**
  - Load **`miscibility_gap.xlsx`** from **Extract Thermo-calc Results → Miscibility Gap**.
  - **At Temperature**: user-specified *T* (K); missing temperatures are interpolated from bracketing values; boundaries colored/labeled by **Phase**; 2D lines or 3D/GIF/Plotly.
  - **Temperature Surfaces**: all boundary points stacked into one smooth *T* surface; **isotherm interval (K)** for labeled contours; surface not drawn below minimum *T* in the Excel data.
  - Shared output settings: visualization mode, smoothness, 3D view angles, image format, GIF parameters.

### Tools

- **Composition Converter (wt% ↔ at%)**
- **Generate Thermo-calc Batch File** (`.tcm`)
  - **Template0** + **loop-body template** + optional **Template1**.
  - Element placeholders `%Element%`; temperature placeholder **`%T%`** with min / max / step when present in the loop body.
  - Composition × temperature Cartesian product when both are configured.
  - **Duplicate skip**: loop blocks whose *T* and/or composition match Template0 `s-c` baseline are omitted from the merged `.tcm`.
  - Optional constraints: sum ≤ 1, exclude all-zero compositions.
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
  - **Melting Range**: scan `.exp` blocks and export liquidus/solidus/melting-range to Excel; optional regex filename filter (default `*_np-T.exp`).
  - **Miscibility Gap**: export phase boundary curves vs temperature to **`miscibility_gap.xlsx`**; temperature from filename; Phase from `$ PLOTTED` lines.
  - **T-zero**: extract `T0 (K)` vs composition and export `t_zero.xlsx`.
- **Extract Pandat Results**
  - **P/Ts (Lever/Scheil)**: read Pandat All table folders (`.csv` / `.dat`) and generate `P.xlsx`, `Ts.xlsx`, `P-S.xlsx`, `Ts-S.xlsx`; supports **Import to ThermoQ** for one-click import after extraction.
  - **T-zero**: read `All table_T0` and export `T0.xlsx` with normalized `w(Element)` columns.
  - **TriST Zone** (Pandat Gibbs):
    - Read `All table_Gibbs` and pair LIQUID + solid Gibbs energies at the same \(T\) and composition.
    - Export a TriST workbook: `T0_tie_1D`, `T0_lines`, `TriST_boundaries`, `TriST_mask`.
    - Optionally saves a companion `_trist_cube.npz` for smooth \(f(C_0)=0\) boundary rendering.
    - **Visualize TriST**: Plotly 3D HTML with user-selected `w(*)` columns as the 2D composition plane (X/Y); \(z=T\).
      - `TriST_boundaries` can be drawn as discrete lines (**Boundary lines every (K)**) and (optionally) as a smooth surface via cubic interpolation in \(T\).
      - `TriST_mask` supports both point-cloud rendering and Mesh3d surface rendering (per temperature).
      - Export supports **Interactive HTML** and **Static image** (image format selection).

### Installation

- **Python**: 3.8+ recommended (3.6+ may work with older dependency pins).
- **GUI**: uses built-in `tkinter` (included with most Python installers on Windows/macOS; on Linux install `python3-tk` if needed).
- Install dependencies:

```bash
pip install -r requirements.txt
```

Optional packages enable extra plots:
- `matplotlib` — 2D/3D static plots and rotation GIFs
- `plotly` — interactive 3D HTML
- `kaleido` — Plotly static image export
- `scikit-learn` / `scipy` — smooth surfaces (phase surfaces, miscibility gap temperature surfaces)

### Run

```bash
python main.py
```

---

## 中文

ThermoQ 是一个用于热力学计算工作流的桌面应用（支持 Pandat / Thermo-Calc 数据导入、批量计算与可视化）。

### 近期更新（2026-04-30 之后）

- **混溶隙工作流（Thermo-Calc）**
  - **Extract Thermo-calc Results → 混溶隙**：解析按温度导出的 `.exp`；从 `XTEXT`/`YTEXT` 读取轴标签；在 `$ PLOTTED` … `BLOCKEND` 之间提取边界点；按 **Phase**（如 `LIQUID#1`）标记；导出 **`miscibility_gap.xlsx`**（`File`、`Temperature_K`、`Phase`、成分列）。
  - **Plot → 绘制混溶隙**：两个页面 — **指定温度**（按 Phase 分色边界线，目标温度不存在时在邻近温度间插值）与 **温度曲面**（全部温度叠加为单一平滑曲面、**等温线间隔**标注、曲面不低于数据最低温度）。
  - 混溶隙导出默认文件名过滤：如 `AlCuLi_800.exp`、`AlCuLi_300K.exp`。
- **Thermo-calc 批处理文件生成器**
  - 循环体模板支持 **`%T%`** 及界面中的温度最小值/最大值/步长（成分 × 温度笛卡尔积）。
  - 若某次循环的 **温度或成分与 Template0 基准**（`s-c t=…`、`s-c w(...)` / `s-c x(...)`）重复，则**整段循环体不写入**输出 `.tcm`，避免重复计算（例如 Template0 已算 300 K 时不再生成 300 K 循环块）。
- **Extract Thermo-calc Results → 熔程**
  - 可选 **文件名过滤**（正则）；默认 `*_np-T.exp`。
- **界面 / 国际化**
  - 混溶隙相关工具已接入 **Help → Language**（中/英切换）。
  - 绘制混溶隙窗口可滚动；绘图按钮仅在当前标签页显示。

示例数据：`test/Liquid Miscibility Gap/`、`test/Fcc Miscibility Gap/`、`test/Generate Thermo-calc Batch File-np-T/`。

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
- **Plot Miscibility Gap（绘制混溶隙）**
  - 加载 **Extract Thermo-calc Results → 混溶隙** 导出的 **`miscibility_gap.xlsx`**。
  - **指定温度**：用户输入 *T* (K)；缺失温度在邻近值间插值；按 **Phase** 分色与图例；支持 2D / 3D / GIF / Plotly。
  - **温度曲面**：全部边界叠加为单一平滑温度曲面；**等温线间隔 (K)**；曲面不低于 Excel 中最低温度。
  - 共用：可视化方式、平滑度、3D 视角、输出路径/格式、GIF 参数。

### Tools 工具集

- **Composition Converter（wt% ↔ at%）**
- **Generate Thermo-calc Batch File（.tcm）**
  - **Template0** + **循环体模板** + 可选 **Template1**。
  - 元素占位符 `%Element%`；循环体含 **`%T%`** 时可配置温度范围与步长。
  - 成分与温度同时配置时做笛卡尔积组合。
  - **重复跳过**：与 Template0 中 `s-c` 基准温度/成分相同的循环块不写入最终 `.tcm`。
  - 可选约束：成分和 ≤ 1、排除全零成分。
- **Generate Pandat Batch File（.pbfx）**
  - **T-zero 页**：从含 `%LI%` 等占位符的模板批量生成 `.pbfx`。
  - **Gibbs 页**：支持元素占位符 `%X%` 与温度占位符 `%T%`。
  - **单位识别**：
    - 成分基准来自 `<unit name="n" value="w%|x%|w|x" />`：`w%/x%` 总量 100；`w/x` 总量 1。
    - 温度单位来自 `<unit name="T" value="K|C|F" />`（用于文件名后缀）。
  - **平衡组元**：删除恰好 1 行作为平衡组元（`total − Σ`），或保留全部并勾选“按列表平衡最后一个”。
  - **默认文件名模式**保持规范元素大小写（如 `Si`、`Li`）。
- **Extract Thermo-calc Results**
  - **Melting Range（熔程）**：扫描 `.exp` 导出液相线/固相线/熔程；可选文件名正则过滤（默认 `*_np-T.exp`）。
  - **Miscibility Gap（混溶隙）**：导出相边界曲线与温度至 **`miscibility_gap.xlsx`**；温度来自文件名；Phase 来自 `$ PLOTTED`。
  - **T-zero**：提取 `T0 (K)` 与成分，导出 `t_zero.xlsx`。
- **Extract Pandat Results**
  - **P/Ts (Lever/Scheil)**：读取 Pandat All table 文件夹（支持 `.csv/.dat`）生成 `P.xlsx`、`Ts.xlsx`、`P-S.xlsx`、`Ts-S.xlsx`；并支持 **Import to ThermoQ** 一键导入。
  - **T-zero**：读取 `All table_T0` 导出 `T0.xlsx`（`w(Element)` 列会规范化合并）。
  - **TriST Zone（Pandat Gibbs）**：
    - 读取 `All table_Gibbs`，在相同 \(T\) 与相同成分下配对 LIQUID 与固相 Gibbs 能。
    - 导出 TriST 工作簿：`T0_tie_1D`、`T0_lines`、`TriST_boundaries`、`TriST_mask`。
    - 可选：在同目录生成 `_trist_cube.npz`，用于 \(f(C_0)=0\) 的光滑边界面渲染。
    - **Visualize TriST**：Plotly 交互 3D；通过 `w(*)` 列选择 2D 成分平面（X/Y），\(z=T\)。
      - `TriST_boundaries` 支持离散温度折线（**Boundary lines every (K)**）与基于 \(T\) 的三次插值光滑曲面（可选）。
      - `TriST_mask` 支持点云与每温度 Mesh3d 曲面渲染。
      - 导出支持 **交互式 HTML** 与 **静态图片**（图片格式可选）。静态图片导出需要 `kaleido`。

### 安装与运行

- 推荐 **Python 3.8+**（GUI 依赖标准库 `tkinter`；Linux 需安装 `python3-tk`）。

```bash
pip install -r requirements.txt
python main.py
```
