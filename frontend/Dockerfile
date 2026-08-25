# Build context is the repo root, so this can be reused consistently
# alongside backend/Dockerfile from docker-compose.yml.

FROM node:20-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./

# Baked in at build time: the browser calls the backend directly at
# this URL (Vite's dev-only proxy doesn't exist in a static build).
# The backend's CORS config must allow whatever origin this frontend
# is actually served from.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM node:20-slim
WORKDIR /app
RUN npm install --global serve@14
COPY --from=build /app/dist ./dist

EXPOSE 5173

CMD ["serve", "-s", "dist", "-l", "5173"]
