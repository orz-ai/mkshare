"""
鼠标共享客户端 - 参考src实现
接收服务端发送的鼠标移动命令并控制本地鼠标
支持TCP接收初始位置和返回消息，UDP接收相对移动
"""
import socket
import json
import yaml
import platform
import threading
from pynput.mouse import Controller
from screeninfo import get_monitors


class MouseShareClient:
    def __init__(self, config_path='config.yaml'):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.server_host = config['network']['client']['server_host']
        self.tcp_port = config['network']['client']['server_port']
        self.udp_port = self.tcp_port + 1  # UDP端口为TCP端口+1
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
        
        self.mouse_controller = Controller()
        self.mouse_focus = False
        self.tcp_socket = None
        
        # 创建UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', 0))  # 绑定任意端口
        self.local_udp_port = self.udp_socket.getsockname()[1]
        
    def connect_to_server(self):
        """连接到服务器"""
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"正在连接到 {self.server_host}:{self.tcp_port}...")
        self.tcp_socket.connect((self.server_host, self.tcp_port))
        
        # 发送连接消息，包含本地UDP端口
        msg = {
            'type': 'connect',
            'udp_port': self.local_udp_port
        }
        self.tcp_socket.sendall(json.dumps(msg).encode('utf-8'))
        
        # 接收服务器UDP端口
        data = self.tcp_socket.recv(1024)
        response = json.loads(data.decode('utf-8'))
        self.server_udp_port = response['udp_port']
        
        print(f"已连接到服务器, 本地UDP端口: {self.local_udp_port}, 服务器UDP端口: {self.server_udp_port}")
    
    def tcp_listener(self):
        """TCP监听，接收服务器发送的move_to消息"""
        # 创建新的TCP server socket监听来自服务器的连接
        tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_server.bind(('0.0.0.0', self.tcp_port))
        tcp_server.listen(5)
        
        while True:
            try:
                client, addr = tcp_server.accept()
                data = client.recv(4096)
                if data:
                    msg = json.loads(data.decode('utf-8'))
                    if msg['type'] == 'move_to':
                        # 鼠标切换到客户端
                        self.mouse_focus = True
                        self.mouse_controller.position = (msg['x'], msg['y'])
                        print(f"鼠标切换到客户端，位置: ({msg['x']}, {msg['y']})")
                client.close()
            except Exception as e:
                print(f"TCP监听错误: {e}")
    
    def udp_receiver(self):
        """UDP接收，处理鼠标移动和点击"""
        while True:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                if not data:
                    continue
                
                msg = json.loads(data.decode('utf-8'))
                msg_type = msg['type']
                
                if msg_type == 'move':
                    # 相对移动
                    if self.mouse_focus:
                        current_x, current_y = self.mouse_controller.position
                        new_x = current_x + msg['x']
                        new_y = current_y + msg['y']
                        self.mouse_controller.position = (new_x, new_y)
                        
                        # 判断是否移出屏幕边界（返回服务端）
                        if self.judge_move_out(new_x, new_y):
                            self.send_mouse_back(new_x, new_y)
                
                elif msg_type == 'click':
                    # 鼠标点击
                    from pynput.mouse import Button
                    button_str = msg['button']
                    pressed = msg['pressed']
                    
                    if 'left' in button_str.lower():
                        button = Button.left
                    elif 'right' in button_str.lower():
                        button = Button.right
                    elif 'middle' in button_str.lower():
                        button = Button.middle
                    else:
                        continue
                    
                    if pressed:
                        self.mouse_controller.press(button)
                    else:
                        self.mouse_controller.release(button)
                
                elif msg_type == 'scroll':
                    # 鼠标滚动
                    self.mouse_controller.scroll(msg['dx'], msg['dy'])
                        
            except Exception as e:
                print(f"UDP接收错误: {e}")
    
    def judge_move_out(self, x, y):
        """判断鼠标是否移出屏幕边界（返回服务端）"""
        # 在左边缘
        if x <= self.edge_threshold:
            return True
        return False
    
    def send_mouse_back(self, x, y):
        """发送鼠标返回服务端的消息"""
        try:
            print("鼠标返回服务端")
            self.mouse_focus = False
            
            # 通过TCP发送返回消息
            tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_client.connect((self.server_host, self.tcp_port))
            msg = {
                'type': 'mouse_back',
                'x': x,
                'y': y
            }
            tcp_client.sendall(json.dumps(msg).encode('utf-8'))
            # 等待确认
            tcp_client.recv(1024)
            tcp_client.close()
        except Exception as e:
            print(f"发送返回消息失败: {e}")
    
    def keep_alive(self):
        """保持TCP连接"""
        try:
            while True:
                # 定期检查连接
                self.tcp_socket.recv(1024)
        except:
            print("TCP连接断开")
    
    def run(self):
        """运行客户端"""
        try:
            self.connect_to_server()
            
            # 启动TCP监听线程
            tcp_thread = threading.Thread(target=self.tcp_listener, daemon=True)
            tcp_thread.start()
            
            # 启动UDP接收线程
            udp_thread = threading.Thread(target=self.udp_receiver, daemon=True)
            udp_thread.start()
            
            print("客户端已启动，等待接收鼠标控制命令...")
            
            # 保持主线程运行
            self.keep_alive()
            
        except KeyboardInterrupt:
            print("\n客户端退出")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.tcp_socket:
                self.tcp_socket.close()
            if self.udp_socket:
                self.udp_socket.close()


if __name__ == '__main__':
    client = MouseShareClient()
    client.run()
