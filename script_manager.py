from flask import Flask, render_template, request, jsonify
import os
import subprocess
import json
import datetime
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import threading
import time

app = Flask(__name__)

# 配置
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
EMAIL_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_settings.json")

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

# 加载邮件设置
def load_email_settings():
    if os.path.exists(EMAIL_SETTINGS_FILE):
        try:
            with open(EMAIL_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

# 保存邮件设置
def save_email_settings(settings):
    with open(EMAIL_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# 发送邮件
def send_email(subject, content, script_name, status, log_content="", log_file_path=""):
    settings = load_email_settings()
    
    if not settings.get('smtp') or not settings.get('from') or not settings.get('to'):
        print("邮件设置不完整，跳过发送")
        return False
    
    try:
        # 截断日志内容，只取前面部分
        truncated_log = ""
        if log_content:
            # 按行分割，只取前50行
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
                    args=[
                        script_path, 
                        job_info.get('args', ''),
                        job_info.get('email_on_success', False),
                        job_info.get('email_on_failure', False)
                    ],
                    replace_existing=True
                )
            except Exception as e:
                print(f"注册任务失败 {job_id}: {e}")

# 执行脚本
def execute_script(script_path, args="", email_on_success=False, email_on_failure=False):
    log_file = os.path.join(LOGS_DIR, f"{os.path.basename(script_path)}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    log_content = ""
    success = False
    
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
                log_content += line
                print(line.strip())
            
            process.wait()
            f.write(f"[{datetime.datetime.now()}] 执行完成，退出码: {process.returncode}\n")
            
            # 判断是否成功
            success = process.returncode == 0
            
            # 发送邮件
            if success and email_on_success:
                send_email("", "", os.path.basename(script_path), "成功", log_content, log_file)
            elif not success and email_on_failure:
                send_email("", "", os.path.basename(script_path), "失败", log_content, log_file)
            
    except Exception as e:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now()}] 执行失败: {e}\n")
            log_content = str(e)
        
        # 发送失败邮件
        if email_on_failure:
            send_email("", "", os.path.basename(script_path), "失败", log_content, log_file)

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
    email_on_success = data.get('email_on_success', False)
    email_on_failure = data.get('email_on_failure', False)
    
    if not script:
        return jsonify({'error': '脚本路径不能为空'}), 400
    
    script_path = os.path.join(SCRIPTS_DIR, script)
    if not os.path.exists(script_path):
        return jsonify({'error': '脚本不存在'}), 404
    
    # 异步执行
    threading.Thread(target=execute_script, args=(script_path, args, email_on_success, email_on_failure)).start()
    
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
    
    email_on_success = data.get('email_on_success', False)
    email_on_failure = data.get('email_on_failure', False)
    
    jobs[job_id] = {
        'script': script,
        'cron': cron,
        'enabled': enabled,
        'args': args,
        'email_on_success': email_on_success,
        'email_on_failure': email_on_failure,
        'created_at': datetime.datetime.now().isoformat()
    }
    
    if enabled:
        try:
            scheduler.add_job(
                execute_script,
                CronTrigger.from_crontab(cron),
                id=job_id,
                args=[script_path, args, email_on_success, email_on_failure],
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
    
    # 获取邮件设置
    email_on_success = data.get('email_on_success', jobs.get(job_id, {}).get('email_on_success', False))
    email_on_failure = data.get('email_on_failure', jobs.get(job_id, {}).get('email_on_failure', False))
    
    # 更新任务
    jobs[job_id] = {
        'script': script,
        'cron': cron,
        'enabled': enabled,
        'args': args,
        'email_on_success': email_on_success,
        'email_on_failure': email_on_failure,
        'updated_at': datetime.datetime.now().isoformat()
    }
    
    # 添加新任务
    if enabled:
        try:
            scheduler.add_job(
                execute_script,
                CronTrigger.from_crontab(cron),
                id=job_id,
                args=[script_path, args, email_on_success, email_on_failure],
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

# 获取邮件设置
@app.route('/api/email/settings')
def api_get_email_settings():
    settings = load_email_settings()
    # 不返回密码
    safe_settings = {k: v for k, v in settings.items() if k != 'password'}
    safe_settings['password'] = '***' if settings.get('password') else ''
    return jsonify(safe_settings)

# 保存邮件设置
@app.route('/api/email/settings', methods=['POST'])
def api_save_email_settings():
    data = request.json
    
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
    return jsonify({'message': '邮件设置保存成功'})

# 测试邮件发送
@app.route('/api/email/test', methods=['POST'])
def api_test_email():
    try:
        result = send_email("测试邮件", "这是一封测试邮件", "test_script", "测试")
        if result:
            return jsonify({'message': '测试邮件发送成功'})
        else:
            return jsonify({'error': '测试邮件发送失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
