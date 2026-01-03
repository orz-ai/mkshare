"""
屏幕管理模块
管理多屏幕信息、设备布局、边缘触发检测
"""

import time
import socket
import platform
import uuid
from dataclasses import dataclass
from typing import List, Dict, Optional
from screeninfo import get_monitors

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Screen:
    """屏幕信息"""
    index: int
    x: int
    y: int
    width: int
    height: int
    is_primary: bool
    name: str = ""
    
    @property
    def bounds(self) -> Dict[str, int]:
        """获取屏幕边界"""
        return {
            'left': self.x,
            'top': self.y,
            'right': self.x + self.width,
            'bottom': self.y + self.height
        }
    
    def contains_point(self, x: int, y: int) -> bool:
        """检查点是否在屏幕内"""
        bounds = self.bounds
        return (bounds['left'] <= x < bounds['right'] and 
                bounds['top'] <= y < bounds['bottom'])
    
    def is_at_edge(self, x: int, y: int, threshold: int = 5) -> Dict[str, bool]:
        """检查点是否在屏幕边缘"""
        bounds = self.bounds
        return {
            'left': abs(x - bounds['left']) <= threshold,
            'right': abs(x - (bounds['right'] - 1)) <= threshold,
            'top': abs(y - bounds['top']) <= threshold,
            'bottom': abs(y - (bounds['bottom'] - 1)) <= threshold
        }


@dataclass
class Device:
    """设备信息"""
    device_id: str
    device_name: str
    os_type: str
    ip_address: str
    port: int
    screens: List[Screen]
    position: str = 'center'  # left/right/top/bottom/center
    is_connected: bool = False
    last_active: float = 0.0


class ScreenManager:
    """屏幕管理器"""
    
    def __init__(self, edge_threshold: int = 5, edge_delay: float = 0.3):
        """
        Args:
            edge_threshold: 边缘触发阈值（像素）
            edge_delay: 边缘停留延迟（秒）
        """
        self.local_device: Optional[Device] = None
        self.remote_devices: Dict[str, Device] = {}
        self.edge_threshold = edge_threshold
        self.edge_delay = edge_delay
        
        self._edge_timer = None
        self._last_edge = None
        
        logger.info(f"ScreenManager initialized (threshold={edge_threshold}, delay={edge_delay})")
    
    def initialize_local_device(self, port: int = 0):
        """初始化本地设备信息"""
        screens = self._detect_screens()
        self.local_device = Device(
            device_id=self._generate_device_id(),
            device_name=socket.gethostname(),
            os_type=platform.system().lower(),
            ip_address=self._get_local_ip(),
            port=port,
            screens=screens,
            position='center',
            is_connected=True,
            last_active=time.time()
        )
        logger.info(f"Local device initialized: {self.local_device.device_name} ({self.local_device.ip_address})")
        return self.local_device
    
    def add_remote_device(self, device: Device):
        """添加远程设备"""
        self.remote_devices[device.device_id] = device
        logger.info(f"Remote device added: {device.device_name} at {device.position}")
    
    def remove_remote_device(self, device_id: str):
        """移除远程设备"""
        if device_id in self.remote_devices:
            device = self.remote_devices.pop(device_id)
            logger.info(f"Remote device removed: {device.device_name}")
    
    def get_device_by_position(self, position: str) -> Optional[Device]:
        """根据位置获取设备"""
        for device in self.remote_devices.values():
            if device.position == position and device.is_connected:
                return device
        return None
    
    def check_edge_trigger(self, x: int, y: int) -> tuple:
        """
        检查是否触发边缘切换
        
        Args:
            x: 鼠标X坐标
            y: 鼠标Y坐标
        
        Returns:
            (should_switch, target_device, edge)
        """
        if not self.local_device:
            return False, None, None
        
        # 查找包含该点的屏幕
        current_screen = None
        for screen in self.local_device.screens:
            if screen.contains_point(x, y):
                current_screen = screen
                break
        
        if not current_screen:
            # 可能在边界外
            current_screen = self._find_nearest_screen(x, y)
        
        if not current_screen:
            return False, None, None
        
        # 检查是否在边缘
        edges = current_screen.is_at_edge(x, y, self.edge_threshold)
        triggered_edge = None
        for edge, at_edge in edges.items():
            if at_edge:
                triggered_edge = edge
                break
        
        if not triggered_edge:
            # 不在边缘，重置计时器
            self._edge_timer = None
            self._last_edge = None
            return False, None, None
        
        # 边缘停留延迟检查
        current_time = time.time()
        
        # 如果是新边缘或不同边缘，重置计时器
        if self._last_edge != triggered_edge:
            self._edge_timer = current_time
            self._last_edge = triggered_edge
            return False, None, None
        
        # 检查是否达到延迟时间
        if current_time - self._edge_timer < self.edge_delay:
            return False, None, None
        
        # 确定目标设备
        target_device = self._find_device_at_edge(triggered_edge)
        if target_device:
            self._edge_timer = None
            self._last_edge = None
            return True, target_device, triggered_edge
        
        return False, None, None
    
    def _find_device_at_edge(self, edge: str) -> Optional[Device]:
        """根据边缘方向查找目标设备"""
        edge_position_map = {
            'left': 'left',
            'right': 'right',
            'top': 'top',
            'bottom': 'bottom'
        }
        target_position = edge_position_map.get(edge)
        return self.get_device_by_position(target_position)
    
    def _find_nearest_screen(self, x: int, y: int) -> Optional[Screen]:
        """查找最近的屏幕"""
        if not self.local_device or not self.local_device.screens:
            return None
        
        # 简化处理：返回主屏幕
        for screen in self.local_device.screens:
            if screen.is_primary:
                return screen
        
        return self.local_device.screens[0] if self.local_device.screens else None
    
    def _detect_screens(self) -> List[Screen]:
        """检测本地屏幕"""
        screens = []
        try:
            monitors = get_monitors()
            for idx, monitor in enumerate(monitors):
                screen = Screen(
                    index=idx,
                    x=monitor.x,
                    y=monitor.y,
                    width=monitor.width,
                    height=monitor.height,
                    is_primary=(idx == 0),  # 简化：第一个屏幕为主屏
                    name=monitor.name if hasattr(monitor, 'name') else f"Screen{idx}"
                )
                screens.append(screen)
                logger.debug(f"Detected screen {idx}: {screen.width}x{screen.height} at ({screen.x}, {screen.y})")
        except Exception as e:
            logger.error(f"Error detecting screens: {e}")
            # 创建默认屏幕
            screens = [Screen(0, 0, 0, 1920, 1080, True, "Default")]
        
        return screens
    
    @staticmethod
    def _generate_device_id() -> str:
        """生成设备唯一标识"""
        return str(uuid.uuid4())
    
    @staticmethod
    def _get_local_ip() -> str:
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.warning(f"Could not get local IP: {e}")
            return "127.0.0.1"
