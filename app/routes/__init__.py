# Routes module
from flask import Blueprint

# 创建蓝图
scripts_bp = Blueprint('scripts', __name__)
jobs_bp = Blueprint('jobs', __name__)
logs_bp = Blueprint('logs', __name__)
email_bp = Blueprint('email', __name__)
queue_bp = Blueprint('queue', __name__)
main_bp = Blueprint('main', __name__)
