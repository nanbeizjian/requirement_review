# requirement_review 前端生产镜像（多阶段构建）
# 构建上下文为 frontend/ 目录：
#   docker build -f frontend/Dockerfile .
#   compose 中 web 服务已按此配置；nginx.conf 由 compose 挂载，不入镜像

# ---- 构建阶段 ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . ./
RUN npm run build

# ---- 托管阶段 ----
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
