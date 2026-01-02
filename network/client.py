"""
网络客户端模块
"""
import socket
import threading
import time
from network.protocol import (
    Protocol, HEADER_SIZE,
    MSG_REGISTER, MSG_REGISTER_ACK, MSG_HEARTBEAT, MSG_HEARTBEAT_ACK,
    MSG_MOUSE_MOVE, MSG_MOUSE_CLICK, MSG_MOUSE_SCROLL, MSG_MOUSE_ENTER, MSG_MOUSE_LEAVE,
    MSG_KEY_PRESS, MSG_KEY_RELEASE,
    MSG_SWITCH_IN, MSG_SWITCH_OUT,
    build_register_message, build_heartbeat_message
)
from utils.logger import setup_logger

logger = setup_logger('NetworkClient')


class NetworkClient:
    """网络客户端类"""
    
    def __init__(self):
        self.socket = None
        self.server_address = None
        self.connected = False
        self.running = False
        self.callbacks = {
            'connected': [],
            'disconnected': [],
            'message_received': []
        }
        self.ping_interval = 5.0
        self.last_ping_time = 0
    
    def connect(self, host, port):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((host, port))
            self.server_address = (host, port)
            self.connected = True
            self.running = True
            
            logger.info(f"已连接到服务器: {host}:{port}")
            
            # 启动接收线程
            recv_thread = threading.Thread(target=self._receive_loop)
            recv_thread.daemon = True
            recv_thread.start()
            
            # 启动心跳线程
            ping_thread = threading.Thread(target=self._ping_loop)
            ping_thread.daemon = True
            ping_thread.start()
            
            # 发送握手消息
            self._send_hello()
            
            return True
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        logger.info("已断开连接")
        self._notify_callbacks('disconnected')
    
    def send_message(self, msg_type, payload=None):
        """发送消息"""
        if not self.connected or not self.socket:
            return False
        
        try:
            packet = Protocol.build_packet(msg_type, payload)
            self.socket.sendall(packet)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
    
    def register_callback(self, event_type, callback):
        """注册回调函数"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def _send_hello(self):
        """发送设备注册消息"""
        from core.screen_manager import ScreenManager
        
        screen_mgr = ScreenManager()
        device_info = screen_mgr.get_device_info()
        
        # 使用build_register_message
        packet = build_register_message(
            device_info.get('device_id', socket.gethostname()),
            device_info.get('screen_width', 1920),
            device_info.get('screen_height', 1080)
        )
        self._send_packet(packet)
        logger.info("已发送设备注册消息")
    
    def _ping_loop(self):
        """心跳循环"""
        while self.running and self.connected:
            try:
                current_time = time.time()
                if current_time - self.last_ping_time >= self.ping_interval:
                    packet = build_heartbeat_message()
                    self._send_packet(packet)
                    self.last_ping_time = current_time
                    logger.debug("发送心跳")
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"心跳错误: {e}")
    
    def _receive_loop(self):
        """接收数据循环"""
        buffer = bytearray()
        self.socket.settimeout(1.0)
        
        while self.running and self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    logger.warning("服务器断开连接")
                    break
                
                buffer.extend(data)
                
                # 解析数据包
                while len(buffer) >= HEADER_SIZE:
                    header = Protocol.parse_header(buffer[:HEADER_SIZE])
                    if not header:
                        logger.warning("无效的数据包头")
                        buffer = buffer[1:]
                        continue
                    
                    total_size = HEADER_SIZE + header['length'] + 4  # header + payload + checksum(4)
                    if len(buffer) < total_size:
                        break
                    
                    packet = buffer[:total_size]
                    buffer = buffer[total_size:]
                    
                    if not Protocol.verify_checksum(packet):
                        logger.warning("校验和验证失败")
                        continue
                    
                    message = Protocol.parse_message(packet, header)
                    self._handle_message(message)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"接收数据错误: {e}")
                break
        
        self.disconnect()
    
    def _handle_message(self, message):
        """处理接收到的消息"""
        msg_type = message['type']
        
        if msg_type == MSG_REGISTER_ACK:
            self._handle_register_ack(message)
        elif msg_type == MSG_HEARTBEAT_ACK:
            logger.debug("收到心跳响应")
        else:
            self._notify_callbacks('message_received', message)
    
    def _handle_register_ack(self, message):
        """处理注册响应"""
        logger.info(f"注册成功: {message['payload']}")
        self._notify_callbacks('connected')
    
    def _notify_callbacks(self, event_type, *args):
        """通知回调函数"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"回调函数执行错误: {e}")
