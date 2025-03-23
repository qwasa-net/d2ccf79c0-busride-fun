.PHONY: service

WORKERS := 30
MESSAGES := 5000
LOGFILE := busride.log

tea: service compose-docker-compose docker-compose-down docker-compose-up

docker-compose-up:
	docker compose -f busride.docker-compose.yml up \
	--no-log-prefix \
	--force-recreate \
	--abort-on-container-exit \
	2>&1 | tee $(LOGFILE)

docker-compose-down:
	-docker compose -f busride.docker-compose.yml down --remove-orphans --timeout 0 --volumes --rmi local

compose-docker-compose:
	bash busride.docker-compose.sh $(WORKERS) $(MESSAGES) \
	| tee busride.docker-compose.yml

service:
	cd service && \
	make venv format lint docker-build
