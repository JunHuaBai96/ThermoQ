# ThermoQ

ThermoQ是一个用于热力学计算的应用程序，提供了直观的元素成分输入和计算功能。

## 功能特点

- 图形化用户界面，操作简单直观
- 支持从元素周期表中选择元素
- 支持两种成分输入方式：
  - 质量分数（wt%）
  - 原子分数（at%）
- 实时成分单位转换
- 支持多种计算模式：
  - QΣbin
  - Qture
  - Qmult
- 支持从Pandat软件导出的Excel文件导入元素成分
- 启动画面显示
- 美观的界面设计
- 可自定义的界面主题（当前版本采用黄色背景主题）

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
  - tkinter
  - Pillow
  - pandas (用于Excel文件导入)

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
   - 选择成分单位（wt% 或 at%）
   - 输入成分值
   - 点击"Add Element"按钮添加元素

3. 管理元素：
   - 在表格中查看已添加的元素
   - 选择元素后点击"Remove Selected"可以删除元素
   - 可以随时切换成分单位，系统会自动转换显示值

4. 从Pandat导入数据：
   - 点击菜单栏中的"Import" > "Pandat to ThermoQ"
   - 在弹出窗口中点击"Browse"选择Pandat导出的Excel文件
   - 预览数据无误后点击"Import"导入元素成分
   - 支持自动识别包含元素和成分的列

4. 进行计算：
   - 选择计算模式（QΣbin/Qture/Qmult）
   - 点击"Calculate"按钮开始计算
   - 点击"Show Results"查看计算结果


## 项目结构
- `main.py`: 主程序文件，包含GUI实现和主要功能
- `periodic_table.py`: 元素周期表数据
- `requirements.txt`: 项目依赖包列表
- `images/`: 存放程序使用的图片资源


## 依赖包

- tkinter: GUI界面
- PIL (Python Imaging Library): 图像处理
- 其他依赖见 requirements.txt


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

1. 确保所有成分值在0-100%之间
2. 同一元素不能重复添加
3. 成分总和应接近100%
4. 程序内部统一使用质量分数（wt%）存储数据
5. 界面主题修改后需要重新启动程序才能生效

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
