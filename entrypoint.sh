#!/usr/bin/env bash
set -Eeuo pipefail

# ---------- helpers -------------------------------------------------------
die()      { echo "FATAL: $*"; exit 1; }

# ---------- sanity checks -------------------------------------------------
[[ -f /project/wsgi.py        ]] || die "wsgi.py not found"
[[ -n "${PORT:-}"             ]] || die "PORT env var not set"

##############################################################################
# 1. Build ~/.ssh and write the private key                                  #
##############################################################################
install -d -m 700 ~/.ssh
ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null || true


printf '%s' $SSH_KEY_BASE64 | base64 -d > ~/.ssh/id_ecdsa        
chmod 600 ~/.ssh/id_ecdsa

# ---------------------------------------------------------------------------
# Self-test: read the key back and make sure it is usable and UNencrypted
# ---------------------------------------------------------------------------
if ! ssh-keygen -yf /dev/stdin >/dev/null 2>&1 < ~/.ssh/id_ecdsa ; then
  die "SSH_KEY is encrypted, truncated or not a private key"
fi
echo "key OK"

# ---------- choose a free local port -------------------------------------
MYSQL_TUNNEL_PORT=$(python - <<'PY'
import socket, json, os
s = socket.socket(); s.bind(("127.0.0.1", 0))
print(s.getsockname()[1]); s.close()
PY
)
echo "Selected free local port: ${MYSQL_TUNNEL_PORT}"

# ---------- open the tunnel ----------------------------------------------

echo "Opening tunnel: \
-L ${MYSQL_TUNNEL_PORT}:${SSH_MYSQL_HOST}:${SSH_MYSQL_HOST_PORT} \
${SSH_MYSQL_USER}@${SSH_MYSQL_BASTION}"

ssh  -o ExitOnForwardFailure=yes \
     -o StrictHostKeyChecking=no \
     -i ~/.ssh/id_ecdsa \
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