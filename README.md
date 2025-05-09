# ThermoQ

ThermoQ是一个用于热力学计算的图形用户界面应用程序，提供了直观的元素成分输入和计算功能。

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
- 启动画面显示
- 美观的界面设计

## 系统要求

- Python 3.6 或更高版本
- 操作系统：Windows/Linux/MacOS

## 安装步骤

1. 克隆或下载项目代码：
```bash
git clone https://github.com/yourusername/ThermoQ.git
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

## 注意事项

1. 确保所有成分值在0-100%之间
2. 同一元素不能重复添加
3. 成分总和应接近100%
4. 程序内部统一使用质量分数（wt%）存储数据

## 贡献指南

欢迎提交问题和改进建议。如果您想贡献代码，请遵循以下步骤：

1. Fork 项目
2. 创建新的分支
3. 提交更改
4. 发起 Pull Request

## 许可证

[添加许可证信息]

## 联系方式

[添加联系方式]
