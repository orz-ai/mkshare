"""
鼠标共享客户端
接收服务端发送的鼠标移动命令并控制本地鼠标
"""
import socket
import json
import yaml
import platform
from pynput.mouse import Controller


class MouseShareClient:
    def __init__(self, config_path='config.yaml'):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.server_host = config['network']['client']['server_host']
        self.server_port = config['network']['client']['server_port']
        
        # 解决Windows缩放偏移问题
        if platform.system().lower() == 'windows':
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        
        self.mouse_controller = Controller()
        self.socket = None
        
    def connect_to_server(self):
        """连接到服务器"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"正在连接到 {self.server_host}:{self.server_port}...")
        self.socket.connect((self.server_host, self.server_port))
        print("已连接到服务器")
    
    def receive_and_process(self):
        """接收并处理鼠标移动命令"""
        buffer = ""
        
        while True:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    print("服务器断开连接")
                    break
                
                buffer += data
                
                # 处理多条命令（以换行符分隔）
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self.process_command(line.strip())
                        
            except Exception as e:
                print(f"接收数据错误: {e}")
                break
    
    def process_command(self, command):
        """处理单条命令"""
        try:
            data = json.loads(command)
            cmd_type = data['type']
            x = data['x']
            y = data['y']
            
            if cmd_type == 'move':
                # 相对移动
                current_x, current_y = self.mouse_controller.position
                new_x = current_x + x
                new_y = current_y + y
                self.mouse_controller.position = (new_x, new_y)
                # print(f"相对移动: ({x}, {y})")
                
            elif cmd_type == 'move_to':
                # 绝对移动
                self.mouse_controller.position = (x, y)
                print(f"鼠标切换到客户端，位置: ({x}, {y})")
                
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}, 命令: {command}")
        except Exception as e:
            print(f"处理命令错误: {e}")
    
    def run(self):
        """运行客户端"""
        try:
            self.connect_to_server()
            print("等待接收鼠标控制命令...")
            self.receive_and_process()
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
