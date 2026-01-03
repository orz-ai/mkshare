#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MKShare Client
客户端主程序 - 接收服务器输入事件并模拟执行
"""

import sys
import time
import logging
import platform

from config.settings import Settings
from core.input_simulator import InputSimulator
from core.screen_manager import ScreenManager
from network.client import NetworkClient
from network.protocol import MessageType
from utils.logger import get_logger

# 全局变量
config = None
logger = None
screen_manager = None
input_simulator = None
network_client = None
reconnect_enabled = True


def init():
    """初始化系统"""
    global config, logger, screen_manager, input_simulator, network_client
    
    # 加载配置
    config = Settings('config.yaml')
    
    # 初始化日志
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logger = get_logger('mkshare.client', log_level, config.log_file)
    
    logger.info("=" * 60)
    logger.info("MKShare Client Starting...")
    logger.info("=" * 60)
    
    # 初始化屏幕管理器
    screen_manager = ScreenManager()
    local_device = screen_manager.initialize_local_device()
    logger.info(f"Local device: {local_device.device_name}")
    logger.info(f"OS: {platform.system()} {platform.release()}")
    logger.info(f"Screens: {len(local_device.screens)}")
    for screen in local_device.screens:
        logger.info(f"  - Screen {screen.index}: {screen.width}x{screen.height} at ({screen.x}, {screen.y})")
    
    # 初始化输入模拟器
    input_simulator = InputSimulator()
    
    # 初始化网络客户端
    network_client = NetworkClient()
    network_client.on_connected = on_connected
    network_client.on_disconnected = on_disconnected
    network_client.on_message_received = on_message_received


def connect_to_server():
    """连接到服务器"""
    global config, network_client, screen_manager
    
    server_host = config.client_server_host
    server_port = config.client_server_port
    
    logger.info(f"Connecting to server {server_host}:{server_port}...")
    
    # 准备设备信息
    local_device = screen_manager.local_device
    device_info = {
        'device_id': local_device.device_id,
        'device_name': local_device.device_name,
        'os_type': local_device.os_type,
        'os_version': platform.release(),
        'screen_count': len(local_device.screens),
        'screens': [
            {
                'index': s.index,
                'width': s.width,
                'height': s.height,
                'x': s.x,
                'y': s.y,
                'is_primary': s.is_primary
            } for s in local_device.screens
        ],
        'protocol_version': '1.0',
        'features': ['mouse', 'keyboard']
    }
    
    # 连接服务器
    return network_client.connect(server_host, server_port, device_info)


def start():
    """启动客户端"""
    global reconnect_enabled
    
    # 连接服务器
    if not connect_to_server():
        logger.error("Failed to connect to server")
        
        # 如果启用自动重连
        if config.auto_reconnect:
            reconnect_enabled = True
            logger.info("Auto-reconnect enabled")
        else:
            return False
    
    logger.info("Client is running. Press Ctrl+C to stop.")
    return True


def stop():
    """停止客户端"""
    global network_client, input_simulator, reconnect_enabled
    
    logger.info("Stopping client...")
    
    reconnect_enabled = False
    
    if input_simulator:
        input_simulator.deactivate()
    
    if network_client:
        network_client.disconnect()
    
    logger.info("Client stopped")


# ===== 网络事件处理 =====

def on_connected():
    """连接成功"""
    logger.info("Successfully connected to server")


def on_disconnected():
    """连接断开"""
    global reconnect_enabled, config, network_client, screen_manager, input_simulator
    
    logger.warning("Disconnected from server")
    
    # 停用输入模拟
    if input_simulator:
        input_simulator.deactivate()
    
    # 自动重连
    if reconnect_enabled and config.auto_reconnect:
        logger.info(f"Reconnecting in {config.reconnect_interval} seconds...")
        time.sleep(config.reconnect_interval)
        
        local_device = screen_manager.local_device
        device_info = {
            'device_id': local_device.device_id,
            'device_name': local_device.device_name,
            'os_type': local_device.os_type,
            'screens': []
        }
        
        network_client.reconnect(device_info)


def on_message_received(message):
    """接收到服务器消息"""
    msg_type = message['type']
    payload = message['payload']
    
    # 处理切换命令
    if msg_type == MessageType.MSG_SWITCH_IN:
        handle_switch_in(payload)
    
    elif msg_type == MessageType.MSG_SWITCH_OUT:
        handle_switch_out(payload)
    
    # 处理鼠标事件
    elif msg_type == MessageType.MSG_MOUSE_MOVE:
        handle_mouse_move(payload)
    
    elif msg_type == MessageType.MSG_MOUSE_DOWN:
        handle_mouse_button(payload, pressed=True)
    
    elif msg_type == MessageType.MSG_MOUSE_UP:
        handle_mouse_button(payload, pressed=False)
    
    elif msg_type == MessageType.MSG_MOUSE_WHEEL:
        handle_mouse_wheel(payload)
    
    # 处理键盘事件
    elif msg_type == MessageType.MSG_KEY_DOWN:
        handle_key_press(payload)
    
    elif msg_type == MessageType.MSG_KEY_UP:
        handle_key_release(payload)


# ===== 消息处理函数 =====

def handle_switch_in(payload):
    """处理切换进入"""
    global input_simulator
    
    reason = payload.get('reason', 'unknown')
    edge = payload.get('edge', '')
    
    logger.info(f"Switched in (reason: {reason}, edge: {edge})")
    
    # 激活输入模拟
    input_simulator.activate()


def handle_switch_out(payload):
    """处理切换离开"""
    global input_simulator
    
    logger.info("Switched out")
    
    # 停用输入模拟
    input_simulator.deactivate()


def handle_mouse_move(payload):
    """处理鼠标移动"""
    global input_simulator
    
    x = payload.get('x', 0)
    y = payload.get('y', 0)
    relative = payload.get('relative', False)
    
    if relative:
        dx = payload.get('dx', 0)
        dy = payload.get('dy', 0)
        input_simulator.move_mouse_relative(dx, dy)
    else:
        input_simulator.move_mouse(x, y)


def handle_mouse_button(payload, pressed: bool):
    """处理鼠标按键"""
    global input_simulator
    
    button = payload.get('button', 1)
    
    if pressed:
        input_simulator.press_mouse_button(button)
    else:
        input_simulator.release_mouse_button(button)


def handle_mouse_wheel(payload):
    """处理鼠标滚轮"""
    global input_simulator
    
    delta_x = payload.get('delta_x', 0)
    delta_y = payload.get('delta_y', 0)
    
    input_simulator.scroll_mouse(delta_x, delta_y)


def handle_key_press(payload):
    """处理键盘按下"""
    global input_simulator
    
    key_code = payload.get('key_code', 0)
    char = payload.get('char', '')
    
    input_simulator.press_key(key_code, char)


def handle_key_release(payload):
    """处理键盘抬起"""
    global input_simulator
    
    key_code = payload.get('key_code', 0)
    char = payload.get('char', '')
    
    input_simulator.release_key(key_code, char)


def main():
    """主函数"""
    global logger
    
    try:
        # 初始化
        init()
        
        # 启动
        if not start():
            if logger:
                logger.error("Failed to start client")
            else:
                print("Failed to start client")
            sys.exit(1)
        
        # 主循环
        while True:
            time.sleep(1)
            
            # 定期发送心跳
            if network_client and network_client.is_connected():
                network_client.send_ping()
    
    except KeyboardInterrupt:
        if logger:
            logger.info("\nReceived interrupt signal")
        else:
            print("\nReceived interrupt signal")
    except Exception as e:
        if logger:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        else:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    finally:
        stop()


if __name__ == '__main__':
    main()

