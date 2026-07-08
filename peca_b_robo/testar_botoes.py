"""
Testa se pyautogui consegue encontrar cada botao do SIMN no ecra actual.

Uso:
  1. Abrir o SIMN e navegar ate ao ecra que queres testar.
     Para o teste completo, ideal:
       - Ecra principal da Compra-venda vazia (mostra Adicionar Vendedor(es),
         Adicionar bem, Novo DUC, Nova Relacao)
  2. Correr:
       python peca_b_robo/testar_botoes.py

Relatorio:
  - ✓ botao encontrado (com coordenadas)
  - ✗ botao nao encontrado

Se algum botao critico (Adicionar Vendedor, Adicionar bem, OK, Nova Relacao)
nao aparecer, tira screenshot do ecra do SIMN e envia ao Rui para novos
recortes.
"""

from __future__ import annotations

import os
import sys

try:
    import pyautogui
except ImportError:
    print("ERRO: pyautogui nao instalado. Corre: pip install pyautogui opencv-python")
    sys.exit(1)


PASTA_IMAGENS = os.path.join(os.path.dirname(__file__), "imagens")


def testar_botao(caminho: str, confianca: float = 0.8) -> tuple[bool, str]:
    """Devolve (encontrado, descricao)."""
    try:
        pos = pyautogui.locateOnScreen(caminho, confidence=confianca)
        if pos:
            return True, f"({int(pos.left)},{int(pos.top)}) {int(pos.width)}x{int(pos.height)}"
        return False, "nao visivel no ecra actual"
    except pyautogui.ImageNotFoundException:
        return False, "nao visivel no ecra actual"
    except NotImplementedError as e:
        return False, f"ERRO: {e}"
    except Exception as e:
        return False, f"erro: {e}"


def main() -> None:
    if not os.path.isdir(PASTA_IMAGENS):
        print(f"ERRO: pasta nao encontrada: {PASTA_IMAGENS}")
        sys.exit(1)

    pngs = sorted(f for f in os.listdir(PASTA_IMAGENS) if f.endswith(".png"))
    if not pngs:
        print(f"ERRO: nenhum PNG em {PASTA_IMAGENS}")
        sys.exit(1)

    print("=" * 68)
    print(f"Teste de reconhecimento de botoes ({len(pngs)} imagens)")
    print(f"Ecra: {pyautogui.size().width}x{pyautogui.size().height}")
    print("=" * 68)

    ok = 0
    falhas = []
    for nome in pngs:
        caminho = os.path.join(PASTA_IMAGENS, nome)
        encontrado, desc = testar_botao(caminho)
        marca = "✓" if encontrado else "✗"
        print(f"  {marca} {nome:40} {desc}")
        if encontrado:
            ok += 1
        else:
            falhas.append(nome)

    print()
    print(f"Resultado: {ok}/{len(pngs)} botoes encontrados")

    if falhas:
        print()
        print("Botoes NAO encontrados:")
        for f in falhas:
            print(f"  - {f}")
        print()
        print("Passos seguintes:")
        print("  1. Confirma que o SIMN esta no ecra certo (Compra-venda vazia).")
        print("  2. Se o botao nao aparece nesse ecra, e' NORMAL nao ser encontrado.")
        print("     Ex: btn_ok so aparece dentro de forms, nao no ecra principal.")
        print("  3. Se um botao que devia estar visivel nao e' encontrado, tira")
        print("     screenshot com Win+Shift+S da janela SIMN inteira e envia ao Rui.")
    else:
        print("Todos os botoes encontrados! Podes avancar para o teste do robo.")


if __name__ == "__main__":
    main()
