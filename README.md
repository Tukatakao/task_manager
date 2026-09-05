# Dev-Workbench

> 开发者自用工作台 —— 项目管理 + AI 辅助工具

## ✨ 特性

- 📁 **项目隔离**：支持多层级子模块，无限嵌套
- 💬 **智能对话**：对接 DeepSeek API（OpenAI 兼容），支持 tool_calls
- ✅ **任务管理**：创建、状态切换、AI 自动拆解
- 📝 **备忘录**：作为永久记忆，自动注入上下文

## 🚀 快速开始

### 环境要求

- Python 3.9+（推荐 3.11）
- 有图形界面的 Linux 桌面（依赖 GTK3）

### 安装依赖

```bash
git clone <你的仓库地址>
cd Dev-Workbench
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 运行

```bash
source .venv/bin/activate
python src/main.py
```

### 配置 DeepSeek API Key

两种方式任选其一：

1. **界面配置**：启动后点左上角 ⚙️ 设置，填入你的 DeepSeek API Key 并保存。
2. **文件配置**：在项目根目录创建 `.env` 文件：

   ```
   DEEPSEEK_API_KEY=sk-你的key
   ```

   可选覆盖：`DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com/v1`）、`DEEPSEEK_MODEL`（默认 `deepseek-chat`）。

> ⚠️ `.env` 和 `app.db` 已被 `.gitignore` 忽略，不会提交到 git，请放心使用。

## 📦 打包为可执行文件 / deb

打包需要 `flet` CLI 和 PyInstaller：

```bash
pip install pyinstaller
```

然后运行：

```bash
./build.sh
```

会在 `dist/` 生成可执行文件，并在项目根目录生成 `.deb` 安装包。

安装 deb：

```bash
sudo apt install ./dev-workbench_*.deb
```

> 打包后的程序会把配置和数据存到 `~/.dev-workbench/` 目录，不会包含打包者的 API Key 或数据。

## 📁 目录结构

```
src/
├── main.py            # 主程序（Flet 界面）
├── database.py        # SQLite 数据库操作
├── hermes_client.py   # DeepSeek API 客户端
└── init_db.py         # 数据库初始化脚本
```
