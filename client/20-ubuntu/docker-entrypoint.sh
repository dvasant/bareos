#!/usr/bin/env bash

bareos_fd_config="/etc/bareos/bareos-fd.d/director/bareos-dir.conf"

if [ ! -f /etc/bareos/bareos-fd-config.control ]; then
  tar xzf /bareos-fd.tgz --backup=simple --suffix=.before-control

  # Force client/file daemon password
  sed -i 's#Password = .*#Password = '\""${BAREOS_FD_PASSWORD}"\"'#' $bareos_fd_config
  sed -i 's#\# Plugin Directory #Plugin Directory #' \
    /etc/bareos/bareos-fd.d/client/myself.conf
  sed -i 's#\# Plugin Names = .*#Plugin Names = "python3" #' \
    /etc/bareos/bareos-fd.d/client/myself.conf

  sed -i 's#Name = .*#Name = '${HOSTNAME}'#' \
    /etc/bareos/bareos-fd.d/client/myself.conf

  sed -i 's#Maximum Concurrent Jobs =.*#Maximum Concurrent Jobs = 30\n  Heartbeat Interval = 60#' \
    /etc/bareos/bareos-fd.d/client/myself.conf

  # Control file
  touch /etc/bareos/bareos-fd-config.control
fi

mkdir -p /etc/bareos/python-scripts/
cp /ax_bareos_cli.py /etc/bareos/python-scripts/ax_bareos_cli.py
chmod +x /etc/bareos/python-scripts/ax_bareos_cli.py

# Fix permissions
find /etc/bareos/bareos-fd.d ! -user bareos -exec chown bareos {} \;

# Run Dockerfile CMD
if [[ $FORCE_ROOT = true ]] ;then
  export BAREOS_DAEMON_USER='root'
fi
exec "$@"
