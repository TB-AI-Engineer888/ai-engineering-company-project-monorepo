FROM node:22-alpine

RUN apk add --no-cache libc6-compat

WORKDIR /uis

# Existing monorepo UIs, installed separately:
# - backoffice is the Next.js admin app and has its own package manifest
# - healthcore-website is the public site and has no package manifest
COPY backoffice/package.json backoffice/package-lock.json ./backoffice/
RUN npm ci --prefix backoffice

COPY . .

RUN chmod +x /uis/start.sh

EXPOSE 3000 3001

CMD ["sh", "./start.sh"]
