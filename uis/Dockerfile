FROM node:22-alpine

RUN apk add --no-cache libc6-compat

WORKDIR /uis

COPY website/package.json website/package-lock.json ./website/
COPY backoffice/package.json backoffice/package-lock.json ./backoffice/
RUN npm ci --prefix website
RUN npm ci --prefix backoffice

COPY . .

RUN chmod +x /uis/start.sh

EXPOSE 3000 3001

CMD ["sh", "./start.sh"]
