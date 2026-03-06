---
name: "email-docker-auto"
description: "Reads IMAP emails to auto-download Docker images from GitHub Actions. Invoke when user needs to automate Docker image download from email notifications or wants to process GitHub Actions build emails."
---

# Email Docker Auto

This skill automates the process of reading emails from IMAP servers and downloading Docker images built by GitHub Actions.

## When to Use

- User wants to automatically download Docker images from GitHub Actions emails
- User needs to process build notifications from GitHub Actions
- User wants to automate the workflow: read email → download Docker image → extract to project
- User asks to check for failed build emails and read error messages

## Prerequisites

Before using this skill, ensure you have:
1. Email account with IMAP access enabled
2. Email password or app-specific password (not login password for Gmail/QQ)
3. Python with `imaplib` and `email` libraries available

## IMAP Configuration

### Common Email Servers

| Email Provider | IMAP Server | Port | SSL |
|---------------|--------------|-------|-----|
| QQ Mail | imap.qq.com | 993 | Yes |
| Gmail | imap.gmail.com | 993 | Yes |
| 163 Mail | imap.163.com | 993 | Yes |
| Outlook | outlook.office365.com | 993 | Yes |

### Email Password Setup

**QQ Mail:**
1. Log in to QQ Mail web interface
2. Settings → Account → POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV Service
3. Enable IMAP service
4. Generate authorization code
5. Use the authorization code as password

**Gmail:**
1. Enable 2-factor authentication
2. Go to Google Account → Security
3. App passwords → Generate
4. Use the app password

## Usage Steps

### Step 1: Read Emails

```python
import imaplib
import email
from email.header import decode_header

def read_emails(server, username, password, folder='INBOX'):
    """Read emails from IMAP server"""
    # Connect to IMAP server
    mail = imaplib.IMAP4_SSL(server, 993)
    mail.login(username, password)
    mail.select(folder)
    
    # Search for emails from GitHub Actions
    status, messages = mail.search(None, '(FROM "noreply@github.com")')
    
    emails = []
    for msg_id in messages[0].split():
        # Fetch email
        status, msg_data = mail.fetch(msg_id, '(RFC822)')
        raw_email = msg_data[0][1]
        
        # Parse email
        msg = email.message_from_bytes(raw_email)
        
        # Extract subject and body
        subject = decode_header(msg['Subject'])[0][0]
        body = get_email_body(msg)
        
        emails.append({
            'subject': subject,
            'body': body,
            'date': msg['Date']
        })
    
    mail.close()
    return emails
```

### Step 2: Check Build Status

```python
def check_build_status(emails):
    """Check if build succeeded or failed"""
    for email in emails:
        subject = email['subject']
        body = email['body']
        
        if 'Build Success' in subject:
            # Extract download link from email body
            download_link = extract_download_link(body)
            return {'status': 'success', 'link': download_link}
        elif 'Build Failed' in subject:
            # Extract error information
            error_info = extract_error_info(body)
            return {'status': 'failed', 'error': error_info}
    
    return {'status': 'none'}
```

### Step 3: Download Docker Image

```python
import requests
import os

def download_docker_image(url, save_path):
    """Download Docker image from URL"""
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return save_path
```

### Step 4: Extract to Project

```python
import tarfile
import gzip

def extract_docker_image(archive_path, project_dir):
    """Extract Docker image to project directory"""
    # Decompress if gzipped
    if archive_path.endswith('.gz'):
        with gzip.open(archive_path, 'rb') as f:
            with open(archive_path[:-3], 'wb') as out:
                out.write(f.read())
        archive_path = archive_path[:-3]
    
    # Extract tar file
    with tarfile.open(archive_path, 'r') as tar:
        tar.extractall(path=project_dir)
    
    # Cleanup
    os.remove(archive_path)
    if archive_path.endswith('.tar'):
        os.remove(archive_path + '.gz')
```

## Complete Workflow

```python
def process_github_actions_emails(email_config, project_dir):
    """Complete automation workflow"""
    
    # 1. Read emails
    emails = read_emails(
        server=email_config['server'],
        username=email_config['username'],
        password=email_config['password']
    )
    
    # 2. Check build status
    result = check_build_status(emails)
    
    if result['status'] == 'success':
        print("Build succeeded, downloading Docker image...")
        
        # 3. Download image
        image_path = download_docker_image(
            url=result['link'],
            save_path=os.path.join(project_dir, 'script-manager.tar.gz')
        )
        
        # 4. Extract to project
        extract_docker_image(image_path, project_dir)
        
        print("Docker image extracted successfully!")
        
    elif result['status'] == 'failed':
        print("Build failed!")
        print("Error information:")
        print(result['error'])
        
    else:
        print("No recent build emails found")
```

## Error Handling

### Common Issues

1. **Authentication Failed**
   - Check username and password
   - Ensure app-specific password is used (not login password)
   - Verify IMAP is enabled in email settings

2. **SSL Certificate Error**
   - Use `ssl.create_default_context()` for older Python versions
   - Or disable SSL verification (not recommended)

3. **No Emails Found**
   - Check email folder (default is INBOX)
   - Verify GitHub Actions is sending emails
   - Check email spam folder

## Example Usage

```python
# Configuration
email_config = {
    'server': 'imap.qq.com',
    'username': 'your-email@qq.com',
    'password': 'your-authorization-code'
}

# Process emails
process_github_actions_emails(email_config, '/path/to/project')
```

## Helper Functions

```python
def get_email_body(msg):
    """Extract email body from message"""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                return part.get_payload(decode=True)
    else:
        return msg.get_payload(decode=True)

def extract_download_link(body):
    """Extract download link from email body"""
    import re
    match = re.search(r'https://github\.com/[^/]+/[^/]+/actions/runs/\d+', body)
    return match.group(0) if match else None

def extract_error_info(body):
    """Extract error information from email body"""
    # Parse error details from email
    return body  # Return full body for review
```

## Security Notes

- Never commit email passwords to version control
- Use environment variables or secure configuration files
- Rotate passwords regularly
- Use app-specific passwords when available
- Enable 2-factor authentication on email accounts
