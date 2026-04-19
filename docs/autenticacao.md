# Autenticacao Da API FAPES

Este documento descreve como realizar a autenticacao na API FAPES `webServicesSig`.

## Endpoint De Autenticacao

Para gerar o token JWT de acesso, envie uma requisicao `POST` para:

```text
https://servicos.fapes.es.gov.br/webServicesSig/auth.php
```

O endpoint espera um corpo JSON com usuario e senha.

## Variaveis De Ambiente

As credenciais devem ser configuradas no arquivo `.env` da raiz do projeto.

```dotenv
FAPES_AUTH_URL="https://servicos.fapes.es.gov.br/webServicesSig/auth.php"
FAPES_USUARIO="..."
FAPES_SENHA="..."
```

O arquivo `.env` contem credenciais locais e nao deve ser versionado.

## Requisicao

```http
POST /webServicesSig/auth.php
Content-Type: application/json
```

Corpo:

```json
{
  "username": "VALOR_DE_FAPES_USUARIO",
  "password": "VALOR_DE_FAPES_SENHA"
}
```

Exemplo com `curl`, usando variaveis de ambiente ja carregadas:

```bash
curl -X POST "$FAPES_AUTH_URL" \
  -H 'Content-Type: application/json' \
  -d "{
    \"username\": \"$FAPES_USUARIO\",
    \"password\": \"$FAPES_SENHA\"
  }"
```

## Resposta Esperada

Com as credenciais corretas, a API retorna um objeto JSON com o token JWT:

```json
{
  "token": "TOKEN_JWT"
}
```

Esse token deve ser enviado no corpo JSON das consultas posteriores, no campo `token`.

Exemplo:

```json
{
  "token": "TOKEN_JWT",
  "funcao": "editais"
}
```

## Resposta Com Credenciais Invalidas

Quando as credenciais estao incorretas, a API pode retornar:

```http
401 Unauthorized
```

```json
{
  "message": "Credenciais inv\u00e1lidas."
}
```
