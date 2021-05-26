# Dockerfile Bareos storage daemon
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
ENV BAREOS_KEY http://download.bareos.org/bareos/release/20/xUbuntu_20.04/Release.key
ENV BAREOS_REPO http://download.bareos.org/bareos/release/20/xUbuntu_20.04/
ENV DEBIAN_FRONTEND noninteractive
ENV TZ UTC

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update -qq \
   && apt-get -qq -y install --no-install-recommends curl tzdata gnupg wget ca-certificates python3-dev python3-pip \
   && curl -Ls $BAREOS_KEY -o /tmp/bareos.key \
   && apt-key --keyring /etc/apt/trusted.gpg.d/breos-keyring.gpg \
      add /tmp/bareos.key \
   && echo "deb $BAREOS_REPO /" > /etc/apt/sources.list.d/bareos.list \
   && apt-get update -qq \
   && apt-get install -qq -y --no-install-recommends \
      bareos-storage bareos-tools bareos-storage-tape mtx scsitools sg3-utils mt-st \
      bareos-storage-ceph bareos-vadp-dumper bareos-vmware-plugin bareos-vmware-vix-disklib bareos-storage-droplet \
   && apt-get clean \
   && rm -rf /var/lib/apt/lists/*

RUN echo "deb http://packages.cloud.google.com/apt gcsfuse-jessie main" | tee /etc/apt/sources.list.d/gcsfuse.list; \
   curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
   && apt-get update ; apt-get install -y apt-utils kmod && apt-get install -y gcsfuse && apt-get clean \
   && rm -rf /var/lib/apt/lists/*

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod u+x /docker-entrypoint.sh

RUN tar czf /bareos-sd.tgz /etc/bareos/bareos-sd.d

EXPOSE 9103

VOLUME /etc/bareos
VOLUME /var/lib/bareos/storage

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["sh", "-c", "/usr/sbin/bareos-sd -u $BAREOS_DAEMON_USER -f"]
