"""
屏幕管理模块
管理屏幕信息和边缘检测
"""
import socket
import platform
from screeninfo import get_monitors
from utils.logger import setup_logger

logger = setup_logger('ScreenManager')


class ScreenManager:
    """屏幕管理器"""
    
    def __init__(self, edge_threshold=5, edge_delay=0.3):
        self.screens = []
        self.edge_threshold = edge_threshold
        self.edge_delay = edge_delay
        self._edge_timer = None
        self._detect_screens()
    
    def _detect_screens(self):
        """检测本地屏幕"""
        try:
            monitors = get_monitors()
            self.screens = []
            
            for idx, monitor in enumerate(monitors):
                screen = {
                    'index': idx,
                    'x': monitor.x,
                    'y': monitor.y,
                    'width': monitor.width,
                    'height': monitor.height,
                    'is_primary': (idx == 0),
                    'name': monitor.name if hasattr(monitor, 'name') else f'Screen {idx}'
                }
                self.screens.append(screen)
                logger.info(f"检测到屏幕 {idx}: {screen['width']}x{screen['height']} at ({screen['x']}, {screen['y']})")
            
        except Exception as e:
            logger.error(f"检测屏幕失败: {e}")
            # 使用默认屏幕
            self.screens = [{
                'index': 0,
                'x': 0,
                'y': 0,
                'width': 1920,
                'height': 1080,
                'is_primary': True,
                'name': 'Default Screen'
            }]
    
    def get_device_info(self):
        """获取设备信息"""
        return {
            'device_name': socket.gethostname(),
            'os_type': platform.system().lower(),
            'os_version': platform.version(),
            'screen_count': len(self.screens),
            'screens': self.screens
        }
    
    def check_edge_trigger(self, x, y):
        """
        检查是否触发屏幕边缘
        :param x: 鼠标X坐标
        :param y: 鼠标Y坐标
        :return: (triggered, edge_direction)
        """
        # 查找包含该点的屏幕
        current_screen = None
        for screen in self.screens:
            if self._point_in_screen(x, y, screen):
                current_screen = screen
                break
        
        if not current_screen:
            return False, None
        
        # 检查是否在边缘
        edges = self._get_edges(x, y, current_screen)
        
        for edge, at_edge in edges.items():
            if at_edge:
                logger.debug(f"触发边缘: {edge} at ({x}, {y})")
                return True, edge
        
        return False, None
    
    def _point_in_screen(self, x, y, screen):
        """检查点是否在屏幕内"""
        return (screen['x'] <= x < screen['x'] + screen['width'] and
                screen['y'] <= y < screen['y'] + screen['height'])
    
    def _get_edges(self, x, y, screen):
        """获取边缘状态"""
        threshold = self.edge_threshold
        edges = {
            'left': x - screen['x'] <= threshold,
            'right': (screen['x'] + screen['width']) - x <= threshold,
            'top': y - screen['y'] <= threshold,
            'bottom': (screen['y'] + screen['height']) - y <= threshold
        }
        return edges
    
    def get_primary_screen(self):
        """获取主屏幕"""
        for screen in self.screens:
            if screen['is_primary']:
                return screen
        return self.screens[0] if self.screens else None
