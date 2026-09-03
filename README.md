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
  - **Plot curves (composition)**: pick a **fixed element** and **fixed content (wt%)** (single value or comma-separated list, e.g. `5, 10, 15`); plot **ΔT**, **ΔTs**, **Qtrue**, **Q/P/β**, etc. vs a **varying element**; multi-quantity overlay on one figure; customizable coordinate range.
  - **Plot Labels**: optional custom figure title and X/Y/Z axis names (empty fields use defaults).
  - **Image export**: BMP/GIF and other formats use a unified save path (PIL conversion where Matplotlib cannot write directly).

### Plot tools

- **Plot Phase Surfaces**: 2D heatmap, 3D static, 3D rotation GIF, Plotly 3D (interactive HTML).
- **Plot Qtrue Values**
- **Plot Liquidus Vectors**
  - U/V/Z vector plots from Pandat P or P-S data.
  - Optional **Z vectors on liquidus surface** (3D static / GIF / Plotly): arrow tips follow the local liquidus temperature field.
  - Saved files are not opened automatically; use **Save As** when prompted.
- **Plot Solid-Liquid Partition Coefficients**
  - **Liquidus tab**: k-vector field and |k−1| heatmap / 3D / GIF / Plotly from imported P or P-S data.
  - **isotherm tab**: U/V/Z at a user-defined temperature from All table_Lever / All table_Scheil (with interpolation).
  - **isocomposition tab**: tie-line projection and 3D animation for a fixed alloy O; optional **k vs T curves** (k = w(*@solid)/w(*@LIQUID)) with sampled **temperature tick labels**; separate coordinate ranges for composition plots and k–T curves; full EN/中文 i18n.
- **Plot T-zero Surface**
  - **Thermo-Calc** workflow: load `t_zero.xlsx` produced by **Extract Thermo-calc Results → T-zero**.
  - **Pandat** workflow: load `T0.xlsx` produced by **Extract Pandat Results → T-zero**.
  - User-defined **isotherm interval (K)** for labeled T0 contours on 2D/3D surfaces.
- **Plot Miscibility Gap**
  - Load **`miscibility_gap.xlsx`** from **Extract Thermo-calc Results → Miscibility Gap**.
  - **At Temperature**: user-specified *T* (K); missing temperatures are interpolated from bracketing values; boundaries colored/labeled by **Phase**; 2D lines or 3D/GIF/Plotly.
  - **Temperature Surfaces**: all boundary points stacked into one smooth *T* surface; **isotherm interval (K)** for labeled contours; surface not drawn below minimum *T* in the Excel data.
  - Chemistry axis labels use canonical element casing (e.g. w(Cu), MOLE_PERCENT_Cu).
  - Shared output settings: visualization mode, smoothness, 3D view angles, image format, GIF parameters.
- **Plot Labels** (where available): optional title and axis names on exported figures; language follows **Help → Language**.

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
- **Extract Thermo-calc Results** (four tabs; scrollable window)
  - **Melting Range**: scan `.exp` blocks and export liquidus/solidus/melting-range to Excel; optional regex filename filter (default `*_np-T.exp`).
  - **Miscibility Gap**: export phase boundary curves vs temperature to **`miscibility_gap.xlsx`**; temperature from filename; Phase from `$ PLOTTED` lines.
  - **T-zero**: extract `T0 (K)` vs composition and export `t_zero.xlsx`.
  - **TriST Zone** (Thermo-Calc Gibbs):
    - Recursively read `*_Gibbs.exp` (default filter `.*_Gibbs.exp$`); parse `$ PLOTTED COLUMNS ARE : W(*) and GMR(PHASE)` sections.
    - Pair LIQUID and a solid phase at the same *T* and composition; export TriST workbook (`T0_tie_1D`, `T0_lines`, `TriST_boundaries`, `TriST_mask`) and optional `_trist_cube.npz`.
    - **Settings**: user-selected 2D composition plane (X/Y `w(*)`); grid size *N* for cubic interpolation; axes auto-detected from folder sample.
    - **Visualize TriST**: Plotly / 2D / 3D / GIF (shared panel with Pandat TriST); optional **Plot Labels**.
  - **Template1 (optional, all four tabs)**: after processing, generate abnormal-point **`.tcm`** files from Status error records using a Template1 reference (`%Element%`, `%T%` placeholders).
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

**Recommended / feature-specific packages** (see `requirements.txt`):
- `matplotlib` — 2D/3D static plots, rotation GIFs, **TriST workbook build** (Thermo-Calc & Pandat)
- `scipy` — cubic interpolation & griddata; **required for TriST extraction** and several smooth-surface tools
- `plotly` — interactive 3D HTML (TriST visualize, phase surfaces, …)
- `kaleido` — Plotly static image export
- `scikit-learn` — Gaussian-process smooth surfaces (phase / miscibility gap)
- `scikit-image` — optional TriST f=0 dome rendering in Matplotlib 3D (marching cubes)

Sample data under `test/`:
- `Extract Thermo-calc Results-Gibbs/` — Al-Cu-Li COST Gibbs `.exp` for TriST extract
- `Extract Thermo-calc Results-Melting Range/` — melting-range `.exp` examples
- `Generate Thermo-calc Batch File-Melting Range/` & `Generate Thermo-calc Batch File-Gibbs/` — `.tcm` batch templates
- Pandat extract / batch examples (Al-Cu-Li, miscibility gap, …)

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
  - **绘制成分曲线**：选择**固定组元**与**固定含量 (wt%)**（单个数值或逗号分隔，如 `5, 10, 15`），以**变化组元**为横轴绘制 **ΔT**、**ΔTs**、**Qtrue**、**Q/P/β** 等；支持多物理量叠加与坐标范围设置。
  - **图名与坐标轴**：可自定义图标题与 X/Y/Z 轴名称（留空则使用默认）。
  - **图像导出**：BMP/GIF 等格式经统一保存路径处理（Matplotlib 不能直接写入时由 PIL 转换）。

### Plot 绘图工具

- **Plot Phase Surfaces**：2D 热图、3D 静态、3D 旋转 GIF、Plotly 3D（交互 HTML）。
- **Plot Qtrue Values**
- **Plot Liquidus Vectors（液相面向量）**
  - 由 Pandat P 或 P-S 数据生成 U/V/Z 向量图。
  - 可选 **液相面上的 Z 向量**（3D 静态 / GIF / Plotly）：箭头终点贴合局部液相面温度场。
  - 保存后不再自动打开文件，可按提示另存为。
- **Plot Solid-Liquid Partition Coefficients（固-液分配系数）**
  - **液相线页**：由已导入 P/P-S 绘制 k 向量场及 |k−1| 热力图 / 3D / GIF / Plotly。
  - **等温页**：从 All table_Lever / All table_Scheil 在指定温度 T 计算 U/V/Z（含插值）。
  - **等成分页**：固定合金成分 O 的固-液配分投影与 3D 动画；可选 **k–T 曲线**（k = w(*@固相)/w(*@LIQUID)），横轴标注采样**温度刻度**；成分图与 k–T 曲线分别可设坐标范围；完整中/英 i18n。
- **Plot T-zero Surface**
  - **Thermo-Calc**：加载 **Extract Thermo-calc Results → T-zero** 生成的 `t_zero.xlsx`。
  - **Pandat**：加载 **Extract Pandat Results → T-zero** 生成的 `T0.xlsx`。
  - 可设置 **等温线间隔 (K)**，用于 2D/3D 曲面上 T0 等温线标注。
- **Plot Miscibility Gap（绘制混溶隙）**
  - 加载 **Extract Thermo-calc Results → 混溶隙** 导出的 **`miscibility_gap.xlsx`**。
  - **指定温度**：用户输入 *T* (K)；缺失温度在邻近值间插值；按 **Phase** 分色与图例；支持 2D / 3D / GIF / Plotly。
  - **温度曲面**：全部边界叠加为单一平滑温度曲面；**等温线间隔 (K)**；曲面不低于 Excel 中最低温度。
  - 化学轴标签采用规范元素大小写（如 w(Cu)、MOLE_PERCENT_Cu）。
  - 共用：可视化方式、平滑度、3D 视角、输出路径/格式、GIF 参数。
- **图名与坐标轴**（适用处）：导出图可选自定义标题与坐标轴名；语言随 **Help → Language** 切换。

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
- **Extract Thermo-calc Results**（四个标签页；可滚动窗口）
  - **Melting Range（熔程）**：扫描 `.exp` 导出液相线/固相线/熔程；可选文件名正则过滤（默认 `*_np-T.exp`）。
  - **Miscibility Gap（混溶隙）**：导出相边界曲线与温度至 **`miscibility_gap.xlsx`**；温度来自文件名；Phase 来自 `$ PLOTTED`。
  - **T-zero**：提取 `T0 (K)` 与成分，导出 `t_zero.xlsx`。
  - **TriST 区域（Thermo-Calc Gibbs）**：
    - 递归读取 `*_Gibbs.exp`（默认 `.*_Gibbs.exp$`）；解析 `$ PLOTTED COLUMNS ARE : W(*) and GMR(相名)` 数据段。
    - 在相同 *T* 与成分下配对 LIQUID 与固相；导出 TriST 工作簿（`T0_tie_1D`、`T0_lines`、`TriST_boundaries`、`TriST_mask`）及可选 `_trist_cube.npz`。
    - **设置**：用户指定 2D 成分平面（X/Y `w(*)`）；插值网格 *N*；浏览文件夹后自动识别可用轴。
    - **Visualize TriST**：Plotly / 2D / 3D / GIF（与 Pandat TriST 共用面板）；可选**图名与坐标轴**。
  - **Template1（可选，四个标签页共用逻辑）**：处理完成后，根据 Status 中的错误记录与 Template1 参考文件（`%元素%`、`%T%`）生成异常点 **`.tcm`**。
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
- 依赖说明见 `requirements.txt`：`matplotlib` + `scipy` 为 **TriST 工作簿构建**（Thermo-Calc / Pandat）所必需；`plotly` / `kaleido` 用于交互 3D 与静态导出；`scikit-learn` / `scikit-image` 用于曲面平滑与可选 TriST 3D 渲染。
- 示例数据（`test/`）：
  - `Extract Thermo-calc Results-Gibbs/` — Al-Cu-Li COST Gibbs `.exp`（TriST 提取）
  - `Extract Thermo-calc Results-Melting Range/` — 熔程 `.exp` 示例
  - `Generate Thermo-calc Batch File-Melting Range/`、`Generate Thermo-calc Batch File-Gibbs/` — `.tcm` 批处理模板
  - Pandat 提取 / 批处理示例（Al-Cu-Li、混溶隙等）

```bash
pip install -r requirements.txt
python main.py
```
