# MKShare 快速启动指南

## 项目已完成！

根据ARCHITECTURE.md文档，MKShare项目的核心功能已经实现。

### 已实现的功能模块：

✅ **核心模块**
- `mkshare/core/input_capture.py` - 鼠标键盘输入捕获
- `mkshare/core/input_simulator.py` - 鼠标键盘输入模拟
- `mkshare/core/screen_manager.py` - 多屏幕管理和边缘触发检测

✅ **网络模块**
- `mkshare/network/protocol.py` - 完整的通信协议实现
- `mkshare/network/server.py` - TCP服务器和连接管理
- `mkshare/network/client.py` - TCP客户端和自动重连

✅ **配置模块**
- `mkshare/config/settings.py` - YAML配置文件管理

✅ **工具模块**
- `mkshare/utils/logger.py` - 彩色日志输出
- `mkshare/utils/validators.py` - 数据验证

✅ **启动脚本**
- `server.py` - 服务端主程序
- `client.py` - 客户端主程序

### 使用步骤：

#### 1. 准备环境

```bash
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 安装依赖（如果还没安装）
pip install -r requirements.txt
```

#### 2. 配置

编辑 `config.yaml`，设置服务器IP地址：

```yaml
network:
  client:
    server_host: 192.168.31.199  # 修改为你的服务器IP
    server_port: 41234
```

#### 3. 启动服务端（主控设备）

在主控电脑上运行：

```bash
python server.py
```

#### 4. 启动客户端（被控设备）

在被控电脑上运行：

```bash
python client.py
```

#### 5. 开始使用

1. 在服务端正常使用鼠标键盘
2. 将鼠标移动到屏幕右边缘并停留0.3秒
3. 鼠标将切换到客户端设备，可以控制客户端
4. 控制完成后，将鼠标移回边缘即可返回

### 架构特点：

- **模块化设计**：各模块职责清晰，便于维护和扩展
- **跨平台支持**：基于pynput实现，支持Windows/macOS/Linux
- **可靠通信**：TCP协议 + CRC32校验 + 序列号
- **边缘检测**：智能屏幕边缘触发机制
- **自动重连**：客户端断线自动重连
- **详细日志**：彩色日志输出，便于调试

### 配置说明：

- `edge_threshold`: 边缘触发阈值（默认5像素）
- `edge_delay`: 边缘停留时间（默认0.3秒）
- `auto_reconnect`: 自动重连（默认开启）
- `logging.level`: 日志级别（INFO/DEBUG/WARNING/ERROR）

### 未来扩展（已在架构文档中规划）：

- 剪贴板同步（clipboard_sync模块）
- UDP设备发现（discovery模块）
- 图形界面（gui模块）
- 加密通信（encryption模块）
- 多客户端同时连接
- 更复杂的设备布局

### 故障排除：

1. **权限问题**：Windows需要管理员权限，macOS需要辅助功能授权
2. **连接失败**：检查防火墙、IP地址、端口设置
3. **输入不响应**：检查日志文件 `logs/mkshare.log`
4. **边缘不触发**：调整 `edge_threshold` 和 `edge_delay` 参数

### 日志位置：

```
logs/mkshare.log
```

查看实时日志可以帮助定位问题。

---

**项目状态**: ✅ 核心功能完成，可以正常使用
**版本**: 1.0.0
**日期**: 2026-01-03
