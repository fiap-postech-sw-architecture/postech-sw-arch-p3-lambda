# Project Memory -- postech-sw-arch-p3-lambda

<!-- last-consolidated: 2026-07-11 -->

Add-only log of project-specific learnings. New entries go to the top of each section. Never edit historical entries -- add a contradicting entry above instead.

Updated by AI agents at task end per `postech-ai-helper/ai/canonical/task-end-review.md`. The `last-consolidated` marker above is updated only when `/consolidate-memory` runs, not on every append.

## Recent decisions

- 2026-07-11 - CD sem workspaces Terraform: um unico state, stages homolog/prod na MESMA HTTP API (function_name fixo - workspace por branch criaria segunda Lambda com o mesmo nome, ResourceConflictException); gate (make check) roda no proprio cd.yml antes do deploy - unico freio, org free nao tem branch protection
- 2026-07-11 - Bootstrap da fase 3: function serverless de autenticacao por CPF (Lambda python3.13 + API GW HTTP API + authorizer); ADRs 026-029 vivem no repo postech-sw-arch-p3 - Terraform da function/gateway vive NESTE repo; SAM e so emulacao local (ADR-029)

## Discovered conventions

- 2026-07-11 - Paridade obrigatoria com o app: normalizacao de CPF (so digitos, `documento.py`), documento_hash HMAC-SHA256 com chave sha256(ENCRYPTION_KEY) (`encryption.py`), claims JWT de `jwt_service.py` - teste de paridade com vetor fixo em tests/test_hashing.py

## Gotchas

- 2026-07-11 - testcontainers + colima: ryuk falha ao montar o socket (~/.colima/.../docker.sock) - Makefile test-integ exporta TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE=/var/run/docker.sock (inocuo no Docker Desktop)
- 2026-07-11 - AWS Academy: NAO criar recursos IAM; usar data source da role LabRole; aws_lambda_permission (resource policy) e permitido

## Tech debt / TODO

- 2026-07-11 - MEDIUM - rota protegida do gateway e exemplo apontando para a propria lambda; integrar HTTP_PROXY com o app no EKS quando o endpoint existir

## Review lessons

- 2026-07-11 - Decode base64/UTF-8 do corpo fora do try do parse virou 500 acionavel (payload malformado derrubava o handler) - borda de parse SEMPRE inteira dentro do try (base64 -> UTF-8 -> JSON), capturando binascii.Error/UnicodeDecodeError/JSONDecodeError -> 400
