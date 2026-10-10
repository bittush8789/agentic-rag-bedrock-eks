.PHONY: help install test lint eval compose-up compose-down tf-init-dev tf-plan-dev tf-init-prod tf-plan-prod helm-template

PYTHON := python
VENV_PYTHON := ./.venv/Scripts/python.exe
VENV_PYTEST := ./.venv/Scripts/pytest.exe

help:
	@echo "Available commands:"
	@echo "  make install        Install project dependencies into virtualenv"
	@echo "  make test           Run unit and integration test suite"
	@echo "  make eval           Execute AI evaluation and grounding benchmarks"
	@echo "  make compose-up     Launch PostgreSQL pgvector, backend, worker, frontend"
	@echo "  make compose-down   Tear down local Docker Compose containers"
	@echo "  make tf-init-dev    Initialize Terraform dev environment"
	@echo "  make tf-plan-dev    Generate Terraform dev plan"
	@echo "  make tf-init-prod   Initialize Terraform prod environment"
	@echo "  make helm-template  Render Helm chart templates locally"

install:
	$(PYTHON) -m venv .venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r backend/requirements.txt
	$(VENV_PYTHON) -m pip install -r worker/requirements.txt

test:
	$(VENV_PYTEST) -v tests/

eval:
	set PYTHONPATH=backend&& $(VENV_PYTHON) evaluation/evaluate.py

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down -v

tf-init-dev:
	cd infrastructure/terraform/environments/dev && terraform init

tf-plan-dev:
	cd infrastructure/terraform/environments/dev && terraform plan

tf-init-prod:
	cd infrastructure/terraform/environments/prod && terraform init

tf-plan-prod:
	cd infrastructure/terraform/environments/prod && terraform plan

helm-template:
	helm template agentic-rag deploy/helm/agentic-rag -f deploy/helm/agentic-rag/values-dev.yaml
