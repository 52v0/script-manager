from flask import Flask, render_template, request, jsonify
import os
import subprocess
import json
import datetime
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import threading
import time

app = Flask(__name__)

# 配置
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# 确保目录存在
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# 初始化调度器
scheduler = BackgroundScheduler()
scheduler.start()

# 加载任务
def load_jobs():
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

# 保存任务
def save_jobs(jobs):
    with open(JOBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

# 全局任务字典
jobs = load_jobs()

# 注册任务到调度器
def register_jobs():
    for job_id, job_info in jobs.items():
        if job_info.get('enabled', False):
            try:
                script_path = os.path.join(SCRIPTS_DIR, job_info['script'])
                scheduler.add_job(
                    execute_script,
                    CronTrigger.from_crontab(job_info['cron']),
                    id=job_id,
                    args=[script_path, job_info.get('args', '')],
                    replace_existing=True
                )
            except Exception as e:
                print(f"注册任务失败 {job_id}: {e}")

# 执行脚本
def execute_script(script_path, args=""):
    log_file = os.path.join(LOGS_DIR, f"{os.path.basename(script_path)}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] 开始执行: {script_path} {args}\n")
            
            # 使用sys.executable获取正确的Python解释器路径
            python_exe = sys.executable
            command = f"{python_exe} {script_path} {args}"
            
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            for line in process.stdout:
                f.write(line)
                print(line.strip())
            
            process.wait()
            f.write(f"[{datetime.datetime.now()}] 执行完成，退出码: {process.returncode}\n")
            
    except Exception as e:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] 执行失败: {e}\n")

# 列出脚本
def list_scripts():
    scripts = []
    metadata = load_script_metadata()
    for file in os.listdir(SCRIPTS_DIR):
        file_path = os.path.join(SCRIPTS_DIR, file)
        if os.path.isfile(file_path) and file.endswith('.py'):
            description = metadata.get(file, {}).get('description', '')
            scripts.append({
                'name': file,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'mtime': os.path.getmtime(file_path),
                'description': description
            })
    return scripts

# 主页
@app.route('/')
def index():
    scripts = list_scripts()
    return render_template('index.html', scripts=scripts, jobs=jobs)

# 脚本列表API
@app.route('/api/scripts')
def api_scripts():
    return jsonify(list_scripts())

# 任务列表API
@app.route('/api/jobs')
def api_jobs():
    return jsonify(jobs)

# 执行脚本
@app.route('/api/execute', methods=['POST'])
def api_execute():
    data = request.json
    script = data.get('script')
    args = data.get('args', '')
    
    if not script:
        return jsonify({'error': '脚本路径不能为空'}), 400
    
    script_path = os.path.join(SCRIPTS_DIR, script)
    if not os.path.exists(script_path):
        return jsonify({'error': '脚本不存在'}), 404
    
    # 异步执行
    threading.Thread(target=execute_script, args=(script_path, args)).start()
    
    return jsonify({'message': '脚本开始执行'})

# 添加定时任务
@app.route('/api/job/add', methods=['POST'])
def api_add_job():
    data = request.json
    job_id = data.get('id')
    script = data.get('script')
    cron = data.get('cron')
    enabled = data.get('enabled', True)
    args = data.get('args', '')
    
    if not job_id or not script or not cron:
        return jsonify({'error': '参数不完整'}), 400
    
    script_path = os.path.join(SCRIPTS_DIR, script)
    if not os.path.exists(script_path):
        return jsonify({'error': '脚本不存在'}), 404
    
    jobs[job_id] = {
        'script': script,
        'cron': cron,
        'enabled': enabled,
        'args': args,
        'created_at': datetime.datetime.now().isoformat()
    }
    
    if enabled:
        try:
            scheduler.add_job(
                execute_script,
                CronTrigger.from_crontab(cron),
                id=job_id,
                args=[script_path, args],
                replace_existing=True
            )
        except Exception as e:
            return jsonify({'error': f'Cron表达式无效: {e}'}), 400
    
    save_jobs(jobs)
    return jsonify({'message': '任务添加成功'})

# 删除定时任务
@app.route('/api/job/delete', methods=['POST'])
def api_delete_job():
    data = request.json
    job_id = data.get('id')
    
    if not job_id:
        return jsonify({'error': '任务ID不能为空'}), 400
    
    if job_id in jobs:
        try:
            scheduler.remove_job(job_id)
        except Exception as e:
            print(f"移除任务失败 {job_id}: {e}")
        del jobs[job_id]
        save_jobs(jobs)
        return jsonify({'message': '任务删除成功'})
    else:
        return jsonify({'error': '任务不存在'}), 404

# 更新定时任务
@app.route('/api/job/update', methods=['POST'])
def api_update_job():
    data = request.json
    job_id = data.get('id')
    script = data.get('script')
    cron = data.get('cron')
    enabled = data.get('enabled', True)
    args = data.get('args', '')
    
    if not job_id:
        return jsonify({'error': '任务ID不能为空'}), 400
    
    if job_id not in jobs:
        return jsonify({'error': '任务不存在'}), 404
    
    script_path = os.path.join(SCRIPTS_DIR, script)
    if not os.path.exists(script_path):
        return jsonify({'error': '脚本不存在'}), 404
    
    # 移除旧任务
    if job_id in jobs and jobs[job_id].get('enabled', False):
        try:
            scheduler.remove_job(job_id)
        except:
            pass
    
    # 更新任务
    jobs[job_id] = {
        'script': script,
        'cron': cron,
        'enabled': enabled,
        'args': args,
        'updated_at': datetime.datetime.now().isoformat()
    }
    
    # 添加新任务
    if enabled:
        try:
            scheduler.add_job(
                execute_script,
                CronTrigger.from_crontab(cron),
                id=job_id,
                args=[script_path, args],
                replace_existing=True
            )
        except Exception as e:
            return jsonify({'error': f'Cron表达式无效: {e}'}), 400
    
    save_jobs(jobs)
    return jsonify({'message': '任务更新成功'})

# 查看日志
@app.route('/api/logs')
def api_logs():
    logs = []
    for file in os.listdir(LOGS_DIR):
        if file.endswith('.log'):
            file_path = os.path.join(LOGS_DIR, file)
            logs.append({
                'name': file,
                'size': os.path.getsize(file_path),
                'mtime': os.path.getmtime(file_path)
            })
    logs.sort(key=lambda x: x['mtime'], reverse=True)
    return jsonify(logs)

# 查看日志内容
@app.route('/api/logs/<filename>')
def api_log_content(filename):
    log_path = os.path.join(LOGS_DIR, filename)
    if not os.path.exists(log_path):
        return jsonify({'error': '日志不存在'}), 404
    
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 脚本简介文件路径
SCRIPT_METADATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "script_metadata.json")

# 加载脚本元数据
def load_script_metadata():
    if os.path.exists(SCRIPT_METADATA_FILE):
        try:
            with open(SCRIPT_METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

# 保存脚本元数据
def save_script_metadata(metadata):
    with open(SCRIPT_METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

# 全局脚本元数据
try:
    script_metadata = load_script_metadata()
except:
    script_metadata = {}

# 获取脚本简介
@app.route('/api/script/description/<script_name>')
def api_get_script_description(script_name):
    metadata = load_script_metadata()
    description = metadata.get(script_name, {}).get('description', '')
    return jsonify({'description': description})

# 更新脚本简介
@app.route('/api/script/description/<script_name>', methods=['POST'])
def api_update_script_description(script_name):
    data = request.json
    description = data.get('description', '')
    
    metadata = load_script_metadata()
    if script_name not in metadata:
        metadata[script_name] = {}
    metadata[script_name]['description'] = description
    save_script_metadata(metadata)
    
    return jsonify({'message': '脚本简介更新成功'})

# 删除日志
@app.route('/api/logs/delete/<filename>', methods=['POST'])
def api_delete_log(filename):
    log_path = os.path.join(LOGS_DIR, filename)
    if not os.path.exists(log_path):
        return jsonify({'error': '日志不存在'}), 404
    
    try:
        os.remove(log_path)
        return jsonify({'message': '日志删除成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 批量删除日志
@app.route('/api/logs/delete', methods=['POST'])
def api_delete_logs():
    data = request.json
    filenames = data.get('filenames', [])
    
    if not filenames:
        return jsonify({'error': '请提供要删除的日志文件列表'}), 400
    
    deleted = []
    failed = []
    
    for filename in filenames:
        log_path = os.path.join(LOGS_DIR, filename)
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
                deleted.append(filename)
            except Exception as e:
                failed.append({'filename': filename, 'error': str(e)})
        else:
            failed.append({'filename': filename, 'error': '文件不存在'})
    
    return jsonify({
        'message': f'成功删除 {len(deleted)} 个日志文件',
        'deleted': deleted,
        'failed': failed
    })

# 主函数
if __name__ == '__main__':
    # 注册已存在的任务
    register_jobs()
    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=False)
