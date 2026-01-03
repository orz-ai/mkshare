"""
鼠标共享服务端
当鼠标移动到屏幕边缘时，控制client机器的鼠标
"""
import socket
import json
import threading
from pynput import mouse
from screeninfo import get_monitors

# 配置
HOST = '0.0.0.0'
PORT = 9999
EDGE_THRESHOLD = 5  # 边缘触发阈值（像素）

class MouseShareServer:
    def __init__(self):
        self.screen_width = 0
        self.screen_height = 0
        self.client_socket = None
        self.is_controlling_client = False
        self.last_pos = (0, 0)
        
        # 获取屏幕尺寸
        monitors = get_monitors()
        if monitors:
            self.screen_width = monitors[0].width
            self.screen_height = monitors[0].height
        
        print(f"屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
    def start_server(self):
        """启动socket服务器"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        print(f"服务器启动，监听 {HOST}:{PORT}")
        
        while True:
            print("等待客户端连接...")
            self.client_socket, addr = server.accept()
            print(f"客户端已连接: {addr}")
            
            # 保持连接
            try:
                while True:
                    data = self.client_socket.recv(1024)
                    if not data:
                        break
            except:
                pass
            
            print("客户端断开连接")
            self.client_socket = None
            self.is_controlling_client = False
    
    def on_move(self, x, y):
        """鼠标移动事件处理"""
        if not self.client_socket:
            return
        
        # 检测是否在边缘
        at_right_edge = x >= self.screen_width - EDGE_THRESHOLD
        at_left_edge = x <= EDGE_THRESHOLD
        at_top_edge = y <= EDGE_THRESHOLD
        at_bottom_edge = y >= self.screen_height - EDGE_THRESHOLD
        
        # 进入客户端控制模式
        if not self.is_controlling_client:
            if at_right_edge:
                print("鼠标移动到右边缘，切换到客户端控制")
                self.is_controlling_client = True
                self.last_pos = (x, y)
                # 发送初始位置到客户端（屏幕左侧）
                self.send_to_client(0, y)
                # 抑制鼠标（将鼠标移回边缘内）
                from pynput.mouse import Controller
                controller = Controller()
                controller.position = (self.screen_width - EDGE_THRESHOLD - 1, y)
                return
        
        # 在客户端控制模式下
        if self.is_controlling_client:
            # 计算相对移动
            dx = x - self.last_pos[0]
            dy = y - self.last_pos[1]
            self.last_pos = (x, y)
            
            # 发送相对移动到客户端
            if dx != 0 or dy != 0:
                self.send_to_client(dx, dy, relative=True)
            
            # 检测是否返回服务端（鼠标向左移动到边缘）
            if at_left_edge and dx < 0:
                print("返回服务端控制")
                self.is_controlling_client = False
                # 将鼠标移到服务端右侧
                from pynput.mouse import Controller
                controller = Controller()
                controller.position = (self.screen_width - EDGE_THRESHOLD - 100, y)
    
    def send_to_client(self, x, y, relative=False):
        """发送鼠标位置到客户端"""
        try:
            data = {
                'x': x,
                'y': y,
                'relative': relative
            }
            self.client_socket.sendall(json.dumps(data).encode() + b'\n')
        except:
            print("发送失败")
            self.is_controlling_client = False
    
    def run(self):
        """运行服务器"""
        # 启动socket服务器线程
        server_thread = threading.Thread(target=self.start_server, daemon=True)
        server_thread.start()
        
        # 启动鼠标监听
        print("开始监听鼠标移动...")
        with mouse.Listener(on_move=self.on_move) as listener:
            listener.join()

if __name__ == '__main__':
    server = MouseShareServer()
    server.run()
