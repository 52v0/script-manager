#!/bin/bash

# 创建下载目录
mkdir -p /app/downloads

# 如果设置了DOWNLOADS_PATH环境变量，创建软链接
if [ -n "$DOWNLOADS_PATH" ]; then
    echo "设置下载路径软链接: $DOWNLOADS_PATH -> /app/downloads"
    ln -sf "$DOWNLOADS_PATH" /app/downloads
else
    echo "使用默认下载路径: /app/downloads"
fi

# 启动应用
exec python app.py
