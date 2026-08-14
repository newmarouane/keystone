FROM node:22-bookworm

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=true

# 1. 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libnss3 \
    libx11-xcb1 \
    libxss1 \
    libxtst6 \
    libgbm1 \
    libdbus-glib-1-2 \
    python3 \
    build-essential \
    xauth \
    && rm -rf /var/lib/apt/lists/*

#    xauth \
#    dbus-x11 \
#    libdbus-glib-1-2 \
#    libdrm2 \
# 1. Bypass the user namespace sandbox check (fixes the EPERM / signal 11 crashes)
ENV MOZ_DISABLE_CONTENT_SANDBOX=1

# 2. Force software rendering since there is no GPU in Docker
ENV LIBGL_ALWAYS_SOFTWARE=1

# 2. 复制依赖文件、脚本和补丁目录，然后安装
COPY package.json pnpm-lock.yaml ./
COPY scripts/ ./scripts/
COPY patches/ ./patches/

RUN npm install
RUN npm install -g pnpm
#RUN pnpm approve-builds
RUN pnpm install --frozen-lockfile --config.dangerouslyAllowAllBuilds=true

# 3. 复制源码并初始化
COPY . .
RUN npm run init


EXPOSE 3000 5900

# 4. 启动服务（配置文件会自动从 config.example.yaml 复制到 data/config.yaml）
CMD ["npm", "start", "--", "-xvfb", "-vnc"]
#CMD ["xvfb-run", "--auto-servernum", "npm", "start", "--", "-xvfb", "-vnc"]
