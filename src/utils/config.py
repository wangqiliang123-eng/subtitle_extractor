import json
import os

class Config:
    def __init__(self):
        self.config_file = 'config/config.json'
        self.config = self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists('config'):
            os.makedirs('config')
            
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self.get_default_config()
        else:
            return self.get_default_config()
            
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
            
    def get_default_config(self):
        """获取默认配置"""
        return {
            "model_path": "models",
            "output_path": "output",
            "language": "ch",
            "max_batch_size": 5
        }