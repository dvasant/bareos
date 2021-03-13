# Dockerfile Bareos client/file daemon
FROM ubuntu:focal

LABEL maintainer="barcus@tou.nu"

ARG BUILD_DATE
ARG NAME
ARG VCS_REF
ARG VERSION

LABEL org.label-schema.schema-version="1.0" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name=$NAME \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/barcus/bareos" \
      org.label-schema.version=$VERSION

ENV BAREOS_DAEMON_USER bareos
ENV DEBIAN_FRONTEND noninteractive
ENV BAREOS_KEY http://download.bareos.org/bareos/release/20/xUbuntu_20.04/Release.key
ENV BAREOS_REPO http://download.bareos.org/bareos/release/20/xUbuntu_20.04/
ENV TZ UTC

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update -qq \
   && apt-get -qq -y install --no-install-recommends curl tzdata gnupg wget ca-certificates python3-dev python3-pip \
   && curl -Ls $BAREOS_KEY -o /tmp/bareos.key \
   && apt-key --keyring /etc/apt/trusted.gpg.d/breos-keyring.gpg \
   add /tmp/bareos.key \
   && echo "deb $BAREOS_REPO /" > /etc/apt/sources.list.d/bareos.list \
   && apt-get update -qq \
   && apt-get install -qq -y --no-install-recommends python3-psycopg2\
   bareos-client mysql-client postgresql-client bareos-tools bareos-vadp-dumper bareos-vmware-vix-disklib \
   bareos-vmware-plugin libssl-dev gcc build-essential \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*

# RUN echo "deb http://packages.cloud.google.com/apt gcsfuse-jessie main" | tee /etc/apt/sources.list.d/gcsfuse.list; \
#    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
#    && apt-get update ; apt-get install -y apt-utils kmod && apt-get install -y gcsfuse && apt-get clean \
#    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade google-cloud-pubsub python-bareos sslpsk

COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY ax_bareos_cli_recovery.py /ax_bareos_cli_recovery.py
COPY ax_bareos_cli_protection.py /ax_bareos_cli_protection.py
RUN chmod u+x /docker-entrypoint.sh

RUN tar czf /bareos-fd.tgz /etc/bareos/bareos-fd.d

RUN pip3 install pyvmomi
RUN mkdir -p /etc/bareos/bareos-fd.d/cbt_tool && \
   wget https://raw.githubusercontent.com/bareos/bareos/master/core/src/vmware/vmware_cbt_tool/vmware_cbt_tool.py -P /etc/bareos/bareos-fd.d/cbt_tool && \
   chmod +x /etc/bareos/bareos-fd.d/cbt_tool/vmware_cbt_tool.py

EXPOSE 9102

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["sh", "-c", "/usr/sbin/bareos-fd -u $BAREOS_DAEMON_USER -f"]
