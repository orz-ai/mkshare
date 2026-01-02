"""
输入捕获模块 - Server 端
捕获本地鼠标和键盘事件
"""
from pynput import mouse, keyboard
import threading
from utils.logger import setup_logger

logger = setup_logger('InputCapture')


class InputCapture:
    """输入捕获类"""
    
    def __init__(self):
        self._mouse_listener = None
        self._keyboard_listener = None
        self._callbacks = {
            'mouse_move': [],
            'mouse_click': [],
            'key_press': [],
            'key_release': []
        }
        self._is_capturing = False
        self._current_pos = (0, 0)
    
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
    
    def _on_mouse_move(self, x, y):
        """鼠标移动事件处理"""
        self._current_pos = (x, y)
        event = {
            'type': 'mouse_move',
            'x': x,
            'y': y
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
