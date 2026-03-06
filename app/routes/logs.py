"""
日志路由
"""
from flask import request, jsonify
from app.routes import logs_bp
from app.config import LOGS_DIR
from app.utils.file_manager import list_log_files, read_log_file, delete_file


@logs_bp.route('/api/logs', methods=['GET'])
def api_logs():
    """获取日志列表"""
    return jsonify(list_log_files(LOGS_DIR))


@logs_bp.route('/api/logs/<filename>', methods=['GET'])
def api_log_content(filename):
    """获取日志内容"""
    import os
    log_path = os.path.join(LOGS_DIR, filename)
    content = read_log_file(log_path)
    
    if content is None:
        return jsonify({'error': '日志不存在'}), 404
    
    return jsonify({'content': content})


@logs_bp.route('/api/logs/delete/<filename>', methods=['POST'])
def api_delete_log(filename):
    """删除单个日志"""
    import os
    log_path = os.path.join(LOGS_DIR, filename)
    
    if delete_file(log_path):
        return jsonify({'message': '日志删除成功'})
    else:
        return jsonify({'error': '日志不存在或删除失败'}), 404


@logs_bp.route('/api/logs/delete', methods=['POST'])
def api_delete_logs():
    """批量删除日志"""
    data = request.json
    filenames = data.get('filenames', [])
    
    if not filenames:
        return jsonify({'error': '请提供要删除的日志文件列表'}), 400
    
    import os
    deleted = []
    failed = []
    
    for filename in filenames:
        log_path = os.path.join(LOGS_DIR, filename)
        if delete_file(log_path):
            deleted.append(filename)
        else:
            failed.append({'filename': filename, 'error': '文件不存在或删除失败'})
    
    return jsonify({
        'message': f'成功删除 {len(deleted)} 个日志文件',
        'deleted': deleted,
        'failed': failed
    })
