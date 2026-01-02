"""
输入模拟模块 - Client 端
模拟鼠标和键盘操作
"""
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
from utils.logger import setup_logger

logger = setup_logger('InputSimulator')


class InputSimulator:
    """输入模拟类"""
    
    def __init__(self):
        self._mouse = MouseController()
        self._keyboard = KeyboardController()
        self._is_active = False
        self._button_map = {
            1: Button.left,
            2: Button.right,
            3: Button.middle
        }
    
    def activate(self):
        """激活输入模拟"""
        self._is_active = True
        logger.info("输入模拟已激活")
    
    def deactivate(self):
        """停用输入模拟"""
        self._is_active = False
        logger.info("输入模拟已停用")
    
    def move_mouse(self, x, y):
        """
        移动鼠标
        :param x: X坐标
        :param y: Y坐标
        """
        if not self._is_active:
            return
        
        try:
            self._mouse.position = (x, y)
        except Exception as e:
            logger.error(f"移动鼠标失败: {e}")
    
    def click_mouse(self, button, pressed):
        """
        点击鼠标按钮
        :param button: 按钮码 (1=左, 2=右, 3=中)
        :param pressed: True=按下, False=抬起
        """
        if not self._is_active:
            return
        
        try:
            btn = self._button_map.get(button, Button.left)
            if pressed:
                self._mouse.press(btn)
            else:
                self._mouse.release(btn)
        except Exception as e:
            logger.error(f"点击鼠标失败: {e}")
    
    def press_key(self, key_str):
        """
        按下按键
        :param key_str: 按键字符串
        """
        if not self._is_active:
            return
        
        try:
            key = self._parse_key(key_str)
            if key:
                self._keyboard.press(key)
        except Exception as e:
            logger.error(f"按下按键失败: {e}")
    
    def release_key(self, key_str):
        """
        释放按键
        :param key_str: 按键字符串
        """
        if not self._is_active:
            return
        
        try:
            key = self._parse_key(key_str)
            if key:
                self._keyboard.release(key)
        except Exception as e:
            logger.error(f"释放按键失败: {e}")
    
    def _parse_key(self, key_str):
        """
        解析按键字符串为 Key 对象
        :param key_str: 按键字符串
        :return: Key 对象或字符
        """
        if not key_str:
            return None
        
        # 特殊按键映射
        special_keys = {
            'ctrl': Key.ctrl,
            'ctrl_l': Key.ctrl_l,
            'ctrl_r': Key.ctrl_r,
            'shift': Key.shift,
            'shift_l': Key.shift_l,
            'shift_r': Key.shift_r,
            'alt': Key.alt,
            'alt_l': Key.alt_l,
            'alt_r': Key.alt_r,
            'cmd': Key.cmd,
            'cmd_l': Key.cmd_l,
            'cmd_r': Key.cmd_r,
            'enter': Key.enter,
            'space': Key.space,
            'tab': Key.tab,
            'backspace': Key.backspace,
            'delete': Key.delete,
            'esc': Key.esc,
            'up': Key.up,
            'down': Key.down,
            'left': Key.left,
            'right': Key.right,
            'home': Key.home,
            'end': Key.end,
            'page_up': Key.page_up,
            'page_down': Key.page_down,
            'caps_lock': Key.caps_lock,
        }
        
        # 检查是否是特殊按键
        key_lower = key_str.lower()
        if key_lower in special_keys:
            return special_keys[key_lower]
        
        # 普通字符键
        if len(key_str) == 1:
            return key_str
        
        return None
    
    def get_current_pos(self):
        """获取当前鼠标位置"""
        return self._mouse.position
