"""
Script Manager - Web 脚本管理器
重构后的主程序入口
"""
from flask import Flask, redirect
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
    from app.routes.webmcp import webmcp_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(scripts_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(webmcp_bp)
    
    # 初始化调度器
    scheduler_service = SchedulerService.get_instance()
    scheduler_service.register_jobs(execute_script)
    
    # 注册API文档路由
    register_api_docs(app)
    
    return app


def register_api_docs(app):
    """注册API文档路由 - 使用Swagger UI静态页面"""
    from flask import render_template_string
    
    # Swagger UI HTML模板 - 使用本地资源
    SWAGGER_UI_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>脚本管理器 API 文档</title>
    <link rel="stylesheet" type="text/css" href="/static/swagger-ui/swagger-ui.css" />
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin: 0; background: #fafafa; }
        .topbar { display: none; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="/static/swagger-ui/swagger-ui-bundle.js"></script>
    <script src="/static/swagger-ui/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            window.ui = SwaggerUIBundle({
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 1,
                displayRequestDuration: true,
                docExpansion: 'list',
                filter: true,
                showExtensions: true,
                showCommonExtensions: true,
                tryItOutEnabled: true
            });
        };
    </script>
</body>
</html>
    '''
    
    # 将APIFlask的路由注册到主应用
    @app.route('/api/docs/')
    def api_docs():
        """API文档页面"""
        return redirect('/api/docs/index.html')
    
    @app.route('/api/docs/index.html')
    def api_docs_index():
        """API文档首页"""
        return render_template_string(SWAGGER_UI_HTML)
    
    @app.route('/openapi.json')
    def openapi_spec():
        """OpenAPI规范"""
        from apiflask import APIFlask, Schema
        from apiflask.fields import String, Integer, Boolean, DateTime, List
        from app.models.script import Script
        from app.utils.file_manager import load_jobs
        from app.services.execution_service import execution_queue
        
        # 创建APIFlask实例用于生成spec
        api_app = APIFlask(
            __name__,
            title='脚本管理器 API',
            version='2.0.0'
        )
        
        # 定义 Schemas
        class ScriptSchema(Schema):
            name = String(required=True, metadata={'description': '脚本名称'})
            path = String(metadata={'description': '脚本路径'})
            size = Integer(metadata={'description': '文件大小(字节)'})
            mtime = DateTime(metadata={'description': '修改时间'})
            description = String(metadata={'description': '脚本描述'})
        
        class TaskSchema(Schema):
            id = String(metadata={'description': '任务ID'})
            script_name = String(metadata={'description': '脚本名称'})
            script_path = String(metadata={'description': '脚本路径'})
            args = String(metadata={'description': '脚本参数'})
            status = String(metadata={'description': '任务状态'})
            log_file = String(metadata={'description': '日志文件路径'})
            start_time = DateTime(metadata={'description': '开始时间'})
            end_time = DateTime(metadata={'description': '结束时间'})
            return_code = Integer(metadata={'description': '返回码'})
        
        class JobSchema(Schema):
            id = String(metadata={'description': '任务ID'})
            script = String(metadata={'description': '脚本名称'})
            cron = String(metadata={'description': 'Cron表达式'})
            enabled = Boolean(metadata={'description': '是否启用'})
            args = String(metadata={'description': '脚本参数'})
            email_on_success = Boolean(metadata={'description': '成功时发送邮件'})
            email_on_failure = Boolean(metadata={'description': '失败时发送邮件'})
        
        class QueueStatusSchema(Schema):
            pending = Integer(metadata={'description': '等待中任务数'})
            running = Integer(metadata={'description': '运行中任务数'})
            completed = Integer(metadata={'description': '已完成任务数'})
            total = Integer(metadata={'description': '总任务数'})
        
        # 定义更多Schemas
        class ExecuteRequestSchema(Schema):
            script = String(required=True, metadata={'description': '脚本路径'})
            args = String(metadata={'description': '脚本参数'})
            email_on_success = Boolean(metadata={'description': '成功时发送邮件'})
            email_on_failure = Boolean(metadata={'description': '失败时发送邮件'})
        
        class ExecuteResponseSchema(Schema):
            message = String(metadata={'description': '操作信息'})
            task_id = String(metadata={'description': '任务ID'})
        
        class UploadResponseSchema(Schema):
            message = String(metadata={'description': '操作信息'})
            script = ScriptSchema()
        
        class DeleteResponseSchema(Schema):
            message = String(metadata={'description': '操作信息'})
        
        class ErrorResponseSchema(Schema):
            error = String(metadata={'description': '错误信息'})
        
        class DescriptionResponseSchema(Schema):
            description = String(metadata={'description': '脚本描述'})
        
        class ViewScriptResponseSchema(Schema):
            content = String(metadata={'description': '脚本内容'})
        
        class BatchDeleteRequestSchema(Schema):
            scripts = List(String(), metadata={'description': '脚本名称列表'})
        
        class BatchDeleteResponseSchema(Schema):
            message = String(metadata={'description': '操作信息'})
        
        class TaskDetailSchema(Schema):
            id = String(metadata={'description': '任务ID'})
            script_name = String(metadata={'description': '脚本名称'})
            script_path = String(metadata={'description': '脚本路径'})
            args = String(metadata={'description': '脚本参数'})
            status = String(metadata={'description': '任务状态'})
            log_file = String(metadata={'description': '日志文件路径'})
            start_time = DateTime(metadata={'description': '开始时间'})
            end_time = DateTime(metadata={'description': '结束时间'})
            return_code = Integer(metadata={'description': '返回码'})
        
        class StopTaskResponseSchema(Schema):
            message = String(metadata={'description': '操作信息'})
        
        class RestartTaskResponseSchema(Schema):
            message = String(metadata={'description': '操作信息'})
            new_task_id = String(metadata={'description': '新任务ID'})
        
        class AddJobRequestSchema(Schema):
            id = String(required=True, metadata={'description': '任务ID'})
            script = String(required=True, metadata={'description': '脚本名称'})
            cron = String(required=True, metadata={'description': 'Cron表达式'})
            enabled = Boolean(metadata={'description': '是否启用'})
            args = String(metadata={'description': '脚本参数'})
            email_on_success = Boolean(metadata={'description': '成功时发送邮件'})
            email_on_failure = Boolean(metadata={'description': '失败时发送邮件'})
        
        class DeleteJobRequestSchema(Schema):
            id = String(required=True, metadata={'description': '任务ID'})
        
        class UpdateJobRequestSchema(Schema):
            id = String(required=True, metadata={'description': '任务ID'})
            script = String(required=True, metadata={'description': '脚本名称'})
            cron = String(required=True, metadata={'description': 'Cron表达式'})
            enabled = Boolean(metadata={'description': '是否启用'})
            args = String(metadata={'description': '脚本参数'})
            email_on_success = Boolean(metadata={'description': '成功时发送邮件'})
            email_on_failure = Boolean(metadata={'description': '失败时发送邮件'})
        
        class BatchDeleteJobsRequestSchema(Schema):
            jobs = List(String(), metadata={'description': '任务ID列表'})
        
        class BatchEnableJobsRequestSchema(Schema):
            jobs = List(String(), metadata={'description': '任务ID列表'})
            enabled = Boolean(required=True, metadata={'description': '是否启用'})
        
        # API路由 - 脚本管理
        @api_app.get('/api/scripts')
        @api_app.output(ScriptSchema(many=True))
        def get_scripts():
            """获取脚本列表"""
            return Script.list_all()
        
        @api_app.post('/api/execute')
        @api_app.input(ExecuteRequestSchema)
        @api_app.output(ExecuteResponseSchema)
        def execute_script():
            """执行脚本"""
            return {"message": "脚本已加入执行队列", "task_id": "test-task-id"}
        
        @api_app.post('/api/script/upload')
        @api_app.output(UploadResponseSchema)
        def upload_script():
            """上传脚本文件"""
            return {"message": "脚本上传成功", "script": {"name": "test.py", "path": "scripts/test.py", "size": 100, "mtime": "2026-03-17T00:00:00", "description": "测试脚本"}}
        
        @api_app.post('/api/script/delete/<script_name>')
        @api_app.output(DeleteResponseSchema)
        def delete_script(script_name):
            """删除脚本"""
            return {"message": "脚本删除成功"}
        
        @api_app.get('/api/script/description/<script_name>')
        @api_app.output(DescriptionResponseSchema)
        def get_script_description(script_name):
            """获取脚本描述"""
            return {"description": "测试脚本描述"}
        
        @api_app.post('/api/script/description/<script_name>')
        @api_app.input({"description": String()})
        @api_app.output(DeleteResponseSchema)
        def update_script_description(script_name):
            """更新脚本描述"""
            return {"message": "脚本简介更新成功"}
        
        @api_app.get('/api/script/view/<script_name>')
        @api_app.output(ViewScriptResponseSchema)
        def view_script(script_name):
            """查看脚本内容"""
            return {"content": "print('Hello World')"}
        
        @api_app.post('/api/scripts/batch-delete')
        @api_app.input(BatchDeleteRequestSchema)
        @api_app.output(BatchDeleteResponseSchema)
        def batch_delete_scripts():
            """批量删除脚本"""
            return {"message": "成功删除 1 个脚本"}
        
        # API路由 - 队列管理
        @api_app.get('/api/queue/tasks')
        @api_app.output(TaskSchema(many=True))
        def get_tasks():
            """获取任务列表"""
            return execution_queue.list_tasks()
        
        @api_app.get('/api/queue/status')
        @api_app.output(QueueStatusSchema)
        def get_queue_status():
            """获取队列状态"""
            return execution_queue.get_queue_status()
        
        @api_app.get('/api/queue/task/<task_id>')
        @api_app.output(TaskDetailSchema)
        def get_task(task_id):
            """获取单个任务详情"""
            return {"id": task_id, "script_name": "test.py", "script_path": "scripts/test.py", "args": "", "status": "completed", "log_file": "logs/test.log", "start_time": "2026-03-17T00:00:00", "end_time": "2026-03-17T00:00:01", "return_code": 0}
        
        @api_app.post('/api/queue/stop/<task_id>')
        @api_app.output(StopTaskResponseSchema)
        def stop_task(task_id):
            """停止正在执行的任务"""
            return {"message": "任务已停止"}
        
        @api_app.post('/api/queue/restart/<task_id>')
        @api_app.output(RestartTaskResponseSchema)
        def restart_task(task_id):
            """重新执行任务"""
            return {"message": "任务已重新提交", "new_task_id": "new-task-id"}
        
        @api_app.get('/api/queue/running')
        @api_app.output(TaskSchema(many=True))
        def get_running_tasks():
            """获取正在运行的任务"""
            return execution_queue.get_running_tasks()
        
        # API路由 - 定时任务
        @api_app.get('/api/jobs')
        @api_app.output(JobSchema(many=True))
        def get_jobs():
            """获取定时任务列表"""
            jobs = load_jobs()
            return [dict({'id': k}, **v) for k, v in jobs.items()]
        
        @api_app.post('/api/job/add')
        @api_app.input(AddJobRequestSchema)
        @api_app.output(DeleteResponseSchema)
        def add_job():
            """添加定时任务"""
            return {"message": "任务添加成功"}
        
        @api_app.post('/api/job/delete')
        @api_app.input(DeleteJobRequestSchema)
        @api_app.output(DeleteResponseSchema)
        def delete_job():
            """删除定时任务"""
            return {"message": "任务删除成功"}
        
        @api_app.post('/api/job/update')
        @api_app.input(UpdateJobRequestSchema)
        @api_app.output(DeleteResponseSchema)
        def update_job():
            """更新定时任务"""
            return {"message": "任务更新成功"}
        
        @api_app.post('/api/jobs/batch-delete')
        @api_app.input(BatchDeleteJobsRequestSchema)
        @api_app.output(BatchDeleteResponseSchema)
        def batch_delete_jobs():
            """批量删除定时任务"""
            return {"message": "成功删除 1 个任务"}
        
        @api_app.post('/api/jobs/batch-enable')
        @api_app.input(BatchEnableJobsRequestSchema)
        @api_app.output(BatchDeleteResponseSchema)
        def batch_enable_jobs():
            """批量启用/禁用定时任务"""
            return {"message": "成功更新 1 个任务"}
        
        return api_app.spec


# 创建应用实例
app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("Script Manager - Web 脚本管理器")
    print("=" * 60)
    print(f"访问地址: http://{FLASK_HOST}:{FLASK_PORT}")
    print("=" * 60)
    
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
