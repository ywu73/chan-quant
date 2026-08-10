# syntax=docker/dockerfile:1.7
FROM public.ecr.aws/docker/library/node:22-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2.10-alpine AS runtime
RUN addgroup --system --gid 10001 chanquant \
    && adduser --system --uid 10001 --ingroup chanquant chanquant \
    && mkdir -p /data /config /srv \
    && chown -R chanquant:chanquant /data /config /srv
COPY --chown=chanquant:chanquant deploy/Caddyfile /etc/caddy/Caddyfile
COPY --chown=chanquant:chanquant --from=builder /app/dist /srv
USER chanquant
EXPOSE 8080
