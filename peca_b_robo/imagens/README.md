# Imagens dos botões do SIMN

Esta pasta contém pequenos PNGs recortados de botões do SIMN. O robô usa-os
para os encontrar no ecrã, seja qual for a resolução ou posição da janela.

## Como criar cada imagem

1. Abre o SIMN no ecrã correspondente.
2. Usa a **Ferramenta de Recorte** do Windows (`Win + Shift + S`).
3. Recorta **apenas o botão**, com pouca margem à volta.
4. Guarda com o nome exacto listado abaixo, dentro desta pasta.

## Ficheiros necessários

Nome exacto, PNG, ~40-100px de largura, sem fundo transparente:

- `btn_adicionar_vendedor.png` — botão "Adicionar Vendedor(es)" na árvore esquerda
- `btn_adicionar_comprador.png` — botão "Adicionar Comprador(es)"
- `btn_adicionar_doador.png` — botão "Adicionar Doador(es)"
- `btn_adicionar_donatario.png` — botão "Adicionar Donatário(s)"
- `btn_adicionar_bem.png` — botão "Adicionar bem"
- `btn_novo_singular.png` — botão "Novo Outorgante Singular" (diálogo Adicionar Outorgante)
- `btn_novo_duc.png` — botão "Novo DUC" no painel direito
- `btn_nova_relacao.png` — botão "Nova Relação"
- `btn_ok.png` — botão OK dos diálogos (o normal, azul-claro)

## Dicas

- Se o botão aparece pouco frequente, tira o recorte com o rato **em cima**
  do botão (highlighted) e outro sem. Guarda o mais neutro.
- Evita recortar texto que muda (ex: contadores dinâmicos).
- Se o robô diz "botão X não encontrado", verifica se a imagem está desta pasta
  e se o nome está exacto (case-sensitive).
