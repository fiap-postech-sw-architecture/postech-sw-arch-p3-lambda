# Project Memory -- postech-sw-arch-p3-lambda

<!-- last-consolidated: 2026-07-11 -->

Add-only log of project-specific learnings. New entries go to the top of each section. Never edit historical entries -- add a contradicting entry above instead.

Updated by AI agents at task end per `postech-ai-helper/ai/canonical/task-end-review.md`. The `last-consolidated` marker above is updated only when `/consolidate-memory` runs, not on every append.

## Recent decisions

- 2026-10-06 - Feedback do professor da fase 3 (CPF): a validacao dos digitos verificadores passou a ser propria, em `src/autenticacao_cpf/cpf.py` (modulo 11, rejeita sequencias repetidas e digitos nao-ASCII) e roda antes de qualquer consulta ao RDS; `brutils` saiu do runtime e ficou so no grupo dev para o teste de paridade (~100 mil CPFs). O pacote da function caiu de 29 MB para 20 MB e o `make build` nao precisa mais do workaround do docopt (dep transitiva de brutils/num2words)
- 2026-09-07 - Primeiro deploy automatico de producao concluido no run 34179043515; Lambdas ficaram `Active`, Terraform aplicou os stages `homolog`/`prod` e o smoke externo confirmou auth 200, rota protegida 200 e sem token 401
- 2026-09-07 - As rotas GET de cliente compartilham uma integração HTTP_PROXY via VPC Link para o listener TCP 8000 do NLB interno; subnets são descobertas por `kubernetes.io/role/internal-elb=1`, o SG restringe a saída à porta 8000 e `overwrite:path=$request.path` remove o stage antes do FastAPI, substituindo o proxy por URL pública
- 2026-09-06 - Terraform de Lambda/Gateway usa backend S3 `pytstop-terraform-state-924563550535` na chave `lambda/terraform.tfstate`, lock nativo (`use_lockfile`, Terraform >=1.10) e o mesmo state nas execucoes local e Actions; homolog/main continuam na mesma HTTP API e sao serializados
- 2026-07-11 - CD sem workspaces Terraform: um unico state, stages homolog/prod na MESMA HTTP API (function_name fixo - workspace por branch criaria segunda Lambda com o mesmo nome, ResourceConflictException); gate (make check) roda no proprio cd.yml antes do deploy - unico freio, org free nao tem branch protection
- 2026-07-11 - Bootstrap da fase 3: function serverless de autenticacao por CPF (Lambda python3.13 + API GW HTTP API + authorizer); ADRs 026-029 vivem no repo postech-sw-arch-p3 - Terraform da function/gateway vive NESTE repo; SAM e so emulacao local (ADR-029)

## Discovered conventions

- 2026-10-06 - Normalizacao de documento e ASCII-only (`re.compile(r"\D", re.ASCII)`), em paridade com o app (`documento.py`): o `\D` padrao do Python e Unicode e deixa passar digitos arabe-indicos, que o `brutils.is_valid` ainda aceita e que gerariam `documento_hash` diferente do cadastrado
- 2026-07-11 - Paridade obrigatoria com o app: normalizacao de CPF (so digitos, `documento.py`), documento_hash HMAC-SHA256 com chave sha256(ENCRYPTION_KEY) (`encryption.py`), claims JWT de `jwt_service.py` - teste de paridade com vetor fixo em tests/test_hashing.py

## Gotchas

- 2026-10-06 - PyJWT 2.13.x (runtime desta function) ganhou 27 advisories em 10/2026, entre eles bypass com chave HMAC vazia e forja de token por Unicode; subido para 2.15.1 com piso no pyproject. O app so acusou porque tem pip-audit e trivy no CI; esta Lambda nao tem SCA e o buraco passaria despercebido
- 2026-10-06 - O avaliador da FIAP conta como "commit direto na main" todo commit sem `(#N)` no titulo (Lambda: 11 = 8 diretos de 11-12/07, antes da protecao, + 3 merges de PR com `--subject` customizado). `gh pr merge --squash --subject` NAO acrescenta o `(#N)`: inclua-o no titulo ou omita `--subject`
- 2026-09-07 - Depois que a integração cria subnets privadas na VPC default, filtrar `data.aws_subnets.default` apenas por VPC também as injeta no `vpc_config` da Lambda; `default-for-az=true` mantém a função nas subnets públicas originais e reserva as privadas ao NLB/VPC Link
- 2026-09-06 - Learner Lab nega `iam:GetRole`; usar o account ID de `aws_caller_identity` para formar o ARN da LabRole existente, sem `data aws_iam_role` e sem criar IAM
- 2026-07-11 - testcontainers + colima: ryuk falha ao montar o socket (~/.colima/.../docker.sock) - Makefile test-integ exporta TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE=/var/run/docker.sock (inocuo no Docker Desktop)
- 2026-07-11 - AWS Academy: NAO criar recursos IAM; usar data source da role LabRole; aws_lambda_permission (resource policy) e permitido

## Tech debt / TODO

- 2026-10-06 - MEDIUM - A Lambda de autenticacao nao tem SCA no CI (so `gate` e `tf-validate`); adicionar `pip-audit` sobre o export de producao ao `gate` (usar `uvx --python 3.13`, o `ensurepip` do Python 3.14.4 do uvx aborta no Mac) para advisories de dependencia nao dependerem do CI do app
- 2026-09-06 - RESOLVIDO - A integracao HTTP_PROXY do Gateway passa a encaminhar as duas rotas protegidas de cliente para o LoadBalancer da aplicacao no EKS; supersede a pendencia de 2026-07-11 sobre a rota de exemplo
- 2026-07-11 - MEDIUM - rota protegida do gateway e exemplo apontando para a propria lambda; integrar HTTP_PROXY com o app no EKS quando o endpoint existir

## Review lessons

- 2026-10-06 - Validacao que existe no handler mas nao no modulo que o avaliador abriu (`hashing.py`) foi lida como ausente (feedback fase 3): regra de dominio com nome proprio num modulo dedicado, teste que prova que o banco nao e tocado e o fluxo descrito no README
- 2026-07-11 - Decode base64/UTF-8 do corpo fora do try do parse virou 500 acionavel (payload malformado derrubava o handler) - borda de parse SEMPRE inteira dentro do try (base64 -> UTF-8 -> JSON), capturando binascii.Error/UnicodeDecodeError/JSONDecodeError -> 400
