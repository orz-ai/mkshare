"""
输入捕获模块 - Server 端
捕获本地鼠标和键盘事件
"""
from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController
import threading
from utils.logger import setup_logger

logger = setup_logger('InputCapture')


class InputCapture:
    """输入捕获类"""
    
    def __init__(self):
        self._mouse_listener = None
        self._keyboard_listener = None
        self._mouse_controller = MouseController()  # 用于重置鼠标位置
        self._callbacks = {
            'mouse_move': [],
            'mouse_click': [],
            'key_press': [],
            'key_release': []
        }
        self._is_capturing = False
        self._current_pos = (0, 0)
        self._suppress_input = False  # 是否抑制输入传递到系统
        self._lock_center = None  # 鼠标锁定中心点
        self._use_relative_mode = False  # 是否使用相对鼠标模式
    
    def start(self):
        """开始捕获输入事件"""
        if self._is_capturing:
            logger.warning("输入捕获已在运行")
            return
        
        self._is_capturing = True
        self._start_listeners()
        logger.info("输入捕获已启动")
    
    def _start_listeners(self):
        """启动监听器"""
        # 启动鼠标监听 - 不使用suppress，我们用锁定模式
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll,
            suppress=False  # 鼠标不拦截，保持真实移动
        )
        self._mouse_listener.start()
        
        # 启动键盘监听
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
            suppress=self._suppress_input  # 键盘根据标志决定是否拦截
        )
        self._keyboard_listener.start()
    
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
    
    def set_suppress(self, suppress):
        """
        设置是否拦截输入事件
        :param suppress: True=拦截事件不传递给系统, False=正常传递
        """
        if self._suppress_input == suppress:
            return
        
        old_suppress = self._suppress_input
        self._suppress_input = suppress
        
        if suppress:
            # 开启相对鼠标模式：只抑制键盘，鼠标使用锁定模式
            self._use_relative_mode = True
            # 设置锁定中心点为屏幕中心
            from screeninfo import get_monitors
            monitors = get_monitors()
            if monitors:
                primary = monitors[0]
                self._lock_center = (primary.width // 2, primary.height // 2)
                # 立即移动鼠标到中心
                self._mouse_controller.position = self._lock_center
                logger.info(f"开启相对鼠标模式，锁定中心: {self._lock_center}")
        else:
            # 关闭相对模式
            self._use_relative_mode = False
            self._lock_center = None
            logger.info("关闭相对鼠标模式")
        
        # 只有键盘需要重新创建监听器来改变suppress
        if self._is_capturing and old_suppress != suppress:
            if self._keyboard_listener:
                self._keyboard_listener.stop()
                self._keyboard_listener = keyboard.Listener(
                    on_press=self._on_key_press,
                    on_release=self._on_key_release,
                    suppress=suppress  # 键盘使用真正的suppress
                )
                self._keyboard_listener.start()
        
        logger.info(f"输入拦截已{'开启' if suppress else '关闭'}")
    
    def _on_mouse_move(self, x, y):
        """鼠标移动事件处理"""
        # 如果在相对模式下，计算相对于锁定中心的移动量
        if self._use_relative_mode and self._lock_center:
            dx = x - self._lock_center[0]
            dy = y - self._lock_center[1]
            
            # 发送相对移动事件
            event = {
                'type': 'mouse_move',
                'x': x,
                'y': y,
                'dx': dx,
                'dy': dy
            }
            self._notify_callbacks('mouse_move', event)
            
            # 立即将鼠标重置回中心
            if abs(dx) > 1 or abs(dy) > 1:  # 有明显移动才重置
                self._mouse_controller.position = self._lock_center
        else:
            # 正常模式，记录绝对位置
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
