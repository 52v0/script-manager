"""
邮件服务
"""
import smtplib
import datetime
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from app.utils.file_manager import load_email_settings


class EmailService:
    """邮件服务类"""
    
    @staticmethod
    def send_email(subject, content, script_name, status, log_content="", log_file_path=""):
        """发送邮件通知"""
        settings = load_email_settings()
        
        if not settings.get('smtp') or not settings.get('from') or not settings.get('to'):
            print("邮件设置不完整，跳过发送")
            return False
        
        try:
            # 截断日志内容，只取前面部分
            truncated_log = ""
            if log_content:
                lines = log_content.split('\n')
                truncated_log = '\n'.join(lines[:50])
                if len(lines) > 50:
                    truncated_log += '\n... (日志内容过长，完整日志已作为附件发送)'
            
            # 替换模板变量
            template = settings.get('template', '脚本名称: {script_name}\n执行状态: {status}\n执行时间: {time}\n\n日志内容:\n{log}')
            email_content = template.format(
                script_name=script_name,
                status=status,
                time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                log=truncated_log
            )
            
            # 替换主题变量
            email_subject = settings.get('subject', '脚本执行通知 - {status}').format(status=status)
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = settings['from']
            msg['To'] = settings['to']
            msg['Subject'] = email_subject
            msg.attach(MIMEText(email_content, 'plain', 'utf-8'))
            
            # 添加日志附件
            if log_file_path and os.path.exists(log_file_path):
                with open(log_file_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(log_file_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(log_file_path)}"'
                    msg.attach(part)
            
            # 发送邮件
            if settings.get('ssl', False):
                server = smtplib.SMTP_SSL(settings['smtp'], settings.get('port', 465))
            else:
                server = smtplib.SMTP(settings['smtp'], settings.get('port', 587))
                server.starttls()
            
            server.login(settings['from'], settings['password'])
            server.send_message(msg)
            server.quit()
            
            print(f"邮件发送成功: {email_subject}")
            return True
            
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
    
    @staticmethod
    def test_email():
        """发送测试邮件"""
        return EmailService.send_email(
            "测试邮件", 
            "这是一封测试邮件", 
            "test_script", 
            "测试"
        )
    
    @staticmethod
    def get_safe_settings():
        """获取安全的邮件设置（隐藏密码）"""
        settings = load_email_settings()
        safe_settings = {k: v for k, v in settings.items() if k != 'password'}
        safe_settings['password'] = '***' if settings.get('password') else ''
        return safe_settings
    
    @staticmethod
    def save_settings(data):
        """保存邮件设置"""
        from app.utils.file_manager import load_email_settings, save_email_settings
        
        settings = {
            'smtp': data.get('smtp', ''),
            'port': data.get('port', ''),
            'from': data.get('from', ''),
            'to': data.get('to', ''),
            'subject': data.get('subject', ''),
            'template': data.get('template', ''),
            'ssl': data.get('ssl', False)
        }
        
        # 如果提供了新密码，则更新
        if data.get('password') and data.get('password') != '***':
            settings['password'] = data.get('password')
        else:
            # 保留旧密码
            old_settings = load_email_settings()
            if old_settings.get('password'):
                settings['password'] = old_settings['password']
        
        save_email_settings(settings)
        return True
