#!/usr/bin/env python3
"""
邮件自动化处理脚本
读取 GitHub Actions 构建邮件，自动下载 Docker 镜像并解压到项目目录
"""

import imaplib
import email
from email.header import decode_header
import re
import requests
import os
import tarfile
import gzip
import sys
from pathlib import Path


class EmailDockerAuto:
    """邮件自动化处理类"""
    
    def __init__(self, server, username, password, project_dir='.'):
        self.server = server
        self.username = username
        self.password = password
        self.project_dir = Path(project_dir)
    
    def read_emails(self, folder='INBOX'):
        """读取邮件"""
        print(f"📧 连接到邮件服务器: {self.server}")
        
        try:
            # 连接到 IMAP 服务器
            mail = imaplib.IMAP4_SSL(self.server, 993)
            mail.login(self.username, self.password)
            mail.select(folder)
            
            # 搜索来自 GitHub Actions 的邮件
            status, messages = mail.search(None, '(FROM "noreply@github.com")')
            
            if status != 'OK':
                print("❌ 搜索邮件失败")
                return []
            
            email_count = len(messages[0].split())
            print(f"📬 找到 {email_count} 封 GitHub Actions 邮件")
            
            emails = []
            for msg_id in messages[0].split():
                # 获取邮件
                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                raw_email = msg_data[0][1]
                
                # 解析邮件
                msg = email.message_from_bytes(raw_email)
                
                # 提取主题和正文
                subject = self._decode_header(msg['Subject'])
                body = self._get_email_body(msg)
                
                emails.append({
                    'subject': subject,
                    'body': body,
                    'date': msg['Date'],
                    'from': msg['From']
                })
            
            mail.close()
            mail.logout()
            
            return emails
            
        except Exception as e:
            print(f"❌ 读取邮件失败: {e}")
            return []
    
    def check_build_status(self, emails):
        """检查构建状态"""
        for email in emails:
            subject = email['subject']
            body = email['body']
            
            if 'Build Success' in subject or '构建成功' in subject:
                print(f"✅ 发现构建成功的邮件: {subject}")
                download_link = self._extract_download_link(body)
                if download_link:
                    return {'status': 'success', 'link': download_link, 'email': email}
            
            elif 'Build Failed' in subject or '构建失败' in subject:
                print(f"❌ 发现构建失败的邮件: {subject}")
                error_info = self._extract_error_info(body)
                return {'status': 'failed', 'error': error_info, 'email': email}
        
        return {'status': 'none'}
    
    def download_docker_image(self, url, save_path):
        """下载 Docker 镜像"""
        print(f"⬇️  下载 Docker 镜像...")
        print(f"URL: {url}")
        
        try:
            # 从 GitHub Actions 页面下载
            # 需要访问 artifact 下载页面
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r下载进度: {progress:.1f}%", end='', flush=True)
            
            print(f"\n✅ 下载完成: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"\n❌ 下载失败: {e}")
            return None
    
    def extract_docker_image(self, archive_path):
        """解压 Docker 镜像到项目目录"""
        print(f"📦 解压 Docker 镜像...")
        
        try:
            # 如果是 gzip 压缩，先解压
            if archive_path.endswith('.gz'):
                print("解压 gzip 文件...")
                with gzip.open(archive_path, 'rb') as f:
                    with open(archive_path[:-3], 'wb') as out:
                        out.write(f.read())
                archive_path = archive_path[:-3]
            
            # 解压 tar 文件
            print("解压 tar 文件...")
            with tarfile.open(archive_path, 'r') as tar:
                tar.extractall(path=self.project_dir)
            
            # 清理临时文件
            if os.path.exists(archive_path):
                os.remove(archive_path)
                print(f"🗑️  删除临时文件: {archive_path}")
            
            print(f"✅ 解压完成到: {self.project_dir}")
            return True
            
        except Exception as e:
            print(f"❌ 解压失败: {e}")
            return False
    
    def process(self):
        """完整处理流程"""
        print("=" * 60)
        print("GitHub Actions 邮件自动化处理")
        print("=" * 60)
        
        # 1. 读取邮件
        emails = self.read_emails()
        if not emails:
            print("⚠️  未找到 GitHub Actions 邮件")
            return
        
        # 2. 检查构建状态
        result = self.check_build_status(emails)
        
        if result['status'] == 'success':
            print("\n" + "=" * 60)
            print("🎉 构建成功！开始下载 Docker 镜像")
            print("=" * 60)
            
            # 3. 下载镜像
            image_path = self.project_dir / 'script-manager.tar.gz'
            downloaded_path = self.download_docker_image(result['link'], image_path)
            
            if downloaded_path:
                # 4. 解压到项目
                print("\n" + "=" * 60)
                print("开始解压到项目目录")
                print("=" * 60)
                success = self.extract_docker_image(downloaded_path)
                
                if success:
                    print("\n" + "=" * 60)
                    print("✅ 全部完成！")
                    print("=" * 60)
                    print(f"镜像已解压到: {self.project_dir}")
                    print("可以使用 build-docker.sh 脚本运行容器")
        
        elif result['status'] == 'failed':
            print("\n" + "=" * 60)
            print("❌ 构建失败！")
            print("=" * 60)
            print("\n错误信息:")
            print(result['error'])
            print("\n邮件详情:")
            print(f"主题: {result['email']['subject']}")
            print(f"时间: {result['email']['date']}")
        
        else:
            print("\n⚠️  未找到最近的构建邮件")
    
    def _decode_header(self, header):
        """解码邮件头"""
        if not header:
            return ''
        
        decoded = decode_header(header)[0]
        if isinstance(decoded[0], bytes):
            return decoded[0].decode('utf-8', errors='ignore')
        return decoded[0]
    
    def _get_email_body(self, msg):
        """提取邮件正文"""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode('utf-8', errors='ignore')
                elif content_type == 'text/html':
                    # 如果是 HTML，提取文本内容
                    payload = part.get_payload(decode=True)
                    if payload:
                        # 简单的 HTML 标签移除
                        import re
                        text = re.sub(r'<[^>]+>', '', payload.decode('utf-8', errors='ignore'))
                        return text
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode('utf-8', errors='ignore')
        return ''
    
    def _extract_download_link(self, body):
        """从邮件正文提取下载链接"""
        # 查找 GitHub Actions 链接
        match = re.search(r'https://github\.com/[^/]+/[^/]+/actions/runs/\d+', body)
        return match.group(0) if match else None
    
    def _extract_error_info(self, body):
        """提取错误信息"""
        # 返回完整的邮件正文用于查看
        return body


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub Actions 邮件自动化处理')
    parser.add_argument('--server', required=True, help='IMAP 服务器 (如: imap.qq.com)')
    parser.add_argument('--username', required=True, help='邮箱用户名')
    parser.add_argument('--password', required=True, help='邮箱密码或授权码')
    parser.add_argument('--project-dir', default='.', help='项目目录 (默认: 当前目录)')
    
    args = parser.parse_args()
    
    # 创建处理器
    processor = EmailDockerAuto(
        server=args.server,
        username=args.username,
        password=args.password,
        project_dir=args.project_dir
    )
    
    # 执行处理
    processor.process()


if __name__ == '__main__':
    main()
