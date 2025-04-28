# entrypoint.sh
set -euo pipefail

# Allocate a free local port and export it
export MYSQL_TUNNEL_PORT=$(ssh -o StrictHostKeyChecking=no -i "$SSH_MYSQL_KEY" \
  -NfL 0:$SSH_MYSQL_HOST:$SSH_MYSQL_HOST_PORT "$SSH_MYSQL_HOST@$SSH_MYSQL_BASTION" \
  -v 2>&1 | grep -oE 'Allocated port [0-9]+' | awk '{print $3}')

echo "SSH tunnel up on 127.0.0.1:$MYSQL_TUNNEL_PORT"

# Launch Gunicorn; workers inherit MYSQL_TUNNEL_PORT
exec gunicorn "wsgi:app" \
    --chdir /project/src \
    --bind "0.0.0.0:${PORT}" \
    --workers 4