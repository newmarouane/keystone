FROM node:22-bookworm

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=true
RUN docker run -d -p 3000:3000 \
-e PORT=3000 \
-e browserLimit=20 \
-e timeOut=60000 \
zfcsoftware/cf-clearance-scraper:latest

EXPOSE 3000
