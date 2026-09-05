#!/bin/bash
# Dev-Workbench 一键安装脚本

set -e

echo "🚀 Dev-Workbench 安装程序"
echo "==========================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python3"
    exit 1
fi

echo "✅ Python3 版本: $(python3 --version)"

# 创建安装目录
INSTALL_DIR="$HOME/.local/share/dev-workbench"
mkdir -p "$INSTALL_DIR"
echo "📁 安装目录: $INSTALL_DIR"

# 复制文件
echo "📦 复制文件..."
cp -r src/* "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# 安装依赖
echo "📦 安装 Python 依赖..."
cd "$INSTALL_DIR"
pip3 install --user -r requirements.txt

# 创建启动脚本
echo "🔧 创建启动脚本..."
cat > "$HOME/.local/bin/dev-workbench" << 'EOF'
#!/bin/bash
cd "$HOME/.local/share/dev-workbench"
python3 main.py
EOF
chmod +x "$HOME/.local/bin/dev-workbench"

# 创建桌面快捷方式
echo "🖥️ 创建桌面快捷方式..."
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/dev-workbench.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Dev-Workbench
Comment=开发者自用工作台
Exec=$HOME/.local/bin/dev-workbench
Icon=applications-development
Terminal=false
Categories=Development;
EOF

# 添加到 PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    if [ -f "$HOME/.bashrc" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
    if [ -f "$HOME/.zshrc" ]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
    fi
    echo "ℹ️ 已添加 ~/.local/bin 到 PATH"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "使用方法："
echo "  1. 运行: dev-workbench"
echo "  2. 或在应用菜单中找到 Dev-Workbench"
echo ""
echo "⚠️  请确保 Hermes Agent 在 http://127.0.0.1:8000 运行"
echo "📁 数据文件: $INSTALL_DIR/app.db"