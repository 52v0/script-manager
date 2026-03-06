"""
任务模型
"""
import datetime
from app.config import SCRIPTS_DIR


class Job:
    """定时任务模型"""
    
    def __init__(self, job_id, script, cron, enabled=True, args='', 
                 email_on_success=False, email_on_failure=False, created_at=None):
        self.id = job_id
        self.script = script
        self.cron = cron
        self.enabled = enabled
        self.args = args
        self.email_on_success = email_on_success
        self.email_on_failure = email_on_failure
        self.created_at = created_at or datetime.datetime.now().isoformat()
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'script': self.script,
            'cron': self.cron,
            'enabled': self.enabled,
            'args': self.args,
            'email_on_success': self.email_on_success,
            'email_on_failure': self.email_on_failure,
            'created_at': self.created_at
        }
    
    @property
    def script_path(self):
        """获取脚本完整路径"""
        from app.config import SCRIPTS_DIR
        return f"{SCRIPTS_DIR}/{self.script}"
    
    def validate(self):
        """验证任务配置"""
        if not self.id:
            return False, '任务ID不能为空'
        if not self.script:
            return False, '脚本不能为空'
        if not self.cron:
            return False, 'Cron表达式不能为空'
        
        # 检查脚本是否存在
        import os
        script_path = os.path.join(SCRIPTS_DIR, self.script)
        if not os.path.exists(script_path):
            return False, '脚本不存在'
        
        return True, None
    
    @classmethod
    def from_dict(cls, job_id, data):
        """从字典创建任务对象"""
        return cls(
            job_id=job_id,
            script=data.get('script', ''),
            cron=data.get('cron', ''),
            enabled=data.get('enabled', True),
            args=data.get('args', ''),
            email_on_success=data.get('email_on_success', False),
            email_on_failure=data.get('email_on_failure', False),
            created_at=data.get('created_at')
        )
