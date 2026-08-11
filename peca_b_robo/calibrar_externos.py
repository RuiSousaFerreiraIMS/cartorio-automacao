r"""
Calibra as POSICOES das celulas da grelha "Editar Outorgantes Externos", para o
robo as poder clicar com o rato (as colunas Data/Natureza/Qualidade so editam com
duplo-clique, nao ha teclado que as abra).

Como funciona: para cada alvo tens 5 segundos para POR O RATO no centro da celula
(nao carregues nada, so aponta). Ele grava a posicao do rato ao fim da contagem.

Uso (NO CARTORIO, com a janela dos Outorgantes Externos aberta e JA com pelo menos
DUAS linhas vazias na lista - carrega "Adicionar" duas vezes primeiro):
    python peca_b_robo/calibrar_externos.py

No fim, COPIA o bloco "ENVIA AO CLAUDE" e cola aqui no chat.
"""
from __future__ import annotations

import time

import pyautogui

ALVOS = [
    "NIF        da 1a linha",
    "Nome       da 1a linha",
    "Data       da 1a linha",
    "Livro      da 1a linha",
    "Folhas     da 1a linha",
    "Natureza   da 1a linha",
    "Qualidade  da 1a linha",
    "NIF        da 2a linha (a de baixo)",
]


def main() -> None:
    print("=" * 60)
    print(" CALIBRAR OUTORGANTES EXTERNOS (posicoes das celulas)")
    print("=" * 60)
    print(" Para cada alvo: poe o rato no CENTRO da celula e espera a")
    print(" contagem. Nao carregues em nada, so aponta com o rato.")
    print(" (Precisas de ter pelo menos 2 linhas vazias na lista.)")
    print("=" * 60)

    pos = {}
    for alvo in ALVOS:
        print(f"\n>>> Aponta o rato para:  {alvo}")
        for s in range(5, 0, -1):
            print(f"    {s}...", end=" ", flush=True)
            time.sleep(1)
        p = pyautogui.position()
        pos[alvo] = (p.x, p.y)
        print(f"\n    gravado:  x={p.x}  y={p.y}")

    print("\n\n" + "=" * 60)
    print(" ENVIA AO CLAUDE (copia daqui para baixo):")
    print("=" * 60)
    for alvo, (x, y) in pos.items():
        print(f" {alvo}  ->  x={x}  y={y}")
    print("=" * 60)
    input("\nEnter para fechar.")


if __name__ == "__main__":
    main()
