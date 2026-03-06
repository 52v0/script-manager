"""
执行队列路由 - 管理执行队列、停止、重新执行等功能
"""
from flask import request, jsonify
from app.routes import queue_bp
from app.services.execution_service import execution_queue


@queue_bp.route('/api/queue/tasks', methods=['GET'])
def api_list_tasks():
    """获取所有任务列表"""
    status = request.args.get('status')  # 可选：按状态筛选
    return jsonify(execution_queue.list_tasks(status))


@queue_bp.route('/api/queue/status', methods=['GET'])
def api_queue_status():
    """获取队列状态"""
    return jsonify(execution_queue.get_queue_status())


@queue_bp.route('/api/queue/task/<task_id>', methods=['GET'])
def api_get_task(task_id):
    """获取单个任务详情"""
    task = execution_queue.get_task(task_id)
    if task:
        return jsonify(task)
    return jsonify({'error': '任务不存在'}), 404


@queue_bp.route('/api/queue/stop/<task_id>', methods=['POST'])
def api_stop_task(task_id):
    """停止正在执行的任务"""
    success, message = execution_queue.stop_task(task_id)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400


@queue_bp.route('/api/queue/restart/<task_id>', methods=['POST'])
def api_restart_task(task_id):
    """重新执行任务"""
    success, result = execution_queue.restart_task(task_id)
    
    if success:
        return jsonify({
            'message': '任务已重新提交',
            'new_task_id': result
        })
    else:
        return jsonify({'error': result}), 400


@queue_bp.route('/api/queue/running', methods=['GET'])
def api_get_running_tasks():
    """获取正在运行的任务"""
    return jsonify(execution_queue.get_running_tasks())
