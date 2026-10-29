#!/bin/sh
set -eu

# Public site already in this repo (uis/healthcore-website) on port 3000.
node <<'JS' &
const http = require("http");
const fs = require("fs");
const path = require("path");

const root = "/uis/healthcore-website";
const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".json": "application/json",
};

http
  .createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    let rel = decodeURIComponent(url.pathname);
    if (rel.endsWith("/")) rel += "index.html";
    const file = path.resolve(root, "." + rel);
    if (file !== root && !file.startsWith(root + path.sep)) {
      res.writeHead(403);
      res.end("forbidden");
      return;
    }
    fs.readFile(file, (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end("not found");
        return;
      }
      const type = types[path.extname(file).toLowerCase()] || "application/octet-stream";
      res.writeHead(200, { "Content-Type": type });
      res.end(data);
    });
  })
  .listen(3000, "0.0.0.0");
JS
website_pid=$!

# Existing Next.js admin app on port 3001.
cd /uis/backoffice
if [ ! -x node_modules/.bin/next ]; then
  npm ci
fi
npx next dev --hostname 0.0.0.0 --port 3001 &
backoffice_pid=$!

trap 'kill "$website_pid" "$backoffice_pid" 2>/dev/null || true' INT TERM

while kill -0 "$website_pid" 2>/dev/null && kill -0 "$backoffice_pid" 2>/dev/null; do
  sleep 1
done

kill "$website_pid" "$backoffice_pid" 2>/dev/null || true
wait "$website_pid" 2>/dev/null || true
wait "$backoffice_pid" 2>/dev/null || true
exit 1
