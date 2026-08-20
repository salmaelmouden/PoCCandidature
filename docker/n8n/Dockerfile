# Local n8n image — built from already-cached node:20-slim (no Docker Hub n8n pull).
# Requires corporate CA at build time (copied by `make n8n-build`).

FROM node:20-slim

USER root

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY=localhost,127.0.0.1
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=${NO_PROXY}

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 make g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Corporate TLS bundle (make n8n-build copies it here)
COPY certs/full-bundle.pem /certs/full-bundle.pem
ENV NODE_EXTRA_CA_CERTS=/certs/full-bundle.pem
ENV SSL_CERT_FILE=/certs/full-bundle.pem

WORKDIR /opt/n8n
COPY package.json ./
RUN npm install --omit=dev --no-fund --no-audit \
    && npm cache clean --force \
    && chown -R node:node /opt/n8n

USER node
ENV N8N_PORT=5678
ENV N8N_PROTOCOL=http
ENV N8N_SECURE_COOKIE=false
ENV N8N_DIAGNOSTICS_ENABLED=false
ENV N8N_PERSONALIZATION_ENABLED=false
ENV GENERIC_TIMEZONE=Europe/Paris
ENV TZ=Europe/Paris
EXPOSE 5678

CMD ["./node_modules/.bin/n8n", "start"]
