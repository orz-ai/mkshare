"""
服务端网络模块
管理TCP服务器和客户端连接
"""

import socket
import threading
import time
from typing import Dict, Optional, Callable

from network.protocol import Protocol, MessageType
from utils.logger import get_logger

logger = get_logger(__name__)


class ClientConnection:
    """客户端连接"""
    
    def __init__(self, conn: socket.socket, addr: tuple, protocol: Protocol):
        self.conn = conn
        self.addr = addr
        self.protocol = protocol
        self.device_info = None
        self.is_active = False
        self.last_ping = time.time()
        self.running = False
        self.receive_thread = None
    
    def start_receiving(self, callback: Callable):
        """启动接收线程"""
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop, args=(callback,), daemon=True)
        self.receive_thread.start()
    
    def _receive_loop(self, callback: Callable):
        """接收消息循环"""
        buffer = b''
        
        while self.running:
            try:
                # 接收数据
                data = self.conn.recv(4096)
                if not data:
                    logger.info(f"Client {self.addr} disconnected")
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
                        callback(self, message)
            
            except Exception as e:
                logger.error(f"Error receiving from {self.addr}: {e}")
                break
        
        self.running = False
    
    def send_message(self, msg_type: MessageType, payload: dict) -> bool:
        """发送消息"""
        try:
            data = self.protocol.pack_message(msg_type, payload)
            self.conn.sendall(data)
            return True
        except Exception as e:
            logger.error(f"Error sending to {self.addr}: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        self.running = False
        try:
            self.conn.close()
        except:
            pass


class NetworkServer:
    """网络服务器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 41234):
        self.host = host
        self.port = port
        self.protocol = Protocol()
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[str, ClientConnection] = {}  # device_id -> ClientConnection
        self.running = False
        self.accept_thread = None
        
        # 回调函数
        self.on_client_connected: Optional[Callable] = None
        self.on_client_disconnected: Optional[Callable] = None
        self.on_message_received: Optional[Callable] = None
    
    def start(self) -> bool:
        """启动服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()
            
            logger.info(f"Server started on {self.host}:{self.port}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False
    
    def stop(self):
        """停止服务器"""
        self.running = False
        
        # 关闭所有客户端连接
        for client in list(self.clients.values()):
            client.close()
        self.clients.clear()
        
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info("Server stopped")
    
    def _accept_loop(self):
        """接受连接循环"""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                logger.info(f"New connection from {addr}")
                
                # 创建客户端连接对象
                client = ClientConnection(conn, addr, self.protocol)
                
                # 启动接收线程
                client.start_receiving(self._handle_client_message)
                
                # 临时存储（等待握手完成后添加到clients字典）
                self._pending_client = client
            
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
    
    def _handle_client_message(self, client: ClientConnection, message: dict):
        """处理客户端消息"""
        msg_type = message['type']
        payload = message['payload']
        
        # 处理握手
        if msg_type == MessageType.MSG_HELLO:
            self._handle_hello(client, payload)
        
        # 处理心跳
        elif msg_type == MessageType.MSG_PING:
            client.last_ping = time.time()
            client.send_message(MessageType.MSG_PONG, {})
        
        # 其他消息转发给上层处理
        elif self.on_message_received:
            self.on_message_received(client, message)
    
    def _handle_hello(self, client: ClientConnection, device_info: dict):
        """处理握手请求"""
        device_id = device_info.get('device_id')
        device_name = device_info.get('device_name', 'Unknown')
        
        # 保存设备信息
        client.device_info = device_info
        self.clients[device_id] = client
        
        # 发送握手响应
        response = {
            'status': 'accepted',
            'server_name': socket.gethostname(),
            'session_id': device_id,
            'message': 'Connected successfully'
        }
        client.send_message(MessageType.MSG_HELLO_ACK, response)
        
        logger.info(f"Client registered: {device_name} ({device_id})")
        
        # 通知上层
        if self.on_client_connected:
            self.on_client_connected(client, device_info)
    
    def send_to_client(self, device_id: str, msg_type: MessageType, payload: dict) -> bool:
        """发送消息到指定客户端"""
        client = self.clients.get(device_id)
        if client:
            return client.send_message(msg_type, payload)
        return False
    
    def send_to_all_clients(self, msg_type: MessageType, payload: dict):
        """广播消息到所有客户端"""
        for client in self.clients.values():
            client.send_message(msg_type, payload)
    
    def get_active_client(self) -> Optional[ClientConnection]:
        """获取当前活动的客户端"""
        for client in self.clients.values():
            if client.is_active:
                return client
        return None
    
    def set_active_client(self, device_id: str):
        """设置活动客户端"""
        for did, client in self.clients.items():
            client.is_active = (did == device_id)
