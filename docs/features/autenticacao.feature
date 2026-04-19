# language: pt

@epic-001 @autenticacao
Funcionalidade: Autenticacao na API FAPES
  Como consumidor da biblioteca fapes_lib
  Quero autenticar na API FAPES usando variaveis de ambiente
  Para obter um token JWT usado nas consultas

  Contexto:
    Dado que a URL de autenticacao da FAPES esta configurada

  @us-001 @configuracao
  Cenario: Carregar credenciais configuradas no ambiente
    Dado que FAPES_USUARIO esta configurado
    E que FAPES_SENHA esta configurado
    Quando a biblioteca carregar a configuracao
    Entao as credenciais devem ficar disponiveis para autenticacao
    E a senha nao deve ser exibida em logs ou mensagens

  @us-001 @erro
  Cenario: Falhar quando credenciais obrigatorias nao estao configuradas
    Dado que uma credencial obrigatoria da FAPES nao esta configurada
    Quando a biblioteca carregar a configuracao
    Entao um erro de configuracao deve ser informado
    E a mensagem deve indicar qual configuracao esta ausente
    Mas a mensagem nao deve expor senha ou token

  @us-002 @us-003 @smoke
  Cenario: Autenticacao com sucesso
    Dado que as credenciais da FAPES estao configuradas
    E que a API de autenticacao retorna um token JWT
    Quando eu solicito um token de autenticacao
    Entao a biblioteca deve armazenar o token em memoria
    E o token deve ficar disponivel para as proximas consultas
    Mas o token completo nao deve ser exibido em logs ou mensagens

  @us-004 @erro
  Cenario: Credenciais invalidas
    Dado que as credenciais configuradas sao invalidas
    Quando eu solicito um token de autenticacao
    Entao a biblioteca deve informar erro de autenticacao
    E a mensagem de erro nao deve expor a senha enviada

  @us-004 @erro
  Cenario: Resposta de autenticacao sem token
    Dado que as credenciais da FAPES estao configuradas
    E que a API de autenticacao responde sem o campo token
    Quando eu solicito um token de autenticacao
    Entao a biblioteca deve informar erro de resposta invalida
    E nenhuma consulta deve ser executada sem token valido
