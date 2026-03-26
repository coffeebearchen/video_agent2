# -*- coding: utf-8 -*-
"""
input_handler.py

【输入处理模块】

作用：
1. 统一处理多种输入源（URL、文本）
2. 生成标准化输入结构
3. 提供验证和元信息

输出格式：
{
  "type": "url" | "text",
  "content": "...",
  "meta": {
    "source": "cli" | "file" | "api",
    "timestamp": "2026-03-20T12:34:56",
    "checksum": "..."
  }
}

时间戳格式：ISO 8601 (YYYY-MM-DDTHH:MM:SS)
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import re


class InputValidator:
    """输入验证器"""
    
    @staticmethod
    def is_valid_url(text: str) -> bool:
        """检查是否为有效URL"""
        url_pattern = r'^https?://[^\s]+'
        return bool(re.match(url_pattern, text.strip()))
    
    @staticmethod
    def is_valid_text(text: str) -> bool:
        """检查是否为有效文本脚本"""
        text = text.strip()
        # 最少需要10个字符
        return len(text) >= 10
    
    @staticmethod
    def calculate_checksum(content: str) -> str:
        """计算内容校验和"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
    
    @staticmethod
    def validate_input_structure(data: dict) -> bool:
        """
        验证输入结构的完整性
        
        要求：
        - 必须有 type 字段
        - 必须有 content 字段
        - 必须有 meta 字段（字典）
        """
        if not isinstance(data, dict):
            return False
        
        required_fields = ['type', 'content', 'meta']
        if not all(field in data for field in required_fields):
            return False
        
        if data['type'] not in ['url', 'text']:
            return False
        
        if not isinstance(data['meta'], dict):
            return False
        
        return True


class InputHandler:
    """输入处理器 - 核心类"""
    
    def __init__(self):
        self.validator = InputValidator()
    
    def detect_input_type(self, content: str) -> str:
        """
        自动检测输入类型
        
        返回：
        - "url": 网页链接
        - "text": 文本脚本
        - "unknown": 无法识别
        """
        content = content.strip()
        
        if self.validator.is_valid_url(content):
            return "url"
        elif self.validator.is_valid_text(content):
            return "text"
        else:
            return "unknown"
    
    def parse_url(self, url: str, source: str = "cli") -> Dict[str, Any]:
        """
        解析并验证 URL 输入
        
        参数：
            url: 网页链接
            source: 输入来源 ("cli", "file", "api" 等)，默认 "cli"
        
        返回：
            标准化的输入结构
        
        异常：
            ValueError: 无效的 URL
        """
        url = url.strip()
        
        if not self.validator.is_valid_url(url):
            raise ValueError(f"❌ 无效的 URL：{url}")
        
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError(f"❌ URL 格式错误：缺少域名")
        except Exception as e:
            raise ValueError(f"❌ URL 解析失败：{str(e)}")
        
        return {
            "type": "url",
            "content": url,
            "meta": {
                "source": source,
                "timestamp": self._get_timestamp(),
                "checksum": self.validator.calculate_checksum(url),
                "domain": parsed.netloc,
                "scheme": parsed.scheme
            }
        }
    
    def parse_text(self, text: str, source: str = "cli") -> Dict[str, Any]:
        """
        解析并验证文本脚本输入
        
        参数：
            text: 文本脚本内容
            source: 输入来源 ("cli", "file", "api" 等)，默认 "cli"
        
        返回：
            标准化的输入结构
        
        异常：
            ValueError: 文本无效（过短）
        """
        text = text.strip()
        
        if not self.validator.is_valid_text(text):
            raise ValueError(f"❌ 脚本太短，至少需要10个字符")
        
        return {
            "type": "text",
            "content": text,
            "meta": {
                "source": source,
                "timestamp": self._get_timestamp(),
                "checksum": self.validator.calculate_checksum(text),
                "length": len(text),
                "lines": len(text.split('\n'))
            }
        }
    
    def parse_input(self, content: str, source: str = "cli") -> Dict[str, Any]:
        """
        自动识别并解析输入
        
        参数：
            content: 用户输入内容
            source: 输入来源 ("cli", "file", "api" 等)，默认 "cli"
        
        返回：
            标准化的输入结构
        
        异常：
            ValueError: 输入无效
        """
        input_type = self.detect_input_type(content)
        
        if input_type == "url":
            return self.parse_url(content, source=source)
        elif input_type == "text":
            return self.parse_text(content, source=source)
        else:
            raise ValueError(
                "❌ 无法识别输入类型\n"
                "支持格式：\n"
                "  1. URL：https://example.com\n"
                "  2. 文本脚本：最少10个字符"
            )
    
    @staticmethod
    def _get_timestamp() -> str:
        """
        获取当前时间戳 (ISO 8601 格式)
        
        格式：YYYY-MM-DDTHH:MM:SS
        例如：2026-03-20T12:34:56
        """
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


class InputFileHandler:
    """从文件读取输入"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.handler = InputHandler()
        self.validator = InputValidator()
    
    def read_from_file(self) -> Dict[str, Any]:
        """
        从文件读取输入
        
        支持格式：
        1. JSON 文件 (.json)：需符合标准结构
           {
             "type": "url" | "text",
             "content": "...",
             "meta": {...}
           }
        
        2. 纯文本文件：单行 URL 或多行脚本
        
        返回：
            标准化的输入结构
        
        异常：
            FileNotFoundError: 文件不存在
            ValueError: JSON 结构不完整或纯文本无效
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"❌ 文件不存在：{self.file_path}")
        
        content = self.file_path.read_text(encoding='utf-8').strip()
        
        # ===== 尝试作为 JSON 读取 =====
        if self.file_path.suffix == '.json':
            try:
                data = json.loads(content)
                
                # 校验结构完整性
                if not self.validator.validate_input_structure(data):
                    raise ValueError(
                        "❌ JSON 结构不完整\n"
                        "必须包含字段：type, content, meta\n"
                        "type 必须为 'url' 或 'text'\n"
                        "meta 必须为字典"
                    )
                
                return data
                
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"❌ JSON 格式错误：{str(e)}\n"
                    f"文件：{self.file_path}"
                )
        
        # ===== 作为纯文本读取 =====
        result = self.handler.parse_input(content, source="file")
        result['meta']['file'] = str(self.file_path.absolute())
        return result


# === 命令行接口 ===

def main():
    """命令行使用示例"""
    print("\n" + "="*50)
    print("📥 输入处理模块 - Input Handler")
    print("="*50 + "\n")
    
    handler = InputHandler()
    
    print("请选择输入方式：")
    print("1. 输入 URL")
    print("2. 输入文本脚本")
    choice = input("\n请选择 (1/2)：").strip()
    
    try:
        if choice == "1":
            url = input("请输入网页 URL：").strip()
            result = handler.parse_url(url)
        elif choice == "2":
            text = input("请输入文本脚本（最少10个字符）：").strip()
            result = handler.parse_text(text)
        else:
            raise ValueError("❌ 无效的选择")
        
        # 输出结果
        print("\n✅ 输入处理成功！\n")
        print("标准化输出：")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 保存到文件
        output_path = Path("input.json")
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"\n📁 已保存到：{output_path}")
        
    except Exception as e:
        print(f"\n{e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
