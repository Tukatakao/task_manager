"""
Dev-Workbench 主程序 - Flet 桌面应用 (修复版)
"""
import flet as ft
import json
import re
import threading
from typing import List, Dict
from database import Database
from hermes_client import HermesClient


class DevWorkbench(ft.Container):
    """主应用控件"""
    
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.pg = page
        self.db = Database()
        self.hermes = HermesClient()
        
        # 当前状态
        self.current_project_id = None
        self.current_module_id = None
        self.current_module_path = []
        self.is_processing = False
        
        # UI 组件引用
        self.project_list = None
        self.module_tree = None
        self.chat_list = None
        self.chat_input = None
        self.task_list = None
        self.note_list = None
        self.project_title = None
        self.module_title = None
        self.breadcrumb = None
        self.send_btn = None
        
        # 加载默认项目
        self.load_default_project()
        
        # 检查 Hermes 服务
        self.check_hermes_health()
        
        # 构建 UI
        self.content = self.build_ui()

    def load_default_project(self):
        """加载默认项目"""
        projects = self.db.get_projects()
        if projects:
            self.current_project_id = projects[0]['id']
            modules = self.db.get_modules(self.current_project_id, parent_id=None)
            if modules:
                self.current_module_id = modules[0]['id']
                self.current_module_path = self.db.get_module_path(self.current_module_id)
    
    def check_hermes_health(self):
        """检查 Hermes 服务健康状态"""
        if not self.hermes.check_health():
            self.pg.snack_bar = ft.SnackBar(
                ft.Text("⚠️ Hermes 服务未连接 (http://127.0.0.1:8000)"),
                bgcolor=ft.Colors.ORANGE_500,
                duration=5000,
            )
            self.pg.snack_bar.open = True
            self.pg.update()
    
    def build_ui(self):
        """构建 UI"""
        return ft.Container(
            content=ft.Row(
                controls=[
                    # 左侧边栏
                    self.build_sidebar(),
                    # 右侧主区域
                    ft.Container(
                        expand=True,
                        content=ft.Column(
                            controls=[
                                self.build_project_panel(),
                                self.build_chat_panel(),
                            ],
                            spacing=0,
                            expand=True,
                        ),
                        padding=0,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
            bgcolor=ft.Colors.GREY_50,
        )
    
    def build_sidebar(self):
        """构建左侧边栏"""
        # 标题
        title = ft.Container(
            content=ft.Text("📁 Dev-Workbench", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            padding=ft.Padding.all(15),
            bgcolor=ft.Colors.BLUE_700,
            width=280,
        )
        
        # 项目列表
        self.project_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        
        # 新建项目按钮
        new_project_btn = ft.Button(
            "➕ 新建项目",
            on_click=self.show_new_project_dialog,
            width=250,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
        )
        
        # 模块树标题
        module_title = ft.Container(
            content=ft.Text("📂 模块导航", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        )
        
        # 模块树
        self.module_tree = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        
        # 新建模块按钮
        new_module_btn = ft.IconButton(
            icon=ft.Icons.CREATE_NEW_FOLDER,
            icon_size=20,
            tooltip="创建子模块",
            on_click=self.show_new_module_dialog,
            style=ft.ButtonStyle(color=ft.Colors.BLUE_600),
        )
        
        module_header = ft.Row(
            controls=[module_title, new_module_btn],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        return ft.Container(
            width=280,
            bgcolor=ft.Colors.BLUE_50,
            content=ft.Column(
                controls=[
                    title,
                    ft.Container(
                        content=self.project_list,
                        height=180,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    ),
                    ft.Divider(height=1),
                    module_header,
                    ft.Container(
                        content=self.module_tree,
                        expand=True,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    ),
                    ft.Container(
                        content=new_project_btn,
                        padding=ft.Padding.all(10),
                        alignment=ft.Alignment.CENTER,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
        )
    
    def build_project_panel(self):
        """构建右上方面板"""
        # 标题区域
        self.project_title = ft.Text("未选择项目", size=18, weight=ft.FontWeight.BOLD)
        self.module_title = ft.Text("", size=14, color=ft.Colors.GREY_600)
        self.breadcrumb = ft.Row(spacing=5, controls=[])
        
        # 备忘录
        note_title = ft.Text("📝 备忘录", size=15, weight=ft.FontWeight.BOLD)
        self.note_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
        add_note_btn = ft.IconButton(
            icon=ft.Icons.ADD,
            icon_size=20,
            tooltip="添加备忘录",
            on_click=self.show_add_note_dialog,
        )
        
        note_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[note_title, add_note_btn],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(height=5),
                        self.note_list,
                    ],
                    spacing=5,
                ),
                padding=ft.Padding.all(10),
                width=350,
                height=230,
            ),
            elevation=2,
        )
        
        # 任务看板
        task_title = ft.Text("✅ 任务看板", size=15, weight=ft.FontWeight.BOLD)
        self.task_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
        add_task_btn = ft.IconButton(
            icon=ft.Icons.ADD,
            icon_size=20,
            tooltip="添加任务",
            on_click=self.show_add_task_dialog,
        )
        task_breakdown_btn = ft.IconButton(
            icon=ft.Icons.SPLITSCREEN,
            icon_size=20,
            tooltip="任务拆解 (AI)",
            on_click=self.show_task_breakdown_dialog,
        )
        
        task_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[task_title, add_task_btn, task_breakdown_btn],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(height=5),
                        self.task_list,
                    ],
                    spacing=5,
                ),
                padding=ft.Padding.all(10),
                expand=True,
                height=230,
            ),
            elevation=2,
        )
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[self.project_title, ft.Text(" / ", size=14, color=ft.Colors.GREY_400), self.module_title],
                                    spacing=5,
                                ),
                                self.breadcrumb,
                            ],
                            spacing=2,
                        ),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    ),
                    ft.Row(
                        controls=[note_card, task_card],
                        spacing=10,
                        expand=True,
                    ),
                ],
                spacing=5,
                expand=True,
            ),
            height=300,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_300)),
            padding=ft.Padding.all(10),
        )
    
    def build_chat_panel(self):
        """构建右下方面板"""
        self.chat_list = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=True,
        )
        
        chat_container = ft.Container(
            content=self.chat_list,
            expand=True,
            padding=ft.Padding.all(10),
            bgcolor=ft.Colors.WHITE,
        )
        
        self.chat_input = ft.TextField(
            hint_text="输入消息... (Enter 发送)",
            multiline=True,
            min_lines=1,
            max_lines=5,
            expand=True,
            on_submit=self.send_message,
        )
        
        self.send_btn = ft.IconButton(
            icon=ft.Icons.SEND,
            icon_size=24,
            tooltip="发送",
            on_click=self.send_message,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_600,
                color=ft.Colors.WHITE,
            ),
        )
        
        extract_note_btn = ft.IconButton(
            icon=ft.Icons.NOTE_ADD,
            icon_size=24,
            tooltip="提取备忘",
            on_click=self.extract_note_from_selection,
        )
        
        input_row = ft.Row(
            controls=[
                self.chat_input,
                extract_note_btn,
                self.send_btn,
            ],
            spacing=10,
            alignment=ft.MainAxisAlignment.END,
        )
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    chat_container,
                    ft.Container(
                        content=input_row,
                        padding=ft.Padding.all(10),
                        bgcolor=ft.Colors.GREY_50,
                        border=ft.Border.only(top=ft.BorderSide(1, ft.Colors.GREY_300)),
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
        )
    
    # ==================== UI 更新方法 ====================
    def update_all(self):
        """更新所有 UI 组件"""
        self.update_project_list()
        self.update_module_tree()
        self.update_project_panel()
        self.update_chat_history()
        self.update()
    
    def update_project_list(self):
        """更新项目列表"""
        projects = self.db.get_projects()
        controls = []
        
        for project in projects:
            is_active = project['id'] == self.current_project_id
            controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.FOLDER_OPEN if is_active else ft.Icons.FOLDER,
                                color=ft.Colors.BLUE_600 if is_active else ft.Colors.GREY_600,
                                size=18,
                            ),
                            ft.Text(
                                project['name'],
                                size=13,
                                weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                                color=ft.Colors.BLUE_700 if is_active else ft.Colors.BLACK,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=16,
                                tooltip="删除项目",
                                data=project['id'],
                                on_click=self.delete_project,
                                icon_color=ft.Colors.RED_400,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=5,
                    ),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    bgcolor=ft.Colors.BLUE_100 if is_active else ft.Colors.TRANSPARENT,
                    border_radius=ft.BorderRadius.all(5),
                    ink=True,
                    on_click=lambda e, pid=project['id']: self.switch_project(pid),
                )
            )
        
        self.project_list.controls = controls
        self.project_list.update()
    
    def update_module_tree(self):
        """更新模块树"""
        if not self.current_project_id:
            self.module_tree.controls = [ft.Text("请选择项目", color=ft.Colors.GREY_500)]
            self.module_tree.update()
            return
        
        all_modules = self.db.get_all_modules(self.current_project_id)
        
        def build_tree(parent_id=None, level=0):
            children = [m for m in all_modules if m['parent_id'] == parent_id]
            controls = []
            
            for module in children:
                is_active = module['id'] == self.current_module_id
                has_children = any(m['parent_id'] == module['id'] for m in all_modules)
                
                controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Container(width=level * 15),
                                ft.Icon(
                                    ft.Icons.FOLDER_OPEN if is_active else 
                                    (ft.Icons.FOLDER if has_children else ft.Icons.DESCRIPTION),
                                    color=ft.Colors.BLUE_600 if is_active else ft.Colors.GREY_600,
                                    size=16,
                                ),
                                ft.Text(
                                    module['name'],
                                    size=12,
                                    weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                                    color=ft.Colors.BLUE_700 if is_active else ft.Colors.BLACK,
                                    expand=True,
                                ),
                                ft.PopupMenuButton(
                                    icon=ft.Icons.MORE_VERT,
                                    icon_size=16,
                                    items=[
                                        ft.PopupMenuItem(
                                            content="新建子模块",
                                            icon=ft.Icons.CREATE_NEW_FOLDER,
                                            on_click=lambda e, mid=module['id']: self.show_new_module_dialog(parent_id=mid),
                                        ),
                                        ft.PopupMenuItem(
                                            content="重命名",
                                            icon=ft.Icons.EDIT,
                                            on_click=lambda e, mid=module['id']: self.show_rename_module_dialog(mid),
                                        ),
                                        ft.PopupMenuItem(
                                            content="删除",
                                            icon=ft.Icons.DELETE,
                                            on_click=lambda e, mid=module['id']: self.delete_module(mid),
                                        ),
                                    ],
                                ),
                            ],
                            spacing=2,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        padding=ft.Padding.symmetric(horizontal=5, vertical=3),
                        bgcolor=ft.Colors.BLUE_50 if is_active else ft.Colors.TRANSPARENT,
                        border_radius=ft.BorderRadius.all(3),
                        ink=True,
                        on_click=lambda e, mid=module['id']: self.switch_module(mid),
                    )
                )
                
                if has_children:
                    controls.extend(build_tree(module['id'], level + 1))
            
            return controls
        
        tree_controls = build_tree()
        if not tree_controls:
            tree_controls.append(ft.Text("暂无模块，请创建", color=ft.Colors.GREY_500))
        
        self.module_tree.controls = tree_controls
        self.module_tree.update()
    
    def update_project_panel(self):
        """更新项目面板"""
        if not self.current_project_id:
            self.project_title.value = "未选择项目"
            self.module_title.value = ""
            self.breadcrumb.controls = []
            self.note_list.controls = [ft.Text("请选择项目", color=ft.Colors.GREY_500)]
            self.task_list.controls = [ft.Text("请选择项目", color=ft.Colors.GREY_500)]
            self.update()
            return
        
        # 项目信息
        project = self.db.get_project(self.current_project_id)
        if project:
            self.project_title.value = f"📁 {project['name']}"
        
        # 模块信息
        if self.current_module_id:
            module = self.db.get_module(self.current_module_id)
            if module:
                self.module_title.value = module['name']
                
                # 面包屑
                path = self.db.get_module_path(self.current_module_id)
                breadcrumb_controls = []
                for i, m in enumerate(path):
                    breadcrumb_controls.append(
                        ft.TextButton(
                            content=ft.Text(
                                m['name'],
                                size=14,
                                weight=ft.FontWeight.BOLD if i == len(path)-1 else ft.FontWeight.NORMAL,
                                color=ft.Colors.BLUE_600 if i < len(path)-1 else ft.Colors.BLACK,
                            ),
                            on_click=lambda e, mid=m['id']: self.switch_module(mid),
                            height=25,
                        )
                    )
                    if i < len(path)-1:
                        breadcrumb_controls.append(ft.Icon(ft.Icons.ARROW_FORWARD, size=14, color=ft.Colors.GREY_400))
                self.breadcrumb.controls = breadcrumb_controls
        
        # 备忘录
        notes = self.db.get_notes(self.current_module_id) if self.current_module_id else []
        note_controls = []
        for note in notes:
            note_controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(note['title'], size=13, weight=ft.FontWeight.BOLD, expand=True),
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            icon_size=16,
                                            tooltip="编辑",
                                            data=note['id'],
                                            on_click=self.show_edit_note_dialog,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            icon_size=16,
                                            tooltip="删除",
                                            data=note['id'],
                                            on_click=self.delete_note,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Text(note['content'] or "", size=12, color=ft.Colors.GREY_700),
                                ft.Text(
                                    note['create_at'][:16] if note['create_at'] else "",
                                    size=10,
                                    color=ft.Colors.GREY_500,
                                ),
                            ],
                            spacing=2,
                        ),
                        padding=ft.Padding.all(8),
                    ),
                    elevation=1,
                )
            )
        
        if not note_controls:
            note_controls.append(ft.Text("暂无备忘录", color=ft.Colors.GREY_500))
        self.note_list.controls = note_controls
        
        # 任务
        tasks = self.db.get_tasks(self.current_module_id) if self.current_module_id else []
        status_map = {0: "待开始", 1: "进行中", 2: "阻塞", 3: "完成"}
        status_colors = {0: ft.Colors.GREY, 1: ft.Colors.BLUE, 2: ft.Colors.RED, 3: ft.Colors.GREEN}
        
        task_controls = []
        for task in tasks:
            status_color = status_colors.get(task['status'], ft.Colors.GREY)
            
            status_dropdown = ft.Dropdown(
                width=90,
                height=32,
                value=str(task['status']),
                options=[
                    ft.dropdown.Option("0", "待开始"),
                    ft.dropdown.Option("1", "进行中"),
                    ft.dropdown.Option("2", "阻塞"),
                    ft.dropdown.Option("3", "完成"),
                ],
                data=task['id'],
                on_change=self.change_task_status,
                text_size=11,
            )
            
            task_controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CIRCLE, color=status_color, size=10),
                                ft.Column(
                                    controls=[
                                        ft.Text(task['title'], size=12, weight=ft.FontWeight.W_500),
                                        ft.Text(task['note'] or "", size=11, color=ft.Colors.GREY_600),
                                    ],
                                    spacing=1,
                                    expand=True,
                                ),
                                status_dropdown,
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_size=16,
                                    tooltip="删除任务",
                                    data=task['id'],
                                    on_click=self.delete_task,
                                    icon_color=ft.Colors.RED_400,
                                ),
                            ],
                            spacing=5,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        padding=ft.Padding.all(6),
                    ),
                    elevation=1,
                )
            )
        
        if not task_controls:
            task_controls.append(ft.Text("暂无任务", color=ft.Colors.GREY_500))
        self.task_list.controls = task_controls
        
        self.update()
    
    def update_chat_history(self):
        """更新对话历史"""
        if not self.current_module_id:
            self.chat_list.controls = [ft.Text("请选择模块", color=ft.Colors.GREY_500)]
            self.chat_list.update()
            return
        
        chats = self.db.get_all_chat_history(self.current_module_id)
        controls = []
        
        for chat in chats:
            if chat['role'] == 'user':
                controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.CircleAvatar(content=ft.Text("👤", size=16), bgcolor=ft.Colors.BLUE_100),
                                ft.Container(
                                    content=ft.Text(chat['content'] or "", size=14),
                                    bgcolor=ft.Colors.BLUE_50,
                                    padding=ft.Padding.all(10),
                                    border_radius=ft.BorderRadius.all(10),
                                    expand=True,
                                ),
                            ],
                            spacing=5,
                        ),
                        margin=ft.Margin.only(bottom=5),
                    )
                )
            elif chat['role'] == 'assistant':
                controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.CircleAvatar(content=ft.Text("🤖", size=16), bgcolor=ft.Colors.GREEN_100),
                                ft.Container(
                                    content=ft.Markdown(chat['content'] or "", selectable=True),
                                    bgcolor=ft.Colors.GREY_100,
                                    padding=ft.Padding.all(10),
                                    border_radius=ft.BorderRadius.all(10),
                                    expand=True,
                                ),
                            ],
                            spacing=5,
                        ),
                        margin=ft.Margin.only(bottom=5),
                    )
                )
                
                if chat.get('tool_calls'):
                    try:
                        tool_calls = json.loads(chat['tool_calls'])
                        for tc in tool_calls:
                            controls.append(
                                ft.Container(
                                    content=ft.Row(
                                        controls=[
                                            ft.Icon(ft.Icons.BUILD, size=16, color=ft.Colors.ORANGE),
                                            ft.Text(
                                                f"🔧 调用: {tc.get('function', {}).get('name', 'unknown')}",
                                                size=12,
                                                color=ft.Colors.ORANGE_700,
                                            ),
                                        ],
                                        spacing=5,
                                    ),
                                    margin=ft.Margin.only(left=40, bottom=5),
                                )
                            )
                    except:
                        pass
            elif chat['role'] == 'tool':
                controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=ft.Colors.GREEN),
                                ft.Text(f"📊 工具结果: {chat['content'][:100]}...", size=12, color=ft.Colors.GREY_600),
                            ],
                            spacing=5,
                        ),
                        margin=ft.Margin.only(left=40, bottom=5),
                    )
                )
        
        if not controls:
            controls.append(ft.Text("暂无对话记录", color=ft.Colors.GREY_500))
        
        self.chat_list.controls = controls
        self.chat_list.update()

    # ==================== 核心操作 ====================
    def switch_project(self, project_id: int):
        """切换项目"""
        if project_id == self.current_project_id:
            return
        
        self.current_project_id = project_id
        modules = self.db.get_modules(project_id, parent_id=None)
        if modules:
            self.current_module_id = modules[0]['id']
            self.current_module_path = self.db.get_module_path(self.current_module_id)
        else:
            self.current_module_id = None
            self.current_module_path = []
        
        self.update_all()
    
    def switch_module(self, module_id: int):
        """切换模块"""
        if module_id == self.current_module_id:
            return
        
        self.current_module_id = module_id
        self.current_module_path = self.db.get_module_path(module_id)
        self.update_all()
    
    def send_message(self, e):
        """发送消息"""
        if self.is_processing:
            self.show_snackbar("正在处理中，请稍候...", ft.Colors.ORANGE)
            return
        
        if not self.current_module_id:
            self.show_snackbar("请先选择模块", ft.Colors.ORANGE)
            return
        
        message = self.chat_input.value.strip()
        if not message:
            return
        
        self.chat_input.value = ""
        self.chat_input.update()
        
        self.is_processing = True
        self.send_btn.disabled = True
        self.send_btn.update()
        
        self.db.save_chat_message(self.current_module_id, "user", content=message)
        self.update_chat_history()
        
        threading.Thread(target=self.process_hermes_request, args=(message,), daemon=True).start()
    
    def process_hermes_request(self, user_message: str):
        """处理 Hermes 请求（后台线程）"""
        try:
            messages = self.build_hermes_context(user_message)
            tools = self.hermes.get_available_tools()
            response = self.hermes.chat_completion(messages, tools)
            
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            content = message.get('content', '')
            tool_calls = message.get('tool_calls', [])
            
            # 自动解析任务
            if content and "任务清单" in content:
                self.parse_tasks_from_response(content)
            
            # 自动解析备忘
            if content and ("备忘" in content or "关键参数" in content):
                self.parse_note_from_response(content)
            
            self.db.save_chat_message(
                self.current_module_id,
                "assistant",
                content=content,
                tool_calls=tool_calls if tool_calls else None
            )
            
            if tool_calls:
                self.process_tool_calls(tool_calls)
            
            self.show_snackbar("✅ 处理完成", ft.Colors.GREEN_400)
            
        except Exception as e:
            self.show_snackbar(f"❌ {str(e)}", ft.Colors.RED_400)
            self.db.save_chat_message(
                self.current_module_id,
                "assistant",
                content=f"❌ 错误: {str(e)}"
            )
        
        finally:
            self.is_processing = False
            self.send_btn.disabled = False
            self.send_btn.update()
            self.update_all()
            self.pg.update()
    
    def build_hermes_context(self, user_message: str) -> List[Dict]:
        """构建 Hermes 上下文"""
        messages = []
        
        # System prompt
        notes = self.db.get_notes(self.current_module_id) if self.current_module_id else []
        notes_text = "\n".join([f"- {note['title']}: {note['content'] or ''}" for note in notes])
        
        path_info = ""
        if self.current_module_path:
            path_names = [m['name'] for m in self.current_module_path]
            path_info = f"当前模块: {' > '.join(path_names)}"
        
        system_prompt = f"""你是 Dev-Workbench 智能助手。

{path_info}

## 当前模块备忘录（永久记忆）
{notes_text}

## 能力
- 帮助管理项目、任务、备忘录
- 调用工具执行文件操作、命令等
- 任务拆解输出 Markdown 格式
- 提取备忘结构化输出

请保持回答简洁专业。"""
        
        messages.append({"role": "system", "content": system_prompt})
        
        # 历史对话（最近14轮）
        history = self.db.get_chat_history(self.current_module_id, limit=14)
        for msg in history:
            if msg['role'] == 'user':
                messages.append({"role": "user", "content": msg['content'] or ""})
            elif msg['role'] == 'assistant':
                assistant_msg = {"role": "assistant", "content": msg['content'] or ""}
                if msg.get('tool_calls'):
                    try:
                        assistant_msg["tool_calls"] = json.loads(msg['tool_calls'])
                    except:
                        pass
                messages.append(assistant_msg)
            elif msg['role'] == 'tool':
                messages.append({
                    "role": "tool",
                    "tool_call_id": msg['tool_call_id'],
                    "content": msg['content'] or ""
                })
        
        messages.append({"role": "user", "content": user_message})
        return messages
    
    def parse_tasks_from_response(self, content: str):
        """解析任务清单"""
        lines = content.split('\n')
        tasks = []
        for line in lines:
            line = line.strip()
            if re.match(r'^[-*]\s+', line) or re.match(r'^\d+\.\s+', line):
                task_text = re.sub(r'^[-*\d]+\.?\s+', '', line)
                task_text = re.sub(r'\[[ xX]\]\s*', '', task_text)
                if task_text:
                    tasks.append({'title': task_text[:100], 'note': '', 'status': 0})
        
        if tasks:
            self.db.batch_create_tasks(self.current_module_id, tasks)
            self.show_snackbar(f"✅ 已创建 {len(tasks)} 个任务", ft.Colors.GREEN)
    
    def parse_note_from_response(self, content: str):
        """解析备忘录"""
        title = "从对话提取的备忘"
        lines = content.split('\n')
        for line in lines:
            if any(kw in line for kw in ['关键参数', '方案', '踩坑', '备忘']):
                title = line.strip()[:50]
                break
        
        self.db.create_note(self.current_module_id, title, content)
        self.show_snackbar("✅ 已保存备忘录", ft.Colors.GREEN)
    
    def process_tool_calls(self, tool_calls: List[Dict]):
        """处理工具调用"""
        pass  # Hermes MCP 自动处理
    
    def change_task_status(self, e):
        """修改任务状态"""
        task_id = e.control.data
        status = int(e.control.value)
        self.db.update_task_status(task_id, status)
        self.update_project_panel()
    
    def delete_task(self, e):
        """删除任务"""
        task_id = e.control.data
        self.db.delete_task(task_id)
        self.update_project_panel()
    
    def delete_note(self, e):
        """删除备忘录"""
        note_id = e.control.data
        self.db.delete_note(note_id)
        self.update_project_panel()
    
    def show_snackbar(self, message: str, color=ft.Colors.BLUE):
        """显示提示消息"""
        self.pg.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color, duration=3000)
        self.pg.snack_bar.open = True
        self.pg.update()
    
    # ==================== 对话框 ====================
    def show_new_project_dialog(self, e):
        """新建项目"""
        print(">>> 点击了「新建项目」按钮", flush=True)
        name_field = ft.TextField(label="项目名称", width=300)
        desc_field = ft.TextField(label="项目描述", width=300, multiline=True, max_lines=3)
        
        def create_project(e):
            name = name_field.value.strip()
            if not name:
                name_field.error_text = "请输入名称"
                dialog.update()
                return
            
            self.db.create_project(name, desc_field.value.strip())
            dialog.open = False
            dialog.update()
            
            projects = self.db.get_projects()
            if projects:
                self.switch_project(projects[0]['id'])
        
        dialog = ft.AlertDialog(
            title=ft.Text("新建项目"),
            content=ft.Column([name_field, desc_field], width=320, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("创建", on_click=create_project),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def show_new_module_dialog(self, e, parent_id=None):
        """新建子模块"""
        name_field = ft.TextField(label="模块名称", width=300)
        desc_field = ft.TextField(label="模块描述", width=300, multiline=True, max_lines=3)
        
        def create_module(e):
            name = name_field.value.strip()
            if not name:
                name_field.error_text = "请输入名称"
                dialog.update()
                return
            
            self.db.create_module(self.current_project_id, name, parent_id, desc_field.value.strip())
            dialog.open = False
            dialog.update()
            self.update_all()
        
        dialog = ft.AlertDialog(
            title=ft.Text("新建子模块"),
            content=ft.Column([name_field, desc_field], width=320, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("创建", on_click=create_module),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def show_rename_module_dialog(self, module_id: int):
        """重命名模块"""
        module = self.db.get_module(module_id)
        if not module:
            return
        
        name_field = ft.TextField(label="模块名称", value=module['name'], width=300)
        
        def rename_module(e):
            name = name_field.value.strip()
            if not name:
                name_field.error_text = "请输入名称"
                dialog.update()
                return
            
            self.db.update_module(module_id, name=name)
            dialog.open = False
            dialog.update()
            self.update_all()
        
        dialog = ft.AlertDialog(
            title=ft.Text("重命名模块"),
            content=name_field,
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("保存", on_click=rename_module),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def delete_project(self, e):
        """删除项目"""
        project_id = e.control.data
        
        def confirm_delete(e):
            self.db.delete_project(project_id)
            dialog.open = False
            dialog.update()
            
            projects = self.db.get_projects()
            if projects:
                self.switch_project(projects[0]['id'])
            else:
                self.current_project_id = None
                self.current_module_id = None
                self.update_all()
        
        dialog = ft.AlertDialog(
            title=ft.Text("确认删除"),
            content=ft.Text("确定要删除该项目及其所有数据吗？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("删除", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def delete_module(self, module_id: int):
        """删除模块"""
        def confirm_delete(e):
            self.db.delete_module(module_id)
            dialog.open = False
            dialog.update()
            
            modules = self.db.get_modules(self.current_project_id, parent_id=None)
            if modules:
                self.switch_module(modules[0]['id'])
            else:
                self.current_module_id = None
                self.update_all()
        
        dialog = ft.AlertDialog(
            title=ft.Text("确认删除"),
            content=ft.Text("确定要删除该模块及其所有子模块和数据吗？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("删除", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def show_add_task_dialog(self, e):
        """添加任务"""
        title_field = ft.TextField(label="任务标题", width=350)
        note_field = ft.TextField(label="备注", width=350, multiline=True, max_lines=3)
        
        def add_task(e):
            title = title_field.value.strip()
            if not title:
                title_field.error_text = "请输入标题"
                dialog.update()
                return
            
            self.db.create_task(self.current_module_id, title, note_field.value.strip())
            dialog.open = False
            dialog.update()
            self.update_project_panel()
        
        dialog = ft.AlertDialog(
            title=ft.Text("添加任务"),
            content=ft.Column([title_field, note_field], width=370, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("添加", on_click=add_task),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def show_add_note_dialog(self, e):
        """添加备忘录"""
        title_field = ft.TextField(label="备忘录标题", width=350)
        content_field = ft.TextField(label="内容", width=350, multiline=True, max_lines=5)
        
        def add_note(e):
            title = title_field.value.strip()
            if not title:
                title_field.error_text = "请输入标题"
                dialog.update()
                return
            
            self.db.create_note(self.current_module_id, title, content_field.value.strip())
            dialog.open = False
            dialog.update()
            self.update_project_panel()
        
        dialog = ft.AlertDialog(
            title=ft.Text("添加备忘录"),
            content=ft.Column([title_field, content_field], width=370, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("添加", on_click=add_note),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def show_edit_note_dialog(self, e):
        """编辑备忘录"""
        note_id = e.control.data
        notes = self.db.get_notes(self.current_module_id) if self.current_module_id else []
        note = next((n for n in notes if n['id'] == note_id), None)
        
        if not note:
            return
        
        title_field = ft.TextField(label="备忘录标题", value=note['title'], width=350)
        content_field = ft.TextField(label="内容", value=note['content'] or "", width=350, multiline=True, max_lines=5)
        
        def update_note(e):
            title = title_field.value.strip()
            if not title:
                title_field.error_text = "请输入标题"
                dialog.update()
                return
            
            self.db.update_note(note_id, title, content_field.value.strip())
            dialog.open = False
            dialog.update()
            self.update_project_panel()
        
        dialog = ft.AlertDialog(
            title=ft.Text("编辑备忘录"),
            content=ft.Column([title_field, content_field], width=370, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("保存", on_click=update_note),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def show_task_breakdown_dialog(self, e):
        """任务拆解"""
        if not self.current_module_id:
            self.show_snackbar("请先选择模块", ft.Colors.ORANGE)
            return
        
        idea_field = ft.TextField(
            label="输入开发想法",
            multiline=True,
            max_lines=5,
            width=400,
            hint_text="描述你想要实现的功能..."
        )
        
        def breakdown_task(e):
            idea = idea_field.value.strip()
            if not idea:
                return
            
            dialog.open = False
            dialog.update()
            self.chat_input.value = f"请将以下想法拆解为任务清单:\n{idea}"
            self.chat_input.update()
            self.send_message(None)
        
        dialog = ft.AlertDialog(
            title=ft.Text("🤖 任务拆解"),
            content=ft.Column([
                ft.Text("AI 将自动拆解为可执行任务清单", size=12, color=ft.Colors.GREY_600),
                idea_field,
            ], width=420, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("拆解", on_click=breakdown_task),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()
    
    def extract_note_from_selection(self, e):
        """提取备忘"""
        if not self.current_module_id:
            self.show_snackbar("请先选择模块", ft.Colors.ORANGE)
            return
        
        chats = self.db.get_all_chat_history(self.current_module_id)
        if len(chats) < 2:
            self.show_snackbar("没有足够的对话可提取", ft.Colors.ORANGE)
            return
        
        context = ""
        for chat in reversed(chats[-10:]):
            if chat['role'] in ['user', 'assistant']:
                context += f"{chat['role']}: {chat['content']}\n"
        
        def extract_note(e):
            dialog.open = False
            dialog.update()
            self.chat_input.value = f"请从以下对话提取关键信息作为备忘:\n\n{context}"
            self.chat_input.update()
            self.send_message(None)
        
        dialog = ft.AlertDialog(
            title=ft.Text("📝 提取备忘"),
            content=ft.Column([
                ft.Text("将分析对话提取关键信息", size=12, color=ft.Colors.GREY_600),
                ft.Container(
                    content=ft.Text(context[:200] + "...", size=12, color=ft.Colors.GREY_700),
                    padding=ft.Padding.all(10),
                    bgcolor=ft.Colors.GREY_100,
                    border_radius=ft.BorderRadius.all(5),
                    width=400,
                ),
            ], width=420, spacing=10),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(dialog, 'open', False) or dialog.update()),
                ft.TextButton("提取", on_click=extract_note),
            ],
        )
        self.pg.dialog = dialog
        dialog.open = True
        self.pg.update()


# ==================== 主入口 ====================
def main(page: ft.Page):
    """应用入口"""
    page.title = "Dev-Workbench - 开发者工作台"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = ft.Colors.GREY_50
    page.window_width = 1400
    page.window_height = 900
    page.window_min_width = 1024
    page.window_min_height = 768
    
    app = DevWorkbench(page)
    page.add(app)
    app.update_all()


if __name__ == "__main__":
    ft.run(main)