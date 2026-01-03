"""
验证工具模块
提供各种数据验证功能
"""

import re
import socket


def validate_ip_address(ip):
    """
    验证IP地址格式
    
    Args:
        ip: IP地址字符串
    
    Returns:
        bool: 是否为有效IP地址
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def validate_port(port):
    """
    验证端口号
    
    Args:
        port: 端口号
    
    Returns:
        bool: 是否为有效端口号
    """
    try:
        port = int(port)
        return 1 <= port <= 65535
    except (ValueError, TypeError):
        return False


def validate_device_name(name):
    """
    验证设备名称
    
    Args:
        name: 设备名称
    
    Returns:
        bool: 是否为有效设备名称
    """
    if not name or not isinstance(name, str):
        return False
    
    # 允许字母、数字、下划线、短横线，长度1-32
    pattern = r'^[a-zA-Z0-9_-]{1,32}$'
    return bool(re.match(pattern, name))


def validate_position(position):
    """
    验证设备位置
    
    Args:
        position: 位置字符串
    
    Returns:
        bool: 是否为有效位置
    """
    valid_positions = ['left', 'right', 'top', 'bottom', 'center']
    return position in valid_positions


def validate_screen_resolution(width, height):
    """
    验证屏幕分辨率
    
    Args:
        width: 宽度
        height: 高度
    
    Returns:
        bool: 是否为有效分辨率
    """
    try:
        w = int(width)
        h = int(height)
        return 100 <= w <= 10000 and 100 <= h <= 10000
    except (ValueError, TypeError):
        return False


def validate_sensitivity(sensitivity):
    """
    验证灵敏度设置
    
    Args:
        sensitivity: 灵敏度值
    
    Returns:
        bool: 是否为有效灵敏度
    """
    try:
        s = float(sensitivity)
        return 0.1 <= s <= 5.0
    except (ValueError, TypeError):
        return False


def validate_edge_threshold(threshold):
    """
    验证边缘阈值
    
    Args:
        threshold: 边缘阈值（像素）
    
    Returns:
        bool: 是否为有效阈值
    """
    try:
        t = int(threshold)
        return 1 <= t <= 50
    except (ValueError, TypeError):
        return False


def validate_delay(delay):
    """
    验证延迟时间
    
    Args:
        delay: 延迟时间（秒）
    
    Returns:
        bool: 是否为有效延迟
    """
    try:
        d = float(delay)
        return 0.0 <= d <= 5.0
    except (ValueError, TypeError):
        return False
