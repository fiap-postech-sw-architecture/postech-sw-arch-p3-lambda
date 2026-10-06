## O que muda e por quê

<!-- Uma ou duas frases. Se atende feedback ou requisito, cite o ID (RF-0xx, RNF-0xx, RN-0xx) ou a seção. -->

## Como foi verificado

- [ ] `make gate` verde localmente (lint, mypy strict, bandit, testes com cobertura mínima, `terraform validate` e `test`, `sam validate`)
- [ ] Testes novos ou ajustados para o comportamento que mudou
- [ ] Documentação atualizada quando a mudança afeta README ou ADR

## Antes de mergear

- [ ] Checks obrigatórios (`gate` e `tf-validate`) verdes
- [ ] Toda conversa de revisão respondida (aplicada com o SHA, ou justificada)
- [ ] Squash merge com `(#N)` no título (o título padrão do GitHub já traz)
