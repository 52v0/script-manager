"""
主路由
"""
from flask import render_template
from app.routes import main_bp
from app.models.script import Script
from app.utils.file_manager import load_jobs


@main_bp.route('/')
def index():
    """主页"""
    scripts = Script.list_all()
    jobs = load_jobs()
    return render_template('index.html', scripts=scripts, jobs=jobs)


@main_bp.route('/api_doc.html')
def api_doc():
    """API文档页面"""
    return render_template('api_doc.html')
