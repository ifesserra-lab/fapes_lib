# CI/CD

Este documento descreve os workflows de qualidade e publicacao da biblioteca
`fapes_lib`.

## Workflows

### CI

Arquivo: `.github/workflows/ci.yml`.

Dispara em:

- pull requests;
- pushes para `main`.

Executa:

- instalacao editavel com dependencias de desenvolvimento;
- `python -m pytest`;
- `ruff check .`;
- `ruff format --check .`;
- `mypy src`.

O CI nao precisa de `.env` e nao deve executar testes contra a API real por
padrao.

### Publish Python Package

Arquivo: `.github/workflows/publish.yml`.

Dispara quando uma GitHub Release e publicada.

Fluxo:

1. Executa a matriz de qualidade em Python 3.11, 3.12 e 3.13.
2. Se a qualidade passar, constroi `sdist` e `wheel`.
3. Valida os artefatos com `twine check --strict`.
4. Se build e validacao passarem, publica no PyPI.

## Publicacao No PyPI

A publicacao usa PyPI Trusted Publishing via OpenID Connect. Isso evita salvar
token PyPI no repositorio ou em secrets do GitHub.

Configuracao esperada no PyPI:

- projeto: `fapes-lib`;
- owner do GitHub: `ifesserra-lab`;
- repositorio: `fapes_lib`;
- workflow: `publish.yml`;
- environment: `pypi`.

Tambem e recomendado criar o environment `pypi` no GitHub com aprovacao manual
antes da publicacao em producao.

## Como Publicar Uma Versao

Antes de publicar:

1. Atualizar a versao em `pyproject.toml`.
2. Atualizar `src/fapes_lib/__init__.py`.
3. Atualizar `release.md` com o changelog da versao.
4. Confirmar que `docs/backlog.md` esta sincronizado com o GitHub.
5. Garantir que os checks locais passam.

Comandos locais recomendados:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m build
python -m twine check --strict dist/*
```

Depois disso:

1. Fazer commit de todas as mudancas da release.
2. Fazer `git push origin main`.
3. Criar uma tag semantica, por exemplo `v0.1.0`.
4. Enviar a tag para o GitHub.
5. Publicar uma GitHub Release a partir da tag.
6. Aguardar o workflow `Publish Python Package`.

Se qualquer etapa de teste, lint, formatacao, type check, build ou validacao de
metadados falhar, a publicacao nao ocorre.

Uma release so deve ser considerada finalizada quando:

- todas as mudancas foram commitadas;
- o push para o GitHub foi concluido;
- a tag semantica existe no GitHub;
- a GitHub Release foi publicada;
- o workflow `Publish Python Package` concluiu com sucesso;
- nao existem mudancas locais pendentes relacionadas a release.

## Seguranca

- Nao versionar tokens PyPI.
- Nao adicionar `.env` ao workflow.
- Nao publicar senha, token JWT ou credenciais da API FAPES em logs.
- Testes de integracao real devem ser opt-in e isolados dos workflows padrao.
