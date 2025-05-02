#!/usr/bin/env bash
set -Eeuo pipefail

die() { echo "FATAL: $*" >&2; exit 1; }

# ─── sanity checks --------------------------------------------------------
[[ -f /project/wsgi.py ]] || die "wsgi.py not found"
[[ -n "${PORT:-}"      ]] || die "PORT env var not set"
[[ -n "${SSH_KEY_BASE64:-}" ]] || die "SSH_KEY_BASE64 env var not set"

# ─── 1. SSH config --------------------------------------------------------
install -d -m 700 ~/.ssh
ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null || true

printf '%s' "$SSH_KEY_BASE64" | base64 -d > ~/.ssh/id_ecdsa
chmod 600 ~/.ssh/id_ecdsa
ssh-keygen -yf ~/.ssh/id_ecdsa >/dev/null || die "SSH key invalid or encrypted"
echo "SSH key OK"

# ─── 2. Pick a free local port for the tunnel -----------------------------
MYSQL_TUNNEL_PORT=$(python - <<'PY'
import socket, os; s = socket.socket(); s.bind(("127.0.0.1", 0))
print(s.getsockname()[1]); s.close()
PY
)
export MYSQL_TUNNEL_PORT
echo "Selected local tunnel port $MYSQL_TUNNEL_PORT"

# ─── 3. Open the tunnel ---------------------------------------------------
echo "Opening SSH tunnel → ${SSH_MYSQL_HOST}:3306 via ${SSH_MYSQL_BASTION}"
ssh -o ExitOnForwardFailure=yes \
    -o StrictHostKeyChecking=no \
    -i ~/.ssh/id_ecdsa \
    -L "${MYSQL_TUNNEL_PORT}:${SSH_MYSQL_HOST}:3306" \
    "${SSH_MYSQL_USER}@${SSH_MYSQL_BASTION}" \
    -N &
TUNNEL_PID=$!

# Wait until the local port is listening
for i in {1..10}; do
  nc -z 127.0.0.1 "$MYSQL_TUNNEL_PORT" && break
  sleep 0.5
done || die "SSH tunnel failed to open"
echo "SSH tunnel up on 127.0.0.1:${MYSQL_TUNNEL_PORT}"

# ─── 4. Launch Gunicorn ---------------------------------------------------
exec gunicorn -w 2 -b "0.0.0.0:${PORT}" wsgi:app