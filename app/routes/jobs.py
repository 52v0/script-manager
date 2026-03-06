"""
任务路由
"""
from flask import request, jsonify
from app.routes import jobs_bp
from app.models.job import Job
from app.services.scheduler_service import SchedulerService
from app.services.execution_service import execute_script
from app.utils.file_manager import load_jobs, save_jobs


@jobs_bp.route('/api/jobs', methods=['GET'])
def api_jobs():
    """获取任务列表"""
    return jsonify(load_jobs())


@jobs_bp.route('/api/job/add', methods=['POST'])
def api_add_job():
    """添加定时任务"""
    data = request.json
    job_id = data.get('id')
    script = data.get('script')
    cron = data.get('cron')
    enabled = data.get('enabled', True)
    args = data.get('args', '')
    
    # 创建任务对象
    job = Job(
        job_id=job_id,
        script=script,
        cron=cron,
        enabled=enabled,
        args=args,
        email_on_success=data.get('email_on_success', False),
        email_on_failure=data.get('email_on_failure', False)
    )
    
    # 验证
    valid, error = job.validate()
    if not valid:
        return jsonify({'error': error}), 400
    
    # 保存任务
    jobs = load_jobs()
    jobs[job_id] = job.to_dict()
    
    # 添加到调度器
    if enabled:
        scheduler = SchedulerService.get_instance()
        success, error = scheduler.add_job(
            job_id,
            execute_script,
            cron,
            args=[job.script_path, args, job.email_on_success, job.email_on_failure]
        )
        if not success:
            return jsonify({'error': f'Cron表达式无效: {error}'}), 400
    
    save_jobs(jobs)
    return jsonify({'message': '任务添加成功'})


@jobs_bp.route('/api/job/delete', methods=['POST'])
def api_delete_job():
    """删除定时任务"""
    data = request.json
    job_id = data.get('id')
    
    if not job_id:
        return jsonify({'error': '任务ID不能为空'}), 400
    
    jobs = load_jobs()
    
    if job_id in jobs:
        # 从调度器移除
        scheduler = SchedulerService.get_instance()
        scheduler.remove_job(job_id)
        
        # 从配置移除
        del jobs[job_id]
        save_jobs(jobs)
        
        return jsonify({'message': '任务删除成功'})
    else:
        return jsonify({'error': '任务不存在'}), 404


@jobs_bp.route('/api/job/update', methods=['POST'])
def api_update_job():
    """更新定时任务"""
    data = request.json
    job_id = data.get('id')
    
    if not job_id:
        return jsonify({'error': '任务ID不能为空'}), 400
    
    jobs = load_jobs()
    
    if job_id not in jobs:
        return jsonify({'error': '任务不存在'}), 404
    
    script = data.get('script')
    cron = data.get('cron')
    enabled = data.get('enabled', True)
    args = data.get('args', '')
    
    # 创建任务对象
    job = Job(
        job_id=job_id,
        script=script,
        cron=cron,
        enabled=enabled,
        args=args,
        email_on_success=data.get('email_on_success', jobs.get(job_id, {}).get('email_on_success', False)),
        email_on_failure=data.get('email_on_failure', jobs.get(job_id, {}).get('email_on_failure', False))
    )
    
    # 验证
    valid, error = job.validate()
    if not valid:
        return jsonify({'error': error}), 400
    
    # 从调度器移除旧任务
    scheduler = SchedulerService.get_instance()
    scheduler.remove_job(job_id)
    
    # 添加新任务
    if enabled:
        success, error = scheduler.add_job(
            job_id,
            execute_script,
            cron,
            args=[job.script_path, args, job.email_on_success, job.email_on_failure]
        )
        if not success:
            return jsonify({'error': f'Cron表达式无效: {error}'}), 400
    
    # 保存
    jobs[job_id] = job.to_dict()
    save_jobs(jobs)
    
    return jsonify({'message': '任务更新成功'})
