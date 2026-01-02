"""
配置管理模块
"""
import yaml
import os


class Settings:
    """配置管理类"""
    
    def __init__(self, config_file='config.yaml'):
        self.config_file = config_file
        self.config = {}
        self.load()
    
    def load(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            return True
        except FileNotFoundError:
            print(f"配置文件未找到: {self.config_file}")
            self._create_default_config()
            return False
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def save(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key_path, default=None):
        """
        获取配置值
        :param key_path: 配置路径，如 'network.server.port'
        :param default: 默认值
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path, value):
        """
        设置配置值
        :param key_path: 配置路径
        :param value: 值
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config = {
            'version': 1.0,
            'network': {
                'server': {'host': '0.0.0.0', 'port': 41234},
                'client': {
                    'server_host': '127.0.0.1',
                    'server_port': 41234,
                    'auto_reconnect': True,
                    'reconnect_interval': 5
                }
            },
            'screen_switch': {
                'edge_threshold': 5,
                'edge_delay': 0.3
            },
            'input': {
                'mouse': {'sensitivity': 1.0, 'smooth_movement': True},
                'keyboard': {'enabled': True}
            },
            'clipboard': {'enabled': False, 'monitor_interval': 0.5},
            'logging': {'level': 'INFO', 'file': 'logs/mkshare.log'}
        }
        self.save()
