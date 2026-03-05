FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY script_manager.py /app/
COPY templates /app/templates

# 创建目录并设置权限
RUN mkdir -p /app/scripts /app/logs && \
    chmod -R 755 /app

VOLUME ["/app/scripts", "/app/logs", "/app/script_metadata.json"]

EXPOSE 5000

ENV TZ=Asia/Shanghai
ENV PYTHONUNBUFFERED=1
ENV HOME=/tmp

CMD ["python", "script_manager.py"]
