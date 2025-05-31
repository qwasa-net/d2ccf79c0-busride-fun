SHELL := /bin/bash
.PHONY: service

WORKERS := 30
MESSAGES := 5000
BUS_TYPE := redis
LOGFILE := busride-$(BUS_TYPE).log

tea: service compose-docker-compose docker-compose-down docker-compose-up

docker-compose-up:
	time \
	docker compose -f _busride.docker-compose.yml up \
	--no-log-prefix \
	--force-recreate \
	--abort-on-container-exit \
	--exit-code-from service-x \
	--timeout 0 \
	--remove-orphans \
	2>&1 | tee $(LOGFILE)

docker-compose-down:
	-docker compose -f _busride.docker-compose.yml down \
	--remove-orphans \
	--timeout 0 \
	--volumes \
	--rmi local

compose-docker-compose:
	bash busride.docker-compose.sh $(WORKERS) $(MESSAGES) $(BUS_TYPE) \
	| tee _busride.docker-compose.yml

service:
	cd service && \
	make venv format lint docker-build
