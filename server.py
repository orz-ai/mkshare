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
last_mouse_pos = None  # 记录上次鼠标位置，用于计算相对移动


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
    global active_client_id, screen_manager, network_server, last_mouse_pos
    
    # 如果没有活动客户端，检查边缘触发
    if not active_client_id:
        should_switch, target_device, edge = screen_manager.check_edge_trigger(x, y)
        
        if should_switch and target_device:
            logger.info(f"Switching to device: {target_device.device_name} (edge: {edge})")
            
            # 计算客户端的初始坐标（根据边缘位置）
            target_x, target_y = convert_coordinates_on_switch(x, y, edge, screen_manager.local_device, target_device)
            
            # 发送切换消息
            switch_msg = create_switch_message(
                MessageType.MSG_SWITCH_IN,
                reason='edge',
                edge=edge,
                cursor_pos={'x': target_x, 'y': target_y}
            )
            network_server.send_to_client(target_device.device_id, switch_msg['type'], switch_msg['payload'])
            
            # 设置活动客户端
            active_client_id = target_device.device_id
            network_server.set_active_client(active_client_id)
            
            # 抑制本地输入
            input_capture.suppress(True)
            
            # 立即发送初始位置（绝对坐标）
            msg = create_mouse_move_message(target_x, target_y, relative=False)
            network_server.send_to_client(active_client_id, msg['type'], msg['payload'])
            
            # 记录当前位置
            last_mouse_pos = (x, y)
            return
    
    # 如果有活动客户端，使用相对移动
    if active_client_id:
        if last_mouse_pos:
            dx = x - last_mouse_pos[0]
            dy = y - last_mouse_pos[1]
            
            # 发送相对移动
            msg = create_mouse_move_message(0, 0, relative=True, dx=dx, dy=dy)
            network_server.send_to_client(active_client_id, msg['type'], msg['payload'])
        else:
            # 没有上次位置，发送绝对坐标
            msg = create_mouse_move_message(x, y, relative=False)
            network_server.send_to_client(active_client_id, msg['type'], msg['payload'])
        
        # 更新上次位置
        last_mouse_pos = (x, y)


def convert_coordinates_on_switch(x, y, edge, local_device, remote_device):
    """
    切换时转换坐标
    
    Args:
        x, y: 本地坐标
        edge: 切换边缘 (left/right/top/bottom)
        local_device: 本地设备
        remote_device: 远程设备
    
    Returns:
        (target_x, target_y): 目标设备上的坐标
    """
    # 获取本地主屏幕
    local_screen = local_device.screens[0] if local_device.screens else None
    if not local_screen:
        return (0, 0)
    
    # 简化处理：假设远程设备也只有一个屏幕，尺寸从客户端信息获取
    # 目前remote_device.screens为空，先用默认值
    remote_width = 1920  # TODO: 从客户端注册信息获取
    remote_height = 1080
    
    if edge == 'right':
        # 从右边缘切换，鼠标应出现在客户端左边缘
        target_x = 0
        target_y = int(y * remote_height / local_screen.height)  # 按比例缩放Y坐标
    elif edge == 'left':
        # 从左边缘切换，鼠标应出现在客户端右边缘
        target_x = remote_width - 1
        target_y = int(y * remote_height / local_screen.height)
    elif edge == 'bottom':
        # 从下边缘切换，鼠标应出现在客户端上边缘
        target_x = int(x * remote_width / local_screen.width)
        target_y = 0
    elif edge == 'top':
        # 从上边缘切换，鼠标应出现在客户端下边缘
        target_x = int(x * remote_width / local_screen.width)
        target_y = remote_height - 1
    else:
        target_x, target_y = 0, 0
    
    logger.debug(f"Coordinate conversion: ({x}, {y}) on {edge} -> ({target_x}, {target_y})")
    return (target_x, target_y)


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
    global active_client_id, input_capture, last_mouse_pos
    
    if client.device_info:
        device_id = client.device_info.get('device_id')
        device_name = client.device_info.get('device_name', 'Unknown')
        logger.info(f"Client disconnected: {device_name}")
        
        # 如果是活动客户端断开，恢复本地输入
        if device_id == active_client_id:
            active_client_id = None
            last_mouse_pos = None
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

