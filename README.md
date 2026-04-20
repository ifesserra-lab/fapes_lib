# fapes_lib

Biblioteca Python para extracao de dados da API FAPES `webServicesSig`.

O projeto esta em desenvolvimento inicial e segue TDD estrito, orientacao a objetos, MVC adaptado para biblioteca Python, EPICs, User Stories e Gherkin.

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

O projeto ja possui a fundacao inicial da biblioteca Python:

- pacote Python com layout `src/`;
- configuracao via ambiente com `FapesSettings`;
- excecoes de dominio com mascaramento de segredos;
- transporte HTTP base com `FapesHttpClient`;
- autenticacao com `FapesAuthenticator` e token mascarado em representacoes textuais;
- CI com testes, lint, format check e type check;
- CD para publicacao no PyPI quando uma release passar nos checks.

## Instalacao

A biblioteca ainda nao foi publicada no PyPI. Enquanto isso, ela pode ser
baixada diretamente pelo GitHub:

- Repositorio: <https://github.com/ifesserra-lab/fapes_lib>
- Download ZIP: <https://github.com/ifesserra-lab/fapes_lib/archive/refs/heads/main.zip>

Instalacao com `pip` a partir do GitHub:

```bash
pip install "fapes-lib @ git+https://github.com/ifesserra-lab/fapes_lib.git@main"
```

Para desenvolvimento local:

```bash
git clone https://github.com/ifesserra-lab/fapes_lib.git
cd fapes_lib
pip install -e ".[dev]"
```

Para usar tambem o dashboard Streamlit:

```bash
pip install -e ".[dashboard]"
```

## Exemplo De Uso

Configure as credenciais no ambiente ou em um arquivo `.env` local:

```dotenv
FAPES_AUTH_URL="https://servicos.fapes.es.gov.br/webServicesSig/auth.php"
FAPES_USUARIO="..."
FAPES_SENHA="..."
```

Consulta simples de editais:

```python
from fapes_lib.controllers import (
    FapesApiClient,
    FapesAuthenticator,
    FapesQueryController,
)
from fapes_lib.infrastructure.http_client import FapesHttpClient
from fapes_lib.settings import FapesSettings

settings = FapesSettings.from_env()
http_client = FapesHttpClient(
    base_url=settings.base_url,
    timeout=settings.timeout_seconds,
)

authenticator = FapesAuthenticator(settings=settings, http_client=http_client)
token = authenticator.authenticate()

query_controller = FapesQueryController(
    http_client=http_client,
    token=token.value,
)
api_client = FapesApiClient(query_controller=query_controller)

editais = api_client.listar_editais()

print(f"Editais encontrados: {editais.qtd}")
print(editais.data[:3])
```

## Documentacao

Ponto de entrada da documentacao:

- [docs/README.md](docs/README.md)

Documentos principais:

- [API FAPES WebServicesSig](docs/api.md)
- [Autenticacao](docs/autenticacao.md)
- [Arquitetura](docs/architecture.md)
- [Backlog de desenvolvimento](docs/backlog.md)
- [CI/CD](docs/cicd.md)
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

## Dados Gerados Localmente

A pasta `downloads/` e usada pelos scripts e pelo dashboard para armazenar
JSONs, CSVs e relatorios gerados localmente a partir da API FAPES. Esses
arquivos podem ser grandes, variam conforme a execucao e nao sao versionados;
gere-os novamente com `scripts/main.py` e `scripts/report.py` quando necessario.

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

Teste de integracao real, protegido por opt-in explicito:

```bash
FAPES_RUN_INTEGRATION=1 FAPES_INTEGRATION_LIMIT=3 pytest -q tests/integration/test_real_editais_projetos.py
```

Sem `FAPES_RUN_INTEGRATION=1`, o teste real e ignorado.

## Extracao Paralela Por Edital

Para baixar os projetos de cada edital em paralelo e gravar um arquivo JSON por
edital:

```python
from fapes_lib.controllers import FapesExtractor

extractor = FapesExtractor(api_client=api_client)
resultado = extractor.extrair_projetos_dos_editais_em_threads(
    destination_dir="downloads/projetos_por_edital",
    max_workers=8,
)
```

O metodo consulta `listar_editais` uma vez, dispara tarefas para consultar
`listar_projetos:<edital_id>` e salva arquivos como
`edital_756_projetos.json`. O resultado retorna os editais enriquecidos com
`projetos` e `arquivo_projetos`, alem de metadados com contagem de `editais`,
`projetos` e `arquivos`. Sem `max_workers`, uma tarefa e criada para cada
edital; informe um limite para reduzir conexoes simultaneas contra a API real.

Tambem ha um script em `scripts/` para baixar os projetos de todos os editais
usando as credenciais da `.env`:

```bash
python scripts/main.py --output-dir downloads/projetos_por_edital --max-workers 4 --retries 2 --skip-existing
```

Para gerar o relatorio agregado por `instituicao_nome` e `instituicao_sigla`,
somando a quantidade de bolsas e o orcamento contratado:

```bash
python scripts/report.py --input-dir downloads/projetos_por_edital --output downloads/relatorio_instituicoes.csv
```

Para buscar na FAPES a alocacao real de bolsistas dos projetos e salvar em CSV
e JSON:

```bash
python scripts/report.py \
  --input-dir downloads/projetos_por_edital \
  --output downloads/relatorio_instituicoes.csv \
  --scholarship-allocations-output downloads/relatorio_alocacao_bolsas.csv \
  --scholarship-allocations-json-output downloads/relatorio_alocacao_bolsas.json \
  --scholarship-allocation-max-workers 4
```

Para abrir o dashboard Streamlit com os JSONs baixados:

```bash
pip install -e ".[dashboard]"
streamlit run scripts/dashboard.py
```

No dashboard, a pagina `Bolsistas alocados` usa
`downloads/relatorio_alocacao_bolsas.json` para analisar bolsistas, projetos,
valores alocados e valores pagos, alem de permitir baixar o recorte filtrado em
CSV ou JSON.

## Logging

A biblioteca usa o modulo `logging` da biblioteca padrao e nao configura handlers
globais. Consumidores podem injetar um logger no extrator:

```python
import logging

from fapes_lib.controllers import FapesExtractor

logger = logging.getLogger("fapes_lib.extracao")
extractor = FapesExtractor(api_client=api_client, logger=logger)
resultado = extractor.extrair_editais_com_projetos()
```

Cada etapa de extracao emite eventos com campos extras `fapes_event` e
`fapes_step`, como `step_started`, `step_finished`, `step_failed` e
`listar_projetos:756`. Logs de falha nao incluem senha, token ou contexto bruto
da resposta.

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
