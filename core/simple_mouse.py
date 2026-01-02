"""
简化的鼠标控制器 - 参考DeviceShare的设计
"""
import platform
from pynput.mouse import Controller as MouseController, Button


class SimpleMouse:
    """简化的鼠标控制器（借鉴DeviceShare）"""
    
    def __init__(self):
        # 解决Windows下缩放偏移问题（关键！）
        if platform.system().lower() == 'windows':
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        
        self._mouse = MouseController()
    
    def get_position(self):
        """获取鼠标位置"""
        return self._mouse.position
    
    def move_to(self, x, y):
        """移动到绝对位置"""
        self._mouse.position = (x, y)
    
    def move(self, dx, dy):
        """相对移动"""
        self._mouse.move(dx, dy)
        return self._mouse.position
    
    def click(self, button, pressed):
        """点击"""
        btn_map = {
            1: Button.left,
            2: Button.right,
            3: Button.middle
        }
        btn = btn_map.get(button, Button.left)
        
        if pressed:
            self._mouse.press(btn)
        else:
            self._mouse.release(btn)
    
    def scroll(self, dx, dy):
        """滚轮"""
        self._mouse.scroll(dx, dy)
