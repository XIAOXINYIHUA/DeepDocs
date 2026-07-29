FROM python:3.11-slim

WORKDIR /app

# 系统依赖（配置镜像源）
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装项目
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev,parsers,providers]"

# 复制源码
COPY packages/ ./packages/
COPY apps/api/ ./apps/api/

EXPOSE 8000

CMD ["uvicorn", "apps.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
