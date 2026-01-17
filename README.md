# ThermoQ

ThermoQ是一个用于热力学计算的应用程序，提供了直观的元素成分输入和计算功能。

## 更新摘要

### 最新版本
- **Tools菜单新增功能**：
  - Composition Converter：质量分数与原子分数转换工具
  - Generate Therocalc Batch File：生成Therocalc批处理文件（.tcm）
  - Extract Therocalc Results：从.exp文件中提取液相线温度、固相线温度和熔程
  - Plot Phase Surfaces：绘制固相面、液相面（2D热图、3D静态图、3D旋转GIF、交互式3D图）
  - Plot Liquidus Vectors：绘制液相面矢量图（U水平、V垂直、Z合成矢量）
- **Pandat导入增强**：
  - 支持四文件导入：`P.xls`、`Ts.xlsx`（平衡凝固）和 `P-S.xlsx`、`Ts-S.xlsx`（Scheil凝固）
  - 修复数据行数丢失问题，正确处理所有数据行
  - 修复FutureWarning警告
- **界面优化**：
  - 简化元素选择界面，仅支持wt%输入
  - 添加成分总和检查功能（自动显示是否达到100 wt%）
  - 修复Total composition显示不全问题

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
- 支持ΔT（熔程）计算模式
- 支持从Pandat软件导出的Excel文件导入元素成分
  - 平衡凝固数据：P.xls 和 Ts.xlsx
  - Scheil凝固数据：P-S.xlsx 和 Ts-S.xlsx（可选）
- 启动画面显示
- 美观的界面设计
- 可自定义的界面主题（当前版本采用黄色背景主题）

### Tools工具集
- **Composition Converter**：质量分数（wt%）与原子分数（at%）双向转换工具
- **Generate Therocalc Batch File**：生成Therocalc批处理文件（.tcm）
  - 支持多元素组合生成
  - 可配置元素范围和步长
  - 支持约束条件设置
- **Extract Therocalc Results**：从Therocalc计算结果中提取数据
  - 提取液相线温度、固相线温度和熔程
  - 支持批量处理.exp文件
  - 自动保存为Excel格式
- **Plot Phase Surfaces**：绘制固相面、液相面可视化
  - 支持2D热图、3D静态图、3D旋转GIF、交互式3D图（Plotly）
  - 支持平衡凝固和Scheil凝固数据
  - 可选择任意两个元素作为X和Y轴
- **Plot Liquidus Vectors**：绘制液相面矢量图
  - 生成U水平矢量图、V垂直矢量图、Z合成矢量图
  - 支持任意两个元素组合
  - 自动识别列名格式
  - 可选数据清理和填充功能

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
   - 点击"Calculate"按钮开始计算ΔT（熔程）
   - 点击"Show Results"查看计算结果

### Tools工具使用

#### Composition Converter（成分转换工具）
1. 打开：`Tools` > `Composition Converter (wt% ↔ at%)`
2. 选择输入单位（wt% 或 at%）
3. 输入元素成分（每行一个元素，格式：`Al 90.0` 或 `Al: 90.0`）
4. 点击"Convert"进行转换
5. 查看转换结果

#### Generate Therocalc Batch File（生成批处理文件）
1. 打开：`Tools` > `Generate Therocalc Batch File`
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

#### Extract Therocalc Results（提取计算结果）
1. 打开：`Tools` > `Extract Therocalc Results`
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

#### Plot Phase Surfaces（绘制相面）
1. 打开：`Tools` > `Plot Phase Surfaces`
2. 选择数据集：Equilibrium/Lever 或 Scheil
3. 选择类型：Liquidus（液相线）或 Solidus（固相线）
4. 选择X和Y元素（从可用元素中选择）
5. 选择可视化类型：
   - 2D Heatmap：2D热图
   - 3D Static：3D静态图
   - 3D Rotation GIF：3D旋转动画GIF
   - Plotly 3D：交互式3D图（HTML格式）
6. 设置输出前缀
7. 点击"Plot"生成图表

#### Plot Liquidus Vectors（绘制液相面矢量图）
1. 打开：`Tools` > `Plot Liquidus Vectors`
2. 选择Excel文件（需包含w(X)、w(Y)、1/dwdT_L(X@LIQUID)、1/dwdT_L(Y@LIQUID)列）
3. 选择X和Y元素（默认：Mg和Si）
4. 可选：勾选"Clean and fill data before plotting"进行数据清理
5. 设置输出前缀（默认：liquid_vectors）
6. 点击"Plot Vectors"生成三个矢量图：
   - U水平矢量图（蓝色）：显示X元素的水平矢量
   - V垂直矢量图（橙色）：显示Y元素的垂直矢量
   - Z合成矢量图（绿色）：显示U和V的合成矢量


## 项目结构
```
ThermoQ/
├── main.py                  # 主程序文件，包含GUI实现和主要功能
├── periodic_table.py        # 元素周期表数据
├── requirements.txt         # 项目依赖包列表
├── README.md                # 项目说明文档
├── LICENSE                  # 许可证文件
├── tcm.py                   # Therocalc批处理文件生成脚本（参考）
├── ExpDataProcessor.py      # Therocalc结果提取脚本（参考）
├── plot_vectors_from_excel.py  # 液相面矢量图绘制脚本（参考）
├── process_excel_clean_fill.py # Excel数据清理和填充脚本（参考）
├── process_solidus_data.py     # 固相线数据处理脚本（参考）
├── process_Liquidus_data.py    # 液相线数据处理脚本（参考）
├── template.txt             # Therocalc模板文件示例
├── template0.txt            # Therocalc头部模板示例
├── template1.txt            # Therocalc尾部模板示例
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

### Therocalc批处理文件生成
1. 模板文件中的占位符格式：`%Element%`（如 `%Fe%`、`%Si%`）
2. 元素配置的Min、Max值应在0-1之间
3. 步长越小，生成的文件越大，处理时间越长
4. 建议先测试小范围生成，确认格式正确后再生成完整文件

### Therocalc结果提取
1. .exp文件必须包含 `$ PLOTTED` 和 `BLOCKEND` 标记之间的数据
2. 数据格式应为：第一列温度，第二列液相分数
3. 如果文件名模式不匹配，将无法提取元素分数，但仍可提取温度数据
4. 处理大量文件时可能需要较长时间，请耐心等待

### 相面绘制
1. 需要先通过 `Import > Pandat to ThermoQ` 导入数据
2. 选择的数据集和类型必须与已导入的文件对应
3. 选择的元素必须在数据中存在（从w(*)列提取）
4. 2D热图和3D图需要matplotlib库
5. 交互式3D图（Plotly 3D）需要plotly库，或会自动生成HTML文件

### 液相面矢量图绘制
1. Excel文件必须包含以下列：
   - `w(X)` 和 `w(Y)`：元素X和Y的质量分数
   - `1/dwdT_L(X@LIQUID)` 和 `1/dwdT_L(Y@LIQUID)`：对应的倒数导数
2. 列名格式支持多种变体（大小写、空格等），程序会自动识别
3. 矢量长度会自动缩放，并裁剪到数据域内
4. 如果数据有缺失值，可以勾选"Clean and fill data"进行插值填充
5. 需要matplotlib库支持

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
