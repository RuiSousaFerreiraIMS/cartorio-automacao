# Checklist para hoje no cartório — versão reduzida

**Já cobrimos 80% com os materiais de ontem.** Hoje é validação + 3 testes.

## Antes de começar (5 min)

- [ ] Enviar-te por email os ficheiros novos:
      - `peca_b_robo/robo.py`
      - `peca_b_robo/robo_actions.py`
      - `peca_b_robo/robo_forms.py`
      - `peca_b_robo/robo_fluxos.py`
      - `peca_b_robo/imagens/` (pasta inteira com os 10 PNGs)
- [ ] Copiar para o mesmo sítio no PC do cartório (ex: Desktop)
      Manter a mesma estrutura de pastas: `imagens/` dentro de `peca_b_robo/`
- [ ] SIMN aberto → Gestão de Actos e Escrituras

## Teste 1 — validar recortes de botões (5 min) ⚡

**Objectivo:** confirmar que as imagens dos botões que gerei aqui batem com o
SIMN do cartório. Se batem, tudo o resto anda.

- [ ] Criar Nova Escritura → Compra-venda → ficar no ecrã principal (sem
      adicionar nada)
- [ ] No PowerShell no PC do cartório:
```powershell
cd C:\Users\Posto5\Desktop\peca_b_robo
python -c "import pyautogui; p = pyautogui.locateOnScreen('imagens/btn_adicionar_vendedor.png', confidence=0.85); print('Adicionar Vendedor:', p)"
```
- [ ] Anotar resultado:
      - Se aparece `Box(left=..., top=..., ...)` → BOTÃO ENCONTRADO ✅
      - Se aparece `None` ou erro → tirar screenshot do ecrã actual e enviar

- [ ] Repetir para `btn_adicionar_bem.png` e `btn_nova_relacao.png`

Se **os três** botões forem encontrados, os recortes servem. Se **algum** falhar,
enviar-me o screenshot do ecrã principal SIMN que apareceu, para eu re-cortar.

## Teste 2 — robô com fluxo completo CV mínimo (10 min)

**Objectivo:** correr `robo.py` e ver se ele navega sozinho pelos sub-forms.

- [ ] SIMN ainda no ecrã principal da CV vazio
- [ ] No PowerShell:
```powershell
python robo.py
```
- [ ] Alt+Tab para o SIMN quando aparecer a contagem decrescente
- [ ] **NÃO mexer no teclado ou rato durante 30-60s**
- [ ] Anotar tudo o que aconteceu (mesmo que caótico):
      - O que preencheu bem?
      - Onde parou / travou?
      - Ficou em que ecrã no fim?

## Teste 3 (só se der tempo) — screenshot Doação (2 min)

- [ ] Cancelar/apagar a CV se ficou no meio
- [ ] Criar Nova Escritura → **Doação**
- [ ] Ecrã principal Doação com árvore esquerda visível
- [ ] Tirar screenshot (Win+Shift+S ou impressão de ecrã) e enviar

Isto vai-me permitir recortar os botões `Adicionar Doador(es)` e
`Adicionar Donatário(s)` para o fluxo Doação. Não é urgente hoje.

## O que trazer

Numa só mensagem/email:
1. Resultado do Teste 1 (3 linhas de output ou screenshot se falhou)
2. Descrição livre do Teste 2 (o que viu acontecer)
3. Screenshot Doação (se der tempo)

## O que NÃO precisas de fazer

- **Não** tens de fazer aquela checklist longa que te dei ontem à noite. Foi
  cautela a mais.
- **Não** tens de mapear ordens de Tabs — os que uso vieram do video e dos
  screenshots.
- **Não** tens de tirar novos recortes de botões CV — já tenho.
