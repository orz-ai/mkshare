"""
MKShare Server - 鼠标共享服务端
当鼠标移动到屏幕边缘时，将控制权转移到客户端
"""
import socket
import threading
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
clients = []
active = True  # True=server控制, False=client控制
screen_width = 0
screen_height = 0

# 获取屏幕尺寸
for monitor in get_monitors():
    if monitor.is_primary:
        screen_width = monitor.width
        screen_height = monitor.height
        break

edge_threshold = config['screen_switch']['edge_threshold']

def broadcast_to_clients(data):
    """发送数据到所有客户端"""
    for client in clients[:]:
        try:
            message = json.dumps(data) + '\n'
            client.sendall(message.encode('utf-8'))
        except:
            clients.remove(client)

def on_move(x, y):
    """鼠标移动事件处理"""
    global active
    
    if not active:
        # client 控制中，抑制 server 的鼠标移动
        return False
    
    # 检查是否到达边缘
    if x >= screen_width - edge_threshold:
        print(f"鼠标到达右边缘，切换到客户端控制")
        active = False
        # 通知客户端激活
        broadcast_to_clients({
            'type': 'activate',
            'x': 0,
            'y': y / screen_height
        })
        return False  # 抑制这次移动

def handle_client(client_socket, addr):
    """处理客户端连接"""
    global active
    print(f"客户端连接: {addr}")
    clients.append(client_socket)
    
    buffer = ""
    try:
        while True:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
            
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    message = json.loads(line)
                    
                    if message['type'] == 'deactivate':
                        print(f"客户端到达左边缘，切换回服务端控制")
                        active = True
                        y = int(message['y'] * screen_height)
                        mouse_controller.position = (screen_width - edge_threshold - 1, y)
                    
                except json.JSONDecodeError:
                    pass
    except:
        pass
    finally:
        if client_socket in clients:
            clients.remove(client_socket)
        client_socket.close()
        print(f"客户端断开: {addr}")

def start_server():
    """启动服务器"""
    host = config['network']['server']['host']
    port = config['network']['server']['port']
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    
    print(f"服务器启动: {host}:{port}")
    print(f"屏幕尺寸: {screen_width}x{screen_height}")
    print(f"边缘阈值: {edge_threshold} 像素")
    print("等待客户端连接...")
    
    while True:
        client_socket, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        thread.daemon = True
        thread.start()

def start_mouse_listener():
    """启动鼠标监听"""
    with Listener(on_move=on_move) as listener:
        listener.join()

if __name__ == '__main__':
    # 启动服务器线程
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 启动鼠标监听（主线程）
    print("\n鼠标共享服务端运行中...")
    print("将鼠标移动到屏幕右边缘以切换到客户端\n")
    start_mouse_listener()
