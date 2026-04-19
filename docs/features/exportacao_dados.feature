# language: pt

@epic-004 @exportacao
Funcionalidade: Exportacao de dados extraidos
  Como consumidor da biblioteca fapes_lib
  Quero exportar dados extraidos em formatos simples
  Para usar os resultados em auditorias, planilhas e fluxos de ETL

  Contexto:
    Dado que existem dados extraidos pela biblioteca

  @us-019
  Cenario: Exportar dados em JSON
    Quando eu exportar os dados no formato JSON
    Entao a biblioteca deve gerar um arquivo JSON valido
    E deve preservar estruturas aninhadas
    E deve permitir incluir metadados da extracao

  @us-020
  Cenario: Exportar registros em JSONL
    Dado que existem registros independentes para exportacao
    Quando eu exportar os dados no formato JSONL
    Entao cada linha do arquivo deve conter um JSON valido
    E cada registro deve ocupar uma unica linha

  @us-021
  Cenario: Exportar dados tabulares em CSV
    Dado que os dados extraidos estao em formato tabular
    Quando eu exportar os dados no formato CSV
    Entao a biblioteca deve gerar um arquivo CSV com cabecalho
    E cada linha deve representar um registro

  @us-021 @erro
  Cenario: Falhar ao exportar dados aninhados diretamente para CSV
    Dado que os dados extraidos possuem estruturas aninhadas
    Quando eu exportar os dados no formato CSV sem normalizacao
    Entao a biblioteca deve informar erro de formato incompativel
    E nao deve gerar arquivo parcial como sucesso

  @us-022
  Cenario: Preservar metadados da extracao
    Dado que os dados extraidos possuem metadados de execucao
    Quando eu exportar os dados
    Entao os metadados permitidos devem ser preservados
    Mas senha e token nao devem ser incluidos na saida

  @erro
  Cenario: Destino de escrita invalido
    Dado que o destino de escrita nao esta disponivel
    Quando eu exportar os dados
    Entao a biblioteca deve informar erro de escrita
    E a mensagem deve preservar contexto sem expor credenciais
