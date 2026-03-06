"""
文件管理工具
"""
import json
import os
from app.config import JOBS_FILE, EMAIL_SETTINGS_FILE, SCRIPT_METADATA_FILE


def load_json_file(file_path, default=None):
    """加载 JSON 文件"""
    if default is None:
        default = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default


def save_json_file(file_path, data):
    """保存 JSON 文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_jobs():
    """加载任务配置"""
    return load_json_file(JOBS_FILE)


def save_jobs(jobs):
    """保存任务配置"""
    save_json_file(JOBS_FILE, jobs)


def load_email_settings():
    """加载邮件设置"""
    return load_json_file(EMAIL_SETTINGS_FILE)


def save_email_settings(settings):
    """保存邮件设置"""
    save_json_file(EMAIL_SETTINGS_FILE, settings)


def load_script_metadata():
    """加载脚本元数据"""
    return load_json_file(SCRIPT_METADATA_FILE)


def save_script_metadata(metadata):
    """保存脚本元数据"""
    save_json_file(SCRIPT_METADATA_FILE, metadata)


def list_log_files(logs_dir):
    """列出日志文件"""
    logs = []
    if os.path.exists(logs_dir):
        for file in os.listdir(logs_dir):
            if file.endswith('.log'):
                file_path = os.path.join(logs_dir, file)
                logs.append({
                    'name': file,
                    'size': os.path.getsize(file_path),
                    'mtime': os.path.getmtime(file_path)
                })
    logs.sort(key=lambda x: x['mtime'], reverse=True)
    return logs


def read_log_file(file_path):
    """读取日志文件内容"""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return str(e)


def delete_file(file_path):
    """删除文件"""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except:
            return False
    return False
