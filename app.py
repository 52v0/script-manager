"""
Script Manager - Web 脚本管理器
重构后的主程序入口
"""
from flask import Flask
from app.config import init_directories, FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from app.services.scheduler_service import SchedulerService
from app.services.execution_service import execute_script

# 初始化 Flask 应用
def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    
    # 初始化目录
    init_directories()
    
    # 注册蓝图
    from app.routes.main import main_bp
    from app.routes.scripts import scripts_bp
    from app.routes.jobs import jobs_bp
    from app.routes.logs import logs_bp
    from app.routes.email import email_bp
    from app.routes.queue import queue_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(scripts_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(queue_bp)
    
    # 初始化调度器
    scheduler_service = SchedulerService.get_instance()
    scheduler_service.register_jobs(execute_script)
    
    return app


# 创建应用实例
app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("Script Manager - Web 脚本管理器")
    print("=" * 60)
    print(f"访问地址: http://{FLASK_HOST}:{FLASK_PORT}")
    print("=" * 60)
    
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
