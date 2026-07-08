"""
Peca B - Helpers pyautogui para acçoes atomicas contra o SIMN.

Todas as funçoes aqui sao "burras" (nao sabem o form em que estao) e sao
compostas em `robo_forms.py` para preencher forms completos.

Truque-chave: ler_campo_atual() usa o clipboard para saber se um campo tem
conteudo (ex: SIMN autopreenche o Nome apos NIF+Tab).
"""

from __future__ import annotations

import subprocess
import time

import pyautogui

# Killswitch: rato no canto superior esquerdo aborta tudo.
pyautogui.FAILSAFE = True
# Pausa por defeito entre acçoes (evita SIMN se perder).
pyautogui.PAUSE = 0.15


# -----------------------------------------------------------------------------
# Escrita / limpeza de campos
# -----------------------------------------------------------------------------
def limpar_campo() -> None:
    """Ctrl+A + Delete: apaga qualquer conteudo pre-existente no campo focado."""
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("delete")


def escrever(texto: str | None, limpar_antes: bool = True) -> None:
    """Escreve texto no campo focado. Suporta acentos via clipboard (Ctrl+V)."""
    if limpar_antes:
        limpar_campo()
    if not texto:
        return
    tem_unicode = any(ord(c) > 127 for c in texto)
    if tem_unicode:
        subprocess.run("clip", input=texto.encode("utf-16le"), check=True, shell=True)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(texto, interval=0.02)


def tab(vezes: int = 1) -> None:
    """Tab N vezes para navegar entre campos."""
    for _ in range(vezes):
        pyautogui.press("tab")


def dropdown_por_letra(primeira_letra: str) -> None:
    """Dropdowns Java Swing autocompletam com a primeira letra do valor."""
    if not primeira_letra:
        return
    pyautogui.press(primeira_letra[0].lower())
    time.sleep(0.15)


# -----------------------------------------------------------------------------
# Leitura de estado
# -----------------------------------------------------------------------------
_SENTINELA_CLIPBOARD = "___ROBO_SENTINELA_VAZIO___"


def _limpar_clipboard() -> None:
    """Poe uma sentinela no clipboard. Se depois de Ctrl+A/Ctrl+C esta la ainda,
    e' porque o campo focado estava vazio (Ctrl+C num campo vazio nao mexe no clipboard).
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{_SENTINELA_CLIPBOARD}'"],
            timeout=3, check=False,
        )
    except Exception:
        pass


def ler_campo_atual() -> str:
    """Le o conteudo do campo focado via clipboard. Devolve '' se vazio.

    Truque: metemos uma sentinela no clipboard PRIMEIRO. Depois Ctrl+A + Ctrl+C.
    Se o campo tem texto, o clipboard passa a ter esse texto.
    Se o campo esta vazio, o Ctrl+C nao substitui a sentinela e ficamos a saber.
    """
    _limpar_clipboard()
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.2)  # tempo para clipboard actualizar
    try:
        conteudo = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            timeout=3,
        ).decode("utf-8", errors="ignore").strip()
    except Exception:
        conteudo = ""
    pyautogui.press("end")  # deselecionar

    # Se a sentinela ainda la esta, o campo estava vazio.
    if conteudo == _SENTINELA_CLIPBOARD:
        return ""
    return conteudo


# -----------------------------------------------------------------------------
# Cliques em botoes / dialogos (a preencher com coords do reconhecimento)
# -----------------------------------------------------------------------------
def clicar_por_imagem(caminho_png: str, confianca: float = 0.85, timeout: float = 5.0) -> bool:
    """Encontra um botao por imagem e clica no centro. Devolve True/False.

    O ficheiro .png deve ser um recorte pequeno do botao (30-100px de largura).
    Cria-os com Snipping Tool do Windows a partir dos screenshots.
    """
    inicio = time.time()
    while time.time() - inicio < timeout:
        try:
            pos = pyautogui.locateCenterOnScreen(caminho_png, confidence=confianca)
            if pos:
                pyautogui.click(pos)
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def esperar_janela_titulo(fragmento_titulo: str, timeout: float = 8.0) -> bool:
    """Espera ate uma janela com esse fragmento no titulo aparecer.
    Usa pywinauto (via pyautogui.getWindowsWithTitle nao existe sempre).
    """
    inicio = time.time()
    while time.time() - inicio < timeout:
        janelas = [w for w in pyautogui.getAllWindows()
                   if fragmento_titulo.lower() in (w.title or "").lower()]
        if janelas:
            return True
        time.sleep(0.3)
    return False


def contagem_decrescente(segundos: int = 5, mensagem: str = "") -> None:
    """Countdown antes de comecar a digitar (dar tempo ao utilizador de Alt+Tab)."""
    if mensagem:
        print(mensagem)
    for i in range(segundos, 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)
