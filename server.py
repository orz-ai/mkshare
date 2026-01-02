
"""
MKShare Server - 服务端主程序
运行在主控设备上，捕获输入并发送到客户端
"""
import sys
import time
import signal
from config.settings import Settings
from core.input_capture import InputCapture
from core.screen_manager import ScreenManager
from network.server import NetworkServer
from network.protocol import (
    MSG_MOUSE_MOVE, MSG_MOUSE_DOWN, MSG_MOUSE_UP,
    MSG_KEY_DOWN, MSG_KEY_UP, MSG_SWITCH_IN, MSG_SWITCH_OUT
)
from utils.logger import setup_logger

logger = setup_logger('Server')


class MKShareServer:
    """MKShare 服务端主类"""
    
    def __init__(self, config_file='config.yaml'):
        self.config = Settings(config_file)
        self.input_capture = None
        self.screen_manager = None
        self.network_server = None
        self.running = False
        self.is_controlling_local = True  # True=控制本地, False=控制远程
        
        # 配置日志级别
        log_level = self.config.get('logging.level', 'INFO')
        import logging
        logger.setLevel(getattr(logging, log_level))
    
    def start(self):
        """启动服务器"""
        logger.info("=" * 50)
        logger.info("MKShare Server 启动中...")
        logger.info("=" * 50)
        
        # 初始化屏幕管理器
        edge_threshold = self.config.get('screen_switch.edge_threshold', 5)
        edge_delay = self.config.get('screen_switch.edge_delay', 0.3)
        self.screen_manager = ScreenManager(edge_threshold, edge_delay)
        
        # 初始化输入捕获
        self.input_capture = InputCapture()
        self.input_capture.register_callback('mouse_move', self._on_mouse_move)
        self.input_capture.register_callback('mouse_click', self._on_mouse_click)
        self.input_capture.register_callback('key_press', self._on_key_press)
        self.input_capture.register_callback('key_release', self._on_key_release)
        self.input_capture.start()
        
        # 初始化网络服务器
        host = self.config.get('network.server.host', '0.0.0.0')
        port = self.config.get('network.server.port', 41234)
        self.network_server = NetworkServer(host, port)
        self.network_server.register_callback('client_connected', self._on_client_connected)
        self.network_server.register_callback('client_disconnected', self._on_client_disconnected)
        
        if not self.network_server.start():
            logger.error("启动网络服务器失败")
            return False
        
        self.running = True
        logger.info("服务器启动成功！")
        logger.info(f"监听地址: {host}:{port}")
        logger.info("等待客户端连接...")
        
        return True
    
    def stop(self):
        """停止服务器"""
        logger.info("正在停止服务器...")
        self.running = False
        
        if self.input_capture:
            self.input_capture.stop()
        
        if self.network_server:
            self.network_server.stop()
        
        logger.info("服务器已停止")
    
    def run(self):
        """运行服务器主循环"""
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        finally:
            self.stop()
    
    def _on_mouse_move(self, event):
        """处理鼠标移动事件"""
        x, y = event['x'], event['y']
        
        # 检查是否触发边缘切换
        if self.is_controlling_local:
            triggered, edge = self.screen_manager.check_edge_trigger(x, y)
            if triggered:
                logger.info(f"触发边缘切换: {edge}")
                self._switch_to_remote()
        
        # 如果正在控制远程，发送鼠标移动事件
        if not self.is_controlling_local and self.network_server.client_connection:
            self.network_server.send_message(MSG_MOUSE_MOVE, {'x': x, 'y': y})
    
    def _on_mouse_click(self, event):
        """处理鼠标点击事件"""
        if not self.is_controlling_local and self.network_server.client_connection:
            self.network_server.send_message(
                MSG_MOUSE_DOWN if event['pressed'] else MSG_MOUSE_UP,
                {
                    'button': event['button'],
                    'x': event['x'],
                    'y': event['y']
                }
            )
    
    def _on_key_press(self, event):
        """处理键盘按下事件"""
        # ESC 键返回本地控制
        if event['key'] == 'esc' and not self.is_controlling_local:
            logger.info("按下 ESC，切换回本地控制")
            self._switch_to_local()
            return
        
        if not self.is_controlling_local and self.network_server.client_connection:
            self.network_server.send_message(MSG_KEY_DOWN, {'key': event['key']})
    
    def _on_key_release(self, event):
        """处理键盘抬起事件"""
        if not self.is_controlling_local and self.network_server.client_connection:
            self.network_server.send_message(MSG_KEY_UP, {'key': event['key']})
    
    def _switch_to_remote(self):
        """切换到远程控制"""
        if not self.network_server.client_connection:
            logger.warning("没有客户端连接，无法切换")
            return
        
        self.is_controlling_local = False
        # 开启输入拦截，防止输入影响本地系统
        self.input_capture.set_suppress(True)
        self.network_server.send_message(MSG_SWITCH_IN)
        logger.info("已切换到远程控制模式")
    
    def _switch_to_local(self):
        """切换回本地控制"""
        self.is_controlling_local = True
        # 关闭输入拦截，恢复本地控制
        self.input_capture.set_suppress(False)
        if self.network_server.client_connection:
            self.network_server.send_message(MSG_SWITCH_OUT)
        logger.info("已切换回本地控制模式")
    
    def _on_client_connected(self, address):
        """客户端连接回调"""
        logger.info(f"客户端已连接: {address}")
    
    def _on_client_disconnected(self):
        """客户端断开回调"""
        logger.warning("客户端已断开")
        self._switch_to_local()


def signal_handler(sig, frame):
    """信号处理器"""
    logger.info("收到终止信号，正在退出...")
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动服务器
    server = MKShareServer()
    
    if server.start():
        server.run()
    else:
        logger.error("服务器启动失败")
        sys.exit(1)


if __name__ == "__main__":
    main()