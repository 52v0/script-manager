"""
脚本路由 - 包含上传功能
"""
from flask import request, jsonify
from app.routes import scripts_bp
from app.models.script import Script
from app.services.execution_service import execution_queue


@scripts_bp.route('/api/scripts', methods=['GET'])
def api_scripts():
    """获取脚本列表"""
    return jsonify(Script.list_all())


@scripts_bp.route('/api/execute', methods=['POST'])
def api_execute():
    """执行脚本"""
    data = request.json
    script = data.get('script')
    args = data.get('args', '')
    email_on_success = data.get('email_on_success', False)
    email_on_failure = data.get('email_on_failure', False)
    
    if not script:
        return jsonify({'error': '脚本路径不能为空'}), 400
    
    script_obj = Script.get(script)
    if not script_obj:
        return jsonify({'error': '脚本不存在'}), 404
    
    # 提交到执行队列
    task_id = execution_queue.submit(
        script_obj.path,
        args,
        email_on_success,
        email_on_failure
    )
    
    return jsonify({
        'message': '脚本已加入执行队列',
        'task_id': task_id
    })


@scripts_bp.route('/api/script/upload', methods=['POST'])
def api_upload_script():
    """上传脚本文件"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    if not file.filename.endswith('.py'):
        return jsonify({'error': '只允许上传 Python 文件 (.py)'}), 400
    
    try:
        script = Script.save_uploaded(file, file.filename)
        return jsonify({
            'message': '脚本上传成功',
            'script': script.to_dict()
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'上传失败: {e}'}), 500


@scripts_bp.route('/api/script/delete/<script_name>', methods=['POST'])
def api_delete_script(script_name):
    """删除脚本"""
    try:
        if Script.delete(script_name):
            return jsonify({'message': '脚本删除成功'})
        else:
            return jsonify({'error': '脚本不存在'}), 404
    except Exception as e:
        return jsonify({'error': f'删除失败: {e}'}), 500


@scripts_bp.route('/api/script/description/<script_name>', methods=['GET'])
def api_get_script_description(script_name):
    """获取脚本描述"""
    script = Script.get(script_name)
    if script:
        return jsonify({'description': script.description})
    return jsonify({'error': '脚本不存在'}), 404


@scripts_bp.route('/api/script/description/<script_name>', methods=['POST'])
def api_update_script_description(script_name):
    """更新脚本描述"""
    data = request.json
    description = data.get('description', '')
    
    if Script.update_description(script_name, description):
        return jsonify({'message': '脚本简介更新成功'})
    return jsonify({'error': '更新失败'}), 500


@scripts_bp.route('/api/script/view/<script_name>', methods=['GET'])
def api_view_script(script_name):
    """查看脚本内容"""
    try:
        script = Script.get(script_name)
        if not script:
            return jsonify({'error': '脚本不存在'}), 404
        
        content = script.get_content()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': f'读取失败: {e}'}), 500


@scripts_bp.route('/api/scripts/batch-delete', methods=['POST'])
def api_batch_delete_scripts():
    """批量删除脚本"""
    try:
        data = request.json
        scripts = data.get('scripts', [])
        
        if not scripts:
            return jsonify({'error': '请选择要删除的脚本'}), 400
        
        deleted_count = 0
        for script_name in scripts:
            if Script.delete(script_name):
                deleted_count += 1
        
        return jsonify({'message': f'成功删除 {deleted_count} 个脚本'})
    except Exception as e:
        return jsonify({'error': f'删除失败: {e}'}), 500
