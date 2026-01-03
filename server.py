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
import platform
from pathlib import Path
from pynput import mouse
import colorlog

# Windows API
if platform.system() == 'Windows':
    import ctypes
    import ctypes.wintypes


class MKShareServer:
    """MKShare 服务端"""
    
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # 网络配置
        self.host = self.config['network']['server']['host']
        self.port = self.config['network']['server']['port']
        
        # 屏幕信息
        from screeninfo import get_monitors
        self.monitors = get_monitors()
        if self.monitors:
            self.screen = self.monitors[0]
            self.screen_width = self.screen.width
            self.screen_height = self.screen.height
            self.edge_threshold = self.config['screen_switch']['edge_threshold']
            self.logger.info(f"屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
        # 服务器状态
        self.server_socket = None
        self.running = False
        self.clients = []
        
        # 共享模式
        self.sharing_mode = False
        self.mouse_listener = None
        self.last_mouse_pos = None
        self.clip_rect = None
        
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
            
            self.logger.info(f"服务器启动: {self.host}:{self.port}")
            
            # 接受客户端连接
            accept_thread = threading.Thread(target=self._accept_clients, daemon=True)
            accept_thread.start()
            
            # 启动鼠标监听
            self._start_mouse_listener()
            
            # 主线程等待
            try:
                while self.running:
                    threading.Event().wait(1)
            except KeyboardInterrupt:
                self.logger.info("停止信号")
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
        """处理客户端连接"""
        try:
            while self.running:
                threading.Event().wait(1)
        except Exception as e:
            self.logger.error(f"处理客户端失败: {e}")
        finally:
            self.logger.info(f"客户端断开: {address}")
            client_socket.close()
            if (client_socket, address) in self.clients:
                self.clients.remove((client_socket, address))
    
    def _start_mouse_listener(self):
        """启动鼠标监听"""
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()
        self.logger.info("鼠标监听已启动")
    
    def _on_mouse_move(self, x, y):
        """鼠标移动事件"""
        if not self.sharing_mode:
            # 检测右边缘
            if x >= self.screen_width - self.edge_threshold:
                self.logger.info("检测到右边缘，进入共享模式")
                self._enter_sharing_mode()
        else:
            # 共享模式：计算增量并广播
            if self.last_mouse_pos:
                dx = x - self.last_mouse_pos[0]
                dy = y - self.last_mouse_pos[1]
                
                if dx != 0 or dy != 0:
                    self._broadcast_message({
                        'type': 'mouse_move',
                        'dx': dx,
                        'dy': dy
                    })
            
            self.last_mouse_pos = (x, y)
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        if self.sharing_mode:
            # 检测退出
            if self.clip_rect and x <= self.clip_rect[0] + 2:
                self.logger.info("检测到退出信号")
                self._exit_sharing_mode()
                return
            
            # 广播点击事件
            button_name = button.name if hasattr(button, 'name') else str(button)
            self._broadcast_message({
                'type': 'mouse_click',
                'button': button_name,
                'pressed': pressed
            })
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """鼠标滚轮事件"""
        if self.sharing_mode:
            self._broadcast_message({
                'type': 'mouse_scroll',
                'dx': dx,
                'dy': dy
            })
    
    def _enter_sharing_mode(self):
        """进入共享模式"""
        self.sharing_mode = True
        
        if platform.system() == 'Windows':
            # 获取当前鼠标位置
            point = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            x, y = point.x, point.y
            self.last_mouse_pos = (x, y)
            
            # 限制在 100x100 像素区域
            left = x - 50
            top = y - 50
            right = x + 50
            bottom = y + 50
            
            # ClipCursor
            rect = ctypes.wintypes.RECT(left, top, right, bottom)
            ctypes.windll.user32.ClipCursor(ctypes.byref(rect))
            self.clip_rect = (left, top, right, bottom)
            
            self.logger.info(f"进入共享模式，鼠标锁定在 ({left},{top},{right},{bottom})")
        else:
            self.logger.warning("仅支持 Windows 系统")
    
    def _exit_sharing_mode(self):
        """退出共享模式"""
        self.sharing_mode = False
        self.last_mouse_pos = None
        self.clip_rect = None
        
        if platform.system() == 'Windows':
            ctypes.windll.user32.ClipCursor(None)
            self.logger.info("退出共享模式")
    
    def _broadcast_message(self, message):
        """广播消息给所有客户端"""
        if not self.clients:
            return
        
        data = json.dumps(message) + '\n'
        for client_socket, address in self.clients[:]:
            try:
                client_socket.sendall(data.encode('utf-8'))
            except Exception as e:
                self.logger.error(f"发送到 {address} 失败: {e}")
                try:
                    client_socket.close()
                except:
                    pass
                if (client_socket, address) in self.clients:
                    self.clients.remove((client_socket, address))
    
    def stop(self):
        """停止服务器"""
        self.logger.info("停止服务器...")
        self.running = False
        
        if self.sharing_mode:
            self._exit_sharing_mode()
        
        if self.mouse_listener:
            self.mouse_listener.stop()
        
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
    print("MKShare Server v1.0 - 鼠标键盘共享服务端")
    print("=" * 50)
    
    server = MKShareServer()
    server.start()


if __name__ == '__main__':
    main()

