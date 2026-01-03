"""
网络通信协议模块
定义消息类型、数据包格式、序列化/反序列化
"""

import json
import struct
import zlib
import time
from enum import IntEnum
from typing import Dict, Any, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


# 消息类型枚举
class MessageType(IntEnum):
    """消息类型定义"""
    # 连接管理类 (0x00 - 0x0F)
    MSG_HELLO = 0x01           # 客户端握手请求
    MSG_HELLO_ACK = 0x02       # 服务端握手响应
    MSG_PING = 0x03            # 心跳包
    MSG_PONG = 0x04            # 心跳响应
    MSG_DISCONNECT = 0x05      # 断开连接
    
    # 输入事件类 (0x10 - 0x2F)
    MSG_MOUSE_MOVE = 0x10      # 鼠标移动
    MSG_MOUSE_DOWN = 0x11      # 鼠标按下
    MSG_MOUSE_UP = 0x12        # 鼠标抬起
    MSG_MOUSE_WHEEL = 0x13     # 鼠标滚轮
    MSG_KEY_DOWN = 0x20        # 键盘按下
    MSG_KEY_UP = 0x21          # 键盘抬起
    
    # 控制命令类 (0x30 - 0x4F)
    MSG_SWITCH_IN = 0x30       # 切换到此设备（激活）
    MSG_SWITCH_OUT = 0x31      # 切换离开此设备（停用）
    MSG_LOCK_CURSOR = 0x32     # 锁定鼠标光标
    MSG_UNLOCK_CURSOR = 0x33   # 解锁鼠标光标
    
    # 剪贴板类 (0x50 - 0x5F)
    MSG_CLIPBOARD_TEXT = 0x50  # 文本剪贴板
    
    # 配置信息类 (0x60 - 0x6F)
    MSG_SCREEN_INFO = 0x60     # 屏幕信息
    MSG_DEVICE_INFO = 0x61     # 设备信息
    
    # 错误状态类 (0x70 - 0x7F)
    MSG_ERROR = 0x70           # 错误消息
    MSG_STATUS = 0x71          # 状态报告


# 标志位定义
class MessageFlag(IntEnum):
    """标志位定义"""
    FLAG_NONE = 0x00           # 无标志
    FLAG_ENCRYPTED = 0x01      # 数据已加密
    FLAG_COMPRESSED = 0x02     # 数据已压缩
    FLAG_PRIORITY = 0x04       # 高优先级
    FLAG_RELIABLE = 0x08       # 需要确认


# 修饰键位掩码
class ModifierKey(IntEnum):
    """修饰键定义"""
    MOD_SHIFT = 0x01      # Shift 键
    MOD_CTRL = 0x02       # Control 键
    MOD_ALT = 0x04        # Alt 键
    MOD_META = 0x08       # Windows/Command 键
    MOD_CAPS = 0x10       # Caps Lock
    MOD_NUM = 0x20        # Num Lock


class Protocol:
    """协议处理类"""
    
    MAGIC = 0x4D  # 'M'
    VERSION = 0x01
    HEADER_SIZE = 24  # 包头大小（字节）
    
    def __init__(self):
        self._sequence = 0
    
    def pack_message(self, msg_type: MessageType, payload: Dict[str, Any], 
                    flags: int = MessageFlag.FLAG_NONE) -> bytes:
        """
        打包消息
        
        Args:
            msg_type: 消息类型
            payload: 消息负载（字典）
            flags: 标志位
        
        Returns:
            打包后的字节数据
        """
        # 序列化payload
        payload_bytes = json.dumps(payload).encode('utf-8')
        payload_len = len(payload_bytes)
        
        # 生成序列号
        self._sequence += 1
        sequence = self._sequence
        
        # 获取时间戳（毫秒）
        timestamp = int(time.time() * 1000)
        
        # 构建包头
        # 格式: BBBBI Q (magic, version, type, flags, length, sequence, timestamp)
        header = struct.pack(
            '!BBBBIQ',
            self.MAGIC,
            self.VERSION,
            msg_type,
            flags,
            payload_len,
            sequence,
            timestamp
        )
        
        # 计算校验和（不包含校验和本身）
        checksum = zlib.crc32(header + payload_bytes)
        
        # 打包完整消息
        message = header + payload_bytes + struct.pack('!I', checksum)
        
        return message
    
    def unpack_message(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        解包消息
        
        Args:
            data: 字节数据
        
        Returns:
            解包后的消息字典，如果失败则返回 None
        """
        if len(data) < self.HEADER_SIZE + 4:  # 最小长度：header + checksum
            logger.error(f"Message too short: {len(data)} bytes")
            return None
        
        try:
            # 解析包头
            magic, version, msg_type, flags, payload_len, sequence, timestamp = struct.unpack(
                '!BBBBIQQ',
                data[:self.HEADER_SIZE]
            )
            
            # 验证魔数
            if magic != self.MAGIC:
                logger.error(f"Invalid magic number: {magic}")
                return None
            
            # 验证版本
            if version != self.VERSION:
                logger.warning(f"Protocol version mismatch: {version}")
            
            # 验证数据长度
            expected_len = self.HEADER_SIZE + payload_len + 4
            if len(data) < expected_len:
                logger.error(f"Incomplete message: expected {expected_len}, got {len(data)}")
                return None
            
            # 提取 payload 和校验和
            payload_bytes = data[self.HEADER_SIZE:self.HEADER_SIZE + payload_len]
            checksum_recv = struct.unpack('!I', data[self.HEADER_SIZE + payload_len:expected_len])[0]
            
            # 验证校验和
            checksum_calc = zlib.crc32(data[:self.HEADER_SIZE + payload_len])
            if checksum_recv != checksum_calc:
                logger.error(f"Checksum mismatch: expected {checksum_calc}, got {checksum_recv}")
                return None
            
            # 反序列化 payload
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            # 返回完整消息
            return {
                'type': MessageType(msg_type),
                'flags': flags,
                'sequence': sequence,
                'timestamp': timestamp,
                'payload': payload
            }
        
        except Exception as e:
            logger.error(f"Error unpacking message: {e}")
            return None
    
    def get_message_length(self, header_data: bytes) -> Optional[int]:
        """
        从包头获取完整消息长度
        
        Args:
            header_data: 包头数据（至少24字节）
        
        Returns:
            完整消息长度，如果失败返回 None
        """
        if len(header_data) < self.HEADER_SIZE:
            return None
        
        try:
            # 解析payload长度
            _, _, _, _, payload_len, _, _ = struct.unpack(
                '!BBBBIQQ',
                header_data[:self.HEADER_SIZE]
            )
            
            # 总长度 = 包头 + payload + 校验和
            return self.HEADER_SIZE + payload_len + 4
        
        except Exception as e:
            logger.error(f"Error getting message length: {e}")
            return None


def create_hello_message(device_info: Dict[str, Any]) -> Dict[str, Any]:
    """创建握手消息"""
    return {
        'type': MessageType.MSG_HELLO,
        'payload': device_info
    }


def create_hello_ack_message(status: str, session_info: Dict[str, Any]) -> Dict[str, Any]:
    """创建握手响应消息"""
    return {
        'type': MessageType.MSG_HELLO_ACK,
        'payload': {
            'status': status,
            **session_info
        }
    }


def create_mouse_move_message(x: int, y: int, relative: bool = False, 
                              dx: int = 0, dy: int = 0) -> Dict[str, Any]:
    """创建鼠标移动消息"""
    return {
        'type': MessageType.MSG_MOUSE_MOVE,
        'payload': {
            'x': x,
            'y': y,
            'relative': relative,
            'dx': dx,
            'dy': dy
        }
    }


def create_mouse_button_message(msg_type: MessageType, button: int, 
                                x: int, y: int, clicks: int = 1) -> Dict[str, Any]:
    """创建鼠标按键消息"""
    return {
        'type': msg_type,
        'payload': {
            'button': button,
            'x': x,
            'y': y,
            'clicks': clicks
        }
    }


def create_mouse_wheel_message(delta_x: int, delta_y: int, 
                               x: int, y: int) -> Dict[str, Any]:
    """创建鼠标滚轮消息"""
    return {
        'type': MessageType.MSG_MOUSE_WHEEL,
        'payload': {
            'delta_x': delta_x,
            'delta_y': delta_y,
            'x': x,
            'y': y
        }
    }


def create_key_message(msg_type: MessageType, key_code: int, 
                      char: str = '', modifiers: int = 0, 
                      is_repeat: bool = False) -> Dict[str, Any]:
    """创建键盘消息"""
    return {
        'type': msg_type,
        'payload': {
            'key_code': key_code,
            'char': char,
            'modifiers': modifiers,
            'is_repeat': is_repeat
        }
    }


def create_switch_message(msg_type: MessageType, reason: str = 'edge', 
                         edge: str = '', cursor_pos: Dict[str, int] = None) -> Dict[str, Any]:
    """创建切换消息"""
    return {
        'type': msg_type,
        'payload': {
            'reason': reason,
            'edge': edge,
            'cursor_pos': cursor_pos or {'x': 0, 'y': 0}
        }
    }


def create_ping_message() -> Dict[str, Any]:
    """创建心跳消息"""
    return {
        'type': MessageType.MSG_PING,
        'payload': {'timestamp': int(time.time() * 1000)}
    }


def create_pong_message() -> Dict[str, Any]:
    """创建心跳响应消息"""
    return {
        'type': MessageType.MSG_PONG,
        'payload': {'timestamp': int(time.time() * 1000)}
    }
