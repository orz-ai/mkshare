"""
输入捕获模块
捕获鼠标和键盘事件
"""

import threading
from typing import Callable, Optional
from pynput import mouse, keyboard

from utils.logger import get_logger

logger = get_logger(__name__)


class InputCapture:
    """输入捕获器"""
    
    def __init__(self):
        self._mouse_listener = None
        self._keyboard_listener = None
        self._is_active = False
        self._is_suppressed = False  # 是否抑制本地输入
        
        # 回调函数
        self._on_mouse_move = None
        self._on_mouse_click = None
        self._on_mouse_scroll = None
        self._on_key_press = None
        self._on_key_release = None
        
        # 鼠标状态
        self._last_mouse_pos = (0, 0)
        
        logger.info("InputCapture initialized")
    
    def set_callbacks(self,
                     on_mouse_move: Optional[Callable] = None,
                     on_mouse_click: Optional[Callable] = None,
                     on_mouse_scroll: Optional[Callable] = None,
                     on_key_press: Optional[Callable] = None,
                     on_key_release: Optional[Callable] = None):
        """
        设置事件回调函数
        
        Args:
            on_mouse_move: 鼠标移动回调 (x, y)
            on_mouse_click: 鼠标点击回调 (x, y, button, pressed)
            on_mouse_scroll: 鼠标滚轮回调 (x, y, dx, dy)
            on_key_press: 键盘按下回调 (key)
            on_key_release: 键盘抬起回调 (key)
        """
        self._on_mouse_move = on_mouse_move
        self._on_mouse_click = on_mouse_click
        self._on_mouse_scroll = on_mouse_scroll
        self._on_key_press = on_key_press
        self._on_key_release = on_key_release
    
    def start(self):
        """启动输入捕获"""
        if self._is_active:
            logger.warning("Input capture already active")
            return
        
        self._is_active = True
        self._is_suppressed = False
        
        # 启动鼠标监听器（初始不抑制）
        self._mouse_listener = mouse.Listener(
            on_move=self._handle_mouse_move,
            on_click=self._handle_mouse_click,
            on_scroll=self._handle_mouse_scroll,
            suppress=False  # 初始不抑制，正常使用
        )
        self._mouse_listener.start()
        
        # 启动键盘监听器（初始不抑制）
        self._keyboard_listener = keyboard.Listener(
            on_press=self._handle_key_press,
            on_release=self._handle_key_release,
            suppress=False  # 初始不抑制，正常使用
        )
        self._keyboard_listener.start()
        
        logger.info("Input capture started")
    
    def stop(self):
        """停止输入捕获"""
        if not self._is_active:
            return
        
        self._is_active = False
        
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        logger.info("Input capture stopped")
    
    def suppress(self, suppressed: bool = False):
        """
        抑制/恢复本地输入
        需要重启监听器以改变suppress模式
        
        Args:
            suppressed: True 抑制，False 恢复
        """
        if self._is_suppressed == suppressed:
            return
        
        self._is_suppressed = suppressed
        
        # 重启监听器以应用新的suppress设置
        if self._is_active:
            # 停止旧监听器
            if self._mouse_listener:
                self._mouse_listener.stop()
            if self._keyboard_listener:
                self._keyboard_listener.stop()
            
            # 创建新监听器
            self._mouse_listener = mouse.Listener(
                on_move=self._handle_mouse_move,
                on_click=self._handle_mouse_click,
                on_scroll=self._handle_mouse_scroll,
                suppress=suppressed  # 根据参数设置是否抑制
            )
            self._mouse_listener.start()
            
            self._keyboard_listener = keyboard.Listener(
                on_press=self._handle_key_press,
                on_release=self._handle_key_release,
                suppress=suppressed  # 根据参数设置是否抑制
            )
            self._keyboard_listener.start()
        
        logger.info(f"Input {'suppressed' if suppressed else 'resumed'}")
    
    def get_mouse_position(self) -> tuple:
        """获取当前鼠标位置"""
        return self._last_mouse_pos
    
    def _handle_mouse_move(self, x, y):
        """处理鼠标移动事件"""
        if not self._is_active:
            return
        
        self._last_mouse_pos = (x, y)
        
        logger.debug(f"Mouse move captured: ({x}, {y}), suppressed={self._is_suppressed}")
        
        if self._on_mouse_move:
            try:
                self._on_mouse_move(x, y)
            except Exception as e:
                logger.error(f"Error in mouse move callback: {e}")
        
        # suppress=True时才有效，返回False会抑制事件
        if self._is_suppressed:
            return False
    
    def _handle_mouse_click(self, x, y, button, pressed):
        """处理鼠标点击事件"""
        if not self._is_active:
            return
        
        if self._on_mouse_click:
            try:
                # 转换按键编号
                button_num = self._convert_mouse_button(button)
                self._on_mouse_click(x, y, button_num, pressed)
            except Exception as e:
                logger.error(f"Error in mouse click callback: {e}")
        
        # suppress=True时才有效，返回False会抑制事件
        if self._is_suppressed:
            return False
    
    def _handle_mouse_scroll(self, x, y, dx, dy):
        """处理鼠标滚轮事件"""
        if not self._is_active:
            return
        
        if self._on_mouse_scroll:
            try:
                self._on_mouse_scroll(x, y, int(dx), int(dy))
            except Exception as e:
                logger.error(f"Error in mouse scroll callback: {e}")
        
        # suppress=True时才有效，返回False会抑制事件
        if self._is_suppressed:
            return False
    
    def _handle_key_press(self, key):
        """处理键盘按下事件"""
        if not self._is_active:
            return
        
        if self._on_key_press:
            try:
                self._on_key_press(key)
            except Exception as e:
                logger.error(f"Error in key press callback: {e}")
        
        # suppress=True时才有效，返回False会抑制事件
        if self._is_suppressed:
            return False
    
    def _handle_key_release(self, key):
        """处理键盘抬起事件"""
        if not self._is_active:
            return
        
        if self._on_key_release:
            try:
                self._on_key_release(key)
            except Exception as e:
                logger.error(f"Error in key release callback: {e}")
        
        # suppress=True时才有效，返回False会抑制事件
        if self._is_suppressed:
            return False
    
    @staticmethod
    def _convert_mouse_button(button) -> int:
        """
        转换鼠标按键到统一编号
        
        Returns:
            1=左键, 2=右键, 3=中键
        """
        if button == mouse.Button.left:
            return 1
        elif button == mouse.Button.right:
            return 2
        elif button == mouse.Button.middle:
            return 3
        else:
            return 0
    
    @staticmethod
    def get_key_info(key):
        """
        获取按键信息
        
        Args:
            key: pynput key 对象
        
        Returns:
            (key_code, char, is_special)
        """
        try:
            # 特殊键
            if hasattr(key, 'vk'):
                # 虚拟键码
                return (key.vk, '', True)
            elif hasattr(key, 'char') and key.char:
                # 字符键
                return (ord(key.char), key.char, False)
            elif hasattr(key, 'name'):
                # 命名键（如 Key.shift）
                # 简化处理：使用hash作为键码
                return (hash(key.name) & 0xFFFF, key.name, True)
            else:
                return (0, '', True)
        except Exception as e:
            logger.error(f"Error getting key info: {e}")
            return (0, '', True)
