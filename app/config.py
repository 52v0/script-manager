"""
配置文件
"""
import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 目录配置
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
JOBS_FILE = os.path.join(BASE_DIR, "jobs.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
EMAIL_SETTINGS_FILE = os.path.join(BASE_DIR, "email_settings.json")
SCRIPT_METADATA_FILE = os.path.join(BASE_DIR, "script_metadata.json")

# Flask 配置
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False

# 确保目录存在
def init_directories():
    """初始化必要的目录"""
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
