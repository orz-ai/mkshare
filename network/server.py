"""
网络服务端模块
"""
import socket
import threading
import queue
import struct
import time
from network.protocol import (
    Protocol, HEADER_SIZE,
    MSG_HELLO, MSG_HELLO_ACK, MSG_PING, MSG_PONG, MSG_DISCONNECT,
    MSG_MOUSE_MOVE, MSG_MOUSE_DOWN, MSG_MOUSE_UP,
    MSG_KEY_DOWN, MSG_KEY_UP,
    MSG_SWITCH_IN, MSG_SWITCH_OUT
)
from utils.logger import setup_logger

logger = setup_logger('NetworkServer')


class NetworkServer:
    """网络服务器类"""
    
    def __init__(self, host='0.0.0.0', port=41234):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_connection = None
        self.client_address = None
        self.running = False
        self.callbacks = {
            'client_connected': [],
            'client_disconnected': [],
            'message_received': []
        }
    
    def start(self):
        """启动服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.running = True
            
            logger.info(f"服务器启动成功: {self.host}:{self.port}")
            
            # 启动接受连接线程
            accept_thread = threading.Thread(target=self._accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            return False
    
    def stop(self):
        """停止服务器"""
        self.running = False
        
        if self.client_connection:
            try:
                self.client_connection.close()
            except:
                pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info("服务器已停止")
    
    def send_message(self, msg_type, payload=None):
        """发送消息到客户端"""
        if not self.client_connection:
            return False
        
        try:
            packet = Protocol.build_packet(msg_type, payload)
            self.client_connection.sendall(packet)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
    
    def register_callback(self, event_type, callback):
        """注册回调函数"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def _accept_connections(self):
        """接受客户端连接"""
        while self.running:
            try:
                logger.info("等待客户端连接...")
                client_socket, address = self.server_socket.accept()
                logger.info(f"客户端已连接: {address}")
                
                self.client_connection = client_socket
                self.client_address = address
                
                # 通知连接建立
                self._notify_callbacks('client_connected', address)
                
                # 启动接收线程
                recv_thread = threading.Thread(target=self._receive_loop)
                recv_thread.daemon = True
                recv_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"接受连接错误: {e}")
                break
    
    def _receive_loop(self):
        """接收数据循环"""
        buffer = bytearray()
        
        while self.running and self.client_connection:
            try:
                data = self.client_connection.recv(4096)
                if not data:
                    logger.warning("客户端断开连接")
                    break
                
                buffer.extend(data)
                
                # 解析数据包
                while len(buffer) >= HEADER_SIZE:
                    header = Protocol.parse_header(buffer[:HEADER_SIZE])
                    if not header:
                        logger.warning("无效的数据包头")
                        buffer = buffer[1:]  # 跳过一个字节
                        continue
                    
                    total_size = HEADER_SIZE - 4 + header['length'] + 4
                    if len(buffer) < total_size:
                        break
                    
                    packet = buffer[:total_size]
                    buffer = buffer[total_size:]
                    
                    if not Protocol.verify_checksum(packet):
                        logger.warning("校验和验证失败")
                        continue
                    
                    message = Protocol.parse_message(packet, header)
                    self._handle_message(message)
                
            except Exception as e:
                logger.error(f"接收数据错误: {e}")
                break
        
        # 清理连接
        if self.client_connection:
            try:
                self.client_connection.close()
            except:
                pass
            self.client_connection = None
            self._notify_callbacks('client_disconnected')
    
    def _handle_message(self, message):
        """处理接收到的消息"""
        msg_type = message['type']
        
        if msg_type == MSG_HELLO:
            self._handle_hello(message)
        elif msg_type == MSG_PING:
            self._handle_ping()
        else:
            self._notify_callbacks('message_received', message)
    
    def _handle_hello(self, message):
        """处理握手消息"""
        logger.info(f"收到握手消息: {message['payload']}")
        
        # 发送握手响应
        response = {
            'status': 'accepted',
            'server_name': socket.gethostname(),
            'message': 'Connection established'
        }
        self.send_message(MSG_HELLO_ACK, response)
    
    def _handle_ping(self):
        """处理心跳"""
        self.send_message(MSG_PONG)
    
    def _notify_callbacks(self, event_type, *args):
        """通知回调函数"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"回调函数执行错误: {e}")
