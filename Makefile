.PHONY: service

service:
	cd service && \
	make venv format lint run docker-build
