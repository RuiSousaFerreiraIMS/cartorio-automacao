# Peça B — Robô SIMN

Le `partilha/campos.json` produzido pela Peça A e preenche o SIMN via keyboard/rato.

## Estrutura

- `robo.py` — entry point. Lê o JSON e despacha para o fluxo correcto.
- `robo_actions.py` — helpers pyautogui (escrever, ler campo, clicar por imagem).
- `robo_forms.py` — preenchimento dos sub-forms (outorgante, bem, DUC, relação).
- `robo_fluxos.py` — orquestradores por tipo de acto (CV, Doação, Habilitação, Partilha).
- `imagens/` — recortes PNG dos botões do SIMN (ver `imagens/README.md`).

## Instalar (uma vez, no PC do cartório)

```powershell
pip install pyautogui pywinauto
```

## Correr manualmente

```powershell
python robo.py
```

Assume que `..\partilha\campos.json` existe (produzido pela Peça A).

Ou apontar para um JSON específico:

```powershell
python robo.py C:\Users\Posto5\Desktop\campos.json
```

## Correr através da app Streamlit (recomendado para a funcionária)

Na app, clicar **"Preencher SIMN"** no fundo. A app lança o robô num terminal
separado e mostra instruções passo-a-passo do que a funcionária deve fazer.

## Estado actual (por tipo de acto)

| Tipo | Cobertura |
|---|---|
| CV | Vendedor singular funcional. Múltiplos, comprador, bem, DUC, relação: esqueleto pronto, aguarda mapeamento no cartório. |
| Doação | Esqueleto pronto, aguarda testes. |
| Habilitação | Esqueleto, forms diferentes por mapear. |
| Partilha | Esqueleto, forms diferentes por mapear. |

## Segurança

- O robô **nunca clica em Gravar/Registar**. A funcionária confirma e grava à mão.
- Killswitch: mover o rato para o canto superior esquerdo interrompe tudo.
- `Ctrl+C` no terminal do robô também pára.
