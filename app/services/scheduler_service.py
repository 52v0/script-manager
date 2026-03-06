"""
调度器服务
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.utils.file_manager import load_jobs


class SchedulerService:
    """调度器服务类"""
    
    _instance = None
    _scheduler = None
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if SchedulerService._scheduler is None:
            SchedulerService._scheduler = BackgroundScheduler()
            SchedulerService._scheduler.start()
    
    @property
    def scheduler(self):
        """获取调度器"""
        return SchedulerService._scheduler
    
    def add_job(self, job_id, func, cron, args=None, replace_existing=True):
        """添加定时任务"""
        try:
            trigger = CronTrigger.from_crontab(cron)
            self.scheduler.add_job(
                func,
                trigger,
                id=job_id,
                args=args or [],
                replace_existing=replace_existing
            )
            return True, None
        except Exception as e:
            return False, str(e)
    
    def remove_job(self, job_id):
        """移除定时任务"""
        try:
            self.scheduler.remove_job(job_id)
            return True
        except:
            return False
    
    def register_jobs(self, execute_func):
        """注册所有已保存的任务"""
        jobs = load_jobs()
        for job_id, job_info in jobs.items():
            if job_info.get('enabled', False):
                from app.config import SCRIPTS_DIR
                script_path = f"{SCRIPTS_DIR}/{job_info['script']}"
                
                try:
                    self.add_job(
                        job_id,
                        execute_func,
                        job_info['cron'],
                        args=[
                            script_path,
                            job_info.get('args', ''),
                            job_info.get('email_on_success', False),
                            job_info.get('email_on_failure', False)
                        ]
                    )
                except Exception as e:
                    print(f"注册任务失败 {job_id}: {e}")
    
    def get_job(self, job_id):
        """获取任务"""
        try:
            return self.scheduler.get_job(job_id)
        except:
            return None
    
    def list_jobs(self):
        """列出所有任务"""
        return self.scheduler.get_jobs()
