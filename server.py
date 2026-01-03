"""
鼠标共享服务端 - 参考src实现
监听鼠标移动，当鼠标移动到屏幕右边缘时，通过TCP发送初始位置，然后通过UDP发送相对移动
"""
import socket
import json
import threading
import yaml
import platform
import time
from pynput import mouse as pynput_mouse
from pynput.mouse import Controller
from screeninfo import get_monitors


class MouseShareServer:
    def __init__(self, config_path='config.yaml'):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.tcp_port = config['network']['server']['port']
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
        
        # 状态变量
        self.client_tcp_socket = None
        self.client_udp_addr = None
        self.is_controlling_client = False
        self.mouse_focus = True
        self.last_mouse_pos = (0, 0)
        self.mouse_controller = Controller()
        
        # 创建UDP socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def start_tcp_server(self):
        """启动TCP服务器，用于接收客户端连接和返回消息"""
        tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_server.bind(('0.0.0.0', self.tcp_port))
        tcp_server.listen(5)
        print(f"TCP服务器启动，监听端口 {self.tcp_port}")
        
        while True:
            client, addr = tcp_server.accept()
            threading.Thread(target=self.handle_tcp_client, args=(client, addr), daemon=True).start()
    
    def handle_tcp_client(self, client_socket, addr):
        """处理TCP客户端连接"""
        try:
            # 接收消息
            data = client_socket.recv(4096)
            if not data:
                return
            
            msg = json.loads(data.decode('utf-8'))
            msg_type = msg.get('type')
            
            if msg_type == 'connect':
                # 客户端建立连接
                self.client_tcp_socket = client_socket
                self.client_udp_addr = (addr[0], msg['udp_port'])
                print(f"客户端已连接: {addr}, UDP端口: {msg['udp_port']}")
                # 发送确认
                response = {'status': 'ok', 'udp_port': self.udp_port}
                client_socket.sendall(json.dumps(response).encode('utf-8'))
                # 保持连接
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
            
            elif msg_type == 'mouse_back':
                # 鼠标返回服务端
                print("鼠标返回服务端")
                self.is_controlling_client = False
                self.mouse_focus = True
                # 将鼠标移动到右边缘
                self.mouse_controller.position = (self.screen_width - 30, msg['y'])
                # 发送确认
                response = {'status': 'ok'}
                client_socket.sendall(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            print(f"处理TCP客户端错误: {e}")
        finally:
            if msg_type == 'connect':
                print("客户端断开连接")
                self.client_tcp_socket = None
                self.client_udp_addr = None
                self.is_controlling_client = False
            client_socket.close()
    
    def on_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        if self.is_controlling_client and self.client_udp_addr:
            msg = {
                'type': 'click',
                'button': str(button),
                'pressed': pressed
            }
            self.udp_socket.sendto(json.dumps(msg).encode('utf-8'), self.client_udp_addr)
    
    def on_move(self, x, y):
        """鼠标移动事件处理"""
        if not self.mouse_focus:
            # 如果焦点不在服务端，不处理
            return
        
        # 检测是否在右边缘
        at_right_edge = x >= self.screen_width - self.edge_threshold
        
        # 进入客户端控制模式
        if not self.is_controlling_client:
            if at_right_edge and self.client_udp_addr:
                print("鼠标移动到右边缘，切换到客户端控制")
                self.is_controlling_client = True
                self.mouse_focus = False
                self.last_mouse_pos = self.mouse_controller.position
                
                # 通过TCP发送初始位置
                try:
                    tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    tcp_client.connect((self.client_udp_addr[0], self.tcp_port))
                    msg = {
                        'type': 'move_to',
                        'x': 30,
                        'y': y
                    }
                    tcp_client.sendall(json.dumps(msg).encode('utf-8'))
                    tcp_client.close()
                except Exception as e:
                    print(f"发送初始位置失败: {e}")
                    self.is_controlling_client = False
                    self.mouse_focus = True
                return
    
    def on_scroll(self, x, y, dx, dy):
        """鼠标滚动事件"""
        if self.is_controlling_client and self.client_udp_addr:
            msg = {
                'type': 'scroll',
                'dx': dx,
                'dy': dy
            }
            self.udp_socket.sendto(json.dumps(msg).encode('utf-8'), self.client_udp_addr)
    
    def mouse_listener_with_suppress(self):
        """使用suppress模式的鼠标监听（控制客户端时）"""
        def on_move_suppressed(x, y):
            if not self.is_controlling_client:
                return False  # 停止监听
            
            # 计算相对移动
            dx = x - self.last_mouse_pos[0]
            dy = y - self.last_mouse_pos[1]
            
            # 发送相对移动到客户端
            if (dx != 0 or dy != 0) and self.client_udp_addr:
                msg = {
                    'type': 'move',
                    'x': dx,
                    'y': dy
                }
                self.udp_socket.sendto(json.dumps(msg).encode('utf-8'), self.client_udp_addr)
            
            # 更新位置但不实际移动鼠标（suppress模式会处理）
            self.last_mouse_pos = (x, y)
            
            # 检测鼠标是否移出边界（回到服务端的边缘检测）
            if x <= 200 or y <= 200 or x >= self.screen_width - 200 or y >= self.screen_height - 200:
                # 将鼠标移动到屏幕中心
                self.mouse_controller.position = (self.screen_width // 2, self.screen_height // 2)
                self.last_mouse_pos = self.mouse_controller.position
            
            return True  # 继续监听
        
        # 使用suppress模式监听
        with pynput_mouse.Listener(on_move=on_move_suppressed, on_click=self.on_click, 
                                   on_scroll=self.on_scroll, suppress=True) as listener:
            listener.join()
    
    def run(self):
        """运行服务器"""
        try:
            # 启动TCP服务器线程
            tcp_thread = threading.Thread(target=self.start_tcp_server, daemon=True)
            tcp_thread.start()
            
            print("鼠标共享服务器已启动")
            print(f"提示: 将鼠标移动到屏幕右边缘可切换到客户端控制")
            
            # 主循环：在正常监听和控制模式之间切换
            while True:
                if self.mouse_focus:
                    # 正常监听模式
                    with pynput_mouse.Events() as events:
                        for event in events:
                            if isinstance(event, pynput_mouse.Events.Move):
                                self.on_move(event.x, event.y)
                                if not self.mouse_focus:
                                    # 切换到控制模式
                                    break
                
                if not self.mouse_focus:
                    # 控制客户端模式
                    self.mouse_controller.position = (self.screen_width // 2, self.screen_height // 2)
                    time.sleep(0.01)
                    self.last_mouse_pos = self.mouse_controller.position
                    self.mouse_listener_with_suppress()
                    # 监听结束后重新聚焦
                    self.mouse_focus = True
                
        except KeyboardInterrupt:
            print("\n服务器关闭")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    server = MouseShareServer()
    server.run()
