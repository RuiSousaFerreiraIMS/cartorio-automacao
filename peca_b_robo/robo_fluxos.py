"""
Peca B - Orquestradores por tipo de acto.

Cada fluxo:
  1. Recebe o dict `campos` completo (lido de campos.json).
  2. Assume que o SIMN esta no ecra principal da escritura (Vendedor(es),
     Bem, etc. na arvore esquerda).
  3. Clica em cada "Adicionar X" na ordem correcta, abre sub-forms, preenche,
     confirma OK, volta ao principal.
  4. NUNCA clica em Gravar/Registar. Funcionaria confirma no fim.

Coordenadas/imagens dos botoes do painel principal ainda por descobrir amanha
no cartorio (a seguir a CHECKLIST_CARTORIO.md).
"""

from __future__ import annotations

import time
from typing import Any

import pyautogui

from robo_actions import clicar_por_imagem, contagem_decrescente, esperar_janela_titulo
from robo_forms import (
    preencher_bem,
    preencher_duc,
    preencher_outorgante,
    preencher_relacao,
)


# -----------------------------------------------------------------------------
# Coordenadas / Imagens (paths absolutos para nao depender do CWD)
# -----------------------------------------------------------------------------
import os
_PASTA_IMAGENS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagens")

def _img(nome: str) -> str:
    return os.path.join(_PASTA_IMAGENS, nome)

BTN_ADICIONAR_VENDEDOR = _img("btn_adicionar_vendedor.png")
BTN_ADICIONAR_COMPRADOR = _img("btn_adicionar_comprador.png")
BTN_ADICIONAR_DOADOR = _img("btn_adicionar_doador.png")
BTN_ADICIONAR_DONATARIO = _img("btn_adicionar_donatario.png")
BTN_ADICIONAR_BEM = _img("btn_adicionar_bem.png")
BTN_NOVO_BEM = _img("btn_novo_bem.png")
BTN_NOVO_OUTORGANTE_SINGULAR = _img("btn_novo_singular.png")
BTN_NOVO_DUC = _img("btn_novo_duc.png")
BTN_NOVA_RELACAO = _img("btn_nova_relacao.png")
BTN_OK_DIALOGO = _img("btn_ok.png")


# -----------------------------------------------------------------------------
# Helpers de navegaçao
# -----------------------------------------------------------------------------
def _clicar_ou_avisar(caminho_img: str, descricao: str) -> bool:
    """Tenta clicar num botao por imagem. Se nao encontrar, avisa e pausa."""
    ok = clicar_por_imagem(caminho_img, timeout=3)
    if not ok:
        print(f"  ⚠️  Botao '{descricao}' nao encontrado (imagem: {caminho_img}).")
        print("  Faz o click a mao e depois carrega ENTER no PowerShell para continuar.")
        input()
        return False
    time.sleep(0.5)
    return True


def _abrir_form_outorgante(botao_adicionar_img: str, tipo: str) -> None:
    """Fluxo comum: clica 'Adicionar X', escolhe 'Novo Singular', form abre."""
    _clicar_ou_avisar(botao_adicionar_img, f"Adicionar {tipo}")
    if not esperar_janela_titulo(f"Adicionar {tipo}", timeout=5):
        print(f"  ⚠️  Dialogo 'Adicionar {tipo}' nao apareceu.")
    _clicar_ou_avisar(BTN_NOVO_OUTORGANTE_SINGULAR, "Novo Outorgante Singular")
    if not esperar_janela_titulo(tipo, timeout=5):
        print(f"  ⚠️  Form de {tipo} nao apareceu.")


def _abrir_form_bem() -> None:
    """Fluxo comum a todos os atos com bens: 'Adicionar bem' -> 'Novo Bem' -> form.

    Espelha _abrir_form_outorgante. Se a sequencia de dialogos do Bem for
    diferente (ex: 'Adicionar bem' abre o form directamente, sem 'Novo Bem'),
    o _clicar_ou_avisar cai no modo manual e a funcionaria clica; confirmar no
    cartorio e ajustar aqui.
    """
    _clicar_ou_avisar(BTN_ADICIONAR_BEM, "Adicionar bem")
    _clicar_ou_avisar(BTN_NOVO_BEM, "Novo Bem")


def _confirmar_ok() -> None:
    """Clica OK no dialogo actual. Se nao encontrar por imagem, tenta Enter."""
    if not clicar_por_imagem(BTN_OK_DIALOGO, timeout=2):
        pyautogui.press("enter")


# -----------------------------------------------------------------------------
# Fluxo Compra-venda
# -----------------------------------------------------------------------------
def fluxo_cv(campos: dict[str, Any]) -> None:
    """Preenche uma Compra-venda completa. Assume ecra principal com CV aberta."""
    print("=" * 60)
    print(f"Fluxo Compra-venda: {len(campos.get('vendedores', []))} vendedor(es), "
          f"{len(campos.get('compradores', []))} comprador(es), "
          f"{len(campos.get('bens', []))} bem(ns), "
          f"{len(campos.get('ducs', []))} DUC(s)")
    print("=" * 60)

    contagem_decrescente(5, "\nDá ALT+TAB para o SIMN AGORA. Ecrã principal da CV.")

    # === VENDEDORES ===
    for i, v in enumerate(campos.get("vendedores", []), 1):
        print(f"\n[Vendedor {i}/{len(campos['vendedores'])}]")
        _abrir_form_outorgante(BTN_ADICIONAR_VENDEDOR, "Vendedor(es)")
        preencher_outorgante(v)
        _confirmar_ok()
        time.sleep(0.5)

    # === COMPRADORES ===
    for i, c in enumerate(campos.get("compradores", []), 1):
        print(f"\n[Comprador {i}/{len(campos['compradores'])}]")
        _abrir_form_outorgante(BTN_ADICIONAR_COMPRADOR, "Comprador(es)")
        preencher_outorgante(c)
        _confirmar_ok()
        time.sleep(0.5)

    # === BENS ===
    for i, b in enumerate(campos.get("bens", []), 1):
        print(f"\n[Bem {i}/{len(campos['bens'])}]")
        _abrir_form_bem()
        preencher_bem(b)
        _confirmar_ok()
        time.sleep(0.5)

    # === CAMPO OBJECTO / VALORES no painel direito ===
    # TODO: focar campo Objecto, escrever campos.objeto
    # TODO: focar Preço da venda, escrever campos.preco_venda
    # TODO: focar Hipoteca (se aplicavel)
    print("\n[Objecto/Valores] — ainda por mapear (painel direito).")

    # === DUCs ===
    for i, d in enumerate(campos.get("ducs", []), 1):
        print(f"\n[DUC {i}/{len(campos['ducs'])}]")
        _clicar_ou_avisar(BTN_NOVO_DUC, "Novo DUC")
        preencher_duc(d)
        _confirmar_ok()
        time.sleep(0.3)

    # === RELACOES ===
    # Cada vendedor liga a cada bem a cada comprador. Simplificaçao: 1 relaçao
    # que liga tudo. Amanha percebemos exactamente como as relaçoes se estruturam
    # para casais / multiplos bens.
    for v in campos.get("vendedores", []):
        for b in campos.get("bens", []):
            for c in campos.get("compradores", []):
                _clicar_ou_avisar(BTN_NOVA_RELACAO, "Nova Relação")
                preencher_relacao(v.get("nif"), b.get("descricao_predial"),
                                  c.get("nif"))
                _confirmar_ok()
                time.sleep(0.3)

    print("\n" + "=" * 60)
    print("FLUXO CV TERMINADO. Revê no SIMN e clica Gravar à mão.")
    print("=" * 60)


# -----------------------------------------------------------------------------
# Fluxo Doação
# -----------------------------------------------------------------------------
def fluxo_doacao(campos: dict[str, Any]) -> None:
    """Preenche uma Doação completa. Assume Doação ja escolhida na Lista de actos."""
    print("=" * 60)
    print(f"Fluxo Doação: {len(campos.get('doadores', []))} doador(es), "
          f"{len(campos.get('donatarios', []))} donatario(s), "
          f"{len(campos.get('bens', []))} bem(ns)")
    print("=" * 60)

    contagem_decrescente(5, "\nDá ALT+TAB para o SIMN AGORA.")

    for i, d in enumerate(campos.get("doadores", []), 1):
        print(f"\n[Doador {i}]")
        _abrir_form_outorgante(BTN_ADICIONAR_DOADOR, "Doador(es)")
        preencher_outorgante(d)
        _confirmar_ok()

    for i, d in enumerate(campos.get("donatarios", []), 1):
        print(f"\n[Donatario {i}]")
        _abrir_form_outorgante(BTN_ADICIONAR_DONATARIO, "Donatario(s)")
        preencher_outorgante(d)
        _confirmar_ok()

    for i, b in enumerate(campos.get("bens", []), 1):
        print(f"\n[Bem {i}]")
        _abrir_form_bem()
        preencher_bem(b)
        _confirmar_ok()

    # TODO: Valor Acto no painel direito

    for d in campos.get("doadores", []):
        for b in campos.get("bens", []):
            for dn in campos.get("donatarios", []):
                _clicar_ou_avisar(BTN_NOVA_RELACAO, "Nova Relação")
                preencher_relacao(d.get("nif"), b.get("descricao_predial"),
                                  dn.get("nif"))
                _confirmar_ok()

    print("\nFluxo Doação terminado.")


# -----------------------------------------------------------------------------
# Fluxo Habilitação (estrutura diferente - sem bens, sem relaçoes)
# -----------------------------------------------------------------------------
def fluxo_habilitacao(campos: dict[str, Any]) -> None:
    """Preenche uma Habilitação Notarial. Estrutura: falecido + herdeiros + declarantes."""
    print("=" * 60)
    print("Fluxo Habilitação (esqueleto - a completar depois do vídeo do cartorio)")
    print("=" * 60)
    print("⚠️  Ainda por mapear - forms provavelmente similares mas com labels diferentes.")


# -----------------------------------------------------------------------------
# Fluxo Partilha
# -----------------------------------------------------------------------------
def fluxo_partilha(campos: dict[str, Any]) -> None:
    print("=" * 60)
    print("Fluxo Partilha (esqueleto - a completar depois do vídeo do cartorio)")
    print("=" * 60)
    print("⚠️  Ainda por mapear.")


# -----------------------------------------------------------------------------
# Dispatcher
# -----------------------------------------------------------------------------
FLUXOS = {
    "CV": fluxo_cv,
    "DOAC": fluxo_doacao,
    "HAB": fluxo_habilitacao,
    "PART": fluxo_partilha,
}


def executar(campos: dict[str, Any]) -> None:
    tipo = campos.get("mnemonica", "?")
    fluxo = FLUXOS.get(tipo)
    if not fluxo:
        raise ValueError(f"Tipo de acto desconhecido: {tipo!r}")
    fluxo(campos)
