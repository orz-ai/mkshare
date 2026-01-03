"""
配置管理模块
加载和管理配置文件
"""

import os
import yaml
from typing import Any, Dict, Optional

from utils.logger import get_logger
from utils.validators import *

logger = get_logger(__name__)


class Settings:
    """配置管理类"""
    
    DEFAULT_CONFIG = {
        'version': '1.0',
        'network': {
            'server': {
                'host': '0.0.0.0',
                'port': 41234,
                'max_clients': 5
            },
            'client': {
                'server_host': '127.0.0.1',
                'server_port': 41234,
                'auto_reconnect': True,
                'reconnect_interval': 5,
                'connection_timeout': 10
            },
            'discovery': {
                'enabled': True,
                'port': 41235,
                'interval': 5
            }
        },
        'screen_switch': {
            'edge_threshold': 5,
            'edge_delay': 0.3
        },
        'input': {
            'mouse': {
                'sensitivity': 1.0,
                'smooth_movement': True
            },
            'keyboard': {
                'enabled': True
            }
        },
        'clipboard': {
            'enabled': False,
            'monitor_interval': 0.5,
            'max_size': 1048576  # 1MB
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/mkshare.log'
        }
    }
    
    def __init__(self, config_file: str = 'config.yaml'):
        """
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> bool:
        """
        加载配置文件
        
        Returns:
            是否成功加载
        """
        # 先加载默认配置
        self.config = self.DEFAULT_CONFIG.copy()
        
        # 如果配置文件存在，加载并合并
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._merge_config(self.config, user_config)
                        logger.info(f"Configuration loaded from {self.config_file}")
                        return True
            except Exception as e:
                logger.error(f"Error loading config file: {e}")
                logger.info("Using default configuration")
                return False
        else:
            logger.warning(f"Config file not found: {self.config_file}")
            logger.info("Using default configuration")
            # 创建默认配置文件
            self.save()
        
        return True
    
    def save(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否成功保存
        """
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving config file: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key_path: 配置路径，用点号分隔，如 'network.server.port'
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        设置配置项
        
        Args:
            key_path: 配置路径
            value: 配置值
        """
        keys = key_path.split('.')
        config = self.config
        
        # 导航到倒数第二层
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
    
    def _merge_config(self, base: Dict, override: Dict):
        """
        合并配置字典（递归）
        
        Args:
            base: 基础配置
            override: 覆盖配置
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    # 便捷访问属性
    
    @property
    def server_host(self) -> str:
        return self.get('network.server.host', '0.0.0.0')
    
    @property
    def server_port(self) -> int:
        return self.get('network.server.port', 41234)
    
    @property
    def client_server_host(self) -> str:
        return self.get('network.client.server_host', '127.0.0.1')
    
    @property
    def client_server_port(self) -> int:
        return self.get('network.client.server_port', 41234)
    
    @property
    def auto_reconnect(self) -> bool:
        return self.get('network.client.auto_reconnect', True)
    
    @property
    def reconnect_interval(self) -> int:
        return self.get('network.client.reconnect_interval', 5)
    
    @property
    def edge_threshold(self) -> int:
        return self.get('screen_switch.edge_threshold', 5)
    
    @property
    def edge_delay(self) -> float:
        return self.get('screen_switch.edge_delay', 0.3)
    
    @property
    def mouse_sensitivity(self) -> float:
        return self.get('input.mouse.sensitivity', 1.0)
    
    @property
    def smooth_movement(self) -> bool:
        return self.get('input.mouse.smooth_movement', True)
    
    @property
    def clipboard_enabled(self) -> bool:
        return self.get('clipboard.enabled', False)
    
    @property
    def log_level(self) -> str:
        return self.get('logging.level', 'INFO')
    
    @property
    def log_file(self) -> str:
        return self.get('logging.file', 'logs/mkshare.log')
