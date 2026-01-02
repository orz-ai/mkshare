"""
MKShare Client - 客户端主程序
运行在被控设备上，接收并模拟输入事件
"""
import sys
import time
import signal
from config.settings import Settings
from core.input_simulator import InputSimulator
from core.screen_manager import ScreenManager
from network.client import NetworkClient
from network.protocol import (
    MSG_MOUSE_MOVE, MSG_MOUSE_CLICK, MSG_MOUSE_SCROLL, MSG_MOUSE_ENTER, MSG_MOUSE_LEAVE,
    MSG_KEY_PRESS, MSG_KEY_RELEASE, MSG_SWITCH_IN, MSG_SWITCH_OUT
)
from utils.logger import setup_logger

logger = setup_logger('Client')


class MKShareClient:
    """MKShare 客户端主类"""
    
    def __init__(self, config_file='config.yaml'):
        self.config = Settings(config_file)
        self.input_simulator = None
        self.screen_manager = None
        self.network_client = None
        self.running = False
        
        # 配置日志级别
        log_level = self.config.get('logging.level', 'INFO')
        import logging
        logger.setLevel(getattr(logging, log_level))
    
    def start(self):
        """启动客户端"""
        logger.info("=" * 50)
        logger.info("MKShare Client 启动中...")
        logger.info("=" * 50)
        
        # 初始化屏幕管理器
        self.screen_manager = ScreenManager()
        
        # 初始化输入模拟器
        self.input_simulator = InputSimulator()
        
        # 初始化网络客户端
        self.network_client = NetworkClient()
        self.network_client.register_callback('connected', self._on_connected)
        self.network_client.register_callback('disconnected', self._on_disconnected)
        self.network_client.register_callback('message_received', self._on_message_received)
        
        # 连接到服务器
        host = self.config.get('network.client.server_host')
        port = self.config.get('network.client.server_port')
        
        if not host:
            logger.error("未配置服务器地址，请编辑 config.yaml 文件")
            return False
        
        logger.info(f"正在连接到服务器: {host}:{port}")
        
        if not self.network_client.connect(host, port):
            logger.error("连接服务器失败")
            return False
        
        self.running = True
        logger.info("客户端启动成功！")
        
        return True
    
    def stop(self):
        """停止客户端"""
        logger.info("正在停止客户端...")
        self.running = False
        
        if self.input_simulator:
            self.input_simulator.deactivate()
        
        if self.network_client:
            self.network_client.disconnect()
        
        logger.info("客户端已停止")
    
    def run(self):
        """运行客户端主循环"""
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        finally:
            self.stop()
    
    def _on_connected(self):
        """连接成功回调"""
        logger.info("已成功连接到服务器")
    
    def _on_disconnected(self):
        """断开连接回调"""
        logger.warning("与服务器断开连接")
        
        # 自动重连
        if self.config.get('network.client.auto_reconnect', True):
            reconnect_interval = self.config.get('network.client.reconnect_interval', 5)
            logger.info(f"{reconnect_interval} 秒后尝试重连...")
            time.sleep(reconnect_interval)
            
            if self.running:
                host = self.config.get('network.client.server_host')
                port = self.config.get('network.client.server_port')
                self.network_client.connect(host, port)
    
    def _on_message_received(self, message):
        """处理接收到的消息"""
        msg_type = message['type']
        payload = message.get('payload', {})
        
        if msg_type == MSG_MOUSE_MOVE:
            self._handle_mouse_move(payload)
        elif msg_type == MSG_MOUSE_ENTER:
            self._handle_mouse_enter(payload)
        elif msg_type == MSG_MOUSE_CLICK:
            self._handle_mouse_button(payload)
        elif msg_type == MSG_MOUSE_SCROLL:
            self._handle_mouse_scroll(payload)
        elif msg_type == MSG_KEY_PRESS:
            self._handle_key(payload, True)
        elif msg_type == MSG_KEY_RELEASE:
            self._handle_key(payload, False)
        elif msg_type == MSG_SWITCH_IN:
            self._handle_switch_in(payload)
        elif msg_type == MSG_SWITCH_OUT:
            self._handle_switch_out()
    
    def _handle_mouse_move(self, payload):
        """处理鼠标移动"""
        # 如果payload包含dx/dy，则使用相对移动
        if 'dx' in payload and 'dy' in payload:
            dx = payload['dx']
            dy = payload['dy']
            logger.debug(f"接收到相对移动: dx={dx}, dy={dy}")
            self.input_simulator.move_mouse_relative(dx, dy)
        else:
            # 向后兼容：绝对坐标
            x = payload.get('x', 0)
            y = payload.get('y', 0)
            logger.debug(f"接收到绝对坐标: x={x}, y={y}")
            self.input_simulator.move_mouse(x, y)
    
    def _handle_mouse_button(self, payload):
        """处理鼠标按键"""
        button = payload.get('button', 1)
        pressed = payload.get('pressed', False)
        self.input_simulator.click_mouse(button, pressed)
    
    def _handle_mouse_scroll(self, payload):
        """处理鼠标滚轮"""
        dx = payload.get('dx', 0)
        dy = payload.get('dy', 0)
        self.input_simulator.scroll_mouse(dx, dy)
    
    def _handle_key(self, payload, pressed):
        """处理键盘按键"""
        key = payload.get('key')
        if key:
            if pressed:
                self.input_simulator.press_key(key)
            else:
                self.input_simulator.release_key(key)
    
    def _handle_switch_in(self, payload=None):
        """处理切换到此设备"""
        logger.info("服务器切换控制到此设备")
        
        # 根据server的触发边缘，设置鼠标的进入位置
        if payload and 'edge' in payload:
            edge = payload['edge']
            self.input_simulator.set_entry_position(edge, self.screen_manager)
        
        self.input_simulator.activate()
    
    def _handle_switch_out(self):
        """处理切换离开此设备"""
        logger.info("服务器切换控制离开此设备")
        self.input_simulator.deactivate()


def signal_handler(sig, frame):
    """信号处理器"""
    logger.info("收到终止信号，正在退出...")
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动客户端
    client = MKShareClient()
    
    if client.start():
        client.run()
    else:
        logger.error("客户端启动失败")
        sys.exit(1)


if __name__ == "__main__":
    main()