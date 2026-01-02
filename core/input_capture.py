"""
输入捕获模块 - Server 端
捕获本地鼠标和键盘事件，支持边缘检测和相对移动
"""
from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController
import threading
import time
from utils.logger import setup_logger

logger = setup_logger('InputCapture')


class InputCapture:
    def __init__(self):
        self._mouse_listener = None
        self._keyboard_listener = None
        self._mouse_controller = MouseController()
        self._callbacks = {
            'mouse_move': [],
            'mouse_click': [],
            'mouse_scroll': [],
            'key_press': [],
            'key_release': [],
            'edge_trigger': []  # 边缘触发回调
        }
        self._is_capturing = False
        self._current_pos = (0, 0)
        self._last_pos = (0, 0)  # 用于计算delta
        self._focus = True  # 是否聚焦于本机
        self._suppress_input = False  # 是否抑制输入事件
        
        # 边缘检测相关
        self._edge_threshold = 5  # 边缘阈值像素
        self._screen_width = 1920
        self._screen_height = 1080
    
    def start(self):
        """开始捕获输入事件"""
        if self._is_capturing:
            logger.warning("输入捕获已在运行")
            return
        
        self._is_capturing = True
        
        # 启动鼠标监听
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self._mouse_listener.start()
        
        # 启动键盘监听
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._keyboard_listener.start()
        
        logger.info("输入捕获已启动")
    
    def stop(self):
        """停止捕获输入事件"""
        self._is_capturing = False
        
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        logger.info("输入捕获已停止")
    
    def register_callback(self, event_type, callback):
        """
        注册事件回调函数
        :param event_type: 事件类型 ('mouse_move', 'mouse_click', 'key_press', 'key_release')
        :param callback: 回调函数
        """
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
    
    def get_current_pos(self):
        """获取当前鼠标位置"""
        return self._current_pos
    
    def set_screen_size(self, width, height):
        """设置屏幕尺寸"""
        self._screen_width = width
        self._screen_height = height
        logger.debug(f"设置屏幕尺寸: {width}x{height}")
    
    def set_edge_threshold(self, threshold):
        """设置边缘阈值"""
        self._edge_threshold = threshold
    
    def check_edge_trigger(self, x, y):
        if not self._focus:
            return None
        
        # 检查左边缘
        if x <= self._edge_threshold:
            return 'left'
        # 检查右边缘
        elif x >= self._screen_width - self._edge_threshold:
            return 'right'
        # 检查上边缘
        elif y <= self._edge_threshold:
            return 'top'
        # 检查下边缘
        elif y >= self._screen_height - self._edge_threshold:
            return 'bottom'
        
        return None
    
    def set_focus(self, focus):
        """设置焦点状态"""
        self._focus = focus
        if focus:
            logger.info("输入焦点回到本机")
        else:
            logger.info("输入焦点切换到远程设备")
    
    def set_suppress(self, suppress):
        """
        设置是否抑制输入
        :param suppress: True=抑制输入, False=正常
        """
        if self._suppress_mode == suppress:
            return
            
        self._suppress_mode = suppress
        
        # 重启监听器以应用新的suppress设置
        if self._is_capturing:
            if self._mouse_listener:
                self._mouse_listener.stop()
            if self._keyboard_listener:
                self._keyboard_listener.stop()
            
            # 重新创建监听器
            self._mouse_listener = mouse.Listener(
                on_move=self._on_mouse_move,
                on_click=self._on_mouse_click,
                on_scroll=self._on_mouse_scroll,
                suppress=suppress
            )
            self._mouse_listener.start()
            
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
                suppress=suppress
            )
            self._keyboard_listener.start()
            
            if suppress:
                self._last_pos = self._mouse_controller.position
            else:
                self._last_pos = None
                
        logger.info(f"输入抑制已{'开启' if suppress else '关闭'}")
    
    def _on_mouse_move(self, x, y):
        """鼠标移动事件处理"""
        self._current_pos = (x, y)
        
        # 计算增量（相对移动）
        if self._last_pos:
            dx = x - self._last_pos[0]
            dy = y - self._last_pos[1]
        else:
            dx, dy = 0, 0
        
        self._last_pos = (x, y)
        
        # 检查边缘触发
        edge = self.check_edge_trigger(x, y)
        if edge:
            event = {
                'type': 'edge_trigger',
                'edge': edge,
                'x': x,
                'y': y
            }
            self._notify_callbacks('edge_trigger', event)
            return  # 边缘触发时不发送鼠标移动事件
        
        # 只有在焦点在本机时才发送鼠标移动事件
        if self._focus:
            event = {
                'type': 'mouse_move',
                'x': x,
                'y': y,
                'dx': dx,
                'dy': dy
            }
            self._notify_callbacks('mouse_move', event)
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件处理"""
        self._current_pos = (x, y)
        
        # 转换按钮类型
        button_map = {
            mouse.Button.left: 1,
            mouse.Button.right: 2,
            mouse.Button.middle: 3
        }
        button_code = button_map.get(button, 1)
        
        event = {
            'type': 'mouse_click',
            'button': button_code,
            'pressed': pressed,
            'x': x,
            'y': y
        }
        self._notify_callbacks('mouse_click', event)
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """鼠标滚轮事件处理"""
        # 暂时不实现
        pass
    
    def _on_key_press(self, key):
        """键盘按下事件处理"""
        key_info = self._get_key_info(key)
        event = {
            'type': 'key_press',
            'key': key_info['key'],
            'char': key_info['char']
        }
        self._notify_callbacks('key_press', event)
    
    def _on_key_release(self, key):
        """键盘抬起事件处理"""
        key_info = self._get_key_info(key)
        event = {
            'type': 'key_release',
            'key': key_info['key'],
            'char': key_info['char']
        }
        self._notify_callbacks('key_release', event)
    
    @staticmethod
    def _get_key_info(key):
        """获取按键信息"""
        key_str = None
        char = None
        
        try:
            # 尝试获取字符
            char = key.char
            key_str = char
        except AttributeError:
            # 特殊按键
            key_str = str(key).replace('Key.', '')
        
        return {'key': key_str, 'char': char}
    
    def _notify_callbacks(self, event_type, event):
        """通知回调函数"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"回调函数执行错误: {e}")
