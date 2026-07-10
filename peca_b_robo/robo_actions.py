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
import unicodedata

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


def tab_ctrl(vezes: int = 1) -> None:
    """Ctrl+Tab N vezes: SAI de campos que engolem o Tab normal.

    Necessario para os TEXTAREA multi-linha do SIMN (ex: 'Moradas' no form do
    Bem): um Tab normal insere um caractere de tabulacao dentro do textarea e NAO
    muda de campo. Em Java Swing, Ctrl+Tab e a travessia de foco para a frente
    (Ctrl+Shift+Tab para tras). Se no SIMN real isto nao sair do textarea, o plano
    B e clicar o campo seguinte por imagem.
    """
    for _ in range(vezes):
        pyautogui.hotkey("ctrl", "tab")
        time.sleep(0.05)


def dropdown_por_letra(primeira_letra: str) -> None:
    """Dropdowns Java Swing autocompletam com a primeira letra do valor."""
    if not primeira_letra:
        return
    pyautogui.press(primeira_letra[0].lower())
    time.sleep(0.15)


def _sem_acentos(texto: str) -> str:
    """Remove acentos (ç->c, á->a...). Necessario porque pyautogui.write escreve
    teclas fisicas e nao consegue os acentos; o key-select do combo compara pelo
    prefixo, por isso um prefixo ASCII chega para acertar (ex 'alcoba' -> Alcobaca)."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def escrever_dropdown(valor: str | None) -> None:
    """Dropdown de ESCRITA (ex: Naturalidade Concelho/Freguesia): escreve as
    letras do valor (sem acentos, minusculas) para o combo saltar para a opcao
    por prefixo. NAO faz paste (nao seleciona num combo) nem Tab/Enter: quem
    chama confirma com Tab e avanca com outro Tab (metodo do notario).
    """
    if not valor:
        return
    v = _sem_acentos(str(valor)).strip().lower()
    if v:
        # Deixar o campo ficar PRONTO antes de escrever. Sem isto, quando o dropdown
        # vem logo a seguir a Tabs rapidos (ex: Morada Concelho a seguir aos 3 Tabs
        # do Codigo Postal), as primeiras letras PERDEM-SE: o campo fica vazio, nao
        # abre popup e o "Tab de confirmacao" passa a mover o foco -> derrapa tudo.
        time.sleep(0.35)
        pyautogui.write(v, interval=0.06)
        time.sleep(0.35)  # deixar o popup do autocomplete abrir e estabilizar


def selecionar_pais_dropdown(valor: str | None) -> None:
    """Dropdown de PAIS (Naturalidade/Morada): combo de SELECAO (NAO editavel),
    diferente do Concelho/Freguesia. Escreve-se so a PRIMEIRA PALAVRA do pais para
    a selecao saltar para ele. Escrever o nome todo estraga tudo: ao chegar ao
    espaco/2a palavra o combo RECOMECA a busca pela letra seguinte e salta para
    outro pais (o Rui provou: 'estados unidos' -> ao 'u' salta para Ucrania).
    NAO leva Tab de confirmacao (nao ha popup como no Concelho): a selecao fica
    feita e quem chama avanca com os Tabs normais.
    """
    if not valor:
        return
    partes = _sem_acentos(str(valor)).strip().lower().split()
    if not partes:
        return
    time.sleep(0.35)
    pyautogui.write(partes[0], interval=0.08)  # so a 1a palavra (ex: "estados")
    time.sleep(0.35)


def radio_selecionar(indice: int) -> None:
    """Selecciona a opcao `indice` (0 = primeira) de um grupo de radios Java Swing.

    Nos forms do SIMN os radios (ex: Urbano/Rustico no Bem) nao vem seleccionados
    por defeito, por isso seleccionamos sempre. Metodo: com o grupo focado, as
    setas (Down) movem E seleccionam a opcao; o Space confirma a focada. Para a 1a
    opcao (indice 0) basta o Space (o foco entra na 1a). A CONFIRMAR no cartorio se
    a seta certa e Down/Right e se o Space e mesmo preciso.
    """
    for _ in range(max(0, indice)):
        pyautogui.press("down")
        time.sleep(0.1)
    pyautogui.press("space")
    time.sleep(0.1)


def dropdown_por_setas(n_baixo: int) -> None:
    """Dropdown de SELECAO (ex: Estado Civil, Regime - os cinzentos): premir Down
    n vezes para chegar a opcao pretendida (n=1 -> primeira opcao da lista).
    Depois quem chama confirma com Tab e avanca com outro Tab. E o metodo do
    notario para estes dropdowns (a letra unica nao serve: 's' ia para Separado
    em vez de Solteiro).
    """
    for _ in range(max(0, n_baixo)):
        pyautogui.press("down")
        time.sleep(0.1)
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


def _info_janela_focada() -> tuple[str, str, str]:
    """Devolve (titulo, class_name, processo) da janela em foco. Strings vazias se falhar.

    Cobre 3 formas de identificar a janela porque:
      - Diálogos Java Swing muitas vezes tem titulo="" (não expõem via Win32)
      - Mas a class_name começa por "SunAwt" (SunAwtFrame, SunAwtDialog, etc.)
      - E o processo é java.exe / javaw.exe
    Qualquer um destes basta para saber que estamos numa janela SIMN.
    """
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = user32.GetForegroundWindow()

        titulo_buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, titulo_buf, 512)
        titulo = titulo_buf.value or ""

        classe_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, classe_buf, 256)
        classe = classe_buf.value or ""

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        processo = ""
        # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if handle:
            try:
                proc_buf = ctypes.create_unicode_buffer(1024)
                tamanho = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(handle, 0, proc_buf, ctypes.byref(tamanho)):
                    processo = proc_buf.value.split("\\")[-1]
            finally:
                kernel32.CloseHandle(handle)

        return titulo, classe, processo
    except Exception as e:
        return "", "", f"(erro: {e})"


def janela_em_foco_titulo() -> str:
    """Compatibilidade: devolve so o titulo."""
    return _info_janela_focada()[0]


def _e_janela_simn(titulo: str, classe: str, processo: str) -> bool:
    """True se a janela em foco e o SIMN.

    Reconhecemos SO por classe (Java Swing) ou processo (java). NAO usamos o
    titulo: os dialogos do SIMN tem titulo vazio via Win32, e pior, o separador
    do Chrome chama-se "Cartorio - Extracao de Escrituras" -> a palavra
    "escritura" fazia a deteccao achar que o BROWSER era o SIMN e o robo
    arrancava com o browser a frente (Ctrl+A na pagina, Tabs perdidos).
    O Chrome e chrome.exe, nunca passa por isto.
    """
    return classe.startswith("SunAwt") or processo.lower() in ("java.exe", "javaw.exe")


def esperar_foco_simn(timeout: float = 30.0) -> bool:
    """Espera (em silencio) ate o SIMN estar em foco. Devolve True no instante em
    que ganha foco, False se esgotar o timeout.

    Substitui a contagem fixa de segundos: a funcionaria clica no campo do SIMN e
    o robo arranca assim que a janela do SIMN fica a frente.
    """
    inicio = time.time()
    while time.time() - inicio < timeout:
        if _e_janela_simn(*_info_janela_focada()):
            return True
        time.sleep(0.15)
    return False


def verificar_foco_simn() -> bool:
    """Devolve True se a janela em foco pertence ao SIMN (imprime aviso se nao).

    Usado no modo interactivo. O modo da app usa esperar_foco_simn (silencioso).
    """
    titulo, classe, processo = _info_janela_focada()
    if _e_janela_simn(titulo, classe, processo):
        return True

    print()
    print("=" * 60)
    print(f"  ⚠️  SIMN NAO ESTA EM FOCO!")
    print(f"  Janela actual:")
    print(f"    titulo   = {titulo!r}")
    print(f"    classe   = {classe!r}")
    print(f"    processo = {processo!r}")
    print(f"  Robo aborta para nao escrever no sitio errado.")
    print(f"  Solucao: Alt+Tab ao form SIMN antes do countdown terminar.")
    print("=" * 60)
    return False
