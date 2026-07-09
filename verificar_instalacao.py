"""
Verificador de instalacao - testes automaticos que TEM de passar num PC novo.

Corre uma bateria de verificacoes e imprime um relatorio claro. No fim diz se
esta TUDO OK ou o que falta. Codigo de saida: 0 = tudo OK, 1 = falhou algo
critico (para o instalar.ps1 saber que nao ficou bem).

Uso:
  python verificar_instalacao.py            # tudo, incluindo teste a' API (internet)
  python verificar_instalacao.py --offline  # salta o teste que precisa de internet
"""

from __future__ import annotations

import importlib
import os
import sys

# Forcar UTF-8 no stdout (consola do Windows sem isto parte nos acentos).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.abspath(__file__))

OK, FALHA, AVISO = "OK", "FALHA", "AVISO"
_SIMBOLO = {OK: "[ OK  ]", FALHA: "[FALHA]", AVISO: "[AVISO]"}

# Cada verificacao acrescenta (nome, estado, detalhe) a esta lista.
_resultados: list[tuple[str, str, str]] = []


def _reg(nome: str, estado: str, detalhe: str = "") -> None:
    _resultados.append((nome, estado, detalhe))
    print(f"  {_SIMBOLO[estado]}  {nome}" + (f"  ->  {detalhe}" if detalhe else ""), flush=True)


# -----------------------------------------------------------------------------
# Verificacoes
# -----------------------------------------------------------------------------
def v_python() -> None:
    v = sys.version_info
    versao = f"{v.major}.{v.minor}.{v.micro}"
    if v >= (3, 10):
        _reg("Versao do Python", OK, versao)
    else:
        _reg("Versao do Python", FALHA, f"{versao} (precisa de 3.10 ou superior)")


def v_pacotes() -> None:
    # (modulo a importar, nome legivel, critico?)
    pacotes = [
        ("anthropic", "anthropic (Claude)", True),
        ("streamlit", "streamlit (interface)", True),
        ("docx", "python-docx (.docx)", True),
        ("pydantic", "pydantic (validacao)", True),
        ("pyautogui", "pyautogui (robo)", True),
        ("pywinauto", "pywinauto (robo)", True),
        ("cv2", "opencv-python (imagens do robo)", True),
        ("google.genai", "google-genai (provedor Gemini, opcional)", False),
        ("groq", "groq (provedor Groq, opcional)", False),
    ]
    for modulo, nome, critico in pacotes:
        try:
            importlib.import_module(modulo)
            _reg(f"Pacote {nome}", OK)
        except Exception as e:
            _reg(f"Pacote {nome}", FALHA if critico else AVISO,
                 f"nao instalado ({e.__class__.__name__}). Corre: pip install -r requirements.txt"
                 if critico else "nao instalado (so preciso se usares esse provedor)")


def _encontrar_soffice() -> str | None:
    import shutil
    candidatos = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    achado = shutil.which("soffice") or shutil.which("libreoffice")
    if achado:
        return achado
    for c in candidatos:
        if os.path.isfile(c):
            return c
    return None


def _encontrar_antiword() -> str | None:
    import shutil
    candidatos = [
        r"C:\Program Files\Git\mingw64\bin\antiword.exe",
        r"C:\Program Files (x86)\Git\mingw64\bin\antiword.exe",
    ]
    achado = shutil.which("antiword")
    if achado:
        return achado
    for c in candidatos:
        if os.path.isfile(c):
            return c
    return None


def v_leitor_doc() -> None:
    soffice = _encontrar_soffice()
    if soffice:
        _reg("Leitor de .doc antigo", OK, f"LibreOffice em {soffice}")
        return
    antiword = _encontrar_antiword()
    if antiword:
        _reg("Leitor de .doc antigo", OK, f"antiword em {antiword}")
        return
    _reg("Leitor de .doc antigo", FALHA,
         "sem LibreOffice nem antiword. As escrituras .doc nao vao abrir. "
         "Instalar LibreOffice: https://pt.libreoffice.org/descarregar/")


def v_chave_api() -> None:
    provedor = (os.environ.get("LLM_PROVIDER") or "gemini").lower()
    _reg("LLM_PROVIDER", OK if os.environ.get("LLM_PROVIDER") else AVISO,
         provedor + ("" if os.environ.get("LLM_PROVIDER") else " (nao definido; assumindo gemini)"))
    chave_por_provedor = {
        "claude": "ANTHROPIC_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY", "gemini": "GOOGLE_API_KEY",
    }
    env_chave = chave_por_provedor.get(provedor, "ANTHROPIC_API_KEY")
    if (os.environ.get(env_chave) or "").strip():
        _reg(f"Chave da API ({env_chave})", OK, "definida")
    else:
        _reg(f"Chave da API ({env_chave})", FALHA,
             f"nao definida. Setar no PowerShell (User) e reabrir a janela.")


def v_modulos_projeto() -> None:
    sys.path.insert(0, os.path.join(RAIZ, "peca_a_extracao"))
    sys.path.insert(0, os.path.join(RAIZ, "peca_b_robo"))
    for modulo, nome in [
        ("modelos", "schema (peca_a_extracao/modelos.py)"),
        ("extrator", "extrator (peca_a_extracao/extrator.py)"),
        ("robo_forms", "robo forms (peca_b_robo/robo_forms.py)"),
        ("robo", "robo entry point (peca_b_robo/robo.py)"),
    ]:
        try:
            importlib.import_module(modulo)
            _reg(f"Modulo do projeto: {nome}", OK)
        except (Exception, SystemExit) as e:
            # robo.py faz sys.exit(1) se faltar o pyautogui: apanhar SystemExit
            # tambem, senao aborta o verificador a meio do relatorio.
            _reg(f"Modulo do projeto: {nome}", FALHA, f"{e.__class__.__name__}: {e}")


def v_schema() -> None:
    try:
        import modelos  # ja no sys.path por v_modulos_projeto
        cv = modelos.CompraVenda(
            vendedores=[modelos.Outorgante(nif="123456789", nome="Teste")],
            compradores=[modelos.Outorgante(nif="987654321", nome="Teste 2")],
        )
        cv.model_dump_json()
        _reg("Validacao do schema (Pydantic)", OK, "CompraVenda cria e serializa")
    except Exception as e:
        _reg("Validacao do schema (Pydantic)", FALHA, f"{e.__class__.__name__}: {e}")


def v_ler_exemplo() -> None:
    import glob
    exemplos = glob.glob(os.path.join(RAIZ, "exemplos", "*.doc")) + \
        glob.glob(os.path.join(RAIZ, "exemplos", "*.docx"))
    if not exemplos:
        _reg("Leitura de escritura de exemplo", AVISO, "sem ficheiros em exemplos/ para testar")
        return
    if not (_encontrar_soffice() or _encontrar_antiword()) and exemplos[0].lower().endswith(".doc"):
        _reg("Leitura de escritura de exemplo", AVISO, "sem leitor de .doc (ver acima)")
        return
    try:
        import extrator
        texto = extrator.ler_documento(exemplos[0])
        n = len(texto or "")
        if n > 100:
            _reg("Leitura de escritura de exemplo", OK,
                 f"{os.path.basename(exemplos[0])} ({n} caracteres)")
        else:
            _reg("Leitura de escritura de exemplo", FALHA,
                 f"leu so {n} caracteres (leitor .doc pode estar mal)")
    except Exception as e:
        _reg("Leitura de escritura de exemplo", FALHA, f"{e.__class__.__name__}: {e}")


def v_api_online() -> None:
    provedor = (os.environ.get("LLM_PROVIDER") or "gemini").lower()
    if provedor not in ("claude", "anthropic"):
        _reg("Teste a' API (internet)", AVISO,
             f"teste online so implementado para Claude (provedor atual: {provedor})")
        return
    chave = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not chave:
        _reg("Teste a' API (internet)", FALHA, "sem ANTHROPIC_API_KEY")
        return
    try:
        import anthropic
        cliente = anthropic.Anthropic(api_key=chave)
        modelo = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
        # count_tokens e' GRATIS e confirma que a chave autentica (401 se estiver ma).
        r = cliente.with_options(timeout=30.0, max_retries=0).messages.count_tokens(
            model=modelo, messages=[{"role": "user", "content": "ok"}],
        )
        _reg("Teste a' API (internet)", OK,
             f"chave valida, modelo {modelo} responde ({r.input_tokens} tokens)")
    except Exception as e:
        _reg("Teste a' API (internet)", FALHA,
             f"{e.__class__.__name__}: {e}. Confirmar chave e ligacao a' internet.")


# -----------------------------------------------------------------------------
def main() -> int:
    offline = "--offline" in sys.argv
    print()
    print("=" * 64)
    print(" VERIFICADOR DE INSTALACAO - Cartorio Automacao de Escrituras")
    print("=" * 64)

    print("\n-- Ambiente --")
    v_python()
    v_pacotes()
    v_leitor_doc()
    v_chave_api()

    print("\n-- Codigo do projeto --")
    v_modulos_projeto()
    v_schema()
    v_ler_exemplo()

    print("\n-- Ligacao a' API --")
    if offline:
        _reg("Teste a' API (internet)", AVISO, "saltado (--offline)")
    else:
        v_api_online()

    # Resumo
    falhas = [n for n, e, _ in _resultados if e == FALHA]
    avisos = [n for n, e, _ in _resultados if e == AVISO]
    print("\n" + "=" * 64)
    if not falhas:
        print(" RESULTADO: TUDO OK." + (f" ({len(avisos)} aviso(s), nao criticos)" if avisos else ""))
        print(" O PC esta pronto. Podes arrancar a app pelo atalho do ambiente de trabalho.")
        print("=" * 64)
        return 0
    print(f" RESULTADO: {len(falhas)} verificacao(oes) CRITICA(s) falharam:")
    for n in falhas:
        print(f"   - {n}")
    print(" Corrige o que esta em cima marcado [FALHA] e volta a correr este verificador.")
    print("=" * 64)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
