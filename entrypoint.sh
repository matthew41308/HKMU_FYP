#!/usr/bin/env bash
# entrypoint.sh
set -Eeuo pipefail
debug() { [[ ${DEBUG:-false} == true ]] && printf '[%(%FT%T%z)T] %s\n' -1 "$*" >&2; }
log()   { printf '[%(%FT%T%z)T] %s\n' -1 "$*" >&2; }
die()   { log "FATAL: $*"; exit 1; }


[[ -f /project/entrypoint.sh ]]  || die "entrypoint.sh not found in /project"
[[ -f /project/wsgi.py ]]        || die "wsgi.py not found"
[[ -n "${PORT:-}" ]]             || die "Environment variable PORT is not set"

debug "Opening tunnel through $SSH_MYSQL_BASTION to $SSH_MYSQL_HOST:$SSH_MYSQL_HOST_PORT"

# Allocate a free local port
MYSQL_TUNNEL_PORT=$(
  ssh  -o ExitOnForwardFailure=yes \
      -o StrictHostKeyChecking=no \
      -i "$PRIVATE_KEY_PATH" \
      -NfL 0:"$SSH_MYSQL_HOST":"$SSH_MYSQL_HOST_PORT" \
      "$SSH_MYSQL_HOST@$SSH_MYSQL_BASTION" \
      -v 2>&1 |
  grep -oE 'port [0-9]+\.?$'      |   # grab “… port <digits>”
  awk '{print $2}'                 |   # keep the number
  head -n1                             # first match
) || die "Couldn't obtain tunnel port from ssh output"


echo "SSH tunnel up on 127.0.0.1:$MYSQL_TUNNEL_PORT"

log "SSH tunnel up on 127.0.0.1:${MYSQL_TUNNEL_PORT}"
debug "MYSQL_TUNNEL_PORT=${MYSQL_TUNNEL_PORT}"

# Launch Gunicorn
debug "Launching Gunicorn on port ${PORT}"
exec python -m gunicorn "wsgi:app" \
     --chdir /project \
     --bind "0.0.0.0:${PORT}" \
     --workers 4