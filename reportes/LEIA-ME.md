# Reportes de problemas (para corrigir com o Claude)

Objetivo: recolher os erros que as funcionárias encontram, com evidência, de
forma a corrigir tudo no mesmo dia sem idas e voltas.

## Como reportar UM problema

1. Copia a pasta `_TEMPLATE` e renomeia para `NN_descricao_curta`
   (ex: `01_estrangeiro_pais`, `02_data_bem`).
2. Abre o `problema.md` lá dentro e preenche (2 linhas chegam).
3. Larga na pasta os anexos que tiveres:
   - **print** do SIMN/app com o erro,
   - **cópia do `campos.json`** (de `partilha/campos.json`, LOGO após a corrida,
     senão a corrida seguinte apaga-o),
   - **`log.txt`** se correste pela consola (ver dica abaixo),
   - o **`.doc`** só se for erro de extração.

## Como me enviar (fim da manhã / em lotes)

Junta 5 a 10 problemas, faz **zip da pasta `reportes/`** e passa-me o caminho do
zip (como o `refeito.zip` de ontem). Eu abro, triago tudo de uma vez, agrupo por
causa e corrijo em série. Também podes colar o conteúdo de um `problema.md` aqui
no chat e arrastar os prints, se for um caso urgente e isolado.

## Duas dicas que aceleram o diagnóstico

- **Diz sempre o tipo de ato.** O robô ramifica por tipo; o mesmo campo pode
  comportar-se diferente numa habilitação e numa compra-venda.
- **Hoje, corre a app pela consola** (`iniciar_app.bat`, não o atalho VBS). Assim
  o robô imprime o que está a fazer ("A preencher outorgante... Estrangeiro...
  País=...") e esse texto (o `log.txt`) diz-me logo onde derrapou.

> Nota: as pastas de problemas (prints, campos.json) NÃO vão para o git (têm
> dados pessoais). Só este LEIA-ME e o `_TEMPLATE` é que ficam versionados.
