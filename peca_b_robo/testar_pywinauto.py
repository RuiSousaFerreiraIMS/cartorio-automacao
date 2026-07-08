"""
Testa se pywinauto consegue enumerar controlos Java Swing do SIMN, agora
que Java Access Bridge esta activo.

Decide se conseguimos automatizar cliques em botoes (Adicionar Vendedor(es),
Novo Singular, OK) por nome, sem depender de reconhecimento de imagem.

Uso:
  1. Abrir SIMN e ficar no ecra principal da CV (com Adicionar Vendedor(es)
     visivel na arvore).
  2. Correr:  python peca_b_robo/testar_pywinauto.py
  3. Enviar o output completo ao Rui.

Interpretacao:
  - Se listar controlos com nomes ("Adicionar Vendedor(es)", "Novo Acto",
    "Gravar", etc.) → GOLDEN. Podemos automatizar tudo.
  - Se so mostrar o Frame raiz sem filhos → JAB nao esta a expor os controlos
    ao pywinauto. Vamos ter de tentar outra abordagem (pyjab).
"""

from __future__ import annotations

import sys
import traceback

try:
    from pywinauto import Application, Desktop
except ImportError:
    print("ERRO: pywinauto nao instalado.")
    sys.exit(1)


def testar_backend(backend: str) -> None:
    print("\n" + "=" * 68)
    print(f"BACKEND: {backend}")
    print("=" * 68)
    try:
        # Listar todas as janelas com SIMN no titulo
        print("\n--- Janelas visiveis com 'SIMN' no titulo ---")
        for w in Desktop(backend=backend).windows(visible_only=True):
            try:
                titulo = w.window_text() or ""
                classe = w.class_name() or ""
                if "simn" in titulo.lower() or "sunawt" in classe.lower():
                    print(f"  titulo={titulo!r}  classe={classe!r}")
            except Exception:
                pass

        # Tentar conectar
        print(f"\n--- A conectar (title_re='.*SIMN.*') ---")
        app = Application(backend=backend).connect(title_re=".*SIMN.*", timeout=5)
        win = app.top_window()
        print(f"Conectado: titulo={win.window_text()!r}  classe={win.class_name()!r}")

        # Enumerar controlos
        print(f"\n--- Arvore de controlos (depth=6) ---")
        win.print_control_identifiers(depth=6)

    except Exception as e:
        print(f"\n[FALHOU] {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    for backend in ("uia", "win32"):
        testar_backend(backend)

    print("\n" + "=" * 68)
    print("Fim. Envia este output completo ao Rui.")
    print("=" * 68)
