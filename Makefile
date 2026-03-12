SERVICES := identity-service task-service query-service api-gateway

.PHONY: install test lint format-check format

install:
	for service in $(SERVICES); do \
		$$service/.venv/bin/pip install -r $$service/requirements.txt; \
	done

test:
	for service in $(SERVICES); do \
		echo "Running tests in $$service"; \
		(cd $$service && .venv/bin/python -m pytest -q); \
	done

lint:
	identity-service/.venv/bin/ruff check identity-service task-service query-service api-gateway

format-check:
	identity-service/.venv/bin/black --check identity-service task-service query-service api-gateway

format:
	identity-service/.venv/bin/black identity-service task-service query-service api-gateway
