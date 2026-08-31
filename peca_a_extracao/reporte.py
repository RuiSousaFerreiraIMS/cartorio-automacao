"""
Reportar problema: junta tudo o que o Rui precisa para ajudar (escritura,
campos.json, descricao da funcionaria, versao da app, erro tecnico, info do PC),
mete num ZIP e ENVIA por email (Gmail). Guarda sempre uma copia local em
`reportes/` para nada se perder, mesmo que o email falhe.

CONFIG (variaveis de ambiente, como as chaves da API; setar 1x por PC):
    REPORT_EMAIL_USER   conta Gmail que ENVIA (ex: cartorio.rui@gmail.com)
    REPORT_EMAIL_PASS   "palavra-passe de app" do Gmail dessa conta (16 letras)
    REPORT_EMAIL_TO     (opcional) para quem vai; por defeito rui.edh.ferreira@gmail.com

Sem REPORT_EMAIL_USER/PASS o reporte ainda funciona: grava o ZIP em `reportes/`
e avisa que o email nao esta configurado.
"""
from __future__ import annotations

import datetime
import io
import os
import platform
import smtplib
import ssl
import subprocess
import sys
import zipfile
from email.message import EmailMessage

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repo
_PASTA_REPORTES = os.path.join(_RAIZ, "reportes")
_DEST_DEFEITO = "rui.edh.ferreira@gmail.com"


def versao_app() -> str:
    """Commit git curto + data, para eu saber que versao a funcionaria tinha."""
    try:
        h = subprocess.run(
            ["git", "-C", _RAIZ, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        d = subprocess.run(
            ["git", "-C", _RAIZ, "log", "-1", "--format=%cd", "--date=short"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        return f"{h} ({d})" if h else "desconhecida"
    except Exception:
        return "desconhecida"


def _provider_info() -> str:
    prov = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if prov == "groq":
        return f"groq / {os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')}"
    if prov in ("claude", "anthropic"):
        return f"claude / {os.environ.get('ANTHROPIC_MODEL', 'claude-haiku-4-5')}"
    return f"gemini / {os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')}"


def texto_diagnostico(nome_ficheiro, tipo_ato, erro) -> str:
    """Bloco de texto legivel com tudo o que ajuda a diagnosticar."""
    linhas = [
        "RELATORIO DE PROBLEMA - Cartorio (app de escrituras)",
        "=" * 55,
        f"Data/hora:      {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
        f"Versao da app:  {versao_app()}",
        f"Ficheiro:       {nome_ficheiro or '(nenhum carregado)'}",
        f"Tipo de ato:    {tipo_ato or '?'}",
        f"Provider LLM:   {_provider_info()}",
        f"PC / utilizador:{os.environ.get('COMPUTERNAME', '?')} / {os.environ.get('USERNAME', '?')}",
        f"Windows:        {platform.platform()}",
        f"Python:         {sys.version.split()[0]}",
    ]
    if erro:
        linhas += ["", "ERRO TECNICO (traceback):", "-" * 55, str(erro).strip()]
    return "\n".join(linhas) + "\n"


def criar_zip(descricao, nome_ficheiro, ficheiro_bytes,
              campos_json, texto_escritura, diag_txt) -> bytes:
    """Empacota tudo num ZIP (bytes)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("DESCRICAO_DA_FUNCIONARIA.txt",
                   (descricao or "(sem descricao)").strip() + "\n")
        z.writestr("DIAGNOSTICO.txt", diag_txt)
        if campos_json:
            z.writestr("campos.json", campos_json)
        if texto_escritura:
            z.writestr("texto_extraido.txt", texto_escritura)
        if ficheiro_bytes and nome_ficheiro:
            # a propria escritura, com o nome original
            z.writestr("escritura/" + os.path.basename(nome_ficheiro), ficheiro_bytes)
    return buf.getvalue()


def _guardar_local(zip_bytes, nome_ficheiro) -> str:
    """Grava o ZIP em reportes/ e devolve o caminho."""
    os.makedirs(_PASTA_REPORTES, exist_ok=True)
    base = os.path.splitext(os.path.basename(nome_ficheiro or "reporte"))[0]
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(_PASTA_REPORTES, f"reporte_{stamp}_{base}.zip")
    with open(caminho, "wb") as f:
        f.write(zip_bytes)
    return caminho


def _enviar_email(zip_bytes, descricao, nome_ficheiro, tipo_ato) -> None:
    """Envia por Gmail SMTP (SSL). Lanca excecao se falhar."""
    user = os.environ.get("REPORT_EMAIL_USER", "").strip()
    pw = os.environ.get("REPORT_EMAIL_PASS", "").replace(" ", "").strip()
    dest = os.environ.get("REPORT_EMAIL_TO", _DEST_DEFEITO).strip() or _DEST_DEFEITO
    if not user or not pw:
        raise RuntimeError("email nao configurado (REPORT_EMAIL_USER/PASS em falta)")

    msg = EmailMessage()
    quem = f"{os.environ.get('USERNAME', '?')}@{os.environ.get('COMPUTERNAME', '?')}"
    msg["Subject"] = f"[Cartorio] Problema: {nome_ficheiro or '?'} ({tipo_ato or '?'})"
    msg["From"] = user
    msg["To"] = dest
    corpo = (descricao or "(sem descricao)").strip()
    msg.set_content(
        f"Reporte automatico da app do cartorio.\n\n"
        f"De: {quem}\nFicheiro: {nome_ficheiro or '?'}\nTipo: {tipo_ato or '?'}\n"
        f"Versao: {versao_app()}\n\n"
        f"Descricao da funcionaria:\n{corpo}\n\n"
        f"(A escritura, o campos.json e o diagnostico vao no ZIP anexo.)\n"
    )
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    msg.add_attachment(zip_bytes, maintype="application", subtype="zip",
                       filename=f"reporte_{stamp}.zip")

    host = os.environ.get("REPORT_EMAIL_HOST", "smtp.gmail.com")
    port = int(os.environ.get("REPORT_EMAIL_PORT", "465"))

    def _send(context):
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as s:
            s.login(user, pw)
            s.send_message(msg)

    # Alguns PCs tem antivirus/firewall a INSPECIONAR o TLS: metem um certificado
    # proprio que o Python rejeita ([SSL: CERTIFICATE_VERIFY_FAILED]). Tentamos
    # primeiro a ligacao SEGURA (verificada); so se falhar POR CAUSA DO CERTIFICADO
    # (ou se REPORT_EMAIL_INSECURE=1) repetimos sem verificar a cadeia. A ligacao
    # continua encriptada; apenas nao se valida o certificado.
    forcar_inseguro = os.environ.get("REPORT_EMAIL_INSECURE", "").strip() in ("1", "true", "True")
    if not forcar_inseguro:
        try:
            _send(ssl.create_default_context())
            return
        except ssl.SSLError:
            pass  # cai para o fallback sem verificacao
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    _send(ctx)


def enviar_reporte(descricao, nome_ficheiro=None, ficheiro_bytes=None,
                   campos_json=None, texto_escritura=None, tipo_ato=None,
                   erro=None) -> tuple[bool, str]:
    """Cria o ZIP, GRAVA SEMPRE uma copia local e tenta enviar por email.

    Devolve (enviado_por_email, mensagem_para_mostrar). O reporte nunca se perde:
    mesmo sem email, fica o ZIP em reportes/.
    """
    diag = texto_diagnostico(nome_ficheiro, tipo_ato, erro)
    zip_bytes = criar_zip(descricao, nome_ficheiro, ficheiro_bytes,
                          campos_json, texto_escritura, diag)
    # 1) copia local (a prova de falhas)
    try:
        caminho = _guardar_local(zip_bytes, nome_ficheiro)
    except Exception as e:
        caminho = f"(falhou gravar local: {e})"
    # 2) email
    try:
        _enviar_email(zip_bytes, descricao, nome_ficheiro, tipo_ato)
        return True, f"Reporte enviado por email ao Rui. Copia local: {caminho}"
    except Exception as e:
        return False, (
            f"Nao consegui enviar o email ({e}). O reporte FICOU GUARDADO em:\n{caminho}\n"
            f"Avisa o Rui para recolher este ficheiro."
        )
