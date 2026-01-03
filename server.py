"""
鼠标共享服务端
当鼠标移动到屏幕边缘时，将鼠标控制权交给客户端
"""
import socket
import json
import threading
import yaml
import platform
from pynput import mouse
from pynput.mouse import Controller
from screeninfo import get_monitors


class MouseShareServer:
    def __init__(self, config_path='config.yaml'):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.host = config['network']['server']['host']
        self.port = config['network']['server']['port']
        self.edge_threshold = config['screen_switch']['edge_threshold']
        
        # 解决Windows缩放偏移问题
        if platform.system().lower() == 'windows':
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        
        # 获取屏幕尺寸
        monitors = get_monitors()
        self.screen_width = monitors[0].width
        self.screen_height = monitors[0].height
        print(f"屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
        # 状态变量
        self.client_socket = None
        self.is_controlling_client = False
        self.last_pos = (0, 0)
        self.mouse_controller = Controller()
        
    def start_server(self):
        """启动socket服务器"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(1)
        print(f"服务器启动，监听 {self.host}:{self.port}")
        
        while True:
            print("等待客户端连接...")
            self.client_socket, addr = server.accept()
            print(f"客户端已连接: {addr}")
            
            # 保持连接，接收心跳
            try:
                while True:
                    data = self.client_socket.recv(1024)
                    if not data:
                        break
            except Exception as e:
                print(f"连接异常: {e}")
            
            print("客户端断开连接")
            self.client_socket = None
            self.is_controlling_client = False
    
    def on_move(self, x, y):
        """鼠标移动事件处理"""
        if not self.client_socket:
            return
        
        # 检测是否在右边缘
        at_right_edge = x >= self.screen_width - self.edge_threshold
        
        # 进入客户端控制模式
        if not self.is_controlling_client:
            if at_right_edge:
                print("鼠标移动到右边缘，切换到客户端控制")
                self.is_controlling_client = True
                self.last_pos = (x, y)
                # 发送初始位置到客户端（客户端屏幕左侧）
                self.send_mouse_command('move_to', 0, y)
                return
        
        # 在客户端控制模式下
        if self.is_controlling_client:
            # 计算相对移动
            dx = x - self.last_pos[0]
            dy = y - self.last_pos[1]
            
            # 发送相对移动到客户端
            if dx != 0 or dy != 0:
                self.send_mouse_command('move', dx, dy)
            
            # 将鼠标固定在右侧边缘，防止移出屏幕
            fixed_x = self.screen_width - 20
            self.mouse_controller.position = (fixed_x, y)
            self.last_pos = (fixed_x, y)
            
            # 检测是否返回服务端（鼠标向左移动）
            if dx < -10:
                print("检测到向左移动，返回服务端控制")
                self.is_controlling_client = False
    
    def send_mouse_command(self, cmd_type, x, y):
        """发送鼠标命令到客户端"""
        try:
            data = {
                'type': cmd_type,  # 'move' 或 'move_to'
                'x': int(x),
                'y': int(y)
            }
            message = json.dumps(data) + '\n'
            self.client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"发送命令失败: {e}")
            self.is_controlling_client = False
    
    def run(self):
        """运行服务器"""
        try:
            # 启动socket服务器线程
            server_thread = threading.Thread(target=self.start_server, daemon=True)
            server_thread.start()
            
            # 启动鼠标监听
            print("开始监听鼠标移动...")
            print(f"提示: 将鼠标移动到屏幕右边缘可切换到客户端控制")
            with mouse.Listener(on_move=self.on_move) as listener:
                listener.join()
        except KeyboardInterrupt:
            print("\n服务器关闭")
        except Exception as e:
            print(f"错误: {e}")


if __name__ == '__main__':
    server = MouseShareServer()
    server.run()
