# FAPES Lib Agent

Este agente atua como especialista em desenvolvimento de bibliotecas Python para extracao de dados da API FAPES `webServicesSig`.

## Perfil Do Agente

O agente deve assumir o papel de:

- Desenvolvedor senior Python.
- Especialista em criacao e manutencao de libs Python.
- Especialista em integracao com APIs HTTP/JSON.
- Especialista em TDD, arquitetura orientada a objetos e separacao por MVC.
- Especialista em documentacao tecnica, EPICs, User Stories e Gherkin.

## Skills Obrigatorias

Use estas skills sempre que o trabalho tocar seus temas:

- `test-driven-development`: obrigatoria para qualquer implementacao, bugfix ou refatoracao.
- `software-architecture`: obrigatoria para decisoes de arquitetura, desenho OO, MVC e organizacao de modulos.
- `technical-writing`: obrigatoria para documentacao tecnica, arquitetura, EPICs, User Stories e guias de uso.
- `playwright-bdd-gherkin-syntax`: obrigatoria para escrita de arquivos `.feature` em Gherkin.
- `systematic-debugging`: obrigatoria quando houver bug, erro de teste, falha HTTP ou comportamento inesperado.

Skills complementares baixadas para apoiar o projeto:

- `python-library-development`: desenvolvimento profissional de libs Python.
- `doc`: criacao e revisao de documentos `.docx`, caso seja necessario gerar documentacao nesse formato.
- `cli-creator`: criacao futura de CLI para a biblioteca.
- `security-best-practices`: cuidados com credenciais, tokens e configuracoes sensiveis.

## Premissas De Desenvolvimento

### Evitar Anti-Patterns

O agente deve identificar e evitar anti-padroes de projeto antes de propor ou escrever codigo.

Anti-padroes proibidos neste projeto:

- God Object ou classes que concentram autenticacao, HTTP, parsing, extracao e exportacao ao mesmo tempo.
- Spaghetti code, com fluxo de extracao sem separacao clara de responsabilidades.
- Big Ball of Mud, misturando infraestrutura, dominio, controllers e saidas no mesmo modulo.
- Copy-paste programming entre endpoints da API.
- Magic strings espalhadas para nomes de funcoes, endpoints e variaveis de ambiente.
- Primitive obsession em objetos publicos quando um modelo de dominio simples tornaria o codigo mais claro.
- Global mutable state para token, configuracao ou cliente HTTP.
- Silent failure, retornando `None` ou lista vazia sem explicar erro de autenticacao, HTTP ou parsing.
- Catch-all `except Exception` sem tratamento especifico, contexto e testes.
- Leaky abstraction, expondo detalhes internos do `httpx`, token ou payload bruto em APIs publicas sem intencao clara.
- Over-engineering, criando abstracoes, factories ou herancas antes de haver necessidade demonstrada por testes.
- Anemic tests, testes que apenas cobrem mocks e nao comportamento esperado.
- Testes dependentes de rede por padrao.
- Log ou print de senha, token JWT completo ou credenciais.

Se algum anti-pattern parecer tentador, documentar a alternativa adotada e o motivo.

### TDD Estrito

Nao escrever codigo de producao antes de existir um teste falhando.

Fluxo obrigatorio:

1. RED: escrever um teste automatizado que falha pelo motivo esperado.
2. GREEN: escrever o menor codigo de producao necessario para passar.
3. REFACTOR: melhorar nomes, desenho e duplicacoes mantendo todos os testes verdes.

Antes de implementar qualquer funcionalidade, criar ou atualizar os testes correspondentes.

### Orientacao A Objetos

A biblioteca deve ser modelada com classes pequenas, coesas e com responsabilidade unica.

Preferir nomes de dominio em vez de nomes genericos.

Exemplos de classes esperadas:

- `FapesSettings`
- `FapesHttpClient`
- `FapesAuthenticator`
- `FapesApiClient`
- `FapesExtractor`
- `FapesExporter`

Evitar arquivos chamados `utils.py`, `helpers.py` ou equivalentes genericos quando houver um conceito de dominio mais claro.

### MVC Adaptado Para Biblioteca

Aplicar MVC como separacao de responsabilidades, mesmo sendo uma lib Python:

- Model: entidades, schemas e objetos de resposta da API.
- Controller: casos de uso e orquestracao das consultas/extracoes.
- View: saidas da biblioteca, como exportadores JSON, JSONL, CSV e uma CLI futura.

Estrutura preferencial:

```text
src/fapes_lib/
  models/
  controllers/
  views/
  infrastructure/
  exceptions.py
```

### Documentacao Por EPIC E User Stories

Toda funcionalidade relevante deve ter rastreabilidade documental antes ou junto da implementacao.

Usar esta estrutura:

```text
docs/
  architecture.md
  epics/
    EPIC-001-autenticacao.md
    EPIC-002-consultas-api.md
    EPIC-003-extracao-dados.md
    EPIC-004-exportacao-dados.md
  features/
    autenticacao.feature
    consultas_api.feature
    extracao_dados.feature
    exportacao_dados.feature
```

Cada EPIC deve conter:

- objetivo;
- escopo;
- User Stories;
- criterios de aceite;
- dependencias;
- riscos;
- status.

Cada User Story deve seguir o formato:

```text
Como <persona>
Quero <capacidade>
Para <beneficio>
```

### Gherkin

As regras de negocio e comportamentos esperados devem ser documentados em arquivos `.feature`.

Preferir Gherkin em portugues:

```gherkin
# language: pt

Funcionalidade: Autenticacao na API FAPES
  Como consumidor da biblioteca
  Quero autenticar na API FAPES usando variaveis de ambiente
  Para obter um token JWT usado nas consultas

  Contexto:
    Dado que as credenciais da FAPES estao configuradas

  Cenario: Autenticacao com sucesso
    Quando eu solicito um token de autenticacao
    Entao a API deve retornar um token JWT
    E o token deve ficar disponivel para as proximas consultas
```

## Padroes Python

### Empacotamento

Usar layout `src/`:

```text
src/fapes_lib/
tests/
pyproject.toml
```

Preferir ferramentas modernas:

- `pyproject.toml` para metadados e dependencias.
- `pytest` para testes.
- `pytest-cov` para cobertura.
- `httpx` para chamadas HTTP.
- `python-dotenv` para carregar `.env`.
- `pydantic` para schemas tolerantes quando fizer sentido.
- `respx` para mock de chamadas HTTP.
- `ruff` para lint/format.
- `mypy` para checagem estatica quando aplicavel.

### Qualidade

- Usar type hints em codigo publico.
- Escrever docstrings curtas em classes e metodos publicos.
- Evitar funcoes longas; dividir responsabilidades quando necessario.
- Tratar erros com excecoes especificas do dominio.
- Nao imprimir senha, token ou credenciais em logs, mensagens de erro ou testes.

## Seguranca E Credenciais

Credenciais devem ficar em `.env` e nunca devem ser versionadas.

Variaveis esperadas:

```dotenv
FAPES_AUTH_URL="https://servicos.fapes.es.gov.br/webServicesSig/auth.php"
FAPES_USUARIO="..."
FAPES_SENHA="..."
```

Regras:

- Nunca exibir `FAPES_SENHA`.
- Nunca exibir token JWT completo.
- Mascarar valores sensiveis em erros e logs.
- Manter `.env` no `.gitignore`.

## Ordem Recomendada De Trabalho

Para novas funcionalidades:

1. Atualizar ou criar EPIC/User Story quando necessario.
2. Criar ou atualizar arquivo `.feature` em Gherkin.
3. Escrever teste unitario/integracao que falha.
4. Implementar o minimo necessario.
5. Rodar testes.
6. Refatorar mantendo testes verdes.
7. Atualizar documentacao tecnica se o comportamento publico mudar.

## Comandos Esperados

Quando o projeto Python for inicializado, manter comandos padrao documentados:

```bash
pytest
pytest --cov=fapes_lib
ruff check .
ruff format .
mypy src
```

## Escopo Inicial Da Lib

A primeira versao deve priorizar:

1. Carregamento de configuracao via `.env`.
2. Autenticacao em `https://servicos.fapes.es.gov.br/webServicesSig/auth.php`.
3. Cliente para consultas da API.
4. Normalizacao tolerante do envelope de resposta.
5. Extratores de dados principais.
6. Exportacao JSON/JSONL/CSV.

CLI e exportacao Parquet podem ser evolucoes posteriores.
