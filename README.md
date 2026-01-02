# MKShare - 跨平台鼠标键盘共享工具

MKShare 是一个简单易用的鼠标键盘共享工具，允许你在多台计算机之间共享一套鼠标和键盘。

## 特性

- ✅ 跨平台支持（Windows/macOS/Linux）
- ✅ 局域网直连，低延迟
- ✅ 屏幕边缘自动切换
- ✅ 简单的配置文件管理
- ✅ 纯 Python 实现，易于理解和扩展

## 系统要求

- Python 3.8+
- Windows/macOS/Linux

## 安装

### 1. 克隆或下载项目

```bash
cd d:\project\python\mkshare
```

### 2. 安装虚拟环境（如果还没有）

```bash
python -m venv .venv
```

### 3. 激活虚拟环境

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
.\.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 4. 安装依赖包

```bash
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml` 文件：

### Server 端（主控设备）配置

```yaml
network:
  server:
    host: 0.0.0.0      # 监听所有网卡
    port: 41234        # 监听端口

screen_switch:
  edge_threshold: 5    # 边缘触发阈值（像素）
  edge_delay: 0.3      # 边缘停留延迟（秒）
```

### Client 端（被控设备）配置

```yaml
network:
  client:
    server_host: 192.168.1.100  # 修改为 Server 的 IP 地址
    server_port: 41234
    auto_reconnect: true        # 自动重连
```

## 使用方法

### 1. 在主控设备上运行 Server

```bash
python server.py
```

你会看到类似的输出：
```
==================================================
MKShare Server 启动中...
==================================================
检测到屏幕 0: 1920x1080 at (0, 0)
输入捕获已启动
服务器启动成功: 0.0.0.0:41234
等待客户端连接...
```

### 2. 在被控设备上运行 Client

首先修改 `config.yaml` 中的 `server_host` 为 Server 的 IP 地址，然后运行：

```bash
python client.py
```

你会看到类似的输出：
```
==================================================
MKShare Client 启动中...
==================================================
正在连接到服务器: 192.168.1.100:41234
已连接到服务器: 192.168.1.100:41234
已发送握手消息
握手成功: {'status': 'accepted', ...}
客户端启动成功！
```

### 3. 使用鼠标键盘共享

- **切换到远程设备**：将鼠标移动到屏幕边缘（默认左边缘），停留 0.3 秒
- **切换回本地设备**：按 `ESC` 键

## 工作原理

```
┌─────────────┐                           ┌─────────────┐
│   Server    │                           │   Client    │
│  (主控设备)  │ ◄────── TCP 连接 ────────► │  (被控设备)  │
└─────────────┘                           └─────────────┘
      │                                          │
      ├─ 捕获鼠标/键盘事件                        ├─ 模拟鼠标/键盘操作
      ├─ 检测屏幕边缘                            ├─ 接收事件数据
      └─ 发送事件到 Client                      └─ 执行输入操作
```

## 权限要求

### Windows
- 可能需要以管理员身份运行

### macOS
- 需要在"系统偏好设置" → "安全性与隐私" → "辅助功能"中授权
- 添加 Terminal 或 Python 应用到允许列表

### Linux
- 确保用户在 `input` 组中
- 或使用 `sudo` 运行

## 故障排除

### 1. 连接失败

- 检查防火墙设置，确保 41234 端口开放
- 确认两台设备在同一局域网
- 检查 Server 的 IP 地址是否正确

### 2. 输入无响应

- 检查 Client 是否显示"服务器切换控制到此设备"
- 确认权限设置正确
- 查看日志输出是否有错误

### 3. 找不到 pynput 模块

```bash
pip install pynput
```

### 4. macOS 权限问题

运行以下命令并在弹出的对话框中允许访问：
```bash
python -c "from pynput import mouse; mouse.Controller()"
```

## 项目结构

```
mkshare/
├── config.yaml              # 配置文件
├── server.py                # Server 主程序
├── client.py                # Client 主程序
├── requirements.txt         # 依赖包列表
├── config/
│   └── settings.py          # 配置管理
├── core/
│   ├── input_capture.py     # 输入捕获
│   ├── input_simulator.py   # 输入模拟
│   └── screen_manager.py    # 屏幕管理
├── network/
│   ├── protocol.py          # 通信协议
│   ├── server.py            # 网络服务器
│   └── client.py            # 网络客户端
└── utils/
    └── logger.py            # 日志工具
```

## 日志

日志文件位于 `logs/mkshare.log`，可以通过修改 `config.yaml` 中的 `logging.level` 调整日志级别：

- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息

## 已知限制

- 目前仅支持一对一连接（一个 Server，一个 Client）
- 剪贴板同步功能未实现
- 暂不支持文件拖放传输
- 屏幕边缘切换仅支持左边缘触发

## 未来计划

- [ ] 支持多客户端连接
- [ ] 剪贴板同步
- [ ] 更灵活的边缘配置（上下左右）
- [ ] 加密通信
- [ ] 设备发现（自动发现局域网内的设备）
- [ ] 图形界面配置工具

## 开发

### 运行测试

```bash
# 安装开发依赖
pip install pytest

# 运行测试
pytest tests/
```

### 代码格式化

```bash
pip install black
black *.py core/ network/ config/ utils/
```

## 许可证

MIT License

## 致谢

- [pynput](https://github.com/moses-palmer/pynput) - 输入捕获和模拟
- [screeninfo](https://github.com/rr-/screeninfo) - 屏幕信息检测
- Synergy - 项目灵感来源

## 联系方式

如有问题或建议，欢迎提 Issue。

---

**Enjoy sharing your mouse and keyboard! 🖱️⌨️**
