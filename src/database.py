"""
数据库操作模块 - 负责所有数据库CRUD操作
"""
import sqlite3
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def _default_db_path() -> str:
    """返回默认数据库路径。打包后存到用户主目录，开发时用当前目录。"""
    if getattr(sys, "frozen", False):
        data_dir = Path.home() / ".dev-workbench"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir / "app.db")
    return "app.db"


class Database:
    """数据库操作封装类"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or _default_db_path()
        self.init_tables()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_tables(self):
        """初始化所有表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建项目表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建子模块表（支持无限层级）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS module (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES module(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建对话表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            tool_calls TEXT,
            tool_call_id TEXT,
            create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES module(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            note TEXT,
            status INTEGER DEFAULT 0,
            sort_id INTEGER DEFAULT 0,
            create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES module(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建备忘录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS note (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES module(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_module ON chat(module_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_module ON task(module_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_note_module ON note(module_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_module_parent ON module(parent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_module_project ON module(project_id)')
        
        # 检查是否有项目，没有则创建默认
        cursor.execute('SELECT COUNT(*) as count FROM project')
        if cursor.fetchone()['count'] == 0:
            cursor.execute('''
            INSERT INTO project (name, description) 
            VALUES (?, ?)
            ''', ('默认项目', '这是默认创建的项目'))
            project_id = cursor.lastrowid
            
            cursor.execute('''
            INSERT INTO module (project_id, parent_id, name, description, sort_order)
            VALUES (?, NULL, ?, ?, ?)
            ''', (project_id, '根模块', '项目的根模块', 0))
        
        conn.commit()
        conn.close()
    
    # ==================== 项目操作 ====================
    def get_projects(self) -> List[Dict]:
        """获取所有项目"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM project ORDER BY create_at DESC')
        projects = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return projects
    
    def create_project(self, name: str, description: str = "") -> int:
        """创建项目，自动创建根模块"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO project (name, description) VALUES (?, ?)',
            (name, description)
        )
        project_id = cursor.lastrowid
        
        cursor.execute('''
        INSERT INTO module (project_id, parent_id, name, description, sort_order)
        VALUES (?, NULL, ?, ?, ?)
        ''', (project_id, '根模块', f'{name} 根模块', 0))
        
        conn.commit()
        conn.close()
        return project_id
    
    def delete_project(self, project_id: int):
        """删除项目（级联删除所有数据）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM project WHERE id = ?', (project_id,))
        conn.commit()
        conn.close()
    
    def get_project(self, project_id: int) -> Optional[Dict]:
        """获取项目信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM project WHERE id = ?', (project_id,))
        project = cursor.fetchone()
        conn.close()
        return dict(project) if project else None
    
    # ==================== 模块操作 ====================
    def get_modules(self, project_id: int, parent_id: int = None) -> List[Dict]:
        """获取子模块列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if parent_id is None:
            cursor.execute('''
                SELECT * FROM module 
                WHERE project_id = ? AND parent_id IS NULL
                ORDER BY sort_order ASC, create_at ASC
            ''', (project_id,))
        else:
            cursor.execute('''
                SELECT * FROM module 
                WHERE project_id = ? AND parent_id = ?
                ORDER BY sort_order ASC, create_at ASC
            ''', (project_id, parent_id))
        
        modules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return modules
    
    def get_all_modules(self, project_id: int) -> List[Dict]:
        """获取项目所有模块"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM module 
            WHERE project_id = ? 
            ORDER BY parent_id, sort_order, create_at
        ''', (project_id,))
        modules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return modules
    
    def create_module(self, project_id: int, name: str, parent_id: int = None, description: str = "") -> int:
        """创建子模块"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if parent_id is None:
            cursor.execute('SELECT MAX(sort_order) as max_sort FROM module WHERE project_id = ? AND parent_id IS NULL', (project_id,))
        else:
            cursor.execute('SELECT MAX(sort_order) as max_sort FROM module WHERE project_id = ? AND parent_id = ?', (project_id, parent_id))
        
        max_sort = cursor.fetchone()['max_sort'] or 0
        
        cursor.execute('''
            INSERT INTO module (project_id, parent_id, name, description, sort_order)
            VALUES (?, ?, ?, ?, ?)
        ''', (project_id, parent_id, name, description, max_sort + 1))
        
        module_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return module_id
    
    def delete_module(self, module_id: int):
        """删除模块（级联删除）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM module WHERE id = ?', (module_id,))
        conn.commit()
        conn.close()
    
    def update_module(self, module_id: int, name: str = None, description: str = None):
        """更新模块"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if name is not None:
            cursor.execute('UPDATE module SET name = ? WHERE id = ?', (name, module_id))
        if description is not None:
            cursor.execute('UPDATE module SET description = ? WHERE id = ?', (description, module_id))
        
        conn.commit()
        conn.close()
    
    def get_module(self, module_id: int) -> Optional[Dict]:
        """获取模块信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM module WHERE id = ?', (module_id,))
        module = cursor.fetchone()
        conn.close()
        return dict(module) if module else None
    
    def get_module_path(self, module_id: int) -> List[Dict]:
        """获取模块路径（从根到当前）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        path = []
        current_id = module_id
        
        while current_id:
            cursor.execute('SELECT * FROM module WHERE id = ?', (current_id,))
            module = cursor.fetchone()
            if not module:
                break
            path.insert(0, dict(module))
            current_id = module['parent_id']
        
        conn.close()
        return path
    
    # ==================== 对话操作 ====================
    def get_chat_history(self, module_id: int, limit: int = 14) -> List[Dict]:
        """获取最近N轮对话"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM chat 
            WHERE module_id = ? 
            ORDER BY create_at DESC 
            LIMIT ?
        ''', (module_id, limit * 2))
        
        rows = cursor.fetchall()
        rows.reverse()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_all_chat_history(self, module_id: int) -> List[Dict]:
        """获取所有对话"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM chat 
            WHERE module_id = ? 
            ORDER BY create_at ASC
        ''', (module_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def save_chat_message(self, module_id: int, role: str, content: str = None, 
                          tool_calls: List = None, tool_call_id: str = None):
        """保存对话消息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        tool_calls_json = None
        if tool_calls:
            tool_calls_json = json.dumps(tool_calls, ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO chat (module_id, role, content, tool_calls, tool_call_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (module_id, role, content, tool_calls_json, tool_call_id))
        
        chat_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return chat_id
    
    # ==================== 任务操作 ====================
    def get_tasks(self, module_id: int) -> List[Dict]:
        """获取任务列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM task 
            WHERE module_id = ? 
            ORDER BY sort_id ASC, create_at ASC
        ''', (module_id,))
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return tasks
    
    def create_task(self, module_id: int, title: str, note: str = "", status: int = 0) -> int:
        """创建任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT MAX(sort_id) as max_sort FROM task WHERE module_id = ?', (module_id,))
        max_sort = cursor.fetchone()['max_sort'] or 0
        
        cursor.execute('''
            INSERT INTO task (module_id, title, note, status, sort_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (module_id, title, note, status, max_sort + 1))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    def update_task_status(self, task_id: int, status: int):
        """更新任务状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE task SET status = ? WHERE id = ?', (status, task_id))
        conn.commit()
        conn.close()
    
    def delete_task(self, task_id: int):
        """删除任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM task WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()
    
    def batch_create_tasks(self, module_id: int, tasks: List[Dict]):
        """批量创建任务"""
        for task in tasks:
            self.create_task(
                module_id,
                task['title'],
                task.get('note', ''),
                task.get('status', 0)
            )
    
    # ==================== 备忘录操作 ====================
    def get_notes(self, module_id: int) -> List[Dict]:
        """获取备忘录列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM note 
            WHERE module_id = ? 
            ORDER BY create_at DESC
        ''', (module_id,))
        notes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return notes
    
    def create_note(self, module_id: int, title: str, content: str = "") -> int:
        """创建备忘录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO note (module_id, title, content)
            VALUES (?, ?, ?)
        ''', (module_id, title, content))
        note_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return note_id
    
    def update_note(self, note_id: int, title: str = None, content: str = None):
        """更新备忘录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if title is not None:
            cursor.execute('UPDATE note SET title = ? WHERE id = ?', (title, note_id))
        if content is not None:
            cursor.execute('UPDATE note SET content = ? WHERE id = ?', (content, note_id))
        
        conn.commit()
        conn.close()
    
    def delete_note(self, note_id: int):
        """删除备忘录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM note WHERE id = ?', (note_id,))
        conn.commit()
        conn.close()