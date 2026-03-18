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


@jobs_bp.route('/api/jobs/batch-delete', methods=['POST'])
def api_batch_delete_jobs():
    """批量删除定时任务"""
    try:
        data = request.json
        jobs_to_delete = data.get('jobs', [])
        
        if not jobs_to_delete:
            return jsonify({'error': '请选择要删除的任务'}), 400
        
        jobs = load_jobs()
        deleted_count = 0
        
        for job_id in jobs_to_delete:
            if job_id in jobs:
                # 从调度器移除
                scheduler = SchedulerService.get_instance()
                scheduler.remove_job(job_id)
                
                # 从配置移除
                del jobs[job_id]
                deleted_count += 1
        
        save_jobs(jobs)
        return jsonify({'message': f'成功删除 {deleted_count} 个任务'})
    except Exception as e:
        return jsonify({'error': f'删除失败: {e}'}), 500


@jobs_bp.route('/api/jobs/batch-enable', methods=['POST'])
def api_batch_enable_jobs():
    """批量启用/禁用定时任务"""
    try:
        data = request.json
        jobs_to_update = data.get('jobs', [])
        enabled = data.get('enabled', True)
        
        if not jobs_to_update:
            return jsonify({'error': '请选择要更新的任务'}), 400
        
        jobs = load_jobs()
        updated_count = 0
        
        for job_id in jobs_to_update:
            if job_id in jobs:
                job_data = jobs[job_id]
                job_data['enabled'] = enabled
                
                # 从调度器移除旧任务
                scheduler = SchedulerService.get_instance()
                scheduler.remove_job(job_id)
                
                # 添加新任务（如果启用）
                if enabled:
                    job = Job(
                        job_id=job_id,
                        script=job_data['script'],
                        cron=job_data['cron'],
                        enabled=enabled,
                        args=job_data.get('args', ''),
                        email_on_success=job_data.get('email_on_success', False),
                        email_on_failure=job_data.get('email_on_failure', False)
                    )
                    scheduler.add_job(
                        job_id,
                        execute_script,
                        job_data['cron'],
                        args=[job.script_path, job_data.get('args', ''), job_data.get('email_on_success', False), job_data.get('email_on_failure', False)]
                    )
                
                updated_count += 1
        
        save_jobs(jobs)
        return jsonify({'message': f'成功更新 {updated_count} 个任务'})
    except Exception as e:
        return jsonify({'error': f'更新失败: {e}'}), 500
