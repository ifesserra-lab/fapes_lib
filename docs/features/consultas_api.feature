# language: pt

@epic-002 @consultas
Funcionalidade: Consultas diretas na API FAPES
  Como consumidor da biblioteca fapes_lib
  Quero consultar os endpoints documentados da API FAPES
  Para obter dados de editais, projetos, bolsas, bolsistas e cadastros auxiliares

  Contexto:
    Dado que existe um token JWT valido
    E que a biblioteca esta autenticada na API FAPES

  @us-005
  Cenario: Consultar setores
    Quando eu consultar a funcao "setores"
    Entao a biblioteca deve retornar a lista de setores
    E cada setor deve preservar os campos sigla e descricao quando existirem

  @us-006 @smoke
  Cenario: Consultar editais
    Quando eu consultar a funcao "editais"
    Entao a biblioteca deve retornar os editais encontrados
    E a resposta deve preservar os metadados encontrado, msg, erro e qtd

  @us-007
  Cenario: Consultar chamadas de um edital
    Dado que existe um codigo de edital "756"
    Quando eu consultar chamadas do edital
    Entao a biblioteca deve enviar o parametro codedt
    E deve retornar as chamadas encontradas para o edital

  @us-007 @erro
  Cenario: Falhar ao consultar chamadas sem codigo de edital
    Dado que nao existe codigo de edital informado
    Quando eu consultar chamadas do edital
    Entao a biblioteca deve informar erro de validacao
    E nenhuma requisicao HTTP deve ser enviada

  @us-008
  Cenario: Consultar projetos de um edital
    Dado que existe um codigo de edital "756"
    Quando eu consultar projetos do edital
    Entao a biblioteca deve enviar o parametro codedt
    E deve retornar projetos vinculados ao edital

  @us-009
  Cenario: Consultar bolsas de um projeto
    Dado que existe um codigo de projeto "48409"
    Quando eu consultar bolsas do projeto
    Entao a biblioteca deve enviar o parametro codprj
    E deve retornar bolsas vinculadas ao projeto

  @us-010
  Cenario: Consultar bolsistas de um projeto
    Dado que existe um codigo de projeto "48409"
    Quando eu consultar bolsistas do projeto
    Entao a biblioteca deve enviar o parametro codprj
    E deve retornar bolsistas vinculados ao projeto
    E deve preservar folhas de pagamento quando existirem

  @us-011
  Cenario: Consultar pesquisador
    Dado que existe um codigo de pesquisador "48409"
    Quando eu consultar o pesquisador
    Entao a biblioteca deve enviar o parametro codpes
    E deve retornar os dados do pesquisador de forma tolerante a tipos inconsistentes

  @us-012
  Cenario: Consultar modalidades de bolsas
    Quando eu consultar a funcao "modalidade_bolsas"
    Entao a biblioteca deve retornar modalidades de bolsas
    E deve preservar niveis de bolsa aninhados

  @us-013
  Cenario: Consultar situacoes de projeto
    Quando eu consultar a funcao "situacao_projeto"
    Entao a biblioteca deve retornar situacoes de projeto

  @erro
  Cenario: Token invalido
    Dado que o token JWT disponivel e invalido
    Quando eu consultar a funcao "editais"
    Entao a biblioteca deve informar erro de autenticacao ou autorizacao
    E a mensagem nao deve exibir o token completo

  @envelope
  Esquema do Cenario: Interpretar envelope padrao de consulta
    Dado que a API respondeu com encontrado igual a "<encontrado>"
    Quando a biblioteca interpretar o envelope da consulta
    Entao o resultado deve conter a lista de dados
    E deve preservar a quantidade informada em qtd

    Exemplos:
      | encontrado |
      | 0          |
      | 1          |
