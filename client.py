#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MKShare Client - 鼠标键盘共享客户端
"""

import socket
import threading
import json
import logging
import yaml
import sys
import time
from pathlib import Path
from pynput import mouse
from pynput.mouse import Controller as MouseController
from screeninfo import get_monitors
import colorlog


class MKShareClient:
    """MKShare 客户端主类"""
    
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # 网络配置
        self.server_host = self.config['network']['client']['server_host']
        self.server_port = self.config['network']['client']['server_port']
        self.auto_reconnect = self.config['network']['client']['auto_reconnect']
        self.reconnect_interval = self.config['network']['client']['reconnect_interval']
        
        # 屏幕配置
        self.edge_threshold = self.config['screen_switch']['edge_threshold']
        self.edge_delay = self.config['screen_switch']['edge_delay']
        
        # 获取屏幕信息
        self.monitors = get_monitors()
        if not self.monitors:
            self.logger.error("未检测到屏幕")
            sys.exit(1)
        
        # 假设只有一个屏幕
        self.screen = self.monitors[0]
        self.screen_width = self.screen.width
        self.screen_height = self.screen.height
        
        self.logger.info(f"屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
        # 客户端状态
        self.socket = None
        self.running = False
        self.connected = False
        self.sharing_mode = False  # 是否在共享模式
        
        # 边缘检测
        self.edge_timer = None
        self.last_edge_time = 0
        
        # 鼠标控制器和锁定
        self.mouse_controller = MouseController()
        self.mouse_listener = None
        self.lock_position = None  # 鼠标锁定位置
        self.last_mouse_pos = None  # 上次鼠标位置（用于计算增量）
        self.is_resetting_mouse = False  # 是否正在重置鼠标（避免递归）
        
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
        self._connect_to_server()
        
        # 启动鼠标监听
        self._start_mouse_listener()
        
        # 主线程等待
        try:
            while self.running:
                threading.Event().wait(1)
                
                # 自动重连
                if not self.connected and self.auto_reconnect:
                    self.logger.info("尝试重连...")
                    self._connect_to_server()
                    
        except KeyboardInterrupt:
            self.logger.info("接收到停止信号")
            self.stop()
    
    def _connect_to_server(self):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.logger.info(f"已连接到服务器 {self.server_host}:{self.server_port}")
        except Exception as e:
            self.logger.error(f"连接服务器失败: {e}")
            self.connected = False
            if self.auto_reconnect:
                time.sleep(self.reconnect_interval)
    
    def _start_mouse_listener(self):
        """启动鼠标监听"""
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()
        self.logger.info("鼠标监听器已启动")
    
    def _on_mouse_move(self, x, y):
        """鼠标移动事件"""
        # 检查是否在屏幕边缘
        if not self.sharing_mode:
            if x >= self.screen_width - self.edge_threshold:
                # 右边缘
                current_time = time.time()
                if current_time - self.last_edge_time >= self.edge_delay:
                    self.logger.info("检测到右边缘，进入共享模式")
                    self._enter_sharing_mode(x, y)
                self.last_edge_time = current_time
        else:
            # 共享模式下锁定本地鼠标
            if self.is_resetting_mouse:
                return
            
            # 计算鼠标移动增量
            if self.last_mouse_pos:
                dx = x - self.last_mouse_pos[0]
                dy = y - self.last_mouse_pos[1]
                
                # 只有真实移动才发送（过滤掉重置产生的移动）
                if abs(dx) > 0 or abs(dy) > 0:
                    # 发送相对移动而不是绝对位置
                    self._send_message({
                        'type': 'mouse_move_relative',
                        'dx': dx,
                        'dy': dy
                    })
            
            # 重置鼠标到锁定位置
            self.last_mouse_pos = (x, y)
            self.is_resetting_mouse = True
            self.mouse_controller.position = self.lock_position
            self.is_resetting_mouse = False
            self.last_mouse_pos = self.lock_position
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        if self.sharing_mode:
            # 发送鼠标点击
            button_name = button.name if hasattr(button, 'name') else str(button)
            self._send_message({
                'type': 'mouse_click',
                'x': x,
                'y': y,
                'button': button_name,
                'pressed': pressed
            })
            
            # 检测退出共享模式（可以通过特定按键或边缘检测）
            if pressed and x <= self.edge_threshold:
                self.logger.info("检测到左边缘，退出共享模式")
                self._exit_sharing_mode()
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """鼠标滚轮事件"""
        if self.sharing_mode:
            self._send_message({
                'type': 'mouse_scroll',
                'x': x,
                'y': y,
                'dx': dx,
                'dy': dy
            })
    
    def _enter_sharing_mode(self, x, y):
        """进入共享模式"""
        self.sharing_mode = True
        # 设置鼠标锁定位置（屏幕中心）
        self.lock_position = (self.screen_width // 2, self.screen_height // 2)
        self.last_mouse_pos = self.lock_position
        # 立即将鼠标移动到锁定位置
        self.is_resetting_mouse = True
        self.mouse_controller.position = self.lock_position
        self.is_resetting_mouse = False
        self.logger.info(f"进入共享模式，鼠标锁定在 {self.lock_position}")
        # 可以添加视觉提示或声音提示
    
    def _exit_sharing_mode(self):
        """退出共享模式"""
        self.sharing_mode = False
        self.lock_position = None
        self.last_mouse_pos = None
        self.logger.info("进入共享模式")
        # 可以添加视觉提示或声音提示
    
    def _exit_sharing_mode(self):
        """退出共享模式"""
        self.sharing_mode = False
        self.logger.info("退出共享模式")
        # 可以添加视觉提示或声音提示
    
    def _send_message(self, message):
        """发送消息到服务器"""
        if not self.connected or not self.socket:
            return
        
        try:
            json_msg = json.dumps(message) + '\n'
            self.socket.sendall(json_msg.encode('utf-8'))
            self.logger.debug(f"发送消息: {message['type']}")
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            self.connected = False
            try:
                self.socket.close()
            except:
                pass
    
    def stop(self):
        """停止客户端"""
        self.logger.info("正在停止客户端...")
        self.running = False
        self.sharing_mode = False
        
        # 停止鼠标监听
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        # 关闭socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        self.logger.info("客户端已停止")


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════╗
║       MKShare Client v1.0            ║
║   鼠标键盘共享 - 客户端               ║
╚══════════════════════════════════════╝
    """)
    
    client = MKShareClient()
    client.start()


if __name__ == '__main__':
    main()

