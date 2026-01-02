"""
通信协议模块
简化的协议设计,专注于功能实现
"""
import struct
import json
import time

# 消息类型定义
MSG_REGISTER = 0x01        # 设备注册
MSG_REGISTER_ACK = 0x02    # 注册响应
MSG_HEARTBEAT = 0x03       # 心跳包
MSG_HEARTBEAT_ACK = 0x04   # 心跳响应
MSG_DISCONNECT = 0x05      # 断开连接

MSG_MOUSE_MOVE = 0x10      # 鼠标移动（相对移动）
MSG_MOUSE_CLICK = 0x11     # 鼠标点击
MSG_MOUSE_SCROLL = 0x12    # 鼠标滚轮
MSG_MOUSE_ENTER = 0x13     # 鼠标进入（绝对位置）
MSG_MOUSE_LEAVE = 0x14     # 鼠标离开

MSG_KEY_PRESS = 0x20       # 键盘按下
MSG_KEY_RELEASE = 0x21     # 键盘释放

MSG_SWITCH_IN = 0x30       # 切换到此设备
MSG_SWITCH_OUT = 0x31      # 切换离开此设备

# 简化的包头大小: magic(2) + version(1) + type(1) + length(4) = 8
HEADER_SIZE = 8


class Protocol:
    """协议处理类 - 简化版本,去掉不必要的复杂性"""
    
    MAGIC = 0x4D4B  # 'MK'
    VERSION = 0x01
    
    @staticmethod
    def build_packet(msg_type, payload=None):
        """
        构建数据包
        :param msg_type: 消息类型
        :param payload: 消息体（dict）
        :return: 完整的数据包（bytes）
        """
        # 处理payload
        if payload is None:
            payload_bytes = b''
        elif isinstance(payload, dict):
            payload_bytes = json.dumps(payload).encode('utf-8')
        elif isinstance(payload, bytes):
            payload_bytes = payload
        else:
            payload_bytes = str(payload).encode('utf-8')
        
        # 构建包头: magic(2) + version(1) + type(1) + length(4)
        header = struct.pack(
            '!HBBxI',
            Protocol.MAGIC,           # magic (2 bytes)
            Protocol.VERSION,         # version (1 byte)
            msg_type,                 # type (1 byte)
            len(payload_bytes)        # length (4 bytes), x是1字节padding
        )
        
        return header + payload_bytes
    
    @staticmethod
    def parse_header(data):
        """
        解析包头
        :param data: 包头数据（至少8字节）
        :return: header dict 或 None
        """
        if len(data) < HEADER_SIZE:
            return None
        
        try:
            magic, version, msg_type, padding, length = struct.unpack('!HBBxI', data[:HEADER_SIZE])
            
            if magic != Protocol.MAGIC:
                return None
            
            return {
                'version': version,
                'type': msg_type,
                'length': length
            }
        except struct.error:
            return None
    
    @staticmethod
    def parse_payload(data, length):
        """
        解析payload
        :param data: payload数据
        :param length: payload长度
        :return: 解析后的数据
        """
        if length == 0:
            return {}
        
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return data
    
    @staticmethod
    def get_packet_size(header):
        """获取完整数据包大小"""
        return HEADER_SIZE + header['length']


# 消息构建辅助函数
def build_register_message(device_id, screen_width, screen_height):
    """构建设备注册消息"""
    return Protocol.build_packet(MSG_REGISTER, {
        'device_id': device_id,
        'screen_width': screen_width,
        'screen_height': screen_height
    })


def build_register_ack_message(success, message=''):
    """构建注册响应"""
    return Protocol.build_packet(MSG_REGISTER_ACK, {
        'success': success,
        'message': message
    })


def build_heartbeat_message():
    """构建心跳消息"""
    return Protocol.build_packet(MSG_HEARTBEAT)


def build_mouse_move_message(dx, dy):
    """构建鼠标移动消息（相对移动）"""
    return Protocol.build_packet(MSG_MOUSE_MOVE, {'dx': dx, 'dy': dy})


def build_mouse_enter_message(x, y, edge):
    """构建鼠标进入消息（绝对位置）"""
    return Protocol.build_packet(MSG_MOUSE_ENTER, {'x': x, 'y': y, 'edge': edge})


def build_mouse_leave_message(x, y):
    """构建鼠标离开消息"""
    return Protocol.build_packet(MSG_MOUSE_LEAVE, {'x': x, 'y': y})


def build_mouse_click_message(button, pressed):
    """构建鼠标点击消息"""
    return Protocol.build_packet(MSG_MOUSE_CLICK, {
        'button': button,
        'pressed': pressed
    })


def build_mouse_scroll_message(dx, dy):
    """构建鼠标滚轮消息"""
    return Protocol.build_packet(MSG_MOUSE_SCROLL, {'dx': dx, 'dy': dy})


def build_key_message(key_code, pressed):
    """构建键盘消息"""
    msg_type = MSG_KEY_PRESS if pressed else MSG_KEY_RELEASE
    return Protocol.build_packet(msg_type, {'key': key_code})


def build_switch_in_message():
    """构建切换进入消息"""
    return Protocol.build_packet(MSG_SWITCH_IN)


def build_switch_out_message():
    """构建切换离开消息"""
    return Protocol.build_packet(MSG_SWITCH_OUT)
