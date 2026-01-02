"""
通信协议模块
定义消息类型和数据包格式
"""
import struct
import json
import zlib
import time

# 消息类型定义
MSG_HELLO = 0x01           # 客户端握手请求
MSG_HELLO_ACK = 0x02       # 服务端握手响应
MSG_PING = 0x03            # 心跳包
MSG_PONG = 0x04            # 心跳响应
MSG_DISCONNECT = 0x05      # 断开连接

MSG_MOUSE_MOVE = 0x10      # 鼠标移动
MSG_MOUSE_DOWN = 0x11      # 鼠标按下
MSG_MOUSE_UP = 0x12        # 鼠标抬起
MSG_MOUSE_WHEEL = 0x13     # 鼠标滚轮

MSG_KEY_DOWN = 0x20        # 键盘按下
MSG_KEY_UP = 0x21          # 键盘抬起

MSG_SWITCH_IN = 0x30       # 切换到此设备
MSG_SWITCH_OUT = 0x31      # 切换离开此设备

# 包头大小
HEADER_SIZE = 26  # 1+1+1+1+4+4+8+4+2 (预留2字节对齐)


class Protocol:
    """协议处理类"""
    
    @staticmethod
    def build_packet(msg_type, payload=None):
        """
        构建数据包
        :param msg_type: 消息类型
        :param payload: 消息体（dict 或 bytes）
        :return: 完整的数据包（bytes）
        """
        # 处理 payload
        if payload is None:
            payload_bytes = b''
        elif isinstance(payload, dict):
            payload_bytes = json.dumps(payload).encode('utf-8')
        elif isinstance(payload, bytes):
            payload_bytes = payload
        else:
            payload_bytes = str(payload).encode('utf-8')
        
        # 构建包头
        header = struct.pack(
            '!BBBBI IQ',
            0x4D,                           # magic (1 byte)
            0x01,                           # version (1 byte)
            msg_type,                       # type (1 byte)
            0x00,                           # flag (1 byte)
            len(payload_bytes),             # length (4 bytes)
            0,                              # sequence (4 bytes)
            int(time.time() * 1000)         # timestamp (8 bytes)
        )
        
        # 计算校验和
        packet = header + payload_bytes
        checksum = zlib.crc32(packet) & 0xFFFFFFFF
        checksum_bytes = struct.pack('!I', checksum)
        
        return packet + checksum_bytes
    
    @staticmethod
    def parse_header(data):
        """
        解析包头
        :param data: 包头数据（至少 26 字节）
        :return: header dict 或 None
        """
        if len(data) < HEADER_SIZE:
            return None
        
        try:
            magic, version, msg_type, flag, length, sequence, timestamp = struct.unpack(
                '!BBBBI IQ', data[:22]
            )
            
            if magic != 0x4D:
                return None
            
            return {
                'version': version,
                'type': msg_type,
                'flag': flag,
                'length': length,
                'sequence': sequence,
                'timestamp': timestamp
            }
        except struct.error:
            return None
    
    @staticmethod
    def parse_message(packet, header):
        """
        解析完整消息
        :param packet: 完整数据包
        :param header: 已解析的包头
        :return: message dict
        """
        payload_start = HEADER_SIZE - 4  # 减去预留的2字节和校验和4字节
        payload_end = payload_start + header['length']
        payload = packet[payload_start:payload_end]
        
        # 尝试解析为 JSON
        try:
            payload_data = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload_data = payload
        
        return {
            'type': header['type'],
            'flag': header['flag'],
            'sequence': header['sequence'],
            'timestamp': header['timestamp'],
            'payload': payload_data
        }
    
    @staticmethod
    def verify_checksum(packet):
        """
        验证校验和
        :param packet: 完整数据包
        :return: bool
        """
        if len(packet) < 4:
            return False
        
        data = packet[:-4]
        checksum_received = struct.unpack('!I', packet[-4:])[0]
        checksum_calculated = zlib.crc32(data) & 0xFFFFFFFF
        
        return checksum_received == checksum_calculated
    
    @staticmethod
    def get_packet_size(header):
        """获取完整数据包大小"""
        return HEADER_SIZE + header['length']


# 消息构建辅助函数
def build_hello_message(device_info):
    """构建握手消息"""
    return Protocol.build_packet(MSG_HELLO, device_info)


def build_mouse_move_message(x, y):
    """构建鼠标移动消息"""
    return Protocol.build_packet(MSG_MOUSE_MOVE, {'x': x, 'y': y})


def build_mouse_button_message(button, pressed, x, y):
    """构建鼠标按键消息"""
    msg_type = MSG_MOUSE_DOWN if pressed else MSG_MOUSE_UP
    return Protocol.build_packet(msg_type, {
        'button': button,
        'x': x,
        'y': y
    })


def build_key_message(key_code, pressed):
    """构建键盘消息"""
    msg_type = MSG_KEY_DOWN if pressed else MSG_KEY_UP
    return Protocol.build_packet(msg_type, {'key': key_code})


def build_ping_message():
    """构建心跳消息"""
    return Protocol.build_packet(MSG_PING)


def build_pong_message():
    """构建心跳响应"""
    return Protocol.build_packet(MSG_PONG)
