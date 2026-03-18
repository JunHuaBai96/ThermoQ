# ThermoQ

ThermoQ是一个用于热力学计算的应用程序，提供了直观的元素成分输入和计算功能。

## 更新摘要

### 最新版本
- **Solid-Liquid Partition Coefficient Vector Plotter（固-液分配系数向量绘图）**：
  - 新增 **Plot → Plot Solid-Liquid Partition Coefficients**（中文：绘制定-液分配系数向量）
  - 仿照 Liquidus Vector Plotter 界面，数据来自 P 或 P-S 文件；**不包含** “Clean and fill data before plotting”
  - 使用 **w(*@FCC_A1)** 与 **w(*@LIQUID)** 计算分配系数 k = w(*@FCC_A1)/w(*@LIQUID)，绘制 2D 矢量图：U（水平，k_X）、V（垂直，k_Y）、Z（合成，k−1 偏差）
  - 输出三张 PNG：`<前缀>_<X>_U.png`、`<前缀>_<Y>_V.png`、`<前缀>_Z.png`，并自动打开
- **Thermo-calc 结果全流程支持（Melting Range / T-zero / 表面绘图）**：
  - **Extract Thermo-calc Results** 现在包含两个子页签：**Melting Range（熔程）** 与 **T-zero**
    - Melting Range：从 `.exp` 文件自动解析所有 `$ PLOTTED ... BLOCKEND` 数据块，提取液相线/固相线温度并计算熔程；从文件名中自动识别任意体系的 w(*)（如 `Al0.04Mg0.09Si_np-T.exp` → w(Mg)=0.04, w(Si)=0.09），并将极小数值（~1e-7）视为 0，避免 `3.9E-08` 之类噪声
    - T-zero：批量读取 `_T0.exp` 文件，解析文件名中的参数成分 w(*) 和数据区的 `XTEXT W(*)` 与 T，输出 `w(param)`、`w(XTEXT 元素)` 与 `T0 (K)`，同时对极小质量分数去噪并去除重复行
  - **Plot → Plot Phase Surfaces** 新增 **Thermo-calc** 页签，可直接加载 Melting Range 导出的 `output.xlsx`，用 `Liquidus_Temperature` / `Solidus_Temperature` 绘制液相面/固相面，轴标签统一为 `w(X)` / `w(Y)`（不带 %）
  - 新增 **Plot → Plot T-zero Surface**，从 T-zero 导出的 `t_zero.xlsx` 读取所有 `w(*)` 列与 `T0 (K)`，支持 2D Heatmap、3D 静态、3D 旋转 GIF 与 Plotly 3D 的 T-zero 曲面绘制
- **Generate Thermo-calc Batch File 改进**：
  - 模板占位符替换对大小写不敏感（`%Li%`、`%LI%` 均可），自动从周期表元素符号匹配
  - 元素步长使用 float64 且根据 step 自动确定小数位数（例如 step=0.005 时写入三位小数），避免 0.005 被格式化为 0.01 以及浮点噪声
- **窗口与交互优化**：
  - Import / Plot / Tools 中的大部分子窗口不再使用 `grab_set()` 强制模态，支持正常最小化与在主窗口之间切换
- **多语言**：Plot 菜单新增项随 Help→Language（English/中文）切换；主窗口 Calculate/Show Results 及菜单栏已接入语言包
- **相/元素自动识别（普适性增强）**：
  - 程序不再固定为 FCC 固相，而是根据 **Extract Pandat Results** 或 **Pandat to ThermoQ** 导入的 Excel 中列名 **w(*@*)**（第一个 * 为元素，第二个 * 为相）自动识别相与元素
  - 主计算、Plot Q Values、Extract Pandat Results 等均使用检测到的固相与 Q 列（如 -T//fw(@FCC_A1)、-T//fw(@BCC_A2)）
  - 组分 Q/P/Beta 针对所有在数据中具备 w(*)、w(*@固相)、w(*@LIQUID)、dwdT_L(*@LIQUID) 的元素计算，不再限于 Mg、Si
- **Extract Pandat Results 增强**：
  - **Lever 与 Scheil 文件夹**：同时支持 `.csv` 和 `.dat`（如 All table_Lever、All table_Scheil 的 CSV 均可）
  - **列名容错**：对 `fs`、`T` 列做大小写不敏感匹配（支持 fs、f_s、Fs；T、t、Temperature），缺失时跳过该文件并提示，避免 KeyError
  - **P-S.xlsx / Ts-S.xlsx**：生成文件中空缺的 **w(*)**（及 P-S 中的 w(*@*)）自动用 **0** 填充
  - **P-S.xlsx**：始终包含 **fw(@FCC_A1)** 和 **-T//fw(@FCC_A1)** 列；若源数据无这两列则自动添加并填 0
  - **FCC 相分离**：若 Scheil 的 CSV 中存在 **fw(@FCC_A1#1)、fw(@FCC_A1#2)** 等列，表示 FCC 分离成两个成分不同的 FCC 相；程序会弹窗提示（英文默认，Help→Language→中文 时显示中文），并用 T 对 fw(@FCC_A1#1) 求导计算 **-T//fw(@FCC_A1)** 补充到 P-S.xlsx；若已有 -T//fw(@FCC_A1) 数值则保留
  - **写入权限**：保存 P/Ts/P-S/Ts-S 时若遇 PermissionError（如文件被 Excel 打开），会提示关闭文件或更换输出目录
  - **窗口与布局**：窗口增高并带滚动区域，底部固定 **Extract Results** 与 **Close** 按钮（左右居中），长状态提示不再遮挡按钮
- **Plot Q Values**：Z 轴 Q 列与标签根据数据中的 **-T//fw(@phase)** 自动识别，支持任意相名（如 BCC_A2）
- **计算功能**：Qtrue 与分量计算使用检测到的固相列（如 w(*@FCC_A1) 或 w(*@BCC_A2)）与 Q 列，支持多体系（Al-Cu-Li、Al-Mg-Si、Ti-Fe-Cu 等）

### 历史更新（Plot 与 Tools 等）
- **Plot工具增强**：
  - 高斯过程平滑：所有绘图功能使用高斯过程回归（GPR）生成平滑、连续曲面
  - 自动打开文件、列名大小写不敏感；Plot Phase Surfaces / Plot Qtrue Values / Plot Liquidus Vectors 等
- **Tools 与计算、Pandat 导入、界面优化**：见上文各条

### 历史版本
- 新增计算模式：`ΔT（熔程）`，计算 `P.xls` 的 `T` 减去 `Ts.xlsx` 的 `T`
- Pandat 导入支持两文件：`P.xls` 与 `Ts.xlsx`
- 导入时自动删除空白行，并将所有 `1/dwdT_L(*@LIQUID)` 列数值除以 100
- 从 `w(*)` 列提取可用元素（如 Al、Mg、Mn），仅激活这些元素供选择
- 启动画面后主窗口自动居中，默认尺寸增至 `1200x800`，并设定最小尺寸以避免界面拥挤

## 功能特点

### 核心功能
- 图形化用户界面，操作简单直观
- 支持从元素周期表中选择元素
- 支持质量分数（wt%）成分输入
- 实时成分总和检查（显示是否达到100 wt%）
- 支持Qtrue、Q值（分量）、P值（分量）、ΔT、ΔTs计算
  - Qtrue：从 P.xlsx 或 P-S.xlsx 中提取 -T//fw(@phase) 值（phase 由数据列名自动识别，如 FCC_A1、BCC_A2）
  - Q值（分量）/ P值（分量）：针对数据中具备 w(*)、w(*@固相)、w(*@LIQUID)、dwdT_L(*@LIQUID) 的**所有元素**计算，不限于 Mg、Si
  - ΔT：平衡凝固的液相线温度与固相线温度差值
  - ΔTs：Scheil凝固的液相线温度与固相线温度差值
- 支持从Pandat软件导出的Excel文件导入元素成分
  - 平衡凝固数据：P.xls 和 Ts.xlsx
  - Scheil凝固数据：P-S.xlsx 和 Ts-S.xlsx（可选）
- 启动画面显示
- 美观的界面设计
- 可自定义的界面主题（当前版本采用黄色背景主题）

### Plot工具集
- **Plot Phase Surfaces**：绘制固相面、液相面可视化
  - 支持2D热图、3D静态图、3D旋转GIF、交互式3D图（Plotly）
  - 支持平衡凝固和Scheil凝固数据
  - 可选择任意两个元素作为X和Y轴
- **Plot Qtrue Values**：绘制 Qtrue 值图
  - X/Y 轴：可选两元素 w(X)、w(Y)；Z/颜色：Q 值（-T//fw(@phase)，phase 由数据列名自动识别）
  - 支持平衡凝固（P.xlsx）与 Scheil（P-S.xlsx）；2D热图、3D静态、3D旋转GIF、Plotly 3D
- **Plot Liquidus Vectors**：绘制液相面矢量图
  - 生成U水平矢量图、V垂直矢量图、Z合成矢量图
  - 支持任意两个元素组合
  - 自动识别列名格式
  - 可选数据清理和填充功能
- **Plot Solid-Liquid Partition Coefficients**：绘制固-液分配系数向量图
  - 数据来自 P 或 P-S 文件（与 Liquidus Vector Plotter 相同）；无 “Clean and fill” 选项
  - 使用 **w(*@FCC_A1)**、**w(*@LIQUID)** 计算 k = w(*@FCC_A1)/w(*@LIQUID)，绘制 U（k_X）、V（k_Y）、Z（合成）三张 2D 矢量图
  - 输出 PNG 并自动打开
- **Plot Phase Surfaces – Thermo-calc 模式**：
  - 可直接加载 **Extract Thermo-calc Results → Melting Range** 导出的 `output.xlsx`，基于 `Liquidus_Temperature` / `Solidus_Temperature` 绘制液相面/固相面
  - X/Y 轴从 Excel 中所有 `w(*)` 列自动识别，坐标轴名称为 `w(X)` / `w(Y)`（无 % 符号）
- **Plot T-zero Surface**：
  - 从 **Extract Thermo-calc Results → T-zero** 导出的 `t_zero.xlsx` 读取 `w(*)` 与 `T0 (K)`，绘制 T-zero 曲面
  - 支持 2D Heatmap、3D Static、3D Rotation GIF 与 Plotly 3D，平滑方式与 Phase Surfaces 相同

### Tools工具集
- **Composition Converter**：质量分数（wt%）与原子分数（at%）双向转换工具
- **Generate Thermo-calc Batch File**：生成Thermo-calc批处理文件（.tcm）
  - 支持多元素组合生成
  - 可配置元素范围和步长
  - 支持约束条件设置
- **Extract Thermo-calc Results**：从Thermo-calc计算结果中提取数据
  - **Melting Range 页签**：批量扫描 `.exp` 文件中所有 `$ PLOTTED ... BLOCKEND` 数据块，提取液相线温度、固相线温度与熔程
    - 自动从文件名解析任意体系的 w(*)（如 `Al0.04Mg0.09Si_np-T.exp`），无需为每个体系单独配置正则
    - 输出 Excel 中的 w(*) 与 Melting_Range 会将接近 0 的浮点噪声（如 `3.9E-08`）视为 0
  - **T-zero 页签**：从 `_T0.exp` 文件提取参数元素 w(*)（来自文件名）、横轴元素 w(*)（来自 `XTEXT W(*)`）与对应 `T0 (K)`，生成长表 `File, w(param), w(XTEXT 元素), T0 (K)`
    - 自动合并同一文件的多个数据块并去除重复点，同时对极小质量分数做近零归零
  - 结果自动保存为 Excel，可直接被 Phase Surface Plotter（Thermo-calc）与 Plot T-zero Surface 使用
- **Extract Pandat Results**：从 Pandat 计算结果中提取数据
  - Lever 与 Scheil 文件夹均支持 **.csv** 和 **.dat**（如 All table_Lever、All table_Scheil 的 CSV）
  - 生成 P.xlsx、Ts.xlsx、P-S.xlsx、Ts-S.xlsx；列名 w(*@*)、fw(@*)、-T//fw(@*) 按数据自动识别
  - 生成文件中空缺的 w(*) 用 0 填充；P-S.xlsx 始终含 fw(@FCC_A1)、-T//fw(@FCC_A1)（缺失则补 0）
  - **FCC 相分离**：若存在 fw(@FCC_A1#1)、fw(@FCC_A1#2) 等列，会提示“FCC 分离成两个成分不同的 FCC 相”，并用 T 对 fw(@FCC_A1#1) 求导计算 -T//fw(@FCC_A1) 补充到 P-S（提示语言随 Help→Language 中/英切换）
  - 保存时若文件被占用会提示关闭或更换输出目录；窗口底部固定 Extract Results / Close 按钮并居中

## 界面主题

### 当前主题
- **背景颜色**：黄色主题，提供温暖舒适的视觉体验
- **启动画面**：黄色背景的启动画面
- **主界面**：统一的黄色背景设计

### 自定义主题
如需修改界面颜色，可以编辑 `main.py` 文件中的以下部分：
- 主窗口背景：修改 `self.root.configure(bg='yellow')` 中的颜色值
- 启动画面背景：修改 `splash_label` 的 `bg` 参数
- 支持的颜色格式：颜色名称（如 'yellow', 'lightblue'）或十六进制颜色代码（如 '#FFFF00'）

## 系统要求

- Python 3.6 或更高版本
- 操作系统：Windows/Linux/MacOS
- 必要的Python包：
  - tkinter（随Python安装）
  - Pillow（图像处理）
  - pandas（数据处理和Excel文件导入）
  - numpy（数值计算和批处理文件生成）
  - openpyxl（读取.xlsx文件）
  - xlrd（读取.xls文件）
  - matplotlib（可选，用于2D/3D绘图和矢量图）
  - plotly（可选，用于交互式3D图）
  - scikit-learn（可选，用于高斯过程平滑）
  - scipy（可选，用于插值备选方案）

## 安装步骤

1. 克隆或下载项目代码：
```bash
git clone https://github.com/JunHuaBai96/ThermoQ.git
cd ThermoQ
```

2. 安装所需的Python包：
```bash
pip install -r requirements.txt
```

3. 确保项目目录结构正确：
```
ThermoQ/
├── main.py
├── periodic_table.py
├── requirements.txt
├── README.md
└── images/
    ├── logo.png
    └── Simplified logo.png
```

## 使用说明

1. 运行程序：
```bash
python main.py
```

2. 添加元素：
   - 从下拉列表中选择元素
   - 输入质量分数成分值（wt%）
   - 点击"Add Element"按钮添加元素

3. 管理元素：
   - 在表格中查看已添加的元素
   - 选择元素后点击"Remove Selected"可以删除元素

4. 从 Pandat 导入数据：
   - 点击菜单栏中的 `Import` > `Pandat to ThermoQ`
   - **必需文件**：
     - `P.xls` 或 `P.xlsx`（平衡凝固的相平衡数据）
     - `Ts.xls` 或 `Ts.xlsx`（平衡凝固的固相线温度）
   - **可选文件**：
     - `P-S.xls` 或 `P-S.xlsx`（Scheil凝固的相平衡数据）
     - `Ts-S.xls` 或 `Ts-S.xlsx`（Scheil凝固的固相线温度）
   - 程序会自动：
     - 删除空白行
     - 处理 `1/dwdT_L(*@LIQUID)` 列（除以 100）
     - 提取 `w(*)` 列的可用元素并启用选择
   - 导入成功后，会在界面中显示"Available elements from Pandat data: ..."说明

5. 进行计算：
   - 确保成分总和为100 wt%（界面会显示绿色✓提示）
   - 点击"Calculate"按钮开始计算Q值、ΔT、ΔTs
   - 计算结果包括：
     - Q (Lever)：从P.xlsx中提取的Q值（如果可用）
     - Q (Scheil)：从P-S.xlsx中提取的Q值（如果可用）
     - ΔT：平衡凝固的液相线温度与固相线温度差值
     - ΔTs：Scheil凝固的液相线温度与固相线温度差值
   - 点击"Show Results"查看详细计算结果

### Plot工具使用

#### Plot Phase Surfaces（绘制相面）
1. 打开：`Plot` > `Plot Phase Surfaces`
2. 选择数据集：Equilibrium/Lever 或 Scheil
3. 选择类型：Liquidus（液相线）或 Solidus（固相线）
4. 选择X和Y元素（从可用元素中选择，支持大小写不敏感匹配）
5. 选择可视化类型：
   - 2D Heatmap：2D热图（使用高斯过程平滑）
   - 3D Static：3D静态图（平滑曲面）
   - 3D Rotation GIF：3D旋转动画GIF（平滑曲面）
   - Plotly 3D：交互式3D图（HTML格式，平滑曲面）
6. 设置输出前缀
7. 点击"Plot"生成图表
8. 图表生成后会自动打开，关闭时可选择另存为到其他位置

#### Plot Qtrue Values（绘制Qtrue值图）
1. 打开：`Plot` > `Plot Qtrue Values`
2. 选择数据集：Equilibrium/Lever 或 Scheil
   - Equilibrium/Lever：使用P.xlsx数据
   - Scheil：使用P-S.xlsx数据
3. 选择可视化类型：
   - 2D Heatmap：2D热图（X轴：w(MG)，Y轴：w(SI)，颜色：Q值，使用高斯过程平滑）
   - 3D Static：3D静态图（平滑曲面）
   - 3D Rotation GIF：3D旋转动画GIF（平滑曲面）
   - Plotly 3D：交互式3D图（HTML格式，平滑曲面）
4. 设置输出前缀（默认：q_value）
5. 点击"Plot"生成图表
6. 图表生成后会自动打开，关闭时可选择另存为到其他位置
7. 注意：需要先通过 `Import > Pandat to ThermoQ` 导入P.xlsx或P-S.xlsx文件

#### Plot Liquidus Vectors（绘制液相面矢量图）
1. 打开：`Plot` > `Plot Liquidus Vectors`
2. 选择Excel文件（需包含w(X)、w(Y)、1/dwdT_L(X@LIQUID)、1/dwdT_L(Y@LIQUID)列）
3. **元素自动识别**：选择Excel文件后，程序会自动从文件中提取可用元素并更新下拉列表
4. 选择X和Y元素（从自动识别的元素中选择，如果未识别则显示所有元素）
5. 可选：勾选"Clean and fill data before plotting"进行数据清理
6. 设置输出前缀（默认：liquid_vectors）
7. 点击"Plot Vectors"生成三个矢量图：
   - U水平矢量图（蓝色）：显示X元素的水平矢量
   - V垂直矢量图（橙色）：显示Y元素的垂直矢量
   - Z合成矢量图（绿色）：显示U和V的合成矢量
8. 图表生成后会自动打开，关闭时可选择另存为到其他位置

#### Plot Solid-Liquid Partition Coefficients（绘制固-液分配系数向量图）
1. 打开：`Plot` > `Plot Solid-Liquid Partition Coefficients`（中文菜单：绘制定-液分配系数向量）
2. 选择凝固模式：Equilibrium/Lever（P 文件）或 Scheil（P-S 文件）；需已通过 Import → Pandat to ThermoQ 导入对应数据
3. 选择 X、Y 元素（从可用元素列表）
4. 设置输出文件名前缀（默认：k_vectors）
5. 点击 “Plot Vectors” 生成三张 2D 矢量图：
   - **U**（蓝色）：水平分量，k(X) = w(X@FCC_A1)/w(X@LIQUID)
   - **V**（橙色）：垂直分量，k(Y) = w(Y@FCC_A1)/w(Y@LIQUID)
   - **Z**（绿色）：合成矢量（k−1 偏差）
6. 数据需含 w(X)、w(Y)、w(X@FCC_A1)、w(Y@FCC_A1)、w(X@LIQUID)、w(Y@LIQUID)；无 “Clean and fill” 选项，直接使用原始数据。图片自动打开并可另存

### Tools工具使用

#### Composition Converter（成分转换工具）
1. 打开：`Tools` > `Composition Converter (wt% ↔ at%)`
2. 选择输入单位（wt% 或 at%）
3. 输入元素成分（每行一个元素，格式：`Al 90.0` 或 `Al: 90.0`）
4. 点击"Convert"进行转换
5. 查看转换结果

#### Generate Thermo-calc Batch File（生成批处理文件）
1. 打开：`Tools` > `Generate Thermo-calc Batch File`
2. 选择模板文件：
   - Template0 File（文件头部）
   - Template File（包含占位符如 %Element%）
   - Template1 File（文件尾部）
3. 配置元素：
   - 添加要生成的元素
   - 设置每个元素的Min、Max、Step值
4. 设置约束条件（可选）：
   - 总和约束：所有元素总和 <= 1
   - 排除全零组合
5. 选择输出文件路径
6. 点击"Generate Batch File"生成.tcm文件

#### Extract Thermo-calc Results（提取计算结果）
1. 打开：`Tools` > `Extract Thermo-calc Results`
2. 选择包含.exp文件的文件夹
3. 配置文件名模式（可选）：
   - 使用正则表达式从文件名提取元素分数
   - 默认模式：`Al(\d+\.\d+)Fe(\d+\.\d+)Si_np-T\.exp`
4. 选择输出Excel文件路径
5. 点击"Process Files"开始处理
6. 查看处理状态和结果
7. 结果将保存为Excel文件，包含：
   - 元素分数列（如果从文件名提取）
   - 液相线温度（Liquidus_Temperature）
   - 固相线温度（Solidus_Temperature）
   - 熔程（Melting_Range）

#### Extract Pandat Results（提取Pandat计算结果）
1. 打开：`Tools` > `Extract Pandat Results`
2. 选择 **Lever 文件夹**：包含平衡凝固文件的文件夹（All table_Lever），支持 **.csv 和 .dat**
3. 选择 **Scheil 文件夹**：包含 Scheil 凝固文件的文件夹（All table_Scheil），支持 **.csv 和 .dat**
4. 选择输出目录
5. 点击 **Extract Results** 开始处理（底部按钮固定、居中，可滚动查看上方状态）
6. 生成 4 个 Excel：**P.xlsx**、**Ts.xlsx**、**P-S.xlsx**、**Ts-S.xlsx**
   - 列 T、fs 支持大小写不敏感（如 fs/f_s/Fs，T/t/Temperature）；缺失 fs 或 T 的文件会被跳过
   - 空缺的 w(*)（及 P-S 中 w(*@*)）会填 0；P-S 始终含 fw(@FCC_A1)、-T//fw(@FCC_A1)（无则补 0）
   - 若 Scheil 文件中存在 **fw(@FCC_A1#1)、fw(@FCC_A1#2)** 等列，会弹窗提示“FCC 分离成两个成分不同的 FCC 相”，并自动用 T 对 fw(@FCC_A1#1) 求导计算 -T//fw(@FCC_A1) 补充到 P-S（语言随 Help→Language 中/英）
7. 若保存时提示权限错误，请关闭已打开的 Excel 或更换输出目录


## 项目结构
```
ThermoQ/
├── main.py                  # 主程序文件，包含GUI实现和主要功能
├── periodic_table.py        # 元素周期表数据
├── requirements.txt         # 项目依赖包列表
├── README.md                # 项目说明文档
├── LICENSE                  # 许可证文件
├── tcm.py                   # Thermo-calc批处理文件生成脚本（参考）
├── ExpDataProcessor.py      # Thermo-calc结果提取脚本（参考）
├── plot_vectors_from_excel.py  # 液相面矢量图绘制脚本（参考）
├── process_excel_clean_fill.py # Excel数据清理和填充脚本（参考）
├── process_solidus_data.py     # 固相线数据处理脚本（参考）
├── process_Liquidus_data.py    # 液相线数据处理脚本（参考）
├── template.txt             # Thermo-calc模板文件示例
├── template0.txt            # Thermo-calc头部模板示例
├── template1.txt            # Thermo-calc尾部模板示例
└── images/                  # 存放程序使用的图片资源
    ├── logo.png
    └── Simplified logo.png
```


## 界面自定义

### 修改背景颜色
如需更改界面背景颜色，请按以下步骤操作：

1. 打开 `main.py` 文件
2. 找到 `ThermoQGUI` 类的 `__init__` 方法
3. 修改以下行：
   ```python
   self.root.configure(bg='yellow')  # 将 'yellow' 改为您想要的颜色
   ```
4. 可选：同时修改启动画面背景颜色：
   ```python
   splash_label = tk.Label(self.splash_root, image=self.splash_photo, bg='yellow')
   ```

### 支持的颜色选项
- 颜色名称：'yellow', 'lightblue', 'lightgreen', 'white', 'gray' 等
- 十六进制：'#FFFF00', '#87CEEB', '#90EE90' 等
- RGB值：需要转换为十六进制格式

## 注意事项

### 元素成分输入
1. 确保所有成分值在0-100%之间
2. 同一元素不能重复添加
3. 成分总和应等于100 wt%（界面会实时显示总和状态）
4. 系统内部统一使用wt%存储，所有计算基于wt%

### Pandat数据导入
1. P文件和Ts文件是必需的（平衡凝固数据）
2. P-S文件和Ts-S文件是可选的（Scheil凝固数据）
3. 导入时会自动处理数据格式和单位转换
4. 导入后只有从数据中提取的元素可用

### Thermo-calc批处理文件生成
1. 模板文件中的占位符格式：`%Element%`（如 `%Fe%`、`%Si%`）
2. 元素配置的Min、Max值应在0-1之间
3. 步长越小，生成的文件越大，处理时间越长
4. 建议先测试小范围生成，确认格式正确后再生成完整文件

### Thermo-calc结果提取
1. .exp文件必须包含 `$ PLOTTED` 和 `BLOCKEND` 标记之间的数据
2. 数据格式应为：第一列温度，第二列液相分数
3. 如果文件名模式不匹配，将无法提取元素分数，但仍可提取温度数据
4. 处理大量文件时可能需要较长时间，请耐心等待

### Pandat结果提取
1. Lever/Scheil 文件夹支持 **.csv 和 .dat**；CSV/DAT 格式：制表符分隔，第一行为列名，第二行为单位行（自动跳过）
2. 列名容错：T、fs 支持大小写及 f_s 等变体；缺失则跳过该文件
3. 生成文件中空缺的 w(*)（及 P-S 的 w(*@*)）用 0 填充；P-S 始终含 fw(@FCC_A1)、-T//fw(@FCC_A1)
4. **FCC 相分离**：若存在 fw(@FCC_A1#1)、fw(@FCC_A1#2) 等列，会提示并用 T 对 fw(@FCC_A1#1) 求导计算 -T//fw(@FCC_A1) 补充
5. 输出列名说明：w(*)、w(*@*)、fw(@*)、-T//fw(@*)、dwdT_L(*@LIQUID) 等

### 计算功能
1. 需要先通过 `Import > Pandat to ThermoQ` 导入数据（至少 P.xlsx 和 Ts.xlsx）
2. **相与 Q 列自动识别**：程序根据数据中的 w(*@*)、-T//fw(@*) 列自动识别固相与 Q 列（如 FCC_A1、BCC_A2），不再固定为 FCC
3. 成分匹配基于整数部分；列名匹配不区分大小写
4. Qtrue 与分量计算针对数据中具备完整列的所有元素，不限于 Mg、Si

### 相面绘制
1. 需要先通过 `Import > Pandat to ThermoQ` 导入数据
2. 选择的数据集和类型必须与已导入的文件对应
3. 选择的元素必须在数据中存在（从w(*)列提取）
4. **列名匹配不区分大小写**：支持w(MG)、w(Mg)、w(mg)等各种大小写组合
5. **平滑曲面**：使用高斯过程回归生成平滑、连续的曲面（需要scikit-learn库）
6. 2D热图和3D图需要matplotlib库
7. 交互式3D图（Plotly 3D）需要plotly库，或会自动生成HTML文件
8. **自动打开和另存为**：绘图完成后自动打开文件，关闭时可选择另存为

### Qtrue值图绘制
1. 需先通过 `Import > Pandat to ThermoQ` 导入 P.xlsx（Equilibrium）或 P-S.xlsx（Scheil）
2. 数据需含 w(X)、w(Y) 及 -T//fw(@phase) 列（phase 自动识别）
3. 列名匹配不区分大小写；X/Y 可选任意已识别元素
4. 平滑曲面需 scikit-learn；2D/3D 需 matplotlib，交互式 3D 需 plotly；绘图后自动打开文件

### 液相面矢量图绘制
1. Excel文件必须包含以下列：
   - `w(X)` 和 `w(Y)`：元素X和Y的质量分数
   - `1/dwdT_L(X@LIQUID)` 和 `1/dwdT_L(Y@LIQUID)`：对应的倒数导数
2. **元素自动识别**：选择Excel文件后，程序会自动从w(*)列中提取可用元素并更新下拉列表
3. 列名格式支持多种变体（大小写、空格等），程序会自动识别
4. 矢量长度会自动缩放，并裁剪到数据域内
5. 如果数据有缺失值，可以勾选"Clean and fill data"进行插值填充
6. 需要matplotlib库支持
7. **自动打开和另存为**：绘图完成后自动打开文件，关闭时可选择另存为
8. **窗口大小优化**：窗口尺寸已优化为800x750，确保所有按钮可见

### 其他
1. 界面主题修改后需要重新启动程序才能生效
2. 确保有足够的磁盘空间存储生成的文件
3. Excel文件需要安装openpyxl或xlrd库才能正确读取

## 贡献指南

欢迎提交问题和改进建议。如果您想贡献代码，请遵循以下步骤：

1. Fork 项目
2. 创建新的分支
3. 提交更改
4. 发起 Pull Request

## 许可证

本项目采用 Mozilla Public License Version 2.0 (MPL-2.0) 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 联系方式

- 邮箱：1786888479@qq.com
