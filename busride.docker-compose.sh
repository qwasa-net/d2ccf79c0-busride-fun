#!/bin/bash

#
WORKERS_COUNT=${1:-3}
WORKERS_LIST=$(seq -s " " 1 "$WORKERS_COUNT")
SERVICES_LIST="${WORKERS_LIST} X"
BUS_TYPE=${BUS_TYPE:-redis}
MESSAGES_COUNT=${2:-100}
WORK_HARD_TIME=0.0025
KICK_HARD_TIME=0

#
if [ "$BUS_TYPE" == "redis" ]; then
    BUS_CONNECTION=${BUS_CONNECTION:-'{\"host\": \"redis\", \"port\": \"6379\", \"db\": \"0\"}'}
elif [ $BUS_TYPE == "kafka" ]; then
    echo "kafka bus is not supported yet, please come back later"
    exit 1
else
    echo "unknown bus type: $BUS_TYPE"
    exit 1
fi

### bus
cat <<EOF
services:

  redis:
    image: ${REDIS_IMAGE:-redis}
    environment:
      - REDIS_PORT=${REDIS_PORT:-6379}
      - REDIS_HOST=${REDIS_HOST:-0.0.0.0}
      - REDIS_DB=${REDIS_DB:-0}
    networks:
      - busride-network

EOF

### workers
for sid in $WORKERS_LIST; do
  cat <<EOF
  service-worker-${sid}:
    image: ${SERVICE_IMAGE:-busride-service}
    hostname: ${SERVICE_HOSTNAME:-busride-service-worker}-${sid}
    depends_on:
      - redis
    environment:
      SERVICE_ID: ${sid}
      SERVICES_LIST: "${SERVICES_LIST}"
      SERVICE_TYPE: worker
      WORK_HARD_TIME: ${WORK_HARD_TIME}
      BUS_TYPE: "${BUS_TYPE}"
      BUS_CONNECTION: "${BUS_CONNECTION}"
    networks:
      - busride-network

EOF
done


### catcher
cat <<EOF
  service-x:
    image: ${SERVICE_IMAGE:-busride-service}
    hostname: ${SERVICE_HOSTNAME:-busride-service-x}
    depends_on:
      - redis
    environment:
      SERVICE_ID: X
      SERVICE_TYPE: catcher
      CATCH_COUNT: ${MESSAGES_COUNT}
      EXIT: yes
      BUS_TYPE: "${BUS_TYPE}"
      BUS_CONNECTION: "${BUS_CONNECTION}"
    networks:
      - busride-network

EOF

### kicker
cat <<EOF
  service-0:
    image: ${SERVICE_IMAGE:-busride-service}
    hostname: ${SERVICE_HOSTNAME:-busride-service-0}
    depends_on:
      - redis
    environment:
      SERVICE_ID: 0
      SERVICE_TYPE: kicker
      SERVICES_LIST: "${WORKERS_LIST}"
      KICK_COUNT: ${MESSAGES_COUNT}
      WORK_HARD_TIME: ${KICK_HARD_TIME}
      BUS_TYPE: "${BUS_TYPE}"
      BUS_CONNECTION: "${BUS_CONNECTION}"
    networks:
      - busride-network

EOF


### busride-network
cat <<EOF
networks:

  busride-network:
    driver: bridge

EOF


### bye-bye
cat <<EOF
# bye-bye
EOF
