#!/bin/bash

#
WORKERS_COUNT=${1:-3}
WORKERS_LIST=$(seq -s " " 1 "$WORKERS_COUNT")
SERVICES_LIST="${WORKERS_LIST} X"

MESSAGES_COUNT=${2:-100}

BUS_TYPE=${3:-redis}

WORK_HARD_TIME=0.0025
KICK_HARD_TIME=0
KICK_START_DELAY=5
START_DELAY=1

DEBUG=${DEBUG:}
DRAW_STATS=${DRAW_STATS:}

#
if [ "$BUS_TYPE" == "redis" ]; then
    BUS_CONNECTION=${BUS_CONNECTION:-'{\"host\": \"redis\", \"port\": \"6379\", \"db\": \"0\"}'}
    BUS_SERVICE=redis
elif [ $BUS_TYPE == "kafka" ]; then
    BUS_CONNECTION=${BUS_CONNECTION:-'{\"bootstrap_servers\": \"kafka:9092\"}'}
    BUS_SERVICE=kafka
    KICK_START_DELAY=15
    START_DELAY=19
else
    echo "unknown bus type: $BUS_TYPE"
    exit 1
fi

### bus
cat <<EOF
services:
EOF

if [ "$BUS_TYPE" == "redis" ]; then
    cat <<EOF

  redis:
    image: ${REDIS_IMAGE:-redis}
    environment:
      - REDIS_PORT=${REDIS_PORT:-6379}
      - REDIS_HOST=${REDIS_HOST:-0.0.0.0}
      - REDIS_DB=${REDIS_DB:-0}
    networks:
      - busride-network

EOF
fi

if [ $BUS_TYPE == "kafka" ]; then
    cat <<EOF

  kafka:
    image: ${KAFKA_IMAGE:-apache/kafka:4.0.0}
    environment:
      - KAFKA_NODE_ID=1
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
      - KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093
      - KAFKA_LOG_DIRS=/tmp/kafka-logs
      - KAFKA_LOG4J_LOGGERS=kafka=WARN
      - KAFKA_LOG4J_ROOT_LOGLEVEL=WARN
      - KAFKA_HEAP_OPTS=-Xmx1G -Xms1G
      - KAFKA_NUM_PARTITIONS=3
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
      - KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1
      - KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1
      - KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS=0
      - KAFKA_LOG_FLUSH_INTERVAL_MESSAGES=1000000
      - KAFKA_LOG_FLUSH_INTERVAL_MS=90000
      - KAFKA_LOG_RETENTION_MS=90000
      - KAFKA_LOG_SEGMENT_BYTES=1073741824
      - KAFKA_LOG_CLEANER_ENABLE=false
      - KAFKA_LOG_INDEX_INTERVAL_BYTES=4096
      - KAFKA_LOG_INDEX_SIZE_MAX_BYTES=10485760
      - KAFKA_MAX_POLL_INTERVAL_MS=900000
      - KAFKA_SESSION_TIMEOUT_MS=300000
      - KAFKA_NUM_IO_THREADS=4
      - KAFKA_NUM_NETWORK_THREADS=3
    networks:
      - busride-network

EOF
fi

### workers
for sid in $WORKERS_LIST; do
  cat <<EOF
  service-worker-${sid}:
    image: ${SERVICE_IMAGE:-busride-service}
    hostname: ${SERVICE_HOSTNAME:-busride-service-worker}-${sid}
    depends_on:
      - ${BUS_SERVICE}
      - service-x
    environment:
      SERVICE_ID: ${sid}
      SERVICES_LIST: "${SERVICES_LIST}"
      SERVICE_TYPE: worker
      WORK_HARD_TIME: ${WORK_HARD_TIME}
      START_DELAY: ${START_DELAY}
      BUS_TYPE: "${BUS_TYPE}"
      BUS_CONNECTION: "${BUS_CONNECTION}"
      DEBUG: ${DEBUG}
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
      - ${BUS_SERVICE}
    environment:
      SERVICE_ID: X
      SERVICE_TYPE: catcher
      CATCH_COUNT: ${MESSAGES_COUNT}
      START_DELAY: ${START_DELAY}
      EXIT: yes
      BUS_TYPE: "${BUS_TYPE}"
      BUS_CONNECTION: "${BUS_CONNECTION}"
      DEBUG: ${DEBUG}
      DRAW_STATS: ${DRAW_STATS}
    networks:
      - busride-network

EOF

### kicker
cat <<EOF
  service-0:
    image: ${SERVICE_IMAGE:-busride-service}
    hostname: ${SERVICE_HOSTNAME:-busride-service-0}
    depends_on:
      - ${BUS_SERVICE}
      - service-x
    environment:
      SERVICE_ID: 0
      SERVICE_TYPE: kicker
      SERVICES_LIST: "${WORKERS_LIST}"
      KICK_COUNT: ${MESSAGES_COUNT}
      WORK_HARD_TIME: ${KICK_HARD_TIME}
      START_DELAY: ${KICK_START_DELAY}
      BUS_TYPE: "${BUS_TYPE}"
      BUS_CONNECTION: "${BUS_CONNECTION}"
      DEBUG: ${DEBUG}
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
