# Stage 1: Build dependencies and package Python environment
FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone the specific nodriver-support fork branch
RUN git clone --branch nodriver-support https://github.com .

# Install dependencies into a local directory to copy to final stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final lightweight execution environment
FROM python:3.11-slim-bookworm

# Install runtime dependencies (Chromium, Xvfb for headless mode, and fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    xvfb \
    xauth \
    fonts-liberation \
    libgconf-2-4 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local
# Copy the application source code
COPY --from=builder /app /app

# Configure required FlareSolverr environment variables
ENV PORT=8191
ENV HOST=0.0.0.0
ENV LOG_LEVEL=info
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

# Expose FlareSolverr API port
EXPOSE 8191

# Start FlareSolverr inside a virtual framebuffer (Xvfb) required by Chromium
CMD ["xvfb-run", "--server-args=-screen 0 1600x1200x24", "python", "src/flaresolverr.py"]
