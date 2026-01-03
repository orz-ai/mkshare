#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MKShare Server - 鼠标键盘共享服务端
"""

import socket
import threading
import json
import logging
import yaml
import sys
from pathlib import Path
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController
import colorlog


class MKShareServer:
    """MKShare 服务端主类"""
    
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # 网络配置
        self.host = self.config['network']['server']['host']
        self.port = self.config['network']['server']['port']
        
        # 控制器
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        # 服务器状态
        self.server_socket = None
        self.running = False
        self.clients = []
        
        self.logger.info("MKShare Server 初始化完成")
    
    def _load_config(self, config_path):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            sys.exit(1)
    
    def _setup_logging(self):
        """设置日志"""
        log_level = self.config['logging']['level']
        log_file = self.config['logging']['file']
        
        # 创建日志目录
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # 配置彩色日志
        formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        # 配置logger
        self.logger = logging.getLogger('MKShareServer')
        self.logger.setLevel(getattr(logging, log_level))
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def start(self):
        """启动服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            self.logger.info(f"服务器启动成功，监听 {self.host}:{self.port}")
            
            # 接受客户端连接
            accept_thread = threading.Thread(target=self._accept_clients, daemon=True)
            accept_thread.start()
            
            # 主线程等待
            try:
                while self.running:
                    threading.Event().wait(1)
            except KeyboardInterrupt:
                self.logger.info("接收到停止信号")
                self.stop()
                
        except Exception as e:
            self.logger.error(f"服务器启动失败: {e}")
            sys.exit(1)
    
    def _accept_clients(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                self.logger.info(f"客户端连接: {address}")
                
                # 为每个客户端创建处理线程
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                self.clients.append((client_socket, address))
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"接受连接失败: {e}")
    
    def _handle_client(self, client_socket, address):
        """处理客户端消息"""
        buffer = ""
        try:
            while self.running:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        self._process_message(line)
                        
        except Exception as e:
            self.logger.error(f"处理客户端 {address} 消息失败: {e}")
        finally:
            self.logger.info(f"客户端断开: {address}")
            client_socket.close()
            if (client_socket, address) in self.clients:
                self.clients.remove((client_socket, address))
    
    def _process_message(self, message):
        """处理接收到的消息"""
        try:
            msg = json.loads(message)
            msg_type = msg.get('type')
            
            if msg_type == 'mouse_move':
                self._handle_mouse_move(msg)
            elif msg_type == 'mouse_move_relative':
                self._handle_mouse_move_relative(msg)
            elif msg_type == 'mouse_click':
                self._handle_mouse_click(msg)
            elif msg_type == 'mouse_scroll':
                self._handle_mouse_scroll(msg)
            elif msg_type == 'mouse_drag':
                self._handle_mouse_drag(msg)
            else:
                self.logger.warning(f"未知的消息类型: {msg_type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失败: {e}")
        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
    
    def _handle_mouse_move(self, msg):
        """处理鼠标移动（绝对位置）"""
        try:
            x = msg['x']
            y = msg['y']
            self.mouse.position = (x, y)
            self.logger.debug(f"鼠标移动到: ({x}, {y})")
        except Exception as e:
            self.logger.error(f"鼠标移动失败: {e}")
    
    def _handle_mouse_move_relative(self, msg):
        """处理鼠标移动（相对移动）"""
        try:
            dx = msg['dx']
            dy = msg['dy']
            current_x, current_y = self.mouse.position
            new_x = current_x + dx
            new_y = current_y + dy
            self.mouse.position = (new_x, new_y)
            self.logger.debug(f"鼠标相对移动: ({dx}, {dy}) -> ({new_x}, {new_y})")
        except Exception as e:
            self.logger.error(f"鼠标相对移动失败: {e}")
    
    def _handle_mouse_click(self, msg):
        """处理鼠标点击"""
        try:
            button_name = msg['button']
            pressed = msg['pressed']
            
            # 转换按钮名称
            button_map = {
                'left': Button.left,
                'right': Button.right,
                'middle': Button.middle
            }
            button = button_map.get(button_name, Button.left)
            
            if pressed:
                self.mouse.press(button)
                self.logger.debug(f"鼠标按下: {button_name}")
            else:
                self.mouse.release(button)
                self.logger.debug(f"鼠标释放: {button_name}")
                
        except Exception as e:
            self.logger.error(f"鼠标点击失败: {e}")
    
    def _handle_mouse_scroll(self, msg):
        """处理鼠标滚轮"""
        try:
            dx = msg['dx']
            dy = msg['dy']
            self.mouse.scroll(dx, dy)
            self.logger.debug(f"鼠标滚动: dx={dx}, dy={dy}")
        except Exception as e:
            self.logger.error(f"鼠标滚动失败: {e}")
    
    def _handle_mouse_drag(self, msg):
        """处理鼠标拖拽"""
        try:
            x = msg['x']
            y = msg['y']
            # 拖拽时移动鼠标即可，按钮状态已经在 mouse_click 中处理
            self.mouse.position = (x, y)
            self.logger.debug(f"鼠标拖拽到: ({x}, {y})")
        except Exception as e:
            self.logger.error(f"鼠标拖拽失败: {e}")
    
    def stop(self):
        """停止服务器"""
        self.logger.info("正在停止服务器...")
        self.running = False
        
        # 关闭所有客户端连接
        for client_socket, address in self.clients:
            try:
                client_socket.close()
            except:
                pass
        
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        self.logger.info("服务器已停止")


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════╗
║       MKShare Server v1.0            ║
║   鼠标键盘共享 - 服务端               ║
╚══════════════════════════════════════╝
    """)
    
    server = MKShareServer()
    server.start()


if __name__ == '__main__':
    main()

