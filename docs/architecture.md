# Arquitetura Da Biblioteca FAPES Lib

## Visao Geral

`fapes_lib` sera uma biblioteca Python para autenticar, consultar, extrair e exportar dados da API FAPES `webServicesSig`.

A primeira entrega do projeto e documental: arquitetura, EPICs e comportamentos em Gherkin. Nenhum codigo de producao deve ser iniciado antes dessa base estar clara.

## Objetivos

- Criar uma lib Python reutilizavel para consumo da API FAPES.
- Isolar autenticacao, HTTP, parsing, casos de uso e exportacao.
- Aplicar TDD estrito em toda implementacao futura.
- Usar design orientado a objetos com responsabilidades pequenas.
- Aplicar MVC adaptado ao contexto de biblioteca.
- Documentar comportamento com EPICs, User Stories e Gherkin.
- Evitar anti-patterns de projeto desde a primeira versao.

## Nao Objetivos

- Implementar codigo de producao nesta etapa.
- Criar interface web.
- Persistir dados em banco de dados na primeira versao.
- Expor token JWT, senha ou credenciais em logs, exceptions ou testes.
- Criar uma arquitetura generica demais antes das necessidades surgirem por testes.

## Premissas

### TDD Estrito

Toda implementacao futura deve seguir:

1. RED: escrever teste que falha pelo motivo esperado.
2. GREEN: implementar o minimo necessario para passar.
3. REFACTOR: melhorar design mantendo todos os testes verdes.

Nao deve existir codigo de producao sem teste automatizado previo.

### Orientacao A Objetos

Classes devem representar colaboradores claros, estado controlado ou conceitos do dominio.

Classes previstas:

- `FapesSettings`
- `FapesHttpClient`
- `FapesAuthenticator`
- `FapesApiClient`
- `FapesExtractor`
- `FapesExporter`

### MVC Adaptado Para Biblioteca

Como o projeto e uma lib, MVC sera aplicado como separacao de responsabilidades:

| Camada | Responsabilidade | Exemplos |
| --- | --- | --- |
| Model | Dados, schemas e respostas da API | `Edital`, `Projeto`, `Bolsista`, `FapesEnvelope` |
| Controller | Casos de uso e orquestracao | autenticar, consultar endpoints, extrair dados encadeados |
| View | Saidas da biblioteca | exportadores JSON, JSONL, CSV e CLI futura |
| Infrastructure | Detalhes externos | `.env`, HTTP, autenticador, cliente `httpx` |

## Estrutura Proposta

```text
src/
  fapes_lib/
    __init__.py
    exceptions.py

    infrastructure/
      settings.py
      http_client.py
      authenticator.py

    models/
      responses.py
      edital.py
      projeto.py
      bolsa.py
      bolsista.py
      pesquisador.py

    controllers/
      auth_controller.py
      consulta_controller.py
      extraction_controller.py

    views/
      json_exporter.py
      jsonl_exporter.py
      csv_exporter.py

tests/
  unit/
  integration/
  bdd/
```

## Componentes

### FapesSettings

Responsavel por carregar e validar configuracao.

Variaveis esperadas:

```dotenv
FAPES_AUTH_URL="https://servicos.fapes.es.gov.br/webServicesSig/auth.php"
FAPES_USUARIO="..."
FAPES_SENHA="..."
FAPES_BASE_URL="https://servicos.fapes.es.gov.br"
FAPES_TIMEOUT_SECONDS="30"
FAPES_SSL_VERIFY="true"
```

`FAPES_BASE_URL`, `FAPES_TIMEOUT_SECONDS` e `FAPES_SSL_VERIFY` podem ser opcionais, com defaults seguros.

### FapesHttpClient

Responsavel por chamadas HTTP.

Deve:

- usar `httpx`;
- aplicar timeout;
- enviar JSON;
- tratar resposta nao JSON;
- encapsular erros de rede;
- permitir `verify=False` somente por configuracao explicita;
- nunca registrar senha ou token.

### FapesAuthenticator

Responsavel por obter token JWT.

Endpoint:

```text
https://servicos.fapes.es.gov.br/webServicesSig/auth.php
```

Payload:

```json
{
  "username": "VALOR_DE_FAPES_USUARIO",
  "password": "VALOR_DE_FAPES_SENHA"
}
```

Resposta real observada:

```json
{
  "token": "TOKEN_JWT"
}
```

### FapesApiClient

Responsavel por expor consultas diretas da API.

Metodos previstos:

- `listar_setores()`
- `listar_editais()`
- `listar_edital_chamadas(codedt)`
- `listar_edital_objetos_filhos(codedt)`
- `listar_projetos(codedt)`
- `listar_projeto_bolsas(codprj)`
- `listar_bolsistas(codprj)`
- `obter_pesquisador(codpes)`
- `listar_modalidade_bolsas()`
- `listar_situacao_projeto()`

Todos os metodos devem usar um mecanismo interno comum de consulta para evitar copy-paste entre endpoints.

### FapesExtractor

Responsavel por fluxos compostos.

Fluxos previstos:

- extrair cadastros auxiliares;
- extrair editais com chamadas;
- extrair editais com projetos;
- extrair projetos com bolsas e bolsistas;
- executar extracao completa.

### FapesExporter

Responsavel por saida dos dados.

Formatos iniciais:

- JSON;
- JSONL;
- CSV.

Exportadores pertencem a camada View do MVC adaptado.

## Fluxo De Dados

```text
.env
  -> FapesSettings
  -> FapesAuthenticator
  -> FapesHttpClient
  -> FapesApiClient
  -> FapesExtractor
  -> FapesExporter
```

Fluxo de extracao completa:

1. Carregar configuracao.
2. Autenticar e obter token.
3. Consultar cadastros auxiliares.
4. Consultar editais.
5. Para cada edital, consultar chamadas, objetos filhos e projetos.
6. Para cada projeto, consultar bolsas e bolsistas.
7. Exportar resultados no formato solicitado.

## API Publica Desejada

Exemplo futuro de uso:

```python
from fapes_lib import FapesClient

with FapesClient.from_env() as client:
    editais = client.listar_editais()
    projetos = client.listar_projetos(codedt=756)
```

Exemplo futuro de extracao:

```python
from fapes_lib import FapesClient, FapesExtractor

with FapesClient.from_env() as client:
    extractor = FapesExtractor(client)
    dados = extractor.extrair_editais_com_projetos()
```

Esses exemplos representam a intencao de API publica; a implementacao deve nascer via TDD.

## Estrategia De Testes

### Unitarios

Devem cobrir:

- leitura de configuracao;
- validacao de variaveis obrigatorias;
- autenticacao bem-sucedida com HTTP mockado;
- falha de autenticacao;
- consultas com token valido;
- parsing do envelope padrao;
- parsing de `setores` sem envelope;
- erros HTTP;
- resposta nao JSON;
- mascaramento de credenciais em erros.

### BDD

Os arquivos `.feature` documentam comportamento esperado e podem ser ligados a testes com `pytest-bdd` ou ferramenta equivalente.

### Integracao

Testes reais contra a API devem ser opcionais e protegidos por variavel:

```dotenv
FAPES_RUN_INTEGRATION=1
```

Testes de integracao nunca devem imprimir token ou senha.

## Excecoes Do Dominio

Excecoes previstas:

```python
class FapesError(Exception): ...
class FapesConfigError(FapesError): ...
class FapesAuthenticationError(FapesError): ...
class FapesRequestError(FapesError): ...
class FapesResponseError(FapesError): ...
class FapesEnvelopeError(FapesError): ...
```

Excecoes devem preservar contexto util sem vazar credenciais.

## Anti-Patterns Evitados

| Anti-pattern | Risco | Alternativa |
| --- | --- | --- |
| God Object | Uma classe faz tudo e fica impossivel testar | Separar settings, HTTP, auth, client, extractor e exporters |
| Big Ball of Mud | Infraestrutura e dominio misturados | MVC adaptado e boundaries claros |
| Copy-paste programming | Endpoints divergentes e bugs repetidos | Metodo interno comum de consulta |
| Magic strings | Erros silenciosos por nomes repetidos | Contratos centralizados para funcoes/endpoints |
| Global mutable state | Token e configuracao imprevisiveis | Injetar dependencias em objetos |
| Silent failure | Perda de dados sem explicacao | Excecoes especificas e testadas |
| Catch-all exception | Erros reais escondidos | Capturar excecoes especificas e reempacotar |
| Leaky abstraction | Usuario depende de detalhes de `httpx` | API publica orientada ao dominio |
| Over-engineering | Complexidade antes da necessidade | Criar abstracoes somente quando testes exigirem |
| Network-dependent unit tests | Suite lenta e instavel | Mocks HTTP e integracao opcional |
| Secret leakage | Vazamento de senha/token | Mascaramento e `.env` ignorado |

## Seguranca

- `.env` deve ficar fora do Git.
- Senha e token JWT completo nunca devem aparecer em logs, exceptions ou testes.
- `FAPES_SSL_VERIFY=false` deve ser considerado apenas para ambiente local controlado.
- O token deve ser mantido em memoria e descartado com o ciclo de vida do cliente.

## Decisoes Iniciais

### D1: Usar layout `src/`

Racional: evita import acidental do pacote local sem instalacao e melhora higiene de empacotamento.

### D2: Usar `httpx`

Racional: cliente HTTP moderno, testavel e com boa ergonomia para sync/async se necessario no futuro.

### D3: Comecar com modelos tolerantes

Racional: o Swagger possui inconsistencias de tipos, especialmente em `pesquisador`.

### D4: Separar exportacao da extracao

Racional: extrair dados e decidir o formato de saida sao responsabilidades diferentes.

## Sequencia De Entrega

1. Concluir arquitetura.
2. Concluir EPICs.
3. Concluir Gherkins.
4. Criar projeto Python com TDD.
5. Implementar configuracao.
6. Implementar autenticacao.
7. Implementar consultas.
8. Implementar extratores.
9. Implementar exportadores.

## Referencias

- [API FAPES WebServicesSig](api.md)
- [Autenticacao Da API FAPES](autenticacao.md)
- [Swagger investigado](fapes-webservices-sig-api.md)
- [AGENTS.MD](../.agents/AGENTS.MD)
