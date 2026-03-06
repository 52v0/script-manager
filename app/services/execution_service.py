"""
执行队列服务
管理脚本执行的队列、停止、重新执行等功能
"""
import subprocess
import sys
import datetime
import threading
import uuid
from enum import Enum
from app.config import LOGS_DIR, SCRIPTS_DIR
from app.services.email_service import EmailService


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "等待中"
    RUNNING = "运行中"
    COMPLETED = "已完成"
    FAILED = "失败"
    STOPPED = "已停止"


class ExecutionTask:
    """执行任务"""
    
    def __init__(self, script_path, args="", email_on_success=False, email_on_failure=False):
        self.id = str(uuid.uuid4())[:8]  # 生成短ID
        self.script_path = script_path
        self.script_name = script_path.split('/')[-1]
        self.args = args
        self.email_on_success = email_on_success
        self.email_on_failure = email_on_failure
        self.status = ExecutionStatus.PENDING
        self.log_file = None
        self.log_content = ""
        self.process = None
        self.start_time = None
        self.end_time = None
        self.return_code = None
        self.thread = None
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'script_name': self.script_name,
            'script_path': self.script_path,
            'args': self.args,
            'status': self.status.value,
            'log_file': self.log_file,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'return_code': self.return_code
        }


class ExecutionQueue:
    """执行队列管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化"""
        self.tasks = {}  # task_id -> ExecutionTask
        self.queue = []  # 等待队列
        self.lock = threading.Lock()
        self.max_concurrent = 3  # 最大并发数
        self.running_count = 0
    
    def submit(self, script_path, args="", email_on_success=False, email_on_failure=False):
        """提交执行任务"""
        task = ExecutionTask(script_path, args, email_on_success, email_on_failure)
        
        with self.lock:
            self.tasks[task.id] = task
            self.queue.append(task)
        
        # 尝试执行
        self._try_execute()
        
        return task.id
    
    def _try_execute(self):
        """尝试执行队列中的任务"""
        with self.lock:
            # 检查并发限制
            if self.running_count >= self.max_concurrent:
                return
            
            # 获取等待中的任务
            pending_tasks = [t for t in self.queue if t.status == ExecutionStatus.PENDING]
            if not pending_tasks:
                return
            
            # 取第一个任务执行
            task = pending_tasks[0]
            self.running_count += 1
        
        # 在后台线程中执行
        task.thread = threading.Thread(target=self._execute_task, args=(task,))
        task.thread.start()
    
    def _execute_task(self, task):
        """执行单个任务"""
        task.status = ExecutionStatus.RUNNING
        task.start_time = datetime.datetime.now()
        
        # 生成日志文件
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        task.log_file = f"{LOGS_DIR}/{task.script_name}_{timestamp}_{task.id}.log"
        
        success = False
        
        try:
            with open(task.log_file, 'w', encoding='utf-8') as f:
                f.write(f"[{datetime.datetime.now()}] 开始执行: {task.script_path} {task.args}\n")
                f.write(f"[{datetime.datetime.now()}] 任务ID: {task.id}\n")
                f.flush()
                
                # 执行脚本
                python_exe = sys.executable
                command = f'{python_exe} "{task.script_path}" {task.args}'
                
                task.process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # 实时读取输出
                for line in task.process.stdout:
                    f.write(line)
                    f.flush()
                    task.log_content += line
                
                # 等待完成
                task.process.wait()
                task.return_code = task.process.returncode
                task.end_time = datetime.datetime.now()
                
                # 判断结果
                success = task.return_code == 0
                task.status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
                
                f.write(f"[{task.end_time}] 执行完成，退出码: {task.return_code}\n")
                
        except Exception as e:
            task.end_time = datetime.datetime.now()
            task.status = ExecutionStatus.FAILED
            task.return_code = -1
            error_msg = f"[{task.end_time}] 执行失败: {e}\n"
            task.log_content += error_msg
            
            with open(task.log_file, 'a', encoding='utf-8') as f:
                f.write(error_msg)
        
        # 发送邮件通知
        if success and task.email_on_success:
            EmailService.send_email(
                "", "", task.script_name, "成功",
                task.log_content, task.log_file
            )
        elif not success and task.email_on_failure:
            EmailService.send_email(
                "", "", task.script_name, "失败",
                task.log_content, task.log_file
            )
        
        # 更新运行计数并尝试执行下一个
        with self.lock:
            self.running_count -= 1
        
        self._try_execute()
    
    def stop_task(self, task_id):
        """停止任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False, "任务不存在"
        
        if task.status != ExecutionStatus.RUNNING:
            return False, f"任务状态为 {task.status.value}，无法停止"
        
        if task.process:
            try:
                task.process.terminate()
                task.status = ExecutionStatus.STOPPED
                task.end_time = datetime.datetime.now()
                
                # 写入日志
                with open(task.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{task.end_time}] 任务被用户停止\n")
                
                # 更新运行计数
                with self.lock:
                    self.running_count -= 1
                
                # 尝试执行下一个
                self._try_execute()
                
                return True, "任务已停止"
            except Exception as e:
                return False, f"停止失败: {e}"
        
        return False, "任务未在运行"
    
    def restart_task(self, task_id):
        """重新执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False, "任务不存在"
        
        # 提交新任务
        new_task_id = self.submit(
            task.script_path,
            task.args,
            task.email_on_success,
            task.email_on_failure
        )
        
        return True, new_task_id
    
    def get_task(self, task_id):
        """获取任务信息"""
        task = self.tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    def list_tasks(self, status=None):
        """列出任务"""
        tasks = list(self.tasks.values())
        
        # 按时间倒序
        tasks.sort(key=lambda t: t.start_time or datetime.datetime.min, reverse=True)
        
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        
        return [t.to_dict() for t in tasks]
    
    def get_running_tasks(self):
        """获取正在运行的任务"""
        return self.list_tasks(ExecutionStatus.RUNNING.value)
    
    def get_queue_status(self):
        """获取队列状态"""
        with self.lock:
            pending = len([t for t in self.queue if t.status == ExecutionStatus.PENDING])
            running = len([t for t in self.tasks.values() if t.status == ExecutionStatus.RUNNING])
            completed = len([t for t in self.tasks.values() if t.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.STOPPED]])
        
        return {
            'pending': pending,
            'running': running,
            'completed': completed,
            'total': len(self.tasks),
            'max_concurrent': self.max_concurrent
        }


# 全局执行队列实例
execution_queue = ExecutionQueue()


def execute_script(script_path, args="", email_on_success=False, email_on_failure=False):
    """执行脚本的入口函数（供调度器调用）"""
    return execution_queue.submit(script_path, args, email_on_success, email_on_failure)
