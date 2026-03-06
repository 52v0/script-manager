"""
邮件路由
"""
from flask import request, jsonify
from app.routes import email_bp
from app.services.email_service import EmailService


@email_bp.route('/api/email/settings', methods=['GET'])
def api_get_email_settings():
    """获取邮件设置"""
    return jsonify(EmailService.get_safe_settings())


@email_bp.route('/api/email/settings', methods=['POST'])
def api_save_email_settings():
    """保存邮件设置"""
    data = request.json
    
    if EmailService.save_settings(data):
        return jsonify({'message': '邮件设置保存成功'})
    else:
        return jsonify({'error': '保存失败'}), 500


@email_bp.route('/api/email/test', methods=['POST'])
def api_test_email():
    """发送测试邮件"""
    try:
        result = EmailService.test_email()
        if result:
            return jsonify({'message': '测试邮件发送成功'})
        else:
            return jsonify({'error': '测试邮件发送失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
