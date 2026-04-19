# Documentacao Da API FAPES WebServicesSig

Referencia tecnica da API `webServicesSig`, baseada no Swagger publicado pela FAPES.

- Swagger UI: <https://servicos.fapes.es.gov.br/webServicesSig/>
- OpenAPI JSON: <https://servicos.fapes.es.gov.br/webServicesSig/swagger.json>
- Data da consulta: 2026-04-19

## Resumo

A API disponibiliza consultas do SIG/FAPES para editais, chamadas, projetos, bolsas, bolsistas, pesquisadores, setores e situacoes de projeto.

O Swagger informa:

| Campo | Valor |
| --- | --- |
| OpenAPI | `3.0.0` |
| Titulo | `API FAPES` |
| Versao | `1.0.0` |
| Base URL | `https://servicos.fapes.es.gov.br` |
| Formato | JSON |
| Metodo | `POST` |

Ao acessar a raiz da documentacao:

```text
https://servicos.fapes.es.gov.br/webServicesSig/
```

o servidor redireciona para:

```text
https://servicos.fapes.es.gov.br/webServicesSig/swagger.php
```

A UI do Swagger carrega o contrato:

```text
https://servicos.fapes.es.gov.br/webServicesSig/swagger.json
```

## Autenticacao

A API usa token JWT. O Swagger declara `bearerAuth`, mas os exemplos oficiais e o comportamento observado indicam que o token deve ser enviado no corpo JSON das consultas, no campo `token`.

### Gerar Token JWT

```http
POST /webServicesSig/auth.php
Content-Type: application/json
```

O endpoint de autenticacao deve receber usuario e senha no corpo JSON.

As credenciais locais ficam no arquivo `.env`:

```dotenv
FAPES_AUTH_URL="https://servicos.fapes.es.gov.br/webServicesSig/auth.php"
FAPES_USUARIO="..."
FAPES_SENHA="..."
```

Corpo enviado para a API:

```json
{
  "username": "VALOR_DE_FAPES_USUARIO",
  "password": "VALOR_DE_FAPES_SENHA"
}
```

Resposta de sucesso observada:

```json
{
  "token": "TOKEN_JWT"
}
```

Resposta observada com credenciais invalidas:

```http
401 Unauthorized
```

```json
{
  "message": "Credenciais inv\u00e1lidas."
}
```

Exemplo:

```bash
curl -X POST "$FAPES_AUTH_URL" \
  -H 'Content-Type: application/json' \
  -d "{
    \"username\": \"$FAPES_USUARIO\",
    \"password\": \"$FAPES_SENHA\"
  }"
```

## Padrao Das Consultas

As consultas seguem este formato:

```http
POST /webServicesSig/consulta.php/{funcao}
Content-Type: application/json
```

Corpo minimo:

```json
{
  "token": "TOKEN_JWT",
  "funcao": "nome_da_funcao"
}
```

Algumas funcoes exigem parametros adicionais:

| Parametro | Uso |
| --- | --- |
| `codedt` | Codigo do edital. |
| `codprj` | Codigo do projeto. |
| `codpes` | Codigo do pesquisador. |

Resposta observada com token invalido:

```http
403 Forbidden
```

```json
{
  "message": "Acesso negado: token inv\u00e1lido.",
  "error": "Wrong number of segments"
}
```

## Envelope De Resposta

A maioria das consultas retorna um array com um objeto de envelope:

```json
[
  {
    "data": [],
    "encontrado": 1,
    "msg": "",
    "erro": "",
    "qtd": 0
  }
]
```

Campos do envelope:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `data` | array | Lista de registros retornados pela consulta. |
| `encontrado` | integer | `0` quando nao ha resultado; `1` quando ha resultado. |
| `msg` | string | Mensagem de retorno. |
| `erro` | string | Descricao do erro, quando existir. |
| `qtd` | integer | Quantidade de registros retornados. |

Excecao documentada: `setores` aparece no Swagger retornando diretamente uma lista de objetos, sem o envelope `data`.

## Catalogo De Endpoints

| Funcao | Endpoint | Corpo JSON |
| --- | --- | --- |
| `autenticacao` | `/webServicesSig/auth.php` | `username`, `password` |
| `setores` | `/webServicesSig/consulta.php/setores` | `token`, `funcao` |
| `editais` | `/webServicesSig/consulta.php/editais` | `token`, `funcao` |
| `edital_chamadas` | `/webServicesSig/consulta.php/edital_chamadas` | `token`, `funcao`, `codedt` |
| `edital_objetos_filhos` | `/webServicesSig/consulta.php/edital_objetos_filhos` | `token`, `funcao`, `codedt` |
| `projetos` | `/webServicesSig/consulta.php/projetos` | `token`, `funcao`, `codedt` |
| `projeto_bolsas` | `/webServicesSig/consulta.php/projeto_bolsas` | `token`, `funcao`, `codprj` |
| `bolsistas` | `/webServicesSig/consulta.php/bolsistas` | `token`, `funcao`, `codprj` |
| `pesquisador` | `/webServicesSig/consulta.php/pesquisador` | `token`, `funcao`, `codpes` |
| `modalidade_bolsas` | `/webServicesSig/consulta.php/modalidade_bolsas` | `token`, `funcao` |
| `situacao_projeto` | `/webServicesSig/consulta.php/situacao_projeto` | `token`, `funcao` |

## Endpoints

### Setores

Consulta gerencias e nucleos da FAPES.

```http
POST /webServicesSig/consulta.php/setores
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "setores"
}
```

Resposta documentada:

```json
[
  {
    "sigla": "string",
    "descricao": "string"
  }
]
```

### Editais

Consulta editais da FAPES.

```http
POST /webServicesSig/consulta.php/editais
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "editais"
}
```

Campos em `data`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `edital_id` | integer | Identificador do edital. |
| `edital_nome` | string | Nome/titulo do edital. |
| `edital_data` | string/date | Data de cadastro. |
| `edital_numero_ano` | string | Numero e ano do edital. |

### Chamadas De Edital

Consulta chamadas de um edital.

```http
POST /webServicesSig/consulta.php/edital_chamadas
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "edital_chamadas",
  "codedt": 756
}
```

Campos em `data`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `edital_id` | integer | Codigo do edital. |
| `edital_chamada_id` | integer | Codigo da chamada. |
| `edital_chamada_vigencia_entrada` | string/date | Inicio do prazo para envio das propostas. |
| `edital_chamada_vigencia_saida` | string/date | Fim do prazo para envio das propostas. |

### Objetos Filhos Do Edital

Consulta objetos filhos de um edital.

```http
POST /webServicesSig/consulta.php/edital_objetos_filhos
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "edital_objetos_filhos",
  "codedt": 756
}
```

O Swagger declara o envelope comum, mas nao informa os campos internos de `data`. A descricao tambem parece ter sido copiada de `edital_chamadas`, entao este endpoint precisa ser validado com resposta real antes de modelar tipos fortes.

### Projetos

Consulta projetos de um edital.

```http
POST /webServicesSig/consulta.php/projetos
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "projetos",
  "codedt": 756
}
```

Campos em `data`:

| Campo | Tipo |
| --- | --- |
| `projeto_id` | integer |
| `projeto_titulo` | string |
| `projeto_data_inicio_previsto` | string/date |
| `projeto_data_fim_previsto` | string/date |
| `projeto_duracao` | integer |
| `projeto_pai` | integer |
| `projeto_situacao` | integer |
| `situacao_descricao` | string |
| `valor_bolsa` | number |
| `coordenador_nome` | string |
| `coordenador_id` | integer |
| `coordenador_cpf` | string |
| `contratado_termo_numero` | string |
| `contratado_termo_siafem` | string |

### Bolsas De Projeto

Consulta bolsas de um projeto.

```http
POST /webServicesSig/consulta.php/projeto_bolsas
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "projeto_bolsas",
  "codprj": 48409
}
```

Campos em `data`:

| Campo | Tipo |
| --- | --- |
| `orcamento_quantidade` | integer |
| `orcamento_duracao` | integer |
| `orcamento_custo` | number |
| `orcamento_bolsa_nivel_id` | integer |
| `cotas` | integer |
| `vlrtot` | number |
| `nome` | string |
| `sigla` | string |

### Bolsistas

Consulta bolsistas de um projeto.

```http
POST /webServicesSig/consulta.php/bolsistas
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "bolsistas",
  "codprj": 48409
}
```

Campos em `data`:

| Campo | Tipo |
| --- | --- |
| `formulario_bolsa_id` | integer |
| `formulario_bolsa_situacao` | integer |
| `bolsista_pesquisador_id` | integer |
| `bolsista_pesquisador_nome` | string |
| `bolsista_pesquisador_cpf` | string |
| `formulario_bolsa_inicio` | string/date |
| `formulario_bolsa_termino` | string/date |
| `banco_id` | integer |
| `formulario_numero_agencia` | string |
| `formulario_numero_conta` | string |
| `bolsa_nivel_nome` | string |
| `bolsa_nivel_valor` | number |
| `bolsa_nivel_id` | integer |
| `bolsa_nome` | string |
| `bolsa_sigla` | string |
| `formulario_cancel_bolsa_id` | integer |
| `formulario_cancel_bolsa_data` | string/date |
| `formulario_cancel_bolsa_situacao` | integer |
| `formulario_subst_bolsa_id` | integer |
| `formulario_subst_bolsa_data` | string/date |
| `formulario_subst_bolsa_situacao` | integer |
| `qtd_bolsas_paga` | integer |
| `folhas_pagamentos` | array |

Campos de `folhas_pagamentos`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `folha_pagamento_id` | integer | Codigo da folha de pagamento. |
| `folha_pagamento_data` | date | Data da folha. |
| `folha_pagamento_gerada` | date | Data de geracao. |
| `folha_pagamento_pesquisador_valor` | number/double | Valor pago. |

### Pesquisador

Consulta dados de um pesquisador.

```http
POST /webServicesSig/consulta.php/pesquisador
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "pesquisador",
  "codpes": 48409
}
```

Campos em `data`:

| Campo |
| --- |
| `pesquisador_id` |
| `pesquisador_nome` |
| `pesquisador_nascimento` |
| `pesquisador_sexo` |
| `pesquisador_mae` |
| `pesquisador_rg` |
| `pesquisador_orgao_emissor` |
| `rg_uf` |
| `pesquisador_email` |
| `pesquisador_telefone_res` |
| `pesquisador_telefone` |
| `pesquisador_celular` |
| `pesquisador_passaporte` |
| `pesquisador_url_lattes` |
| `instituicao_id` |
| `pesquisador_departamento` |
| `endereco_res_id` |
| `endereco_id` |
| `endereco_rua` |
| `endereco_bairro` |
| `endereco_numero` |
| `endereco_complemento` |
| `endereco_cep` |
| `municipio_nome` |
| `estado_nome` |
| `estado_uf` |
| `instituicao_nome` |
| `instituicao_sigla` |

Observacao: o Swagger marca quase todos esses campos como `integer`, inclusive campos que devem ser texto, como nome, email, endereco e sigla. A implementacao deve aceitar tipos flexiveis ate que respostas reais sejam validadas.

### Modalidades De Bolsas

Consulta modalidades de bolsas e seus niveis.

```http
POST /webServicesSig/consulta.php/modalidade_bolsas
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "modalidade_bolsas"
}
```

Campos em `data`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `bolsa_id` | integer | Codigo da bolsa. |
| `bolsa_nome` | string | Nome da bolsa. |
| `bolsa_sigla` | string | Sigla da bolsa. |
| `bolsa_ativa` | boolean | Status da bolsa. O Swagger indica `0` para inativo e `1` para ativo. |
| `nivel` | array | Niveis da bolsa. |

Campos de `nivel`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `bolsa_nivel_id` | integer | Codigo do nivel da bolsa. |
| `bolsa_nivel_nome` | string | Nome do nivel da bolsa. |
| `bolsa_nivel_valor` | number/float | Valor do nivel da bolsa. |
| `bolsa_nivel_ativo` | boolean | Status do nivel. O Swagger indica `0` para inativo e `1` para ativo. |

### Situacao De Projeto

Consulta tipos de situacao do projeto.

```http
POST /webServicesSig/consulta.php/situacao_projeto
```

```json
{
  "token": "TOKEN_JWT",
  "funcao": "situacao_projeto"
}
```

Campos em `data`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `situacao_id` | integer | Codigo da situacao do projeto. |
| `situacao_descricao` | string | Descricao da situacao do projeto. |
| `situacao_status` | string | Status da situacao. |

## Exemplos De Consulta

### Listar Editais

```bash
curl -X POST 'https://servicos.fapes.es.gov.br/webServicesSig/consulta.php/editais' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "TOKEN_JWT",
    "funcao": "editais"
  }'
```

### Listar Projetos De Um Edital

```bash
curl -X POST 'https://servicos.fapes.es.gov.br/webServicesSig/consulta.php/projetos' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "TOKEN_JWT",
    "funcao": "projetos",
    "codedt": 756
  }'
```

### Listar Bolsistas De Um Projeto

```bash
curl -X POST 'https://servicos.fapes.es.gov.br/webServicesSig/consulta.php/bolsistas' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "TOKEN_JWT",
    "funcao": "bolsistas",
    "codprj": 48409
  }'
```

## Ordem Recomendada De Consumo

Uma sincronizacao completa pode seguir esta ordem:

1. Autenticar em `/webServicesSig/auth.php`.
2. Consultar dados auxiliares: `setores`, `modalidade_bolsas`, `situacao_projeto`.
3. Consultar `editais`.
4. Para cada edital, consultar `edital_chamadas`, `edital_objetos_filhos` e `projetos`.
5. Para cada projeto, consultar `projeto_bolsas` e `bolsistas`.
6. Para pesquisadores especificos, consultar `pesquisador` com `codpes`.

## Inconsistencias Do Swagger

O contrato publicado tem alguns pontos que devem ser tratados com cuidado:

1. Autenticacao define `username` e `password`, mas marca `token` e `funcao` como obrigatorios.
2. Os endpoints usam placeholders como `{editais}` e `{projetos}`, mas nao declaram parametros de path.
3. `codedt`, `codprj` e `codpes` nao aparecem como obrigatorios, embora sejam necessarios para consultas especificas.
4. A seguranca global declara `bearerAuth`, mas os exemplos usam `token` no corpo JSON.
5. `pesquisador` tem tipos provavelmente incorretos, com campos textuais declarados como `integer`.
6. `edital_objetos_filhos` nao informa os campos retornados em `data`.
7. O Swagger documenta a resposta de autenticacao como array, mas a resposta real observada e um objeto com a chave `token`.
8. Algumas descricoes parecem reaproveitadas de outros endpoints.

## Recomendacoes Para Integracao

- Centralizar a geracao e reutilizacao do token JWT.
- Enviar sempre `Content-Type: application/json`.
- Manter o valor de `funcao` igual ao segmento final do endpoint.
- Tratar datas como `string` ate confirmar o formato real de retorno.
- Usar decimal para valores financeiros.
- Implementar desserializacao tolerante a campos ausentes e tipos inconsistentes.
- Corrigir a cadeia de certificados do ambiente caso ocorra erro TLS; evitar `curl -k` ou equivalente em producao.
