"""
Hermes Agent 客户端 - 对接本地 Hermes 服务
"""
import requests
from typing import List, Dict, Any
import json


class HermesClient:
    """Hermes Agent HTTP 客户端"""
    
    def __init__(self, base_url="http://127.0.0.1:8000/v1"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def chat_completion(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """
        调用 Hermes Chat Completion API
        
        Args:
            messages: 消息列表
            tools: 工具定义列表（可选）
        
        Returns:
            API 响应字典
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": "hermes",
            "messages": messages,
            "stream": False,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到 Hermes Agent，请确保服务在 http://127.0.0.1:8000 运行")
        except requests.exceptions.Timeout:
            raise Exception("Hermes Agent 响应超时，请检查服务状态")
        except requests.exceptions.RequestException as e:
            raise Exception(f"调用 Hermes API 失败: {str(e)}")
    
    def check_health(self) -> bool:
        """检查 Hermes 服务是否可用"""
        try:
            response = self.session.get(f"{self.base_url}/models", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def get_available_tools(self) -> List[Dict]:
        """获取 Hermes 提供的工具列表"""
        # 返回常用工具定义
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "文件路径"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "写入文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "文件路径"
                            },
                            "content": {
                                "type": "string",
                                "description": "文件内容"
                            }
                        },
                        "required": ["file_path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "执行 Shell 命令",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的 Shell 命令"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_code",
                    "description": "在代码目录中搜索内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "搜索目录"
                            },
                            "pattern": {
                                "type": "string",
                                "description": "搜索模式"
                            }
                        },
                        "required": ["directory", "pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "列出目录内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "目录路径"
                            }
                        },
                        "required": ["directory"]
                    }
                }
            }
        ]