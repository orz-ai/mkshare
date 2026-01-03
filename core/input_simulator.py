"""
输入模拟模块
模拟鼠标和键盘事件
"""

from typing import Set
from pynput import mouse, keyboard
from pynput.mouse import Button

from utils.logger import get_logger

logger = get_logger(__name__)


class InputSimulator:
    """输入模拟器"""
    
    def __init__(self):
        self._mouse_controller = mouse.Controller()
        self._keyboard_controller = keyboard.Controller()
        self._is_active = False
        self._pressed_keys: Set[int] = set()
        
        # 按键映射表
        self._key_map = self._build_key_map()
        
        logger.info("InputSimulator initialized")
    
    def activate(self):
        """激活模拟器"""
        self._is_active = True
        logger.info("Input simulator activated")
    
    def deactivate(self):
        """停用模拟器"""
        self._is_active = False
        self.release_all_keys()
        logger.info("Input simulator deactivated")
    
    def is_active(self) -> bool:
        """检查模拟器是否激活"""
        return self._is_active
    
    # ===== 鼠标模拟 =====
    
    def move_mouse(self, x: int, y: int):
        """
        移动鼠标到指定位置
        
        Args:
            x: X坐标
            y: Y坐标
        """
        if not self._is_active:
            return
        
        try:
            self._mouse_controller.position = (x, y)
        except Exception as e:
            logger.error(f"Error moving mouse: {e}")
    
    def move_mouse_relative(self, dx: int, dy: int):
        """
        相对移动鼠标
        
        Args:
            dx: X方向移动量
            dy: Y方向移动量
        """
        if not self._is_active:
            return
        
        try:
            current_x, current_y = self._mouse_controller.position
            self._mouse_controller.position = (current_x + dx, current_y + dy)
        except Exception as e:
            logger.error(f"Error moving mouse relatively: {e}")
    
    def press_mouse_button(self, button: int):
        """
        按下鼠标按键
        
        Args:
            button: 按键编号 (1=左键, 2=右键, 3=中键)
        """
        if not self._is_active:
            return
        
        try:
            btn = self._convert_mouse_button(button)
            if btn:
                self._mouse_controller.press(btn)
        except Exception as e:
            logger.error(f"Error pressing mouse button: {e}")
    
    def release_mouse_button(self, button: int):
        """
        抬起鼠标按键
        
        Args:
            button: 按键编号 (1=左键, 2=右键, 3=中键)
        """
        if not self._is_active:
            return
        
        try:
            btn = self._convert_mouse_button(button)
            if btn:
                self._mouse_controller.release(btn)
        except Exception as e:
            logger.error(f"Error releasing mouse button: {e}")
    
    def click_mouse(self, button: int, clicks: int = 1):
        """
        点击鼠标
        
        Args:
            button: 按键编号
            clicks: 点击次数
        """
        if not self._is_active:
            return
        
        try:
            btn = self._convert_mouse_button(button)
            if btn:
                self._mouse_controller.click(btn, clicks)
        except Exception as e:
            logger.error(f"Error clicking mouse: {e}")
    
    def scroll_mouse(self, dx: int, dy: int):
        """
        滚动鼠标滚轮
        
        Args:
            dx: 水平滚动量
            dy: 垂直滚动量
        """
        if not self._is_active:
            return
        
        try:
            self._mouse_controller.scroll(dx, dy)
        except Exception as e:
            logger.error(f"Error scrolling mouse: {e}")
    
    def get_mouse_position(self) -> tuple:
        """获取当前鼠标位置"""
        return self._mouse_controller.position
    
    @staticmethod
    def _convert_mouse_button(button_num: int):
        """
        转换按键编号到 pynput Button
        
        Args:
            button_num: 按键编号
        
        Returns:
            pynput Button 对象
        """
        button_map = {
            1: Button.left,
            2: Button.right,
            3: Button.middle
        }
        return button_map.get(button_num)
    
    # ===== 键盘模拟 =====
    
    def press_key(self, key_code: int, char: str = ''):
        """
        按下按键
        
        Args:
            key_code: 按键码
            char: 字符（如果是字符键）
        """
        if not self._is_active:
            return
        
        try:
            key = self._map_key(key_code, char)
            if key:
                self._keyboard_controller.press(key)
                self._pressed_keys.add(key_code)
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
    
    def release_key(self, key_code: int, char: str = ''):
        """
        抬起按键
        
        Args:
            key_code: 按键码
            char: 字符（如果是字符键）
        """
        if not self._is_active:
            return
        
        try:
            key = self._map_key(key_code, char)
            if key:
                self._keyboard_controller.release(key)
                self._pressed_keys.discard(key_code)
        except Exception as e:
            logger.error(f"Error releasing key: {e}")
    
    def type_text(self, text: str):
        """
        输入文本
        
        Args:
            text: 要输入的文本
        """
        if not self._is_active:
            return
        
        try:
            self._keyboard_controller.type(text)
        except Exception as e:
            logger.error(f"Error typing text: {e}")
    
    def release_all_keys(self):
        """释放所有按下的按键"""
        for key_code in list(self._pressed_keys):
            self.release_key(key_code)
        self._pressed_keys.clear()
    
    def _map_key(self, key_code: int, char: str):
        """
        映射按键码到 pynput Key 对象
        
        Args:
            key_code: 按键码
            char: 字符
        
        Returns:
            pynput Key 或字符
        """
        # 优先使用字符
        if char and len(char) == 1:
            return char
        
        # 使用按键映射表
        return self._key_map.get(key_code)
    
    @staticmethod
    def _build_key_map():
        """构建按键映射表"""
        from pynput.keyboard import Key
        
        # 创建统一按键码到 pynput Key 的映射
        # 使用 Windows 虚拟键码作为参考
        key_map = {}
        
        # 安全添加键的辅助函数
        def safe_add(code, key_name):
            try:
                key_map[code] = getattr(Key, key_name)
            except AttributeError:
                pass  # 该平台不支持此键
        
        # 基础功能键（大多数平台都支持）
        safe_add(0x08, 'backspace')
        safe_add(0x09, 'tab')
        safe_add(0x0D, 'enter')
        safe_add(0x10, 'shift')
        safe_add(0x11, 'ctrl')
        safe_add(0x12, 'alt')
        safe_add(0x13, 'pause')  # Windows/Linux
        safe_add(0x14, 'caps_lock')
        safe_add(0x1B, 'esc')
        safe_add(0x20, 'space')
        safe_add(0x21, 'page_up')
        safe_add(0x22, 'page_down')
        safe_add(0x23, 'end')
        safe_add(0x24, 'home')
        
        # 方向键
        safe_add(0x25, 'left')
        safe_add(0x26, 'up')
        safe_add(0x27, 'right')
        safe_add(0x28, 'down')
        
        # 编辑键
        safe_add(0x2D, 'insert')  # macOS 没有
        safe_add(0x2E, 'delete')
        
        # 功能键 F1-F12
        safe_add(0x70, 'f1')
        safe_add(0x71, 'f2')
        safe_add(0x72, 'f3')
        safe_add(0x73, 'f4')
        safe_add(0x74, 'f5')
        safe_add(0x75, 'f6')
        safe_add(0x76, 'f7')
        safe_add(0x77, 'f8')
        safe_add(0x78, 'f9')
        safe_add(0x79, 'f10')
        safe_add(0x7A, 'f11')
        safe_add(0x7B, 'f12')
        
        # 数字键盘锁定键
        safe_add(0x90, 'num_lock')  # macOS 可能没有
        safe_add(0x91, 'scroll_lock')  # macOS 没有
        
        # 修饰键
        safe_add(0xA0, 'shift_l')
        safe_add(0xA1, 'shift_r')
        safe_add(0xA2, 'ctrl_l')
        safe_add(0xA3, 'ctrl_r')
        safe_add(0xA4, 'alt_l')
        safe_add(0xA5, 'alt_r')
        
        return key_map
