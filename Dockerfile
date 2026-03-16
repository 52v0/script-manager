FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py /app/
COPY app /app/app
COPY templates /app/templates
COPY entrypoint.sh /app/

# 创建目录并设置权限
RUN mkdir -p /app/scripts /app/logs /app/downloads && \
    chmod -R 755 /app && \
    chmod +x /app/entrypoint.sh

VOLUME ["/app/scripts", "/app/logs", "/app/downloads"]

EXPOSE 5000

ENV TZ=Asia/Shanghai
ENV PYTHONUNBUFFERED=1
ENV HOME=/tmp

CMD ["/app/entrypoint.sh"]
