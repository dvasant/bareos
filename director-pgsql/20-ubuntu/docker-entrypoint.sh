#!/usr/bin/env bash

# github_bareos='raw.githubusercontent.com/bareos/bareos'
# webui_admin_conf='master/webui/install/bareos/bareos-dir.d/profile/webui-admin.conf'
# admin_conf='master/webui/install/bareos/bareos-dir.d/console/admin.conf.example'

if [ ! -f /etc/bareos/bareos-config.control ]; then
  tar xzf /bareos-dir.tgz --backup=simple --suffix=.before-control

  # Download default admin profile config
  if [ ! -f /etc/bareos/bareos-dir.d/profile/webui-admin.conf ]; then
    cp /webui-admin.conf /etc/bareos/bareos-dir.d/profile/webui-admin.conf
    # curl --silent --insecure "https://${github_bareos}/${webui_admin_conf}" \
      # --output /etc/bareos/bareos-dir.d/profile/webui-admin.conf
  fi

  # Download default webUI admin config
  if [ ! -f /etc/bareos/bareos-dir.d/console/admin.conf ]; then
    cp /admin.conf  /etc/bareos/bareos-dir.d/console/admin.conf
    # curl --silent --insecure "https://${github_bareos}/${admin_conf}" \
      # --output /etc/bareos/bareos-dir.d/console/admin.conf
  fi

  # Update bareos-director configs
  # Director / mycatalog & mail report
  sed -i 's#dbpassword = ""#dbpassword = '\"${DB_PASSWORD}\"'#' \
    /etc/bareos/bareos-dir.d/catalog/MyCatalog.conf
  sed -i 's#dbname = "bareos"#dbname = '\"${DB_NAME}\"'\n  dbaddress = '\"${DB_HOST}\"'\n  dbport = '\"${DB_PORT}\"'#' \
    /etc/bareos/bareos-dir.d/catalog/MyCatalog.conf

  if [ -n "${SMTP_HOST}" ]
    then
      sed -i "s#/usr/bin/bsmtp -h localhost#/usr/bin/bsmtp -h ${SMTP_HOST}#" \
        /etc/bareos/bareos-dir.d/messages/Daemon.conf
      sed -i "s#/usr/bin/bsmtp -h localhost#/usr/bin/bsmtp -h ${SMTP_HOST}#" \
        /etc/bareos/bareos-dir.d/messages/Standard.conf
      sed -i "s#<%r#<${SENDER_MAIL}#g" \
        /etc/bareos/bareos-dir.d/messages/Daemon.conf
      sed -i "s#<%r#<${SENDER_MAIL}#g" \
        /etc/bareos/bareos-dir.d/messages/Standard.conf
      sed -i "s#mail = root#mail = ${ADMIN_MAIL}#" \
        /etc/bareos/bareos-dir.d/messages/Daemon.conf
      sed -i "s#mail = root#mail = ${ADMIN_MAIL}#" \
        /etc/bareos/bareos-dir.d/messages/Standard.conf
    else
      sed -i '/mail/d' /etc/bareos/bareos-dir.d/messages/*
      sed -i '/operator/d' /etc/bareos/bareos-dir.d/messages/*
  fi

  # Setup webhook
  if [ "${WEBHOOK_NOTIFICATION}" = true ]; then
    sed -i "s#/usr/bin/bsmtp -h.*#/usr/local/bin/webhook-notify %t %e %c %l %n\"#" \
      /etc/bareos/bareos-dir.d/messages/Daemon.conf
    sed -i "s#/usr/bin/bsmtp -h.*#/usr/local/bin/webhook-notify %t %e %c %l %n\"#" \
      /etc/bareos/bareos-dir.d/messages/Standard.conf
  fi

  # director daemon
  if [[ ! -z "${BAREOS_DIRECTOR_PASSWORD}" ]]; then
  sed -i 's#Password = .*#Password = '\""${BAREOS_DIRECTOR_PASSWORD}"\"'#' \
    /etc/bareos/bareos-dir.d/director/bareos-dir.conf
  sed -i 's#Password = .*#Password = '\""${BAREOS_DIRECTOR_PASSWORD}"\"'#' \
    /etc/bareos/bconsole.conf
  fi
  sed -i 's#Maximum Concurrent Jobs =.*#Maximum Concurrent Jobs = 1000#' \
    /etc/bareos/bareos-dir.d/director/bareos-dir.conf

  sed -i 's/# Heartbeat Interval = .*/Heartbeat Interval = 60/' \
    /etc/bareos/bareos-dir.d/director/bareos-dir.conf

  # storage daemon
  sed -i 's#Address = .*#Address = '\""${BAREOS_SD_HOST}"\"'#' \
    /etc/bareos/bareos-dir.d/storage/File.conf
  sed -i 's#Password = .*#Password = '\""${BAREOS_SD_PASSWORD}"\"'#' \
    /etc/bareos/bareos-dir.d/storage/File.conf
  sed -i 's#}#  Maximum Concurrent Jobs = 30 \n}#' /etc/bareos/bareos-dir.d/storage/File.conf

  # client/file daemon
  sed -i 's#Address = .*#Address = '\""${BAREOS_FD_HOST}"\"'#' \
    /etc/bareos/bareos-dir.d/client/bareos-fd.conf
  sed -i 's#Password = .*#Password = '\""${BAREOS_FD_PASSWORD}"\"'#' \
    /etc/bareos/bareos-dir.d/client/bareos-fd.conf
  sed -i 's#\}#  Maximum Concurrent Jobs = 30 \n}#' /etc/bareos/bareos-dir.d/client/bareos-fd.conf

  # webUI
  sed -i 's#Password = .*#Password = '\""${BAREOS_WEBUI_PASSWORD}"\"'#' \
    /etc/bareos/bareos-dir.d/console/admin.conf
  sed -i "s#}#  TlsEnable = false\n}#" \
    /etc/bareos/bareos-dir.d/console/admin.conf

  # MyCatalog Backup
  sed -i "s#/var/lib/bareos/bareos.sql#/var/lib/bareos-director/bareos.sql#" \
    /etc/bareos/bareos-dir.d/fileset/Catalog.conf

  # Default config file
  cp /default.conf /etc/bareos/bareos-dir.d/job/default.conf

  # Control file
  touch /etc/bareos/bareos-config.control
fi

# if [[ ! -z "${GCSFUSE_BUCKET}" ]]; then

#    #Mount bucket to /etc/bareos/
#    gcsfuse --uid 101 --gid 101 -o allow_other,nonempty --limit-bytes-per-sec "-1" --limit-ops-per-sec "-1" \
#     --stat-cache-ttl "1h" --type-cache-ttl "1h"  $GCSFUSE_BUCKET /etc/bareos/

#    #allow_other users
#    sed -i 's/#user_allow_other/user_allow_other/' /etc/fuse.conf
# fi

if [ ! -f /etc/bareos/bareos-db.control ]
  then
    # Waiting Postgresql is up
    sqlup=1
    while [ "$sqlup" -ne 0 ] ; do
      echo "Waiting for postgresql..."
      pg_isready --dbname="${DB_NAME}" --host="${DB_HOST}" --port="${DB_PORT}"
      if [ $? -ne 0 ] ; then
        sqlup=1
        sleep 5
      else
        sqlup=0
        echo "...postgresql is alive"
      fi
    done
    # Init Postgresql DB
    export PGUSER=postgres
    export PGHOST=${DB_HOST}
    export PGPASSWORD=${DB_PASSWORD}
    psql -c 'create user bareos with createdb createrole createuser login;'
    psql -c "alter user bareos password '${DB_PASSWORD}';"
    /usr/lib/bareos/scripts/create_bareos_database
    /usr/lib/bareos/scripts/make_bareos_tables
    /usr/lib/bareos/scripts/grant_bareos_privileges

    # Control file
    touch /etc/bareos/bareos-db.control
  else
    # Try Postgres upgrade
    export PGUSER=postgres
    export PGHOST=${DB_HOST}
    export PGPASSWORD=${DB_PASSWORD}
    /usr/lib/bareos/scripts/update_bareos_tables
    /usr/lib/bareos/scripts/grant_bareos_privileges
fi
# send bareos logs to container logs
  # touch /var/log/bareos/bareos.log && ln -sf /dev/stdout /var/log/bareos/bareos.log
  # touch /var/log/bareos/bareos-audit.log && ln -sf /dev/stderr /var/log/bareos/bareos-audit.log

mkdir -p /etc/bareos/python-scripts/
cp /ax_sql_storage_update.py /etc/bareos/python-scripts/ax_sql_storage_update.py
chmod +x /etc/bareos/python-scripts/ax_sql_storage_update.py

# Fix permissions
find /etc/bareos ! -user bareos -exec chown bareos {} \;
chown -R bareos:bareos /var/lib/bareos

# Run Dockerfile CMD
# if [[ $FORCE_ROOT = true ]] ;then
#   export BAREOS_DAEMON_USER='root'
# fi
exec "$@"
