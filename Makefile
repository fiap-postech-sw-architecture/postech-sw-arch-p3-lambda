.PHONY: lint typecheck security test test-integ check build sam-local tf-validate gate

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy

security:
	uv run bandit -c pyproject.toml -r src

test:
	uv run pytest -m "not integration" --cov --cov-report=term-missing

# Socket override: necessario com colima (ryuk monta o socket dentro do
# container); inocuo com Docker Desktop, que tambem expoe /var/run/docker.sock.
test-integ:
	TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE=/var/run/docker.sock uv run pytest -m integration --no-cov

check: lint typecheck security test

# Empacota src + dependencias para o zip do Terraform (rodar antes do apply).
# --python-platform: wheels linux x86_64 (psycopg binario) para o runtime da Lambda.
build:
	rm -rf build/lambda && mkdir -p build/lambda
	uv export --frozen --no-dev --no-emit-project -o build/requirements.txt
	uv pip install --target build/lambda --python-platform x86_64-manylinux2014 \
		--python-version 3.13 --only-binary :all: -r build/requirements.txt
	cp -R src build/lambda/src

sam-local:
	sam local start-api

tf-validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false > /dev/null
	terraform -chdir=terraform validate

gate: check tf-validate
