.PHONY: lint typecheck security test test-integ check build sam-local tf-validate sam-validate gate

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
# docopt (dep transitiva brutils->num2words) e sdist-only e colide com
# --only-binary :all: -- instalado em etapa separada (puro-Python, sem deps).
# build (producao, Terraform): SEMPRE x86_64 — runtime real da Lambda (main.tf).
# build-local (emulacao SAM): arch NATIVA do host — sob qemu (x86 emulado em
# Mac ARM) o runtime emulado crasha intermitente ("bad g in signal handler",
# 502). Diretorios separados para o zip do Terraform nunca sair com arch errada.
build:
	rm -rf build/lambda && mkdir -p build/lambda
	uv export --frozen --no-dev --no-emit-project --no-emit-package docopt \
		-o build/requirements.txt
	uv pip install --target build/lambda --python-platform x86_64-manylinux2014 \
		--python-version 3.13 --only-binary :all: --no-deps -r build/requirements.txt
	uv pip install --target build/lambda --python-version 3.13 --no-deps docopt==0.6.2
	cp -R src build/lambda/src
	find build/lambda -name '*.pyc' -delete
	find build/lambda -type d -name __pycache__ -prune -exec rm -rf {} +

UNAME_M := $(shell uname -m)
# aarch64: psycopg-binary nao publica wheel manylinux2014 (glibc 2.17) — usa
# manylinux_2_28 (runtime Lambda AL2023 = glibc 2.34, compativel).
LOCAL_PLATFORM := $(if $(filter arm64 aarch64,$(UNAME_M)),aarch64-manylinux_2_28,x86_64-manylinux2014)
build-local:
	rm -rf build/lambda-local && mkdir -p build/lambda-local
	uv export --frozen --no-dev --no-emit-project --no-emit-package docopt \
		-o build/requirements.txt
	uv pip install --target build/lambda-local --python-platform $(LOCAL_PLATFORM) \
		--python-version 3.13 --only-binary :all: --no-deps -r build/requirements.txt
	uv pip install --target build/lambda-local --python-version 3.13 --no-deps docopt==0.6.2
	cp -R src build/lambda-local/src
	find build/lambda-local -name '*.pyc' -delete
	find build/lambda-local -type d -name __pycache__ -prune -exec rm -rf {} +

# Depende de build-local: o CodeUri do template.yaml aponta para
# build/lambda-local (deps vendorizadas na arch do host). env.json = segredos
# de demo (ver env.json.example). Em Docker via colima, exporte DOCKER_HOST.
sam-local: build-local
	@test -f env.json || { echo "env.json ausente — rode: cp env.json.example env.json"; exit 1; }
	sam local start-api --env-vars env.json

tf-validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false > /dev/null
	terraform -chdir=terraform validate

# Gate real do template SAM. Sem o SAM CLI o alvo FALHA — o gate nao pode
# passar em silencio sem validar. Instalacao: brew install aws-sam-cli
sam-validate:
	@command -v sam >/dev/null 2>&1 || { \
		echo "sam-validate: SAM CLI nao encontrado — instale com: brew install aws-sam-cli"; \
		exit 1; }
	sam validate --lint

gate: check tf-validate sam-validate
