# RTD LLM API Makefile

# Variables
IMAGE_NAME = rtd-llm-api
CONTAINER_NAME = rtd-llm-api
PORT = 8000

# Default target
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  build       - Build Docker image"
	@echo "  run         - Run container"
	@echo "  stop        - Stop container"
	@echo "  restart     - Restart container"
	@echo "  logs        - View container logs"
	@echo "  shell       - Open shell in container"
	@echo "  clean       - Remove container and image"
	@echo "  up          - Start with docker-compose"
	@echo "  down        - Stop docker-compose services"
	@echo "  setup       - Setup environment"
	@echo "  test        - Test project structure"

# Docker commands
.PHONY: build
build:
	docker build -t $(IMAGE_NAME) .

.PHONY: run
run:
	docker run -d \
		--name $(CONTAINER_NAME) \
		-p $(PORT):$(PORT) \
		--env-file .env \
		$(IMAGE_NAME)

.PHONY: stop
stop:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

.PHONY: restart
restart: stop run

.PHONY: logs
logs:
	docker logs -f $(CONTAINER_NAME)

.PHONY: shell
shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

.PHONY: clean
clean: stop
	docker rmi $(IMAGE_NAME) || true

# Docker Compose commands
.PHONY: up
up:
	docker-compose up -d

.PHONY: down
down:
	docker-compose down

.PHONY: compose-logs
compose-logs:
	docker-compose logs -f

# Development commands
.PHONY: setup
setup:
	python setup.py

.PHONY: test
test:
	python test_structure.py

.PHONY: dev
dev:
	python main.py

# Install dependencies
.PHONY: install
install:
	pip install -r requirements.txt

# Create .env from example
.PHONY: env
env:
	cp .env.example .env
	@echo "Please edit .env file with your actual API keys"