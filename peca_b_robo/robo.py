r"""
Peca B - Robo (entry point).

Le campos.json e despacha para o fluxo apropriado (CV, Doacao, Habilitacao, Partilha).

Uso:
  python robo.py                          # le ../partilha/campos.json
  python robo.py C:/path/to/campos.json   # le ficheiro custom

Pre-requisitos:
  - SIMN aberto e no ecra principal da escritura ja criada (Nova Escritura +
    tipo de acto ja escolhido).
  - pyautogui instalado (pip install pyautogui)

Instalar (uma vez, no PC do cartorio):
  pip install pyautogui pywinauto opencv-python
"""

from __future__ import annotations

import json
import os
import sys

try:
    import pyautogui  # noqa: F401 - so para falhar cedo se nao estiver instalado
except ImportError:
    print("ERRO: pyautogui nao instalado. Corre: pip install pyautogui")
    sys.exit(1)

# Import dos modulos locais
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robo_fluxos import executar  # noqa: E402


CAMINHO_JSON_DEFAULT = os.path.join(
    os.path.dirname(__file__), "..", "partilha", "campos.json"
)


def carregar_json(caminho: str) -> dict:
    if not os.path.exists(caminho):
        print(f"ERRO: {caminho} nao encontrado.")
        print("Executa a Peca A primeiro para gerar o campos.json.")
        sys.exit(1)
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    caminho = sys.argv[1] if len(sys.argv) > 1 else CAMINHO_JSON_DEFAULT
    caminho = os.path.abspath(caminho)

    print("=" * 60)
    print("ROBO Peca B — modo maquina de escrever")
    print("=" * 60)
    print(f"JSON: {caminho}")

    campos = carregar_json(caminho)
    tipo = campos.get("mnemonica", "?")
    print(f"Tipo de acto: {tipo}")

    executar(campos)


if __name__ == "__main__":
    main()
