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
from pynput.mouse import Controller as MouseController, Button
import colorlog


class MKShareClient:
    """客户端 - 接收服务端控制"""
    
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        # 网络配置
        self.server_host = self.config['network']['client']['server_host']
        self.server_port = self.config['network']['client']['server_port']
        
        # 鼠标控制器
        self.mouse = MouseController()
        
        # 客户端状态
        self.socket = None
        self.running = False
        self.connected = False
        
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
        
        # 启动接收线程
        recv_thread = threading.Thread(target=self._receive_messages, daemon=True)
        recv_thread.start()
        
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
    
    def _receive_messages(self):
        """接收服务端消息"""
        buffer = ""
        try:
            while self.running and self.connected:
                data = self.socket.recv(8192).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self._process_message(line.strip())
                        
        except Exception as e:
            self.logger.error(f"接收消息失败: {e}")
            self.connected = False
    
    def _process_message(self, message):
        """处理消息"""
        try:
            msg = json.loads(message)
            msg_type = msg.get('type')
            
            if msg_type == 'mouse_move':
                self._handle_mouse_move(msg)
            elif msg_type == 'mouse_click':
                self._handle_mouse_click(msg)
            elif msg_type == 'mouse_scroll':
                self._handle_mouse_scroll(msg)
            else:
                self.logger.warning(f"未知消息: {msg_type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
    
    def _handle_mouse_move(self, msg):
        """处理鼠标移动"""
        try:
            dx = msg['dx']
            dy = msg['dy']
            current_x, current_y = self.mouse.position
            new_x = current_x + dx
            new_y = current_y + dy
            self.mouse.position = (new_x, new_y)
            self.logger.debug(f"鼠标移动: dx={dx}, dy={dy}")
        except Exception as e:
            self.logger.error(f"鼠标移动失败: {e}")
    
    def _handle_mouse_click(self, msg):
        """处理鼠标点击"""
        try:
            button_name = msg['button']
            pressed = msg['pressed']
            
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
    
    def stop(self):
        """停止客户端"""
        self.logger.info("停止客户端...")
        self.running = False
        
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

