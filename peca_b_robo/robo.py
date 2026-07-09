r"""
Peca B - Robo (entry point) - MODO INTERACTIVO.

Le campos.json e mostra um menu com todos os outorgantes.
Escolhes qual queres preencher, o robo faz apenas isso.

Fluxo tipico:
  1. Na Streamlit: fazer upload, extrair, exportar.
  2. No SIMN: Nova Escritura -> CV -> clicar em Adicionar Vendedor -> Novo Singular
  3. Cursor no primeiro campo do form (Nº Contribuinte)
  4. Alt+Tab ao terminal onde este script mostra o menu
  5. Escolher qual outorgante preencher, contagem de 5s, Alt+Tab ao SIMN, robo digita.
  6. Confirmar visualmente, clicar OK
  7. Voltar ao menu e escolher o proximo

Uso:
  python robo.py                          # menu interactivo
  python robo.py C:/path/to/campos.json   # ficheiro custom

Emergencia: rato ao canto superior esquerdo aborta o pyautogui.
"""

from __future__ import annotations

import json
import os
import sys
import time

# Forcar UTF-8 no stdout/stderr para nao rebentar quando corrido sem consola
# (subprocess com CREATE_NO_WINDOW usa cp1252 por defeito, que nao suporta unicode).
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
    esperar_foco_simn,
    verificar_foco_simn,
)
from robo_forms import preencher_outorgante  # noqa: E402


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


def listar_outorgantes(campos: dict) -> list[tuple[str, str, dict]]:
    """Devolve lista de (rotulo, tipo, dict). Ex: ('Vendedor 1', 'vendedor', {...})."""
    items: list[tuple[str, str, dict]] = []
    mapeamento = [
        ("Vendedor", campos.get("vendedores", [])),
        ("Comprador", campos.get("compradores", [])),
        ("Doador", campos.get("doadores", [])),
        ("Donatario", campos.get("donatarios", [])),
        ("Herdeiro", campos.get("herdeiros", [])),
        ("Partilhante", campos.get("partilhantes", [])),
    ]
    for tipo_singular, lista in mapeamento:
        for i, o in enumerate(lista, 1):
            rotulo = f"{tipo_singular} {i}"
            items.append((rotulo, tipo_singular.lower(), o))
    # autor_heranca (habilitacao / partilha)
    if campos.get("autor_heranca"):
        items.append(("Autor da Heranca (falecido)", "autor_heranca", campos["autor_heranca"]))
    return items


def mostrar_menu(items: list) -> str | None:
    """Mostra menu numerado. Devolve indice escolhido ou None se sair."""
    print()
    print("=" * 60)
    print("Escolhe quem preencher:")
    print("=" * 60)
    for idx, (rotulo, _tipo, o) in enumerate(items, 1):
        nome = o.get("nome") or "(sem nome)"
        nif = o.get("nif") or "?"
        print(f"  [{idx}] {rotulo:20} {nome} (NIF {nif})")
    print(f"  [q] Sair")
    print()

    while True:
        escolha = input("Escolha: ").strip().lower()
        if escolha in ("q", "quit", "sair", "exit"):
            return None
        if escolha.isdigit() and 1 <= int(escolha) <= len(items):
            return int(escolha) - 1
        print(f"  Opcao invalida. Numeros de 1 a {len(items)} ou q para sair.")


def _escrever_status(estado: str, rotulo: str, msg: str) -> None:
    """Escreve o estado do robo em partilha/robo_status.json para a app mostrar.

    estado: 'a_preencher' | 'ok' | 'erro'.
    """
    caminho = os.path.join(os.path.dirname(__file__), "..", "partilha", "robo_status.json")
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(
                {"estado": estado, "rotulo": rotulo, "msg": msg,
                 "ts": time.strftime("%H:%M:%S")},
                f, ensure_ascii=False,
            )
    except Exception:
        pass


def modo_batch(caminho_json: str, idx: int) -> int:
    """Preenche o outorgante idx e sai. Chamado pela Streamlit (corre sem consola).

    Sem contagem nem pausa: espera o SIMN ganhar foco e arranca no instante em
    que a funcionaria clica no campo do SIMN. O estado vai para robo_status.json
    (a app le e mostra), nao para a consola.

    Return code: 0=sucesso, 1=idx invalido, 2=SIMN nao ganhou foco, 3=erro.
    """
    campos = carregar_json(caminho_json)
    items = listar_outorgantes(campos)
    if idx < 0 or idx >= len(items):
        _escrever_status("erro", f"idx {idx}", f"fora de gama ({len(items)} outorgantes).")
        return 1
    rotulo, _tipo, outorgante = items[idx]
    _escrever_status("a_preencher", rotulo, "vai ao SIMN e clica no campo Nº Contribuinte.")

    if not esperar_foco_simn(timeout=30.0):
        _escrever_status(
            "erro", rotulo,
            "o SIMN nao ficou a frente a tempo. Clica ▶ Preencher outra vez.",
        )
        return 2
    time.sleep(0.2)  # pequena folga apos ganhar foco

    try:
        preencher_outorgante(outorgante)
        _escrever_status("ok", rotulo, "preenchido. Confere e clica OK no SIMN.")
        return 0
    except pyautogui.FailSafeException:
        _escrever_status("erro", rotulo, "abortado (rato ao canto do ecra).")
        return 3
    except Exception as e:
        _escrever_status("erro", rotulo, f"erro: {e}")
        return 3


def _pausa_final() -> None:
    """Impede a consola de fechar logo, para o utilizador ver o output."""
    try:
        input("\n[Enter para fechar esta janela...] ")
    except (EOFError, KeyboardInterrupt):
        pass


def main() -> None:
    # Suporte a modo batch: --idx N (chamado pela Streamlit)
    if "--idx" in sys.argv:
        i = sys.argv.index("--idx")
        try:
            idx = int(sys.argv[i + 1])
        except (IndexError, ValueError):
            print("ERRO: --idx requer um numero inteiro.")
            sys.exit(1)
        # Caminho JSON: primeiro argumento (nao --idx) ou default
        caminho = CAMINHO_JSON_DEFAULT
        for a in sys.argv[1:]:
            if a != "--idx" and not a.isdigit():
                caminho = a
                break
        sys.exit(modo_batch(os.path.abspath(caminho), idx))

    # Modo interactivo (comportamento original)
    caminho = sys.argv[1] if len(sys.argv) > 1 else CAMINHO_JSON_DEFAULT
    caminho = os.path.abspath(caminho)

    print("=" * 60)
    print("ROBO Peca B - modo interactivo")
    print("=" * 60)
    print(f"JSON: {caminho}")

    campos = carregar_json(caminho)
    tipo = campos.get("mnemonica", "?")
    print(f"Tipo de acto: {tipo}")

    items = listar_outorgantes(campos)
    if not items:
        print("ERRO: nenhum outorgante encontrado no JSON.")
        sys.exit(1)

    # Loop principal - permite preencher varios outorgantes sem sair
    while True:
        idx = mostrar_menu(items)
        if idx is None:
            print("A sair.")
            break

        rotulo, _tipo, outorgante = items[idx]
        print(f"\nVou preencher: {rotulo} - {outorgante.get('nome', '?')}")
        print("Confirma:")
        print("  1. SIMN aberto com o form ja no ecra")
        print("  2. Cursor no campo Nº Contribuinte")
        print("  3. Alt+Tab para o SIMN quando comecar a contagem")

        contagem_decrescente(8, "\nA arrancar em 8 segundos. Alt+Tab AGORA para o SIMN.")

        # Verificar foco antes de escrever qualquer tecla
        if not verificar_foco_simn():
            input("Enter para voltar ao menu... ")
            continue

        try:
            preencher_outorgante(outorgante)
            print("\n✓ Terminado. Confere no SIMN e clica OK.\n")
        except pyautogui.FailSafeException:
            print("\nABORTADO (rato ao canto superior esquerdo).\n")
        except KeyboardInterrupt:
            print("\nInterrompido pelo utilizador.\n")

        input("Enter para voltar ao menu (ou Ctrl+C para sair)... ")


if __name__ == "__main__":
    main()
