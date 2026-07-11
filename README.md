# postech-sw-arch-p3-lambda — Autenticação por CPF (PytStop)

Function serverless de autenticação da fase 3 do Tech Challenge (PytStop, oficina mecânica). O cliente informa o CPF; a function valida o formato, verifica existência e status na base do app e emite um JWT compatível com o app principal ([postech-sw-arch-p3](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3)).

Decisões de arquitetura: ADRs 026–029 no repo principal (`postech-sw-arch-p3/docs/arquitetura/adr/fase3/`).

## Tecnologias

- **Python 3.13** (runtime `python3.13` da AWS Lambda) com [uv](https://docs.astral.sh/uv/)
- **AWS Lambda** + **API Gateway HTTP API** (rota `POST /auth` + Lambda authorizer nas rotas protegidas)
- **PyJWT** (HS256, mesmos claims do app), **psycopg** (PostgreSQL), **brutils** (validação de CPF, ADR-010)
- **Terraform** (deploy real — a IaC da function e do gateway vive NESTE repo)
- **AWS SAM CLI** (apenas emulação local, ADR-029)
- Qualidade: ruff, mypy (strict), bandit, pytest com cobertura ≥ 95%, testcontainers
- Dockerfile: n/a — deploy é pacote zip via Terraform (ADR-029), sem imagem de container

## Arquitetura

```mermaid
flowchart LR
    C[Cliente] -->|"POST /auth {cpf}"| GW[API Gateway HTTP API]
    GW --> L[Lambda autenticacao-cpf]
    L -->|"busca por documento_hash"| RDS[(PostgreSQL RDS)]
    L -->|"JWT HS256"| C

    C -->|"Bearer JWT"| GW
    GW -.->|rotas protegidas| AUT[Lambda authorizer]
    AUT -.->|"isAuthorized + context"| GW
    GW -->|proxy| EKS[App PytStop no EKS]
```

Compatibilidade com o app (replicada bit a bit, com teste de paridade):

- Normalização do CPF: apenas dígitos (mesma regra do VO `CPF` do app).
- Busca: `documento_hash = HMAC-SHA256(key=sha256(ENCRYPTION_KEY), msg=cpf_normalizado)` na tabela `clientes`.
- JWT: claims `sub`, `email`, `papel="cliente"`, `type="access"`, `jti`, `iat`, `exp`, assinado com o mesmo `JWT_SECRET` — validado sem mudança pelo app.
- Anti-enumeração: cliente inexistente e inativo recebem a mesma resposta `401`.

## Rodando local

```bash
uv sync            # instala Python 3.13 + dependências
make check         # lint + typecheck + security + testes (cobertura >= 95%)
make test-integ    # testes de integração com PostgreSQL real (exige Docker)
make sam-local     # emulação da API local (exige SAM CLI; ADR-029)
sam local invoke AutenticacaoCpfFunction -e events/auth.json
```

Variáveis de ambiente da function: `DATABASE_URL`, `JWT_SECRET`, `ENCRYPTION_KEY` (obrigatórias — ausência aborta o cold start) e `JWT_EXPIRATION_MINUTES` (default 30).

### Demo local integrada (lambda + app no kind)

Fluxo completo CPF→JWT→API sem AWS, com o app do repo principal rodando no kind (`make cd-local` lá):

```bash
# 1. App + banco no kind (repo postech-sw-arch-p3):
#    make cd-local  — sobe cluster, banco, API e monitoramento.
# 2. Exponha o Postgres do cluster para a lambda local (15432 evita colisão
#    com um Postgres local ou do compose da fase 2 em 5432):
kubectl --context kind-pytstop -n pytstop-infra port-forward svc/postgres 15432:5432 &
# 3. Env de demo da lambda (mesmos JWT_SECRET/ENCRYPTION_KEY dos Secrets de
#    demo do app em k8s/secret.yaml):
cp env.json.example env.json
# 4. Emule gateway + function apontando para o MESMO banco e segredos do app
#    (o alvo roda `make build` antes — o template usa deps de build/lambda):
make sam-local     # POST http://localhost:3000/auth {"cpf": "<cpf de cliente semeado>"}
# 5. Consuma a API do app com o token emitido:
#    curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/...
```

> **Nota (demo only)**: os valores de `env.json.example` são os segredos de
> demonstração PÚBLICOS do app (`k8s/secret.yaml` do repo principal, marcados
> `gitleaks:allow` lá) — nunca valores reais. `env.json` está no `.gitignore`
> para o caso de alguém trocar por valores próprios.

Paridade parcial documentada (RFC-003 §3): o roteamento gateway→app não existe localmente — o app valida o JWT com o mesmo segredo (validação redundante do ADR-027). O authorizer É emulado pelo SAM: a rota de exemplo `GET /auth/exemplo-protegido` exige Bearer JWT (401 sem token). Rotas de papel `cliente` entram na Onda 3/4.

## Deploy (Terraform + AWS Academy)

Restrições do AWS Academy: sem criação de recursos IAM (usa a role `LabRole` existente via data source), credenciais rotativas no profile `academy`, região `us-east-1`.

```bash
make build                             # empacota deps (wheels linux) + src em build/lambda/
cd terraform
terraform init
terraform apply \
  -var jwt_secret=... -var encryption_key=... -var database_url=...
```

Um único state, **sem workspaces**: os stages `homolog` e `prod` existem na mesma HTTP API (`terraform/main.tf`) e as functions têm `function_name` fixo — workspaces duplicariam a Lambda com o mesmo nome (`ResourceConflictException`). Um `apply` sobe os dois stages juntos.

O CD (`.github/workflows/cd.yml`) roda `make check` (gate — único freio, já que a org free não tem branch protection) e aplica o mesmo terraform em push para `homolog` e `main`; o que muda por branch é só qual stage o resumo do deploy referencia. Ver nota sobre cota/credenciais no topo do arquivo e o runbook `aws-academy-setup.md` no repo `postech-sw-arch-p3-docs`.

## API

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth` | `{"cpf": "..."}` → `200 {access_token, token_type, expires_in}` \| `400` CPF malformado \| `401` credenciais inválidas |

Documentação completa (Swagger/Postman): [collection Postman da fase 3](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/entrega/fase3/postman-collection-fase3.json) (inclui esta rota `POST /auth` com a variável `gateway_url`) e [OpenAPI da API principal](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/entrega/fase3/openapi-fase3.json).

## Status e pendências

- [x] Function + authorizer implementados, gate local verde (lint, mypy strict, bandit, cobertura ≥ 95%, terraform validate)
- [ ] Deploy real na AWS — **aguardando credenciais AWS Academy** (rotativas por sessão de laboratório)
  - Links de deploys ativos: n/a permanente — AWS Academy é efêmero por design (destroy pós-demo, ADR-026); este README documenta como subir o ambiente em minutos
- [ ] Execução do CI/CD no GitHub — **cota de Actions da organização esgotada** (gate roda local via `make gate`)
- [ ] Integração das rotas protegidas do gateway com o app no EKS (hoje há uma rota de exemplo com o authorizer)
