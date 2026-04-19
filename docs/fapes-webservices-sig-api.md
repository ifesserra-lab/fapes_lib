# API FAPES WebServicesSig

Documentacao de referencia para integracao com a API publica documentada em:

- Swagger UI: <https://servicos.fapes.es.gov.br/webServicesSig/>
- OpenAPI JSON: <https://servicos.fapes.es.gov.br/webServicesSig/swagger.json>

Consulta realizada em 2026-04-19.

## Visao Geral

A API `webServicesSig` expoe informacoes relacionadas a FAPES, como editais, chamadas, projetos, bolsas, bolsistas, pesquisadores, setores e situacoes de projeto.

O Swagger declara OpenAPI `3.0.0`, titulo `API FAPES`, versao `1.0.0`.

Base URL observada:

```text
https://servicos.fapes.es.gov.br
```

Ao acessar `https://servicos.fapes.es.gov.br/webServicesSig/`, o servidor redireciona para:

```text
https://servicos.fapes.es.gov.br/webServicesSig/swagger.php
```

A UI carrega o arquivo:

```text
https://servicos.fapes.es.gov.br/webServicesSig/swagger.json
```

Todas as operacoes documentadas usam `POST` com corpo JSON.

## Observacao Sobre TLS

Durante a consulta local, `curl` falhou na validacao da cadeia TLS com:

```text
SSL certificate problem: unable to get local issuer certificate
```

Para inspecionar a API, foi necessario usar `curl -k`. Em clientes de producao, prefira corrigir a cadeia de certificados confiaveis do ambiente em vez de desabilitar validacao TLS.

## Fluxo De Autenticacao

O fluxo esperado e:

1. Enviar usuario e senha para gerar um token JWT.
2. Enviar o token no corpo JSON das consultas.

Apesar de o OpenAPI declarar `bearerAuth`, os exemplos oficiais indicam o uso do campo `token` dentro do corpo da requisicao. A resposta real para token invalido tambem confirma que o corpo JSON e analisado pela API.

### Gerar Token

Endpoint documentado:

```http
POST /webServicesSig/auth.php/{autenticacao}
Content-Type: application/json
```

Uso pratico confirmado:

```http
POST /webServicesSig/auth.php
Content-Type: application/json
```

As credenciais devem ser mantidas no arquivo `.env` da raiz do projeto:

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
  "token": "jwt..."
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

## Convencoes Das Consultas

As consultas usam o endpoint:

```http
POST /webServicesSig/consulta.php/{funcao}
Content-Type: application/json
```

O corpo sempre inclui:

```json
{
  "token": "jwt...",
  "funcao": "nome_da_funcao"
}
```

Algumas consultas exigem tambem um identificador:

- `codedt`: codigo de identificacao do edital.
- `codprj`: codigo de identificacao do projeto.
- `codpes`: codigo de identificacao do pesquisador.

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

Campos comuns:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `data` | array | Resultado da consulta. |
| `encontrado` | integer | `0` quando nao ha resultado, `1` quando ha resultado. |
| `msg` | string | Mensagem de retorno. |
| `erro` | string | Descricao do erro, quando existir. |
| `qtd` | integer | Quantidade de linhas retornadas. |

A consulta de setores e uma excecao no Swagger: ela aparece retornando diretamente uma lista de objetos com `sigla` e `descricao`, sem o envelope `data`.

## Catalogo De Endpoints

| Funcao | Endpoint | Campos no corpo |
| --- | --- | --- |
| Autenticacao | `/webServicesSig/auth.php` | `username`, `password` |
| Setores | `/webServicesSig/consulta.php/{setores}` | `token`, `funcao` |
| Editais | `/webServicesSig/consulta.php/{editais}` | `token`, `funcao` |
| Chamadas de edital | `/webServicesSig/consulta.php/{edital_chamadas}` | `token`, `funcao`, `codedt` |
| Objetos filhos do edital | `/webServicesSig/consulta.php/{edital_objetos_filhos}` | `token`, `funcao`, `codedt` |
| Projetos de edital | `/webServicesSig/consulta.php/{projetos}` | `token`, `funcao`, `codedt` |
| Bolsas de projeto | `/webServicesSig/consulta.php/{projeto_bolsas}` | `token`, `funcao`, `codprj` |
| Bolsistas de projeto | `/webServicesSig/consulta.php/{bolsistas}` | `token`, `funcao`, `codprj` |
| Pesquisador | `/webServicesSig/consulta.php/{pesquisador}` | `token`, `funcao`, `codpes` |
| Modalidades de bolsas | `/webServicesSig/consulta.php/{modalidade_bolsas}` | `token`, `funcao` |
| Situacao de projeto | `/webServicesSig/consulta.php/{situacao_projeto}` | `token`, `funcao` |

## Endpoints Em Detalhe

### Setores

Consulta gerencias e nucleos da FAPES.

```http
POST /webServicesSig/consulta.php/setores
Content-Type: application/json
```

```json
{
  "token": "jwt...",
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
Content-Type: application/json
```

```json
{
  "token": "jwt...",
  "funcao": "editais"
}
```

Campos em `data`:

| Campo | Tipo | Descricao documentada |
| --- | --- | --- |
| `edital_id` | integer | Numero de identificacao do projeto no SigFapes. |
| `edital_nome` | string | Titulo do projeto registrado no SigFapes. |
| `edital_data` | string/date | Data de cadastro no SigFapes. |
| `edital_numero_ano` | string | Numero e ano do edital. |

### Chamadas De Edital

Consulta chamadas de um edital.

```http
POST /webServicesSig/consulta.php/edital_chamadas
Content-Type: application/json
```

```json
{
  "token": "jwt...",
  "funcao": "edital_chamadas",
  "codedt": 756
}
```

Campos em `data`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `edital_id` | integer | Codigo de identificacao do edital. |
| `edital_chamada_id` | integer | Codigo de identificacao da chamada. |
| `edital_chamada_vigencia_entrada` | string/date | Inicio do prazo para envio das propostas. |
| `edital_chamada_vigencia_saida` | string/date | Prazo final para envio das propostas. |

### Objetos Filhos Do Edital

Consulta objetos filhos de um edital.

```http
POST /webServicesSig/consulta.php/edital_objetos_filhos
Content-Type: application/json
```

```json
{
  "token": "jwt...",
  "funcao": "edital_objetos_filhos",
  "codedt": 756
}
```

O Swagger documenta o envelope comum, mas nao declara os campos internos de `data`. O resumo e a descricao tambem foram copiados de `edital_chamadas`, indicando documentacao incompleta.

### Projetos De Edital

Consulta projetos vinculados a um edital.

```http
POST /webServicesSig/consulta.php/projetos
Content-Type: application/json
```

```json
{
  "token": "jwt...",
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
Content-Type: application/json
```

```json
{
  "token": "jwt...",
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

### Bolsistas De Projeto

Consulta bolsistas de um projeto.

```http
POST /webServicesSig/consulta.php/bolsistas
Content-Type: application/json
```

```json
{
  "token": "jwt...",
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
Content-Type: application/json
```

```json
{
  "token": "jwt...",
  "funcao": "pesquisador",
  "codpes": 48409
}
```

Campos em `data` documentados pelo Swagger:

```text
pesquisador_id
pesquisador_nome
pesquisador_nascimento
pesquisador_sexo
pesquisador_mae
pesquisador_rg
pesquisador_orgao_emissor
rg_uf
pesquisador_email
pesquisador_telefone_res
pesquisador_telefone
pesquisador_celular
pesquisador_passaporte
pesquisador_url_lattes
instituicao_id
pesquisador_departamento
endereco_res_id
endereco_id
endereco_rua
endereco_bairro
endereco_numero
endereco_complemento
endereco_cep
municipio_nome
estado_nome
estado_uf
instituicao_nome
instituicao_sigla
```

O Swagger marca quase todos esses campos como `integer`, inclusive nomes, email, endereco e siglas. Isso provavelmente e erro de documentacao. Em implementacoes, trate esses campos como dados potencialmente textuais e valide por valor real retornado.

### Modalidades De Bolsas

Consulta modalidades de bolsas e seus niveis.

```http
POST /webServicesSig/consulta.php/modalidade_bolsas
Content-Type: application/json
```

```json
{
  "token": "jwt...",
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
| `nivel` | array | Lista de niveis da bolsa. |

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
Content-Type: application/json
```

```json
{
  "token": "jwt...",
  "funcao": "situacao_projeto"
}
```

Campos em `data`:

| Campo | Tipo | Descricao |
| --- | --- | --- |
| `situacao_id` | integer | Codigo da situacao do projeto. |
| `situacao_descricao` | string | Descricao da situacao do projeto. |
| `situacao_status` | string | Status da situacao. |

## Exemplos De Uso Com Curl

Autenticacao:

```bash
curl -X POST "$FAPES_AUTH_URL" \
  -H 'Content-Type: application/json' \
  -d "{
    \"username\": \"$FAPES_USUARIO\",
    \"password\": \"$FAPES_SENHA\"
  }"
```

Consultar editais:

```bash
curl -X POST 'https://servicos.fapes.es.gov.br/webServicesSig/consulta.php/editais' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "SEU_TOKEN_JWT",
    "funcao": "editais"
  }'
```

Consultar projetos de um edital:

```bash
curl -X POST 'https://servicos.fapes.es.gov.br/webServicesSig/consulta.php/projetos' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "SEU_TOKEN_JWT",
    "funcao": "projetos",
    "codedt": 756
  }'
```

Consultar bolsas de um projeto:

```bash
curl -X POST 'https://servicos.fapes.es.gov.br/webServicesSig/consulta.php/projeto_bolsas' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "SEU_TOKEN_JWT",
    "funcao": "projeto_bolsas",
    "codprj": 48409
  }'
```

Consultar bolsistas de um projeto:

```bash
curl -X POST 'https://servicos.fapes.es.gov.br/webServicesSig/consulta.php/bolsistas' \
  -H 'Content-Type: application/json' \
  -d '{
    "token": "SEU_TOKEN_JWT",
    "funcao": "bolsistas",
    "codprj": 48409
  }'
```

## Inconsistencias Encontradas No Swagger

1. O endpoint de autenticacao declara propriedades `username` e `password`, mas marca como obrigatorios `token` e `funcao`. O correto para autenticacao deve ser `username` e `password`.

2. Os endpoints usam placeholders como `{editais}`, `{projetos}` e `{autenticacao}`, mas o Swagger nao declara parametros de path. Na pratica, esses valores funcionam como o nome da funcao no caminho.

3. Consultas que dependem de `codedt`, `codprj` ou `codpes` nao marcam esses campos como obrigatorios no schema, embora sejam necessarios para identificar edital, projeto ou pesquisador.

4. A documentacao global declara seguranca `bearerAuth`, mas os exemplos oficiais usam `token` no corpo JSON. A implementacao deve priorizar o comportamento real da API.

5. O schema de `pesquisador` provavelmente tem tipos errados: campos textuais aparecem como `integer`.

6. O endpoint `edital_objetos_filhos` tem schema de retorno incompleto e descricao repetida de chamadas de edital.

7. O Swagger documenta a resposta de autenticacao como array, mas a resposta real observada e um objeto com a chave `token`.

8. Alguns nomes e descricoes parecem reaproveitados ou inconsistentes, por exemplo `edital_id` em `editais` descrito como identificacao do projeto.

## Recomendacoes Para Implementacao

- Centralize a autenticacao e reutilize o token enquanto ele for valido.
- Envie `Content-Type: application/json` em todas as chamadas.
- Use o campo `funcao` igual ao segmento final do endpoint.
- Modele as respostas com tolerancia a campos ausentes e tipos inconsistentes.
- Trate `encontrado` como flag numerica `0` ou `1`.
- Trate datas inicialmente como `string` e converta apenas depois de confirmar o formato real retornado.
- Use tipo decimal para valores financeiros, como `valor_bolsa`, `orcamento_custo`, `vlrtot`, `bolsa_nivel_valor` e `folha_pagamento_pesquisador_valor`.
- Nao desabilite validacao TLS em producao; corrija o trust store do ambiente se encontrar o mesmo erro de certificado.

## Ordem Sugerida De Consumo

Para sincronizar dados da API, uma ordem natural e:

1. Autenticar em `/webServicesSig/auth.php`.
2. Consultar cadastros auxiliares: `setores`, `modalidade_bolsas`, `situacao_projeto`.
3. Consultar `editais`.
4. Para cada edital, consultar `edital_chamadas`, `edital_objetos_filhos` e `projetos`.
5. Para cada projeto, consultar `projeto_bolsas` e `bolsistas`.
6. Para pessoas especificas, consultar `pesquisador` com `codpes`.

## Referencias

- Swagger UI: <https://servicos.fapes.es.gov.br/webServicesSig/>
- OpenAPI JSON: <https://servicos.fapes.es.gov.br/webServicesSig/swagger.json>
