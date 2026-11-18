#!/bin/sh
set -eu

cd /uis/website
if [ ! -x node_modules/.bin/next ]; then
  npm ci
fi
npx next dev --hostname 0.0.0.0 --port 3000 &
website_pid=$!

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
