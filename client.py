"""
MKShare Client - 鼠标共享客户端
接收服务端的鼠标控制命令并控制本地鼠标
"""
import socket
import json
import time
from pynput import mouse
from pynput.mouse import Controller, Listener
from screeninfo import get_monitors
import yaml

# 加载配置
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 全局变量
mouse_controller = Controller()
active = False  # True=client控制, False=等待激活
screen_width = 0
screen_height = 0
sock = None

# 获取屏幕尺寸
for monitor in get_monitors():
    if monitor.is_primary:
        screen_width = monitor.width
        screen_height = monitor.height
        break

edge_threshold = config['screen_switch']['edge_threshold']

def on_move(x, y):
    """鼠标移动事件处理"""
    global active
    
    if active:
        # 检查是否到达左边缘
        if x <= edge_threshold:
            print(f"鼠标到达左边缘，归还控制权给服务端")
            active = False
            # 通知服务端
            try:
                message = json.dumps({
                    'type': 'deactivate',
                    'y': y / screen_height  # 归一化 y 坐标
                }) + '\n'
                sock.sendall(message.encode('utf-8'))
            except:
                pass
            return False  # 抑制此次移动
    else:
        # 未激活，抑制所有鼠标移动
        return False

def connect_to_server():
    """连接到服务器"""
    global sock
    
    server_host = config['network']['client']['server_host']
    server_port = config['network']['client']['server_port']
    
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((server_host, server_port))
            print(f"已连接到服务器: {server_host}:{server_port}")
            return sock
        except Exception as e:
            print(f"连接失败: {e}，5秒后重试...")
            time.sleep(5)

def handle_server_messages():
    """处理服务器消息"""
    global active, sock
    
    buffer = ""
    while True:
        try:
            data = sock.recv(1024).decode('utf-8')
            if not data:
                print("服务器断开连接，尝试重连...")
                sock = connect_to_server()
                buffer = ""
                continue
            
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    message = json.loads(line)
                    
                    # 服务端激活客户端控制
                    if message['type'] == 'activate':
                        print(f"接收控制权，鼠标从左边缘进入")
                        active = True
                        y = int(message['y'] * screen_height)
                        # 将鼠标移到左边缘
                        mouse_controller.position = (edge_threshold + 1, y)
                
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"通信错误: {e}，尝试重连...")
            time.sleep(1)
            sock = connect_to_server()
            buffer = ""

def start_mouse_listener():
    """启动鼠标监听"""
    with Listener(on_move=on_move) as listener:
        listener.join()

if __name__ == '__main__':
    import threading
    
    print(f"屏幕尺寸: {screen_width}x{screen_height}")
    print(f"边缘阈值: {edge_threshold} 像素")
    
    # 连接到服务器
    sock = connect_to_server()
    
    # 启动消息处理线程
    msg_thread = threading.Thread(target=handle_server_messages)
    msg_thread.daemon = True
    msg_thread.start()
    
    # 启动鼠标监听（主线程）
    print("\n鼠标共享客户端运行中...")
    print("等待服务端发送控制命令...\n")
    start_mouse_listener()

