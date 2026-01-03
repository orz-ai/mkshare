#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MKShare Client - 鼠标键盘共享客户端
"""

import socket
import json
import logging
import yaml
import sys
import time
from pathlib import Path
from pynput import mouse
from screeninfo import get_monitors
import colorlog
import platform

# Windows API
if platform.system() == 'Windows':
    import ctypes
    import ctypes.wintypes


class MKShareClient:
    """MKShare 客户端"""
    
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # 网络配置
        self.server_host = self.config['network']['client']['server_host']
        self.server_port = self.config['network']['client']['server_port']
        
        # 屏幕信息
        self.monitors = get_monitors()
        if not self.monitors:
            self.logger.error("未检测到屏幕")
            sys.exit(1)
        
        self.screen = self.monitors[0]
        self.screen_width = self.screen.width
        self.screen_height = self.screen.height
        self.edge_threshold = self.config['screen_switch']['edge_threshold']
        
        self.logger.info(f"屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
        # 客户端状态
        self.socket = None
        self.running = False
        self.connected = False
        self.sharing_mode = False
        
        # 鼠标状态
        self.mouse_listener = None
        self.last_mouse_pos = None
        self.clip_rect = None
        
        self.logger.info("MKShare Client 初始化完成")
    
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
        self.logger = logging.getLogger('MKShareClient')
        self.logger.setLevel(getattr(logging, log_level))
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def start(self):
        """启动客户端"""
        self.running = True
        self.logger.info("客户端启动")
        
        # 连接服务器
        if not self._connect_to_server():
            self.logger.error("无法连接到服务器")
            return
        
        # 启动鼠标监听
        self._start_mouse_listener()
        
        # 主线程等待
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("停止信号")
            self.stop()
    
    def _connect_to_server(self):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.logger.info(f"已连接: {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            self.connected = False
            return False
    
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
            # 共享模式：计算增量并发送
            if self.last_mouse_pos:
                dx = x - self.last_mouse_pos[0]
                dy = y - self.last_mouse_pos[1]
                
                if dx != 0 or dy != 0:
                    self._send_message({
                        'type': 'mouse_move',
                        'dx': dx,
                        'dy': dy
                    })
            
            self.last_mouse_pos = (x, y)
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        if self.sharing_mode:
            # 检测退出（在限制区域左边缘点击）
            if self.clip_rect and x <= self.clip_rect[0] + 2:
                self.logger.info("检测到退出信号")
                self._exit_sharing_mode()
                return
            
            # 发送点击事件
            button_name = button.name if hasattr(button, 'name') else str(button)
            self._send_message({
                'type': 'mouse_click',
                'button': button_name,
                'pressed': pressed
            })
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """鼠标滚轮事件"""
        if self.sharing_mode:
            self._send_message({
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
            
            self.logger.info(f"进入共享模式，鼠标限制在 ({left},{top},{right},{bottom})")
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
    
    def _send_message(self, message):
        """发送消息"""
        if not self.connected:
            return
        
        try:
            data = json.dumps(message) + '\n'
            self.socket.sendall(data.encode('utf-8'))
        except Exception as e:
            self.logger.error(f"发送失败: {e}")
            self.connected = False
    
    def stop(self):
        """停止客户端"""
        self.logger.info("停止客户端...")
        self.running = False
        
        if self.sharing_mode:
            self._exit_sharing_mode()
        
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        self.logger.info("客户端已停止")


def main():
    """主函数"""
    print("MKShare Client v1.0 - 鼠标键盘共享客户端")
    print("=" * 50)
    
    client = MKShareClient()
    client.start()


if __name__ == '__main__':
    main()

