#!/usr/bin/env bash

bareos_sd_config="/etc/bareos/bareos-sd.d/director/bareos-dir.conf"
# mount_command="${GCSFUSE_BUCKET} /var/lib/bareos/storage gcsfuse rw,nonempty,_netdev,allow_other,uid=101,gid=101"
if [ ! -f /etc/bareos/bareos-sd-config.control ]; then
  tar xfz /bareos-sd.tgz --backup=simple --suffix=.before-control

  # Update bareos-storage configs
  sed -i 's#Password = .*#Password = '\""${BAREOS_SD_PASSWORD}"\"'#' $bareos_sd_config

  sed -i 's#Maximum Concurrent Jobs =.*#Maximum Concurrent Jobs = 30\n  Heartbeat Interval = 60#' \
    /etc/bareos/bareos-sd.d/storage/bareos-sd.conf

  # Control file
  touch /etc/bareos/bareos-sd-config.control
fi

if [[ ! -z "${GCSFUSE_BUCKET}" ]]; then

   #Mount bucket to /var/lib/bareos/storage
   gcsfuse --uid 101 --gid 101 -o allow_other --limit-bytes-per-sec "-1" --limit-ops-per-sec "-1" \
    --stat-cache-ttl "1h" --type-cache-ttl "1h"  $GCSFUSE_BUCKET /var/lib/bareos/storage/
   
   #allow_other users
   sed -i 's/#user_allow_other/user_allow_other/' /etc/fuse.conf
fi

# Fix permissions
find /etc/bareos/bareos-sd.d ! -user bareos -exec chown bareos {} \;
chown -R bareos /var/lib/bareos 

# Run Dockerfile CMD
exec "$@"
