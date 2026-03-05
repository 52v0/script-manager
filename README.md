# Script Manager

一个基于Flask的Web脚本管理系统，支持在NAS上自动执行Python脚本，具有定时任务调度、日志管理和邮件通知功能。

## 功能特性

- 📝 **脚本管理**：上传、编辑、执行Python脚本
- ⏰ **定时调度**：支持Cron表达式的定时任务
- 📊 **日志管理**：查看、删除执行日志
- 📧 **邮件通知**：脚本执行成功/失败时发送邮件通知
- 🐳 **Docker部署**：支持Docker容器化部署
- 🔒 **安全保护**：敏感配置文件不会被提交到仓库

## 快速开始

### Docker部署

```bash
docker-compose up -d
```

### 手动部署

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动服务：
```bash
python script_manager.py
```

3. 访问Web界面：
```
http://localhost:5000
```

## 配置说明

### 邮件设置

在Web界面的"设置"页面配置邮件通知：
- SMTP服务器地址
- 端口号
- 发件人邮箱和密码
- 收件人邮箱
- 邮件主题和内容模板

### 定时任务

支持标准的Cron表达式格式：
- 分 时 日 月 周
- 示例：`0 2 * * *` 表示每天凌晨2点执行

## 目录结构

```
.
├── script_manager.py       # 主程序
├── requirements.txt        # Python依赖
├── Dockerfile             # Docker镜像构建文件
├── docker-compose.yml     # Docker编排文件
├── templates/
│   └── index.html         # Web界面
├── scripts/               # 脚本目录
│   └── *.py              # 用户脚本
├── logs/                  # 日志目录
├── .github/workflows/     # GitHub Actions
└── .gitignore            # Git忽略文件
```

## 注意事项

- 敏感配置文件（email_settings.json、jobs.json等）不会被提交到Git仓库
- 建议使用环境变量或配置文件管理敏感信息
- 日志文件会自动按时间命名，方便追溯

## 许可证

MIT License
