"""
数据库初始化脚本 - 独立运行
"""
import os
import sys
from database import Database


def init_database():
    """初始化数据库"""
    db_path = "app.db"
    
    # 检查数据库是否已存在
    if os.path.exists(db_path):
        response = input(f"⚠️ 数据库文件 '{db_path}' 已存在。\n是否删除并重新创建？(y/N): ")
        if response.lower() == 'y':
            os.remove(db_path)
            print(f"✅ 已删除旧数据库: {db_path}")
        else:
            print("ℹ️ 保留现有数据库")
            return
    
    # 创建新数据库
    db = Database(db_path)
    print("✅ 数据库初始化成功！")
    print(f"📁 数据库文件: {os.path.abspath(db_path)}")
    print("📋 已创建默认项目和根模块")
    
    # 显示表结构
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    print(f"\n📊 已创建表: {', '.join(tables)}")
    conn.close()


if __name__ == "__main__":
    print("🚀 Dev-Workbench 数据库初始化")
    print("=" * 40)
    init_database()
    print("\n💡 提示: 运行 'python3 main.py' 启动应用")