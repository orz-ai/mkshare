"""
客户端网络模块
管理与服务器的TCP连接
"""

import socket
import threading
import time
from typing import Optional, Callable

from network.protocol import Protocol, MessageType
from utils.logger import get_logger

logger = get_logger(__name__)


class NetworkClient:
    """网络客户端"""
    
    def __init__(self):
        self.protocol = Protocol()
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.receive_thread = None
        
        self.server_host = ''
        self.server_port = 0
        
        # 回调函数
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_message_received: Optional[Callable] = None
    
    def connect(self, host: str, port: int, device_info: dict, timeout: int = 10) -> bool:
        """
        连接到服务器
        
        Args:
            host: 服务器地址
            port: 服务器端口
            device_info: 本地设备信息
            timeout: 连接超时（秒）
        
        Returns:
            是否成功连接
        """
        self.server_host = host
        self.server_port = port
        
        try:
            # 创建socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            # 连接服务器
            logger.info(f"Connecting to {host}:{port}...")
            self.socket.connect((host, port))
            self.socket.settimeout(None)  # 取消超时
            
            self.connected = True
            logger.info(f"Connected to server {host}:{port}")
            
            # 发送握手消息
            self.send_message(MessageType.MSG_HELLO, device_info)
            
            # 启动接收线程
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # 通知连接成功
            if self.on_connected:
                self.on_connected()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
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
        
        logger.info("Disconnected from server")
        
        if self.on_disconnected:
            self.on_disconnected()
    
    def reconnect(self, device_info: dict) -> bool:
        """重新连接"""
        if not self.server_host or not self.server_port:
            logger.error("Cannot reconnect: no server info")
            return False
        
        logger.info("Attempting to reconnect...")
        self.disconnect()
        time.sleep(1)
        return self.connect(self.server_host, self.server_port, device_info)
    
    def _receive_loop(self):
        """接收消息循环"""
        buffer = b''
        
        while self.running and self.connected:
            try:
                # 接收数据
                data = self.socket.recv(4096)
                if not data:
                    logger.warning("Server closed connection")
                    break
                
                buffer += data
                
                # 处理缓冲区中的完整消息
                while len(buffer) >= self.protocol.HEADER_SIZE:
                    # 获取消息长度
                    msg_len = self.protocol.get_message_length(buffer)
                    if not msg_len:
                        break
                    
                    # 检查是否有完整消息
                    if len(buffer) < msg_len:
                        break
                    
                    # 提取并解析消息
                    msg_data = buffer[:msg_len]
                    buffer = buffer[msg_len:]
                    
                    message = self.protocol.unpack_message(msg_data)
                    if message:
                        self._handle_message(message)
            
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving data: {e}")
                break
        
        # 连接断开
        self.connected = False
        self.running = False
        
        if self.on_disconnected:
            self.on_disconnected()
    
    def _handle_message(self, message: dict):
        """处理接收到的消息"""
        msg_type = message['type']
        payload = message['payload']
        
        # 处理握手响应
        if msg_type == MessageType.MSG_HELLO_ACK:
            status = payload.get('status')
            if status == 'accepted':
                logger.info("Handshake successful")
            else:
                logger.warning(f"Handshake failed: {payload.get('message')}")
        
        # 处理心跳响应
        elif msg_type == MessageType.MSG_PONG:
            pass  # 心跳响应，无需处理
        
        # 其他消息转发给上层
        elif self.on_message_received:
            self.on_message_received(message)
    
    def send_message(self, msg_type: MessageType, payload: dict) -> bool:
        """
        发送消息
        
        Args:
            msg_type: 消息类型
            payload: 消息负载
        
        Returns:
            是否成功发送
        """
        if not self.connected or not self.socket:
            logger.warning("Not connected, cannot send message")
            return False
        
        try:
            data = self.protocol.pack_message(msg_type, payload)
            self.socket.sendall(data)
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_ping(self):
        """发送心跳包"""
        self.send_message(MessageType.MSG_PING, {'timestamp': int(time.time() * 1000)})
    
    def is_connected(self) -> bool:
        """检查是否连接"""
        return self.connected
