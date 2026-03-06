"""
脚本模型
"""
import os
from app.config import SCRIPTS_DIR
from app.utils.file_manager import load_script_metadata


class Script:
    """脚本模型"""
    
    def __init__(self, name, path=None):
        self.name = name
        self.path = path or os.path.join(SCRIPTS_DIR, name)
        self._load_info()
    
    def _load_info(self):
        """加载脚本信息"""
        if os.path.exists(self.path):
            self.size = os.path.getsize(self.path)
            self.mtime = os.path.getmtime(self.path)
        else:
            self.size = 0
            self.mtime = 0
        
        # 加载描述
        metadata = load_script_metadata()
        self.description = metadata.get(self.name, {}).get('description', '')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'name': self.name,
            'path': self.path,
            'size': self.size,
            'mtime': self.mtime,
            'description': self.description
        }
    
    @classmethod
    def list_all(cls):
        """列出所有脚本"""
        scripts = []
        if os.path.exists(SCRIPTS_DIR):
            for file in os.listdir(SCRIPTS_DIR):
                file_path = os.path.join(SCRIPTS_DIR, file)
                if os.path.isfile(file_path) and file.endswith('.py'):
                    scripts.append(cls(file).to_dict())
        return scripts
    
    @classmethod
    def get(cls, name):
        """获取单个脚本"""
        path = os.path.join(SCRIPTS_DIR, name)
        if os.path.exists(path) and name.endswith('.py'):
            return cls(name, path)
        return None
    
    @classmethod
    def update_description(cls, name, description):
        """更新脚本描述"""
        from app.utils.file_manager import load_script_metadata, save_script_metadata
        metadata = load_script_metadata()
        if name not in metadata:
            metadata[name] = {}
        metadata[name]['description'] = description
        save_script_metadata(metadata)
        return True
    
    @classmethod
    def save_uploaded(cls, file, filename):
        """保存上传的脚本文件"""
        # 安全检查：只允许 .py 文件
        if not filename.endswith('.py'):
            raise ValueError("只允许上传 Python 脚本文件 (.py)")
        
        # 安全检查：文件名不能包含路径分隔符
        filename = os.path.basename(filename)
        
        file_path = os.path.join(SCRIPTS_DIR, filename)
        file.save(file_path)
        return cls(filename, file_path)
    
    @classmethod
    def delete(cls, name):
        """删除脚本"""
        path = os.path.join(SCRIPTS_DIR, name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
