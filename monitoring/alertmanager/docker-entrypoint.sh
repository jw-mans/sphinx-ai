#!/bin/sh
set -e

sed \
  -e "s|__ALERT_SMTP_HOST__|${ALERT_SMTP_HOST}|g" \
  -e "s|__ALERT_SMTP_PORT__|${ALERT_SMTP_PORT}|g" \
  -e "s|__ALERT_SMTP_USER__|${ALERT_SMTP_USER}|g" \
  -e "s|__ALERT_SMTP_PASSWORD__|${ALERT_SMTP_PASSWORD}|g" \
  -e "s|__ALERT_FROM_EMAIL__|${ALERT_FROM_EMAIL}|g" \
  -e "s|__ALERT_TO_EMAIL__|${ALERT_TO_EMAIL}|g" \
  /etc/alertmanager/alertmanager.yml.template > /tmp/alertmanager.yml

exec /bin/alertmanager --config.file=/tmp/alertmanager.yml "$@"
