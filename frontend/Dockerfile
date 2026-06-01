# ── Stage 1: deps ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

# ── Stage 2: builder ───────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* must be present at BUILD time (inlined into the client bundle).
# Railway passes service variables as build args automatically.
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_COMPANY_CODE
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_COMPANY_CODE=$NEXT_PUBLIC_COMPANY_CODE
RUN npm run build

# ── Stage 3: runner (minimal, non-root) ────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY --from=builder --chown=appuser:appgroup /app/public ./public
COPY --from=builder --chown=appuser:appgroup /app/.next/standalone ./
COPY --from=builder --chown=appuser:appgroup /app/.next/static ./.next/static

USER appuser

# Next standalone server.js honours $PORT (Railway injects it; default 3000 local).
EXPOSE 3000
ENV HOSTNAME="0.0.0.0"
CMD ["sh", "-c", "PORT=${PORT:-3000} node server.js"]
