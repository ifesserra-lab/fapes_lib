# EPIC-001: Autenticacao Da API FAPES

## Status

Planejada.

## Objetivo

Permitir que a biblioteca autentique na API FAPES usando credenciais de ambiente e disponibilize um token JWT para consultas posteriores.

## Escopo

Inclui:

- carregar variaveis do `.env`;
- validar credenciais obrigatorias;
- enviar requisicao `POST` para `https://servicos.fapes.es.gov.br/webServicesSig/auth.php`;
- extrair o campo `token` da resposta;
- manter o token em memoria durante o ciclo de vida do cliente;
- tratar falhas sem expor senha ou token.

Nao inclui:

- persistir token em disco;
- renovar token automaticamente sem necessidade demonstrada;
- implementar UI ou CLI;
- versionar credenciais reais.

## Dependencias

- Arquitetura: issue #1.
- Documentacao de autenticacao: `docs/autenticacao.md`.
- Feature BDD: `docs/features/autenticacao.feature`.

## User Stories

### US-001: Carregar Credenciais Do Ambiente

Como consumidor da biblioteca, quero carregar as credenciais da FAPES a partir do `.env`, para evitar hardcode de usuario e senha no codigo.

Criterios de aceite:

- Dado que `FAPES_AUTH_URL`, `FAPES_USUARIO` e `FAPES_SENHA` estao definidos, quando a configuracao for carregada, entao os valores devem estar disponiveis para autenticacao.
- Dado que uma variavel obrigatoria esta ausente, quando a configuracao for carregada, entao a biblioteca deve gerar erro de configuracao.
- A mensagem de erro nao deve exibir `FAPES_SENHA`.

### US-002: Autenticar No Endpoint Da FAPES

Como consumidor da biblioteca, quero solicitar autenticacao na API FAPES, para obter um token JWT valido.

Criterios de aceite:

- A requisicao deve usar `POST`.
- A URL deve vir de `FAPES_AUTH_URL`.
- O corpo deve conter `username` e `password`.
- A resposta com `token` deve ser aceita como sucesso.

### US-003: Disponibilizar Token Para Consultas

Como consumidor da biblioteca, quero que o token autenticado fique disponivel para consultas, para nao precisar autenticar manualmente a cada chamada.

Criterios de aceite:

- Depois de autenticar, o cliente deve conseguir incluir o token nas consultas.
- O token deve ficar encapsulado no objeto responsavel.
- O token completo nao deve ser retornado em representacoes textuais ou logs.

### US-004: Tratar Falhas De Autenticacao

Como consumidor da biblioteca, quero receber erro claro quando a autenticacao falhar, para corrigir credenciais ou diagnosticar indisponibilidade.

Criterios de aceite:

- Credenciais invalidas devem gerar erro de autenticacao.
- Resposta sem `token` deve gerar erro de resposta.
- Erros de rede devem ser encapsulados em erro da biblioteca.
- Nenhum erro deve expor senha ou token.

## Estrategia De Testes

Seguir TDD:

1. Testar configuracao valida.
2. Testar configuracao ausente.
3. Testar autenticacao com HTTP mockado retornando `token`.
4. Testar credenciais invalidas.
5. Testar resposta sem `token`.
6. Testar mascaramento de credenciais em mensagens de erro.

## Riscos

- O Swagger documenta autenticacao de forma inconsistente.
- A API pode alterar formato de resposta.
- O ambiente local pode ter problema de cadeia TLS.

## Anti-Patterns Evitados

- Credenciais hardcoded.
- Token global mutavel.
- Falha silenciosa quando o token nao vem na resposta.
- Log de senha ou token.

## Rastreabilidade

- Feature: `docs/features/autenticacao.feature`.
- Arquitetura: `docs/architecture.md`.
- Issue: #2.
