#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MKShare Server
服务端主程序 - 捕获本地输入并发送到客户端
"""

import sys
import time
import logging

from config.settings import Settings
from core.input_capture import InputCapture
from core.screen_manager import ScreenManager, Device
from network.server import NetworkServer
from network.protocol import (
    MessageType, create_mouse_move_message, create_mouse_button_message,
    create_mouse_wheel_message, create_key_message, create_switch_message
)
from utils.logger import get_logger

# 全局变量
config = None
logger = None
screen_manager = None
input_capture = None
network_server = None
active_client_id = None


def init():
    """初始化系统"""
    global config, logger, screen_manager, input_capture, network_server
    
    # 加载配置
    config = Settings('config.yaml')
    
    # 初始化日志
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logger = get_logger('mkshare.server', log_level, config.log_file)
    
    logger.info("=" * 60)
    logger.info("MKShare Server Starting...")
    logger.info("=" * 60)
    
    # 初始化屏幕管理器
    screen_manager = ScreenManager(
        edge_threshold=config.edge_threshold,
        edge_delay=config.edge_delay
    )
    local_device = screen_manager.initialize_local_device(port=config.server_port)
    logger.info(f"Local device: {local_device.device_name}")
    logger.info(f"Screens: {len(local_device.screens)}")
    for screen in local_device.screens:
        logger.info(f"  - Screen {screen.index}: {screen.width}x{screen.height} at ({screen.x}, {screen.y})")
    
    # 初始化输入捕获
    input_capture = InputCapture()
    input_capture.set_callbacks(
        on_mouse_move=on_mouse_move,
        on_mouse_click=on_mouse_click,
        on_mouse_scroll=on_mouse_scroll,
        on_key_press=on_key_press,
        on_key_release=on_key_release
    )
    
    # 初始化网络服务器
    network_server = NetworkServer(
        host=config.server_host,
        port=config.server_port
    )
    network_server.on_client_connected = on_client_connected
    network_server.on_client_disconnected = on_client_disconnected
    network_server.on_message_received = on_message_received


def start():
    """启动服务器"""
    global network_server, input_capture
    
    # 启动网络服务器
    if not network_server.start():
        logger.error("Failed to start network server")
        return False
    
    # 启动输入捕获
    input_capture.start()
    
    logger.info("Server is running. Press Ctrl+C to stop.")
    return True


def stop():
    """停止服务器"""
    global network_server, input_capture
    
    logger.info("Stopping server...")
    
    if input_capture:
        input_capture.stop()
    
    if network_server:
        network_server.stop()
    
    logger.info("Server stopped")


# ===== 输入事件处理 =====

def on_mouse_move(x, y):
    """鼠标移动事件"""
    global active_client_id, screen_manager, network_server
    
    # 检查边缘触发
    should_switch, target_device, edge = screen_manager.check_edge_trigger(x, y)
    
    if should_switch and target_device:
        logger.info(f"Switching to device: {target_device.device_name} (edge: {edge})")
        
        # 发送切换消息
        switch_msg = create_switch_message(
            MessageType.MSG_SWITCH_IN,
            reason='edge',
            edge=edge,
            cursor_pos={'x': x, 'y': y}
        )
        network_server.send_to_client(target_device.device_id, switch_msg['type'], switch_msg['payload'])
        
        # 设置活动客户端
        active_client_id = target_device.device_id
        network_server.set_active_client(active_client_id)
        
        # 抑制本地输入
        input_capture.suppress(True)
        return
    
    # 如果有活动客户端，发送鼠标移动事件
    if active_client_id:
        msg = create_mouse_move_message(x, y)
        network_server.send_to_client(active_client_id, msg['type'], msg['payload'])


def on_mouse_click(x, y, button, pressed):
    """鼠标点击事件"""
    global active_client_id, network_server
    
    if active_client_id:
        msg_type = MessageType.MSG_MOUSE_DOWN if pressed else MessageType.MSG_MOUSE_UP
        msg = create_mouse_button_message(msg_type, button, x, y)
        network_server.send_to_client(active_client_id, msg['type'], msg['payload'])


def on_mouse_scroll(x, y, dx, dy):
    """鼠标滚轮事件"""
    global active_client_id, network_server
    
    if active_client_id:
        msg = create_mouse_wheel_message(dx, dy, x, y)
        network_server.send_to_client(active_client_id, msg['type'], msg['payload'])


def on_key_press(key):
    """键盘按下事件"""
    global active_client_id, network_server, input_capture
    
    if active_client_id:
        key_code, char, is_special = InputCapture.get_key_info(key)
        msg = create_key_message(MessageType.MSG_KEY_DOWN, key_code, char)
        network_server.send_to_client(active_client_id, msg['type'], msg['payload'])


def on_key_release(key):
    """键盘抬起事件"""
    global active_client_id, network_server, input_capture
    
    if active_client_id:
        key_code, char, is_special = InputCapture.get_key_info(key)
        msg = create_key_message(MessageType.MSG_KEY_UP, key_code, char)
        network_server.send_to_client(active_client_id, msg['type'], msg['payload'])


# ===== 网络事件处理 =====

def on_client_connected(client, device_info):
    """客户端连接"""
    global screen_manager
    
    device_name = device_info.get('device_name', 'Unknown')
    device_id = device_info.get('device_id')
    
    logger.info(f"Client connected: {device_name}")
    
    # 创建远程设备对象
    remote_device = Device(
        device_id=device_id,
        device_name=device_name,
        os_type=device_info.get('os_type', 'unknown'),
        ip_address=client.addr[0],
        port=client.addr[1],
        screens=[],  # TODO: 解析屏幕信息
        position='right',  # TODO: 从配置获取
        is_connected=True,
        last_active=time.time()
    )
    
    screen_manager.add_remote_device(remote_device)


def on_client_disconnected(client):
    """客户端断开"""
    global active_client_id, input_capture
    
    if client.device_info:
        device_id = client.device_info.get('device_id')
        device_name = client.device_info.get('device_name', 'Unknown')
        logger.info(f"Client disconnected: {device_name}")
        
        # 如果是活动客户端断开，恢复本地输入
        if device_id == active_client_id:
            active_client_id = None
            input_capture.suppress(False)


def on_message_received(client, message):
    """接收到客户端消息"""
    msg_type = message['type']
    payload = message['payload']
    
    # 处理客户端发来的消息（目前主要是状态报告）
    logger.debug(f"Received message from client: {msg_type}")


def main():
    """主函数"""
    try:
        # 初始化
        init()
        
        # 启动
        if not start():
            sys.exit(1)
        
        # 主循环
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        stop()


if __name__ == '__main__':
    main()

