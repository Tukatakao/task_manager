"""
AI 客户端 - 对接 DeepSeek（OpenAI 兼容接口）
"""
import os
from pathlib import Path

import requests
from typing import List, Dict, Any


def _find_env_path() -> Path:
    """返回 .env 文件路径（优先已存在的，否则项目根目录）。"""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[1]


def _load_dotenv():
    """加载 .env 文件（若存在），格式：KEY=VALUE 每行一个。"""
    path = _find_env_path()
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


class HermesClient:
    """AI HTTP 客户端（OpenAI 兼容）

    通过环境变量配置：
      - DEEPSEEK_API_KEY   必填，DeepSeek 的 API Key
      - DEEPSEEK_BASE_URL  可选，默认 https://api.deepseek.com/v1
      - DEEPSEEK_MODEL     可选，默认 deepseek-chat
    """

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url or os.environ.get(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
        )
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

        self.session = requests.Session()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self.session.headers.update(headers)

    def set_api_key(self, api_key: str):
        """更新内存中的 API Key 及请求头（立即生效，不落盘）。"""
        self.api_key = api_key
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        else:
            self.session.headers.pop("Authorization", None)

    def save_api_key(self, api_key: str):
        """保存 API Key 到 .env 文件并立即生效。"""
        self.set_api_key(api_key)

        env_path = _find_env_path()
        lines = (
            env_path.read_text(encoding="utf-8").splitlines()
            if env_path.exists()
            else []
        )

        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith("DEEPSEEK_API_KEY"):
                lines[i] = f"DEEPSEEK_API_KEY={api_key}"
                updated = True
                break
        if not updated:
            lines.append(f"DEEPSEEK_API_KEY={api_key}")

        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def chat_completion(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """
        调用 Chat Completion API

        Args:
            messages: 消息列表
            tools: 工具定义列表（可选）

        Returns:
            API 响应字典
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
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
            raise Exception(f"无法连接到 AI 服务 ({self.base_url})，请检查网络或代理")
        except requests.exceptions.Timeout:
            raise Exception("AI 服务响应超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            # 尝试提取服务端返回的错误信息
            detail = ""
            try:
                detail = response.json().get("error", {}).get("message", "")
            except Exception:
                detail = ""
            raise Exception(f"调用 AI API 失败: {detail or str(e)}")

    def check_health(self) -> bool:
        """检查 AI 服务是否可用"""
        if not self.api_key:
            return False
        try:
            response = self.session.get(f"{self.base_url}/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_available_tools(self) -> List[Dict]:
        """返回可用的工具定义列表"""
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
