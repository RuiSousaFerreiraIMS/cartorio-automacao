# CLAUDE.md — Instruções para o Claude Code neste projeto

> Lê este ficheiro no arranque. Para o contexto narrativo completo (decisões,
> ROI, histórico), vê `CONTEXTO_PROJETO.md`. Este ficheiro é o operacional.

## O que é o projeto

Automatizar o registo de escrituras no **SIMN** (app desktop Windows do cartório do
Notário Rui Ferreira, Alcobaça). Uma escritura .doc entra, os campos são extraídos e
validados por um humano, e um robô preenche o SIMN. ~150 atos/mês. Objetivo do notário:
**prático, não perfeito**. Validação humana é obrigatória, sempre.

## Arquitetura: DUAS peças desacopladas, ligadas por um JSON. Nunca entrelaçar.

```
escritura .doc -> [PEÇA A: extração + interface Streamlit] -> campos.json -> [PEÇA B: robô PyWinAuto] -> SIMN
```

- A validação humana acontece na Peça A (no ecrã), ANTES de o robô correr.
- O robô só executa o que já foi aprovado. Nunca carregar em Gravar/Registar sozinho.

## Stack (decidida, não trocar sem motivo)

- Python para tudo.
- Peça A: `python-docx` (.docx) + LibreOffice/antiword (.doc antigo) + Gemini API
  (`google-genai` SDK, modelo gemini-2.5-flash) + Pydantic (validação) + Streamlit.
- Peça B: PyWinAuto (SIMN é app desktop nativa .exe, NÃO web; logo não é Playwright).
- Tudo corre LOCAL na máquina do cartório. Não cloud. Único dado que sai: texto da
  escritura para a Gemini API.

## Estrutura de ficheiros

- `peca_a_extracao/modelos.py` — schemas Pydantic (CompraVenda, Outorgante, Bem, DUC). O alicerce.
- `peca_a_extracao/extrator.py` — lê .doc/.docx, chama a Gemini API, devolve CompraVenda validado.
- `peca_a_extracao/app.py` — interface Streamlit (carregar, rever, exportar campos.json).
- `peca_b_robo/robo.py` — STUB. Só se desenvolve no cartório, contra o SIMN real.
- `partilha/campos.json` — o contrato entre as peças (a Peça A escreve, a Peça B lê).
- `partilha/campos_exemplo.json` — exemplo real já extraído, para referência.
- `exemplos/` — escrituras reais de teste.

## Comandos úteis

```bash
pip install -r requirements.txt
export GOOGLE_API_KEY=...                # necessário para o extrator (chave do AI Studio)
# testar extração numa escritura:
cd peca_a_extracao && python extrator.py ../exemplos/CV_fracao_entre_particulares.doc
# correr a interface:
cd peca_a_extracao && streamlit run app_v2_backup.py   # abre em localhost:8501
```

## Regras de trabalho (importantes)

- **Sem em-dashes** no texto escrito. Usar vírgulas, parênteses ou pontos.
- Tom direto, aplicado, iterativo. Nunca vender IA onde automação simples chega.
- Ler .doc antigo exige LibreOffice (ou antiword) instalado na máquina. Não é pacote pip.
- A Peça B NÃO se testa fora do cartório (não há SIMN aqui). Só escrever esqueleto/lógica.
- O extrator nunca inventa dados: campo não encontrado = null. Validação humana apanha o resto.
- O JSON de saída é validado por Pydantic. Se mexes nos campos, atualiza `modelos.py` primeiro.

## Factos do domínio (aprendidos com escrituras reais)

- Outorgantes aparecem em blocos "Primeiro:/Segundo:". Um bloco pode ser um CASAL
  (2 NIFs "respectivamente"). Separar em 2 outorgantes ligados por `conjuge_de_nif`.
- O papel (vendedor/comprador) define-se pela redação ("vendem ao segundo outorgante"),
  não pela ordem cega.
- Preço vem POR EXTENSO ("DUZENTOS E OITENTA MIL EUROS" = 280000.0). O LLM converte.
- DUCs (IMT + TGIS) aparecem como nº de documento no "Arquivo". O MONTANTE não está na
  escritura (vem das Finanças). Provavelmente passo manual, confirmar no vídeo.
- `codigo_simn` (ex: 100108-U-1948) é interno do SIMN, NÃO vem da escritura.
- Não fiar pelo título interno do .doc (um dizia "PARTILHA" sendo compra-venda).

## Perguntas em aberto (resolver com o vídeo do SIMN)

1. Outorgantes inseridos só por NIF (já na base do SIMN) ou escritos de raiz?
2. De onde vem o `codigo_simn` do bem? (base / pesquisa predial / à mão?)
3. O DUC (montante) é colado à mão das Finanças? (confirmar que fica fora do âmbito do robô)
4. O campo "Objeto" (texto grande do SIMN): o que a funcionária escreve lá?
