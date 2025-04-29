#!/usr/bin/env bash
set -Eeuo pipefail

# ---------- helpers -------------------------------------------------------
die()      { echo "FATAL: $*"; exit 1; }

# ---------- sanity checks -------------------------------------------------
[[ -f /project/wsgi.py        ]] || die "wsgi.py not found"
[[ -n "${PORT:-}"             ]] || die "PORT env var not set"

# ---------- choose a free local port -------------------------------------
MYSQL_TUNNEL_PORT=$(python - <<'PY'
import socket, json, os
s = socket.socket(); s.bind(("127.0.0.1", 0))
print(s.getsockname()[1]); s.close()
PY
)
echo "Selected free local port: ${MYSQL_TUNNEL_PORT}"

SECRET_KEY_SRC=/etc/secrets/ssh_key
cp "$SECRET_KEY_SRC" /tmp/ssh_key && chmod 600 /tmp/ssh_key
export PRIVATE_KEY=/tmp/ssh_key
# ---------- open the tunnel ----------------------------------------------

echo "Opening tunnel: \
-L ${MYSQL_TUNNEL_PORT}:${SSH_MYSQL_HOST}:${SSH_MYSQL_HOST_PORT} \
${SSH_MYSQL_USER}@${SSH_MYSQL_BASTION}"

ssh  -o ExitOnForwardFailure=yes \
     -o StrictHostKeyChecking=no \
     -i "$PRIVATE_KEY" \
     -Nf \
     -L "${MYSQL_TUNNEL_PORT}:${SSH_MYSQL_HOST}:${SSH_MYSQL_HOST_PORT}" \
     "${SSH_MYSQL_USER}@${SSH_MYSQL_BASTION}" \
     || die "SSH tunnel setup failed"

echo  "SSH tunnel up on 127.0.0.1:${MYSQL_TUNNEL_PORT}"

# ---------- launch Gunicorn ----------------------------------------------
exec python -m gunicorn "wsgi:app" \
     --chdir /project \
     --bind "0.0.0.0:${PORT}" \
     --workers 4 \
     --env MYSQL_TUNNEL_PORT="${MYSQL_TUNNEL_PORT}"