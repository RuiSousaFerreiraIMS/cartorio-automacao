r"""
Peca B - CALIBRADOR do form (mapeia a ORDEM REAL dos Tabs).

Porque existe:
  Os tab(N) em robo_forms.preencher_outorgante sao ADIVINHADOS. Quando uma
  contagem esta errada, tudo a seguir desalinha (ex: o "c" de "casado" cai na
  Morada Concelho e dispara o autocomplete). Como o pywinauto nao ve os controls
  Java Swing do SIMN, nao da para verificar a posicao por codigo. Este script
  torna a ordem dos Tabs VISIVEL, com UMA corrida.

MODO MAPA (default):
  A partir do primeiro campo, escreve um marcador numerado ("00", "01", "02", ...)
  em cada paragem de Tab. No fim, tiras UM screenshot do form e ves exactamente
  que campo fisico recebeu que indice. Os campos que ficam VAZIOS sao dropdowns
  ou checkboxes (nao aceitam os digitos) - isso tambem te diz onde estao. Com
  esse mapa, corrigem-se os tab(N) no robo_forms com precisao.

  Escolhi marcadores so com digitos de proposito: nenhuma opcao dos dropdowns do
  SIMN (Estado Civil, Regime, Concelho, Pais...) comeca por numero, portanto os
  digitos NUNCA seleccionam nada por engano num dropdown.

MODO LER (--ler):
  Nao escreve nada. Tab a Tab, le o conteudo de cada campo via clipboard e
  imprime. Util para ver o que o SIMN autopreenche (ex: Nome logo apos NIF).

Uso (NO CARTORIO, com o form Vendedor(es) aberto e o cursor no Nº Contribuinte):
  python peca_b_robo/calibrar_form.py                 # mapa, 25 paragens
  python peca_b_robo/calibrar_form.py --campos 30     # mais paragens
  python peca_b_robo/calibrar_form.py --ler           # so leitura, nao escreve

IMPORTANTE: e uma corrida DESCARTAVEL. Depois de ler o mapa, FECHAR o form SEM
gravar. O robo nunca grava; este script tambem nao.

Emergencia: rato ao canto superior esquerdo aborta (FailSafe do pyautogui).
"""

from __future__ import annotations

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import pyautogui  # noqa: F401 - falha cedo se nao estiver instalado
except ImportError:
    print("ERRO: pyautogui nao instalado. Corre: pip install pyautogui")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robo_actions import (  # noqa: E402
    contagem_decrescente,
    escrever,
    ler_campo_atual,
    tab,
    verificar_foco_simn,
)


def _parse_campos(argv: list[str], default: int = 25) -> int:
    if "--campos" in argv:
        i = argv.index("--campos")
        try:
            return max(1, int(argv[i + 1]))
        except (IndexError, ValueError):
            print("AVISO: --campos requer um numero. A usar o default.")
    return default


def modo_mapa(n: int) -> None:
    """Escreve "00".."NN" em cada paragem de Tab, para ser lido do screenshot."""
    print()
    print("=" * 62)
    print("MODO MAPA: vou escrever um marcador numerado em cada campo.")
    print(f"Paragens de Tab a testar: {n}")
    print("No fim, TIRA UM SCREENSHOT do form (Win+Shift+S) e le os numeros.")
    print("=" * 62)

    contagem_decrescente(8, "\nAlt+Tab AGORA para o form do SIMN (cursor no Nº Contribuinte).")

    if not verificar_foco_simn():
        _pausa_final()
        return

    for i in range(n):
        marcador = f"{i:02d}"
        escrever(marcador)          # limpa o campo e escreve o indice
        print(f"  campo {marcador} preenchido", flush=True)
        time.sleep(0.15)
        tab()

    print()
    print("=" * 62)
    print("FEITO. Agora, sem tocar em mais nada:")
    print("  1. Tira UM screenshot do form todo (Win+Shift+S).")
    print("  2. Anota que numero apareceu em cada campo com etiqueta")
    print("     (Nº Contribuinte, Nome, Naturalidade Concelho, Morada, ...).")
    print("  3. Campos que ficaram VAZIOS sao dropdowns/checkboxes.")
    print("  4. Envia o screenshot / a lista ao Claude para corrigir os tab(N).")
    print("  5. FECHA o form SEM gravar.")
    print("=" * 62)
    _pausa_final()


def modo_ler(n: int) -> None:
    """Le (via clipboard) o conteudo de cada paragem de Tab, sem escrever nada."""
    print()
    print("=" * 62)
    print("MODO LER: nao escrevo nada, so leio cada campo via clipboard.")
    print(f"Paragens de Tab a ler: {n}")
    print("=" * 62)

    contagem_decrescente(8, "\nAlt+Tab AGORA para o form do SIMN (cursor no Nº Contribuinte).")

    if not verificar_foco_simn():
        _pausa_final()
        return

    print()
    resultados: list[tuple[int, str]] = []
    for i in range(n):
        conteudo = ler_campo_atual()
        etiqueta = conteudo if conteudo else "(vazio - provavel dropdown/checkbox)"
        print(f"  [{i:02d}] {etiqueta}", flush=True)
        resultados.append((i, conteudo))
        tab()

    print()
    print("=" * 62)
    print("FEITO. Campos com texto sao os que o SIMN autopreencheu ou que ja")
    print("tinham valor. Vazios sao onde o robo tem de escrever ou saltar.")
    print("=" * 62)
    _pausa_final()


def _pausa_final() -> None:
    try:
        input("\n[Enter para fechar esta janela...] ")
    except (EOFError, KeyboardInterrupt):
        pass


def main() -> None:
    n = _parse_campos(sys.argv)
    if "--ler" in sys.argv:
        modo_ler(n)
    else:
        modo_mapa(n)


if __name__ == "__main__":
    main()
