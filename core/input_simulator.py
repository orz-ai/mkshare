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
        移动鼠标到绝对坐标
        :param x: X坐标
        :param y: Y坐标
        """
        if not self._is_active:
            return
        
        try:
            self._mouse.position = (x, y)
        except Exception as e:
            logger.error(f"移动鼠标失败: {e}")
    
    def move_mouse_relative(self, dx, dy):
        """
        相对移动鼠标
        :param dx: X方向移动量
        :param dy: Y方向移动量
        """
        if not self._is_active:
            return
        
        try:
            current_x, current_y = self._mouse.position
            self._mouse.position = (current_x + dx, current_y + dy)
        except Exception as e:
            logger.error(f"相对移动鼠标失败: {e}")
    
    def set_entry_position(self, edge, screen_manager):
        """
        根据server的退出边缘，设置client的进入位置
        :param edge: server退出的边缘方向 ('left', 'right', 'top', 'bottom')
        :param screen_manager: 屏幕管理器
        """
        try:
            primary_screen = screen_manager.get_primary_screen()
            if not primary_screen:
                return
            
            # server从某边缘出去，client从相对的边缘进入
            edge_map = {
                'right': 'left',   # server右边出 -> client左边进
                'left': 'right',   # server左边出 -> client右边进
                'top': 'bottom',   # server上边出 -> client下边进
                'bottom': 'top'    # server下边出 -> client上边进
            }
            
            enter_edge = edge_map.get(edge, 'left')
            
            # 获取屏幕中心Y坐标
            center_y = primary_screen['y'] + primary_screen['height'] // 2
            center_x = primary_screen['x'] + primary_screen['width'] // 2
            
            # 根据进入边缘设置位置
            if enter_edge == 'left':
                # 从左边进入，设置在左边缘
                x = primary_screen['x'] + 10
                y = center_y
            elif enter_edge == 'right':
                # 从右边进入，设置在右边缘
                x = primary_screen['x'] + primary_screen['width'] - 10
                y = center_y
            elif enter_edge == 'top':
                # 从上边进入，设置在上边缘
                x = center_x
                y = primary_screen['y'] + 10
            else:  # bottom
                # 从下边进入，设置在下边缘
                x = center_x
                y = primary_screen['y'] + primary_screen['height'] - 10
            
            self._mouse.position = (x, y)
            logger.info(f"鼠标从{enter_edge}边缘进入，位置: ({x}, {y})")
            
        except Exception as e:
            logger.error(f"设置进入位置失败: {e}")
    
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
