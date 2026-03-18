"""
WebMCP API 路由
提供MCP协议的HTTP接口
"""
from flask import Blueprint, request, jsonify, Response
from app.webmcp_server import get_webmcp_server
import json

webmcp_bp = Blueprint('webmcp', __name__, url_prefix='/mcp')


@webmcp_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'service': 'WebMCP Server',
        'version': '1.0.0'
    })


@webmcp_bp.route('/capabilities', methods=['GET'])
def get_capabilities():
    """获取MCP服务器能力"""
    server = get_webmcp_server()
    return jsonify(server.get_capabilities())


@webmcp_bp.route('/tools/call', methods=['POST'])
def call_tool():
    """调用MCP工具"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': '请求体不能为空'
            }), 400
        
        name = data.get('name')
        params = data.get('params', {})
        
        if not name:
            return jsonify({
                'error': '工具名称不能为空'
            }), 400
        
        server = get_webmcp_server()
        result = server.call_tool(name, params)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'error': f'调用工具失败: {str(e)}'
        }), 500


@webmcp_bp.route('/resources/read', methods=['POST'])
def read_resource():
    """读取MCP资源"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': '请求体不能为空'
            }), 400
        
        uri = data.get('uri')
        
        if not uri:
            return jsonify({
                'error': '资源URI不能为空'
            }), 400
        
        server = get_webmcp_server()
        result = server.read_resource(uri)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'error': f'读取资源失败: {str(e)}'
        }), 500


@webmcp_bp.route('/prompts/get', methods=['POST'])
def get_prompt():
    """获取MCP提示词"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': '请求体不能为空'
            }), 400
        
        name = data.get('name')
        arguments = data.get('arguments', {})
        
        if not name:
            return jsonify({
                'error': '提示词名称不能为空'
            }), 400
        
        server = get_webmcp_server()
        result = server.get_prompt(name, arguments)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'error': f'获取提示词失败: {str(e)}'
        }), 500


@webmcp_bp.route('/sse', methods=['GET'])
def sse_endpoint():
    """SSE端点 - 用于实时通信"""
    def generate():
        server = get_webmcp_server()
        
        # 发送初始连接消息
        yield f'data: {json.dumps({"type": "connected", "message": "WebMCP Server Connected"})}\n\n'
        
        # 这里可以添加心跳或其他实时消息
        # 目前仅保持连接打开
        
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@webmcp_bp.route('/docs', methods=['GET'])
def get_docs():
    """获取WebMCP API文档"""
    docs = {
        'title': 'WebMCP API 文档',
        'version': '1.0.0',
        'description': '脚本管理器的MCP协议接口',
        'endpoints': {
            '/mcp/health': {
                'method': 'GET',
                'description': '健康检查',
                'response': {
                    'status': 'ok',
                    'service': 'WebMCP Server',
                    'version': '1.0.0'
                }
            },
            '/mcp/capabilities': {
                'method': 'GET',
                'description': '获取服务器能力（工具、资源、提示词列表）',
                'response': {
                    'tools': ['...'],
                    'resources': ['...'],
                    'prompts': ['...']
                }
            },
            '/mcp/tools/call': {
                'method': 'POST',
                'description': '调用MCP工具',
                'request': {
                    'name': '工具名称',
                    'params': {'参数名': '参数值'}
                },
                'response': {
                    'content': [{'type': 'text', 'text': '结果'}]
                }
            },
            '/mcp/resources/read': {
                'method': 'POST',
                'description': '读取MCP资源',
                'request': {
                    'uri': '资源URI'
                },
                'response': {
                    'contents': [{'uri': '...', 'mimeType': '...', 'text': '...'}]
                }
            },
            '/mcp/prompts/get': {
                'method': 'POST',
                'description': '获取MCP提示词',
                'request': {
                    'name': '提示词名称',
                    'arguments': {'参数名': '参数值'}
                },
                'response': {
                    'description': '...',
                    'messages': [{'role': 'user', 'content': {...}}]
                }
            }
        },
        'tools': {
            'list_scripts': {
                'description': '获取所有脚本列表',
                'params': {}
            },
            'get_script': {
                'description': '获取指定脚本的详细信息',
                'params': {'name': '脚本名称'}
            },
            'execute_script': {
                'description': '执行指定脚本',
                'params': {
                    'name': '脚本名称',
                    'args': '脚本参数（可选）'
                }
            },
            'create_script': {
                'description': '创建新脚本',
                'params': {
                    'name': '脚本名称',
                    'content': '脚本内容',
                    'description': '脚本描述（可选）'
                }
            },
            'delete_script': {
                'description': '删除指定脚本',
                'params': {'name': '脚本名称'}
            },
            'list_tasks': {
                'description': '获取任务队列中的所有任务',
                'params': {'status': '任务状态筛选（可选）'}
            },
            'get_task': {
                'description': '获取指定任务的详细信息',
                'params': {'task_id': '任务ID'}
            },
            'stop_task': {
                'description': '停止正在执行的任务',
                'params': {'task_id': '任务ID'}
            },
            'get_queue_status': {
                'description': '获取任务队列状态统计',
                'params': {}
            },
            'list_jobs': {
                'description': '获取所有定时任务列表',
                'params': {}
            },
            'add_job': {
                'description': '添加定时任务',
                'params': {
                    'id': '任务ID',
                    'script': '脚本名称',
                    'cron': 'Cron表达式',
                    'enabled': '是否启用（默认true）',
                    'args': '脚本参数（可选）'
                }
            },
            'delete_job': {
                'description': '删除定时任务',
                'params': {'id': '任务ID'}
            },
            'toggle_job': {
                'description': '启用/禁用定时任务',
                'params': {
                    'id': '任务ID',
                    'enabled': '是否启用'
                }
            }
        },
        'resources': {
            'scripts://list': '脚本列表',
            'tasks://list': '任务列表',
            'jobs://list': '定时任务列表'
        },
        'prompts': {
            'create_script': {
                'description': '创建新脚本的提示词模板',
                'arguments': ['purpose']
            },
            'debug_task': {
                'description': '调试失败任务的提示词模板',
                'arguments': ['task_id']
            }
        }
    }
    
    return jsonify(docs)
