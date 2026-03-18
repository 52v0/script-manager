"""
WebMCP 服务器模块
为脚本管理器提供MCP协议支持
"""
import json
import os
from typing import Any, Dict, List, Optional
from app.models.script import Script
from app.services.execution_service import execution_queue
from app.utils.file_manager import load_jobs, save_jobs
from app.services.scheduler_service import SchedulerService


class WebMCPServer:
    """WebMCP服务器 - 提供MCP协议支持"""
    
    def __init__(self):
        self.tools = {}
        self.resources = {}
        self.prompts = {}
        self._register_all()
    
    def _register_all(self):
        """注册所有MCP组件"""
        self._register_tools()
        self._register_resources()
        self._register_prompts()
    
    def _register_tools(self):
        """注册MCP工具"""
        # 脚本管理工具
        self.tools['list_scripts'] = {
            'name': 'list_scripts',
            'description': '获取所有脚本列表',
            'inputSchema': {
                'type': 'object',
                'properties': {}
            },
            'handler': self._handle_list_scripts
        }
        
        self.tools['get_script'] = {
            'name': 'get_script',
            'description': '获取指定脚本的详细信息',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': '脚本名称'
                    }
                },
                'required': ['name']
            },
            'handler': self._handle_get_script
        }
        
        self.tools['execute_script'] = {
            'name': 'execute_script',
            'description': '执行指定脚本',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': '脚本名称'
                    },
                    'args': {
                        'type': 'string',
                        'description': '脚本参数（可选）'
                    }
                },
                'required': ['name']
            },
            'handler': self._handle_execute_script
        }
        
        self.tools['create_script'] = {
            'name': 'create_script',
            'description': '创建新脚本',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': '脚本名称'
                    },
                    'content': {
                        'type': 'string',
                        'description': '脚本内容'
                    },
                    'description': {
                        'type': 'string',
                        'description': '脚本描述（可选）'
                    }
                },
                'required': ['name', 'content']
            },
            'handler': self._handle_create_script
        }
        
        self.tools['delete_script'] = {
            'name': 'delete_script',
            'description': '删除指定脚本',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': '脚本名称'
                    }
                },
                'required': ['name']
            },
            'handler': self._handle_delete_script
        }
        
        # 任务队列工具
        self.tools['list_tasks'] = {
            'name': 'list_tasks',
            'description': '获取任务队列中的所有任务',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'description': '任务状态筛选（可选）：pending, running, completed, failed'
                    }
                }
            },
            'handler': self._handle_list_tasks
        }
        
        self.tools['get_task'] = {
            'name': 'get_task',
            'description': '获取指定任务的详细信息',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'task_id': {
                        'type': 'string',
                        'description': '任务ID'
                    }
                },
                'required': ['task_id']
            },
            'handler': self._handle_get_task
        }
        
        self.tools['stop_task'] = {
            'name': 'stop_task',
            'description': '停止正在执行的任务',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'task_id': {
                        'type': 'string',
                        'description': '任务ID'
                    }
                },
                'required': ['task_id']
            },
            'handler': self._handle_stop_task
        }
        
        self.tools['get_queue_status'] = {
            'name': 'get_queue_status',
            'description': '获取任务队列状态统计',
            'inputSchema': {
                'type': 'object',
                'properties': {}
            },
            'handler': self._handle_get_queue_status
        }
        
        # 定时任务工具
        self.tools['list_jobs'] = {
            'name': 'list_jobs',
            'description': '获取所有定时任务列表',
            'inputSchema': {
                'type': 'object',
                'properties': {}
            },
            'handler': self._handle_list_jobs
        }
        
        self.tools['add_job'] = {
            'name': 'add_job',
            'description': '添加定时任务',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'id': {
                        'type': 'string',
                        'description': '任务ID'
                    },
                    'script': {
                        'type': 'string',
                        'description': '脚本名称'
                    },
                    'cron': {
                        'type': 'string',
                        'description': 'Cron表达式，如 "0 0 * * *"'
                    },
                    'enabled': {
                        'type': 'boolean',
                        'description': '是否启用（默认true）'
                    },
                    'args': {
                        'type': 'string',
                        'description': '脚本参数（可选）'
                    }
                },
                'required': ['id', 'script', 'cron']
            },
            'handler': self._handle_add_job
        }
        
        self.tools['delete_job'] = {
            'name': 'delete_job',
            'description': '删除定时任务',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'id': {
                        'type': 'string',
                        'description': '任务ID'
                    }
                },
                'required': ['id']
            },
            'handler': self._handle_delete_job
        }
        
        self.tools['toggle_job'] = {
            'name': 'toggle_job',
            'description': '启用/禁用定时任务',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'id': {
                        'type': 'string',
                        'description': '任务ID'
                    },
                    'enabled': {
                        'type': 'boolean',
                        'description': '是否启用'
                    }
                },
                'required': ['id', 'enabled']
            },
            'handler': self._handle_toggle_job
        }
    
    def _register_resources(self):
        """注册MCP资源"""
        self.resources['scripts'] = {
            'uri': 'scripts://list',
            'name': '脚本列表',
            'description': '获取所有可用脚本的列表',
            'handler': self._handle_resource_scripts
        }
        
        self.resources['tasks'] = {
            'uri': 'tasks://list',
            'name': '任务列表',
            'description': '获取任务队列中的所有任务',
            'handler': self._handle_resource_tasks
        }
        
        self.resources['jobs'] = {
            'uri': 'jobs://list',
            'name': '定时任务列表',
            'description': '获取所有定时任务',
            'handler': self._handle_resource_jobs
        }
    
    def _register_prompts(self):
        """注册MCP提示词模板"""
        self.prompts['create_script'] = {
            'name': 'create_script',
            'description': '创建新脚本的提示词模板',
            'arguments': [
                {
                    'name': 'purpose',
                    'description': '脚本的用途描述',
                    'required': True
                }
            ],
            'handler': self._handle_prompt_create_script
        }
        
        self.prompts['debug_task'] = {
            'name': 'debug_task',
            'description': '调试失败任务的提示词模板',
            'arguments': [
                {
                    'name': 'task_id',
                    'description': '失败任务的ID',
                    'required': True
                }
            ],
            'handler': self._handle_prompt_debug_task
        }
    
    # ========== 工具处理器 ==========
    
    def _handle_list_scripts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取脚本列表"""
        scripts = Script.list_all()
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'scripts': scripts,
                        'total': len(scripts)
                    }, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    def _handle_get_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取脚本详情"""
        name = params.get('name')
        script = Script.get(name)
        
        if not script:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：脚本 "{name}" 不存在'
                    }
                ],
                'isError': True
            }
        
        try:
            content = script.get_content()
        except:
            content = '无法读取脚本内容'
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'name': script.name,
                        'path': script.path,
                        'size': script.size,
                        'mtime': script.mtime.isoformat() if script.mtime else None,
                        'description': script.description,
                        'content': content
                    }, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    def _handle_execute_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理执行脚本"""
        name = params.get('name')
        args = params.get('args', '')
        
        script = Script.get(name)
        if not script:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：脚本 "{name}" 不存在'
                    }
                ],
                'isError': True
            }
        
        task_id = execution_queue.submit(
            script.path,
            args,
            email_on_success=False,
            email_on_failure=False
        )
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': f'脚本 "{name}" 已加入执行队列\n任务ID: {task_id}'
                }
            ]
        }
    
    def _handle_create_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理创建脚本"""
        name = params.get('name')
        content = params.get('content')
        description = params.get('description', '')
        
        # 确保文件名以.py结尾
        if not name.endswith('.py'):
            name += '.py'
        
        try:
            from app.config import SCRIPTS_DIR
            script_path = os.path.join(SCRIPTS_DIR, name)
            
            # 检查文件是否已存在
            if os.path.exists(script_path):
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': f'错误：脚本 "{name}" 已存在'
                        }
                    ],
                    'isError': True
                }
            
            # 写入文件
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 保存描述
            if description:
                Script.update_description(name, description)
            
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'脚本 "{name}" 创建成功'
                    }
                ]
            }
        except Exception as e:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'创建脚本失败: {str(e)}'
                    }
                ],
                'isError': True
            }
    
    def _handle_delete_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理删除脚本"""
        name = params.get('name')
        
        if Script.delete(name):
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'脚本 "{name}" 删除成功'
                    }
                ]
            }
        else:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：脚本 "{name}" 不存在或删除失败'
                    }
                ],
                'isError': True
            }
    
    def _handle_list_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取任务列表"""
        status = params.get('status')
        tasks = execution_queue.list_tasks(status)
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'tasks': tasks,
                        'total': len(tasks),
                        'filter': status or 'all'
                    }, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    def _handle_get_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取任务详情"""
        task_id = params.get('task_id')
        task = execution_queue.get_task(task_id)
        
        if not task:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：任务 "{task_id}" 不存在'
                    }
                ],
                'isError': True
            }
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(task, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    def _handle_stop_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理停止任务"""
        task_id = params.get('task_id')
        success, message = execution_queue.stop_task(task_id)
        
        if success:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': message
                    }
                ]
            }
        else:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：{message}'
                    }
                ],
                'isError': True
            }
    
    def _handle_get_queue_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取队列状态"""
        status = execution_queue.get_queue_status()
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(status, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    def _handle_list_jobs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取定时任务列表"""
        jobs = load_jobs()
        job_list = [{'id': k, **v} for k, v in jobs.items()]
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'jobs': job_list,
                        'total': len(job_list)
                    }, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    def _handle_add_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理添加定时任务"""
        from app.models.job import Job
        from app.services.execution_service import execute_script
        
        job_id = params.get('id')
        script_name = params.get('script')
        cron = params.get('cron')
        enabled = params.get('enabled', True)
        args = params.get('args', '')
        
        # 验证脚本存在
        script = Script.get(script_name)
        if not script:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：脚本 "{script_name}" 不存在'
                    }
                ],
                'isError': True
            }
        
        # 创建任务对象
        job = Job(
            job_id=job_id,
            script=script_name,
            cron=cron,
            enabled=enabled,
            args=args
        )
        
        # 验证
        valid, error = job.validate()
        if not valid:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'验证失败: {error}'
                    }
                ],
                'isError': True
            }
        
        # 保存任务
        jobs = load_jobs()
        jobs[job_id] = job.to_dict()
        
        # 添加到调度器
        if enabled:
            scheduler = SchedulerService.get_instance()
            success, error = scheduler.add_job(
                job_id,
                execute_script,
                cron,
                args=[job.script_path, args, False, False]
            )
            if not success:
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': f'Cron表达式无效: {error}'
                        }
                    ],
                    'isError': True
                }
        
        save_jobs(jobs)
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': f'定时任务 "{job_id}" 添加成功'
                }
            ]
        }
    
    def _handle_delete_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理删除定时任务"""
        job_id = params.get('id')
        
        jobs = load_jobs()
        
        if job_id not in jobs:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：任务 "{job_id}" 不存在'
                    }
                ],
                'isError': True
            }
        
        # 从调度器移除
        scheduler = SchedulerService.get_instance()
        scheduler.remove_job(job_id)
        
        # 从配置移除
        del jobs[job_id]
        save_jobs(jobs)
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': f'定时任务 "{job_id}" 删除成功'
                }
            ]
        }
    
    def _handle_toggle_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理启用/禁用定时任务"""
        from app.models.job import Job
        from app.services.execution_service import execute_script
        
        job_id = params.get('id')
        enabled = params.get('enabled')
        
        jobs = load_jobs()
        
        if job_id not in jobs:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：任务 "{job_id}" 不存在'
                    }
                ],
                'isError': True
            }
        
        job_data = jobs[job_id]
        job_data['enabled'] = enabled
        
        scheduler = SchedulerService.get_instance()
        scheduler.remove_job(job_id)
        
        if enabled:
            job = Job(
                job_id=job_id,
                script=job_data['script'],
                cron=job_data['cron'],
                enabled=True,
                args=job_data.get('args', '')
            )
            scheduler.add_job(
                job_id,
                execute_script,
                job_data['cron'],
                args=[job.script_path, job_data.get('args', ''), False, False]
            )
        
        save_jobs(jobs)
        
        status = '启用' if enabled else '禁用'
        return {
            'content': [
                {
                    'type': 'text',
                    'text': f'定时任务 "{job_id}" 已{status}'
                }
            ]
        }
    
    # ========== 资源处理器 ==========
    
    def _handle_resource_scripts(self, uri: str) -> Dict[str, Any]:
        """处理脚本列表资源"""
        scripts = Script.list_all()
        return {
            'contents': [
                {
                    'uri': uri,
                    'mimeType': 'application/json',
                    'text': json.dumps(scripts, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    def _handle_resource_tasks(self, uri: str) -> Dict[str, Any]:
        """处理任务列表资源"""
        tasks = execution_queue.list_tasks()
        return {
            'contents': [
                {
                    'uri': uri,
                    'mimeType': 'application/json',
                    'text': json.dumps(tasks, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    def _handle_resource_jobs(self, uri: str) -> Dict[str, Any]:
        """处理定时任务列表资源"""
        jobs = load_jobs()
        job_list = [{'id': k, **v} for k, v in jobs.items()]
        return {
            'contents': [
                {
                    'uri': uri,
                    'mimeType': 'application/json',
                    'text': json.dumps(job_list, indent=2, ensure_ascii=False)
                }
            ]
        }
    
    # ========== 提示词处理器 ==========
    
    def _handle_prompt_create_script(self, arguments: Dict[str, str]) -> Dict[str, Any]:
        """处理创建脚本提示词"""
        purpose = arguments.get('purpose', '')
        
        prompt = f"""请帮我创建一个Python脚本，用于：{purpose}

要求：
1. 使用Python 3语法
2. 添加适当的注释说明
3. 包含错误处理
4. 使用标准库或常见的第三方库

请提供完整的脚本代码。"""
        
        return {
            'description': f'创建用于{purpose}的脚本',
            'messages': [
                {
                    'role': 'user',
                    'content': {
                        'type': 'text',
                        'text': prompt
                    }
                }
            ]
        }
    
    def _handle_prompt_debug_task(self, arguments: Dict[str, str]) -> Dict[str, Any]:
        """处理调试任务提示词"""
        task_id = arguments.get('task_id', '')
        
        # 获取任务信息
        task = execution_queue.get_task(task_id)
        
        if not task:
            return {
                'description': f'调试任务 {task_id}',
                'messages': [
                    {
                        'role': 'user',
                        'content': {
                            'type': 'text',
                            'text': f'任务 {task_id} 不存在，请检查任务ID是否正确。'
                        }
                    }
                ]
            }
        
        # 获取日志内容
        log_content = ''
        if task.get('log_file') and os.path.exists(task['log_file']):
            try:
                with open(task['log_file'], 'r', encoding='utf-8') as f:
                    log_content = f.read()[-2000:]  # 读取最后2000字符
            except:
                log_content = '无法读取日志文件'
        
        prompt = f"""请帮我分析这个失败的脚本执行任务：

任务信息：
- 任务ID: {task_id}
- 脚本: {task.get('script_name', '未知')}
- 状态: {task.get('status', '未知')}
- 返回码: {task.get('return_code', '未知')}
- 开始时间: {task.get('start_time', '未知')}
- 结束时间: {task.get('end_time', '未知')}

日志内容（最后部分）：
```
{log_content}
```

请分析：
1. 失败的可能原因
2. 如何修复问题
3. 预防措施"""
        
        return {
            'description': f'调试失败任务 {task_id}',
            'messages': [
                {
                    'role': 'user',
                    'content': {
                        'type': 'text',
                        'text': prompt
                    }
                }
            ]
        }
    
    # ========== 公共API ==========
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取服务器能力"""
        return {
            'tools': [
                {
                    'name': tool['name'],
                    'description': tool['description'],
                    'inputSchema': tool['inputSchema']
                }
                for tool in self.tools.values()
            ],
            'resources': [
                {
                    'uri': resource['uri'],
                    'name': resource['name'],
                    'description': resource['description']
                }
                for resource in self.resources.values()
            ],
            'prompts': [
                {
                    'name': prompt['name'],
                    'description': prompt['description'],
                    'arguments': prompt.get('arguments', [])
                }
                for prompt in self.prompts.values()
            ]
        }
    
    def call_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if name not in self.tools:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'错误：未知工具 "{name}"'
                    }
                ],
                'isError': True
            }
        
        try:
            return self.tools[name]['handler'](params)
        except Exception as e:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': f'工具执行失败: {str(e)}'
                    }
                ],
                'isError': True
            }
    
    def read_resource(self, uri: str) -> Dict[str, Any]:
        """读取资源"""
        for resource in self.resources.values():
            if resource['uri'] == uri:
                try:
                    return resource['handler'](uri)
                except Exception as e:
                    return {
                        'contents': [
                            {
                                'uri': uri,
                                'mimeType': 'text/plain',
                                'text': f'读取资源失败: {str(e)}'
                            }
                        ]
                    }
        
        return {
            'contents': [
                {
                    'uri': uri,
                    'mimeType': 'text/plain',
                    'text': f'错误：未知资源 "{uri}"'
                }
            ]
        }
    
    def get_prompt(self, name: str, arguments: Dict[str, str]) -> Dict[str, Any]:
        """获取提示词"""
        if name not in self.prompts:
            return {
                'description': f'未知提示词: {name}',
                'messages': [
                    {
                        'role': 'user',
                        'content': {
                            'type': 'text',
                            'text': f'错误：未知提示词 "{name}"'
                        }
                    }
                ]
            }
        
        try:
            return self.prompts[name]['handler'](arguments)
        except Exception as e:
            return {
                'description': f'获取提示词失败',
                'messages': [
                    {
                        'role': 'user',
                        'content': {
                            'type': 'text',
                            'text': f'获取提示词失败: {str(e)}'
                        }
                    }
                ]
            }


# 单例实例
_webmcp_server = None


def get_webmcp_server() -> WebMCPServer:
    """获取WebMCP服务器单例"""
    global _webmcp_server
    if _webmcp_server is None:
        _webmcp_server = WebMCPServer()
    return _webmcp_server
