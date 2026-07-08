# Automacao do Cartorio

Le escrituras .doc/.docx, extrai os campos, valida com humano, e (Peca B) preenche o SIMN.

## Dois ficheiros de contexto
- `CLAUDE.md` - lido automaticamente pelo Claude Code no arranque (operacional).
- `CONTEXTO_PROJETO.md` - contexto narrativo completo (decisoes, ROI, historico).
  Cola este nas instrucoes do Project no Claude.ai.

## Estrutura
- `peca_a_extracao/` - extracao + interface Streamlit (desenvolve-se sem SIMN)
  - `modelos.py` - schemas Pydantic (o alicerce)
  - `extrator.py` - .doc/.docx -> CompraVenda via Claude API
  - `app.py` - interface mediadora (carregar/rever/exportar)
- `peca_b_robo/` - robo PyWinAuto (desenvolve-se no cartorio, contra o SIMN real)
- `partilha/campos.json` - o "contrato" entre as duas pecas
- `partilha/campos_exemplo.json` - exemplo real ja extraido
- `exemplos/` - escrituras reais de teste

## Arrancar (Peca A)
```bash
# 1. Instalar LibreOffice na maquina (le os .doc antigos). Nao e pacote pip.
# 2. Dependencias Python:
pip install -r requirements.txt
# 3. Chave da API:
export ANTHROPIC_API_KEY=...
# 4. Testar extracao:
cd peca_a_extracao
python extrator.py ../exemplos/CV_fracao_entre_particulares.doc
# 5. Interface:
streamlit run app_v2_backup.py   # abre em http://localhost:8501
```

## Ordem de construcao
schema -> extracao -> interface -> robo. Os 3 primeiros fazem-se sem SIMN.

Ver CONTEXTO_PROJETO.md para tudo o resto.
