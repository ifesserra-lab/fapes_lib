# fapes_lib

Biblioteca Python para extracao de dados da API FAPES `webServicesSig`.

O projeto esta em fase inicial de planejamento e sera desenvolvido com TDD estrito, orientacao a objetos, MVC adaptado para biblioteca Python, EPICs, User Stories e Gherkin.

Repositorio publico:

```text
https://github.com/ifesserra-lab/fapes_lib
```

## Objetivo

`fapes_lib` pretende oferecer uma interface Python reutilizavel para:

- autenticar na API FAPES;
- consultar endpoints documentados no Swagger;
- extrair dados encadeados de editais, projetos, bolsas e bolsistas;
- exportar resultados em formatos simples como JSON, JSONL e CSV.

## Status

O projeto ainda nao possui implementacao de codigo de producao.

A etapa atual e a organizacao do desenvolvimento:

- documentacao da API;
- arquitetura;
- EPICs;
- cenarios Gherkin;
- backlog de issues;
- preparacao para implementacao com TDD.

## Documentacao

Ponto de entrada da documentacao:

- [docs/README.md](docs/README.md)

Documentos principais:

- [API FAPES WebServicesSig](docs/api.md)
- [Autenticacao](docs/autenticacao.md)
- [Arquitetura](docs/architecture.md)
- [Backlog de desenvolvimento](docs/backlog.md)
- [Releases e changelog](release.md)
- [Notas detalhadas do Swagger](docs/fapes-webservices-sig-api.md)

EPICs:

- [EPIC-001: Autenticacao](docs/epics/EPIC-001-autenticacao.md)
- [EPIC-002: Consultas da API](docs/epics/EPIC-002-consultas-api.md)
- [EPIC-003: Extracao de dados](docs/epics/EPIC-003-extracao-dados.md)
- [EPIC-004: Exportacao de dados](docs/epics/EPIC-004-exportacao-dados.md)

Gherkin:

- [Autenticacao](docs/features/autenticacao.feature)
- [Consultas da API](docs/features/consultas_api.feature)
- [Extracao de dados](docs/features/extracao_dados.feature)
- [Exportacao de dados](docs/features/exportacao_dados.feature)

## Principios De Desenvolvimento

Este projeto segue as regras registradas em [.agents/AGENTS.MD](.agents/AGENTS.MD).

Principios obrigatorios:

- TDD estrito: teste falhando antes de codigo de producao.
- Orientacao a objetos com classes pequenas e coesas.
- MVC adaptado para biblioteca Python.
- Documentacao por EPIC, User Story e Gherkin.
- Issues antes de implementacao.
- Backlog atualizado em [docs/backlog.md](docs/backlog.md).
- Anti-patterns evitados explicitamente.
- Nenhuma credencial real versionada.

## Configuracao Local

A autenticacao usa variaveis de ambiente carregadas por `.env`.

Exemplo seguro:

```dotenv
FAPES_AUTH_URL="https://servicos.fapes.es.gov.br/webServicesSig/auth.php"
FAPES_USUARIO="..."
FAPES_SENHA="..."
```

O arquivo `.env` e local, contem segredos e nao deve ser versionado.

## Desenvolvimento

Fluxo esperado para qualquer implementacao:

1. Abrir ou selecionar issue no GitHub.
2. Verificar EPIC/Gherkin relacionado.
3. Escrever teste automatizado que falha.
4. Implementar o minimo necessario para passar.
5. Refatorar mantendo testes verdes.
6. Atualizar documentacao e backlog quando necessario.

Comandos planejados para quando o pacote Python for inicializado:

```bash
pytest
pytest --cov=fapes_lib
ruff check .
ruff format --check .
mypy src
```

## Backlog

O desenvolvimento sera gerenciado por GitHub Issues e pelo backlog documental:

- [docs/backlog.md](docs/backlog.md)

Releases, versoes e changelog:

- [release.md](release.md)

Issues iniciais de implementacao:

- [#10](https://github.com/ifesserra-lab/fapes_lib/issues/10): inicializar pacote Python.
- [#11](https://github.com/ifesserra-lab/fapes_lib/issues/11): implementar `FapesSettings` com TDD.
- [#14](https://github.com/ifesserra-lab/fapes_lib/issues/14): implementar autenticacao com TDD.

## Seguranca

- Nunca versionar `.env`.
- Nunca exibir senha ou token JWT completo em logs.
- Testes unitarios nao devem depender de rede real.
- Testes de integracao real devem exigir opt-in explicito.

## Licenca

Este projeto esta licenciado sob a licenca MIT. Consulte [LICENSE](LICENSE).
