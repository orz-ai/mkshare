"""
鼠标共享客户端
接收服务端发送的鼠标移动命令并控制本地鼠标
"""
import socket
import json
from pynput.mouse import Controller

# 配置
SERVER_HOST = '192.168.31.199'  # 修改为你的服务端IP地址
SERVER_PORT = 9999

class MouseShareClient:
    def __init__(self):
        self.controller = Controller()
        self.socket = None
        
    def connect_to_server(self):
        """连接到服务器"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"正在连接到 {SERVER_HOST}:{SERVER_PORT}...")
        self.socket.connect((SERVER_HOST, SERVER_PORT))
        print("已连接到服务器")
    
    def receive_and_move(self):
        """接收并处理鼠标移动命令"""
        buffer = ""
        
        while True:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    print("服务器断开连接")
                    break
                
                buffer += data
                
                # 处理多条命令（以换行符分隔）
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self.process_command(line)
                        
            except Exception as e:
                print(f"接收数据错误: {e}")
                break
    
    def process_command(self, command):
        """处理单条命令"""
        try:
            data = json.loads(command)
            x = data['x']
            y = data['y']
            relative = data.get('relative', False)
            
            if relative:
                # 相对移动
                current_x, current_y = self.controller.position
                new_x = current_x + x
                new_y = current_y + y
                self.controller.position = (new_x, new_y)
                print(f"相对移动: ({x}, {y}) -> 新位置: ({new_x}, {new_y})")
            else:
                # 绝对移动
                self.controller.position = (x, y)
                print(f"绝对移动到: ({x}, {y})")
                
        except Exception as e:
            print(f"处理命令错误: {e}")
    
    def run(self):
        """运行客户端"""
        try:
            self.connect_to_server()
            self.receive_and_move()
        except KeyboardInterrupt:
            print("\n客户端退出")
        except Exception as e:
            print(f"错误: {e}")
        finally:
            if self.socket:
                self.socket.close()

if __name__ == '__main__':
    client = MouseShareClient()
    client.run()
