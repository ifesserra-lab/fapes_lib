# language: pt

@epic-003 @extracao
Funcionalidade: Extracao encadeada de dados da API FAPES
  Como consumidor da biblioteca fapes_lib
  Quero executar fluxos de extracao compostos
  Para obter dados relacionados da API FAPES em uma estrutura coerente

  Contexto:
    Dado que a biblioteca esta autenticada
    E que as consultas diretas da API estao disponiveis

  @us-014
  Cenario: Extrair cadastros auxiliares
    Quando eu executar a extracao de cadastros auxiliares
    Entao a biblioteca deve consultar setores
    E deve consultar modalidades de bolsas
    E deve consultar situacoes de projeto
    E o resultado deve identificar a origem de cada conjunto de dados

  @us-015
  Cenario: Extrair editais com chamadas
    Dado que a API possui editais retornados
    Quando eu executar a extracao de editais com chamadas
    Entao a biblioteca deve consultar chamadas para cada edital com identificador
    E cada edital deve preservar sua lista de chamadas

  @us-016
  Cenario: Extrair editais com projetos
    Dado que a API possui editais retornados
    Quando eu executar a extracao de editais com projetos
    Entao a biblioteca deve consultar projetos para cada edital com identificador
    E cada edital deve preservar sua lista de projetos

  @us-017
  Cenario: Extrair projetos com bolsas e bolsistas
    Dado que a API possui projetos retornados
    Quando eu executar a extracao de projetos com bolsas e bolsistas
    Entao a biblioteca deve consultar bolsas para cada projeto
    E deve consultar bolsistas para cada projeto
    E cada projeto deve preservar suas bolsas e seus bolsistas

  @us-018 @smoke
  Cenario: Executar extracao completa em ordem previsivel
    Quando eu executar a extracao completa
    Entao a biblioteca deve autenticar antes das consultas quando necessario
    E deve extrair cadastros auxiliares
    E deve extrair editais
    E deve extrair dados relacionados aos editais
    E deve retornar dados e metadados da execucao

  @erro
  Cenario: Falha em consulta encadeada
    Dado que uma consulta encadeada retorna erro
    Quando eu executar a extracao completa
    Entao a biblioteca deve informar qual etapa falhou
    E nao deve retornar sucesso silencioso
    E a mensagem nao deve expor senha ou token

  @sem-dados
  Cenario: Extracao sem dados encontrados
    Dado que a API responde sem registros encontrados
    Quando eu executar uma extracao
    Entao a biblioteca deve retornar resultado vazio de forma explicita
    E deve preservar metadados da consulta
