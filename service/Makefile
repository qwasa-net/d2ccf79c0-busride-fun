MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
MAKEFILE_DIR := $(dir $(MAKEFILE_PATH))
HOME_PATH := $(MAKEFILE_DIR)
VENV_PATH ?= $(HOME_PATH)/_venv

PYTHON ?= PYTHONPATH=$(HOME_PATH) $(VENV_PATH)/bin/python
SYSTEM_PYTHON ?= python3

DOCKER ?= DOCKER_BUILDKIT=1 BUILDKIT_PROGRESS=plain docker
DOCKER_IMAGE ?= busride-service

SRCFILES := service

venv: ##
	test -d $(VENV_PATH) || $(SYSTEM_PYTHON) -m venv $(VENV_PATH) --clear
	$(PYTHON) -m pip install --requirement requirements.txt
	$(PYTHON) -m pip install --requirement requirements-dev.txt

format:  ##
	$(PYTHON) -m black $(SRCFILES)
	$(PYTHON) -m isort --profile black $(SRCFILES)

lint:  ##
	$(PYTHON) -m black --check $(SRCFILES)
	$(PYTHON) -m ruff check $(SRCFILES)

run:  ##
	$(PYTHON) -m service

docker-build:  ##
	$(DOCKER) build -f service.dockerfile -t $(DOCKER_IMAGE) $(HOME_PATH)

