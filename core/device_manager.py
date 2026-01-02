"""
设备管理模块
管理已连接的客户端设备,包括位置关系和状态
"""
import threading
import time
from enum import Enum
from utils.logger import setup_logger

logger = setup_logger('DeviceManager')


class Position(Enum):
    """设备位置枚举（相对于服务端的位置）"""
    LEFT = 'left'
    RIGHT = 'right'
    TOP = 'top'
    BOTTOM = 'bottom'


class Device:
    """设备信息类"""
    
    def __init__(self, device_id, addr, screen_width, screen_height):
        self.device_id = device_id
        self.ip = addr[0]
        self.port = addr[1]
        self.addr = addr
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.position = None  # 相对于服务端的位置
        self.last_heartbeat = time.time()
        self.is_online = True
        self.is_active = False  # 是否正在被控制
    
    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = time.time()
        self.is_online = True
    
    def check_online(self, timeout=10):
        """检查设备是否在线"""
        if time.time() - self.last_heartbeat > timeout:
            self.is_online = False
        return self.is_online
    
    def __repr__(self):
        return f"Device({self.device_id}, {self.ip}:{self.port}, {self.position}, online={self.is_online})"


class DeviceManager:
    def __init__(self):
        self._devices = {}  # device_id -> Device
        self._position_map = {}  # Position -> device_id
        self._lock = threading.RLock()
        self._current_device = None  # 当前正在控制的设备
    
    def add_device(self, device):
        """
        添加设备
        :param device: Device对象
        """
        with self._lock:
            self._devices[device.device_id] = device
            logger.info(f"添加设备: {device}")
    
    def remove_device(self, device_id):
        """
        移除设备
        :param device_id: 设备ID
        """
        with self._lock:
            if device_id in self._devices:
                device = self._devices.pop(device_id)
                # 从位置映射中移除
                if device.position and device.position in self._position_map:
                    if self._position_map[device.position] == device_id:
                        del self._position_map[device.position]
                
                # 如果是当前设备，清除
                if self._current_device and self._current_device.device_id == device_id:
                    self._current_device = None
                
                logger.info(f"移除设备: {device}")
    
    def get_device(self, device_id):
        """获取设备"""
        with self._lock:
            return self._devices.get(device_id)
    
    def get_all_devices(self):
        """获取所有设备列表"""
        with self._lock:
            return list(self._devices.values())
    
    def set_device_position(self, device_id, position):
        """
        设置设备位置
        :param device_id: 设备ID
        :param position: Position枚举
        """
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                logger.warning(f"设备 {device_id} 不存在")
                return False
            
            # 检查该位置是否已被占用
            if position in self._position_map:
                old_device_id = self._position_map[position]
                if old_device_id != device_id:
                    logger.warning(f"位置 {position.value} 已被设备 {old_device_id} 占用")
                    return False
            
            # 清除旧位置映射
            if device.position and device.position in self._position_map:
                del self._position_map[device.position]
            
            # 设置新位置
            device.position = position
            self._position_map[position] = device_id
            logger.info(f"设置设备 {device_id} 位置为 {position.value}")
            return True
    
    def get_device_by_position(self, position):
        """
        :param position: Position枚举或字符串
        """
        with self._lock:
            # 如果是字符串,转换为枚举
            if isinstance(position, str):
                try:
                    position = Position(position)
                except ValueError:
                    logger.warning(f"无效的位置: {position}")
                    return None
            
            device_id = self._position_map.get(position)
            if device_id:
                device = self._devices.get(device_id)
                if device and device.is_online:
                    return device
            return None
    
    def set_current_device(self, device):
        """设置当前正在控制的设备"""
        with self._lock:
            # 清除之前设备的active状态
            if self._current_device:
                self._current_device.is_active = False
            
            self._current_device = device
            if device:
                device.is_active = True
                logger.info(f"切换到设备: {device.device_id}")
            else:
                logger.info("切换回本地控制")
    
    def get_current_device(self):
        """获取当前正在控制的设备"""
        with self._lock:
            return self._current_device
    
    def update_heartbeat(self, device_id):
        """更新设备心跳"""
        with self._lock:
            device = self._devices.get(device_id)
            if device:
                device.update_heartbeat()
    
    def check_online_devices(self, timeout=10):
        """
        检查所有设备的在线状态
        :param timeout: 超时时间（秒）
        :return: 离线的设备ID列表
        """
        offline_devices = []
        with self._lock:
            for device_id, device in list(self._devices.items()):
                if not device.check_online(timeout):
                    offline_devices.append(device_id)
                    logger.warning(f"设备 {device_id} 离线")
        
        return offline_devices
    
    def get_device_count(self):
        """获取设备数量"""
        with self._lock:
            return len(self._devices)
