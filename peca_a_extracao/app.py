"""
Interface mediadora v4 (Streamlit) - Peça A.

Implementa o design exportado de Claude Design:
  - Sidebar navy com Ficheiro Atual + Progresso + Sistema + Destino + Simular
  - Top bar branca com chips (Tipo / Data / Verbete / Objeto / avisos pill)
  - Painel de avisos dourado "REVER ANTES DE EXPORTAR"
  - Tabs card branco (Outorgantes / Bem / Valores / DUCs)
  - Cards de outorgante com avatar circular, summary line e NIF badge
  - Bem com badge U/R/M no header
  - Valores em tiles grandes + alert vermelho para hipoteca a cancelar
  - DUCs com badges coloridos por tipo (IMT azul, TGIS roxo)
  - JSON preview toggleable (fundo navy)
  - Bottom bar fixo (Carregar outra · {} JSON · Exportar)

Correr localmente:
  $env:GROQ_API_KEY = "..."          # ou GOOGLE_API_KEY
  python -m streamlit run app.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import tempfile

import streamlit as st

from extrator import extrair_de_ficheiro
from modelos import (
    Bem, CompraVenda, DUC, Doacao, EstadoCivil, Habilitacao,
    Outorgante, Partilha, RegimeBens,
)

# ─────────────────────────────────────────────────────────────
# Configuração
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cartório — Extração de Escrituras",
    layout="wide",
    initial_sidebar_state="expanded",
)

CAMINHO_JSON = os.path.join("..", "partilha", "campos.json")
PADROES_INFO = ("casal detetado",)

# Paleta do design
NAVY = "#1B2B45"
NAVY_HOVER = "#243556"
CREAM = "#EDE9E1"
GOLD = "#C8963E"
BORDER = "#DDD9D1"
BORDER_SOFT = "#E5DDD0"
GREEN = "#16A34A"
WARN_BG = "#FFFBEB"
WARN_BORDER = "#FDE68A"
WARN_TEXT = "#92400E"
WARN_LABEL = "#B45309"
DANGER_BG = "#FEF2F2"
DANGER_BORDER = "#FECACA"
DANGER_TEXT = "#991B1B"
INFO_BG = "#EFF6FF"
INFO_BORDER = "#BFDBFE"
INFO_TEXT = "#1E40AF"


# ─────────────────────────────────────────────────────────────
# CSS global
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html, body, [class*="css"], .stApp, button, input, textarea, select {{
    font-family: 'Inter', sans-serif !important;
  }}

  /* Fundo cream */
  .stApp {{ background:{CREAM} !important; }}

  /* Esconder header/footer Streamlit */
  header[data-testid="stHeader"] {{ display:none !important; }}
  footer {{ display:none !important; }}
  #MainMenu {{ display:none !important; }}
  .stDeployButton {{ display:none !important; }}

  /* Padding zero no topo */
  .block-container {{ padding-top:0 !important; padding-bottom:88px !important; max-width:none !important; }}

  /* ─── SIDEBAR ─── */
  [data-testid="stSidebar"] > div:first-child {{
    background:{NAVY};
    padding-top:0 !important;
  }}
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] .stCaption {{
    color:rgba(255,255,255,.6) !important;
  }}
  [data-testid="stSidebar"] hr {{ display:none; }}
  [data-testid="stSidebar"] code {{
    color:rgba(255,255,255,.4) !important;
    background:rgba(255,255,255,.06) !important;
    word-break:break-all;
  }}
  [data-testid="stSidebar"] [data-testid="stFileUploader"] {{
    background:rgba(255,255,255,.05);
    border:1px dashed rgba(255,255,255,.15);
    border-radius:8px;
    padding:10px;
  }}
  [data-testid="stSidebar"] [data-testid="stFileUploader"] label {{
    color:rgba(255,255,255,.8) !important;
    font-size:12px;
  }}
  [data-testid="stSidebar"] button[kind="secondary"] {{
    background:rgba(255,255,255,.05) !important;
    border:1px solid rgba(255,255,255,.1) !important;
    color:rgba(255,255,255,.6) !important;
    font-size:11px !important;
    font-weight:500 !important;
  }}
  [data-testid="stSidebar"] button[kind="secondary"]:hover {{
    background:rgba(255,255,255,.09) !important;
    color:rgba(255,255,255,.85) !important;
  }}

  /* ─── TABS ─── */
  .stTabs [data-baseweb="tab-list"] {{
    gap:0;
    border-bottom:1px solid {BORDER_SOFT};
    background:#fff;
    padding:0 6px;
    border-radius:10px 10px 0 0;
  }}
  .stTabs [data-baseweb="tab"] {{
    padding:11px 16px !important;
    font-size:13px !important;
    font-weight:500 !important;
    color:#9CA3AF !important;
    background:transparent !important;
  }}
  .stTabs [aria-selected="true"] {{
    color:{NAVY} !important;
    font-weight:600 !important;
    border-bottom:2px solid {NAVY} !important;
  }}
  .stTabs [data-baseweb="tab-panel"] {{
    background:#fff;
    border:1px solid {BORDER};
    border-top:none;
    border-radius:0 0 10px 10px;
    padding:20px 20px 24px;
  }}

  /* ─── INPUTS ─── */
  .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {{
    background:#fff !important;
    border:1px solid {BORDER} !important;
    border-radius:5px !important;
    font-size:12px !important;
    color:#1A1A1A !important;
  }}
  .stTextInput label, .stNumberInput label, .stSelectbox label, .stTextArea label, .stCheckbox label {{
    font-size:10px !important;
    font-weight:600 !important;
    color:#9CA3AF !important;
    text-transform:uppercase;
    letter-spacing:.06em;
  }}
  .stTextArea textarea {{
    background:#fff !important;
    border:1px solid {BORDER} !important;
    font-size:12px !important;
  }}

  /* ─── PRIMARY BUTTON ─── */
  .stButton > button[kind="primary"] {{
    background:{NAVY} !important;
    border:none !important;
    color:#fff !important;
    font-weight:600 !important;
    border-radius:7px !important;
    padding:9px 18px !important;
  }}
  .stButton > button[kind="primary"]:hover {{
    background:{NAVY_HOVER} !important;
  }}

  /* ─── ALERTS Streamlit defaults (escondidos a favor dos custom) ─── */
  .stAlert {{ display:none; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _vazio_para_none(v):
    return v if v else None


def _euros(v):
    if v is None or v == 0:
        return "0 €"
    return f"{v:,.0f} €".replace(",", " ")


def _nif_format(nif):
    """222350245 -> 222 350 245"""
    if not nif:
        return "?"
    s = "".join(c for c in nif if c.isdigit())
    if len(s) == 9:
        return f"{s[:3]} {s[3:6]} {s[6:]}"
    return nif


def _nif_valido(nif):
    return bool(nif and nif.isdigit() and len(nif) == 9)


def _iniciais(nome):
    if not nome:
        return "??"
    partes = [p for p in nome.split() if p]
    if not partes:
        return "??"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def _cor_avatar(nome):
    """Cor pastel determinística baseada no nome."""
    if not nome:
        return ("#E5E7EB", "#6B7280")
    paletas = [
        ("#DBEAFE", "#1D4ED8"),  # azul
        ("#EDE9FE", "#7C3AED"),  # roxo
        ("#D1FAE5", "#065F46"),  # verde
        ("#FEE2E2", "#B91C1C"),  # vermelho
        ("#FEF3C7", "#92400E"),  # âmbar
        ("#FCE7F3", "#BE185D"),  # rosa
    ]
    h = int(hashlib.md5(nome.encode()).hexdigest(), 16)
    return paletas[h % len(paletas)]


def _data_curta(d):
    """2026-06-22 -> '22 jun 2026'"""
    if not d:
        return "—"
    try:
        dt = datetime.date.fromisoformat(d)
        meses = ["jan", "fev", "mar", "abr", "mai", "jun",
                 "jul", "ago", "set", "out", "nov", "dez"]
        return f"{dt.day} {meses[dt.month-1]} {dt.year}"
    except (ValueError, TypeError):
        return d


def _tipo_humano(mnemonica):
    return {"CV": "Compra-venda", "DOAC": "Doação",
            "HAB": "Habilitação Notarial", "PART": "Partilha"}.get(mnemonica, mnemonica)


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
def render_sidebar(obj, nome_ficheiro):
    with st.sidebar:
        # Identidade
        st.markdown(f"""
        <div style="padding:22px 4px 16px; border-bottom:1px solid rgba(255,255,255,.07);">
          <div style="font-size:10px; font-weight:700; letter-spacing:.1em;
                      color:{GOLD}; text-transform:uppercase;">Cartório Notarial</div>
          <div style="font-size:17px; font-weight:700; color:#fff; margin-top:3px;">Rui Ferreira</div>
          <div style="font-size:11px; color:rgba(255,255,255,.35); margin-top:1px;">Alcobaça</div>
        </div>
        """, unsafe_allow_html=True)

        # Ficheiro atual
        if obj is not None and nome_ficheiro:
            ts = st.session_state.get("ts_extracao", "")
            tipo = _tipo_humano(obj.mnemonica).upper()
            st.markdown(f"""
            <div style="padding:14px 4px 16px; border-bottom:1px solid rgba(255,255,255,.07);">
              <div style="font-size:9px; font-weight:700; letter-spacing:.1em;
                          color:rgba(255,255,255,.28); text-transform:uppercase; margin-bottom:10px;">
                Ficheiro atual
              </div>
              <div style="display:flex; gap:10px; align-items:flex-start;">
                <div style="width:30px; height:30px; min-width:30px; background:rgba(200,150,62,.15);
                            border-radius:6px; display:flex; align-items:center; justify-content:center;">
                  <span style="color:{GOLD}; font-size:14px;">📄</span>
                </div>
                <div style="min-width:0; flex:1;">
                  <div style="font-size:12px; font-weight:500; color:#fff;
                              word-break:break-word; line-height:1.4;">{nome_ficheiro}</div>
                  <div style="margin-top:5px;">
                    <span style="background:{GOLD}; color:#fff; font-size:9px; font-weight:700;
                                 padding:2px 6px; border-radius:4px; letter-spacing:.04em;">{tipo}</span>
                  </div>
                  <div style="font-size:10px; color:rgba(255,255,255,.28); margin-top:5px;">{ts}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Progresso
        passo = 2 if obj is not None else 1
        exportado = st.session_state.get("exportado", False)
        if exportado:
            passo = 3
        st.markdown(f"""
        <div style="padding:14px 4px 16px; border-bottom:1px solid rgba(255,255,255,.07);">
          <div style="font-size:9px; font-weight:700; letter-spacing:.1em;
                      color:rgba(255,255,255,.28); text-transform:uppercase; margin-bottom:12px;">
            Progresso
          </div>
          {_passo(1, "Carregar escritura", obj is not None or exportado, passo == 1)}
          {_passo(2, "Rever e corrigir", exportado, passo == 2)}
          {_passo(3, "Exportar para robô", exportado, passo == 3, exportado=exportado)}
        </div>
        """, unsafe_allow_html=True)

        # Sistema
        provedor = os.environ.get("LLM_PROVIDER", "gemini").lower()
        if provedor == "groq":
            modelo = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
            tem_chave = bool(os.environ.get("GROQ_API_KEY"))
        else:
            modelo = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
            tem_chave = bool(os.environ.get("GOOGLE_API_KEY"))
        cor_dot = "#16A34A" if tem_chave else "#EF4444"
        chave_txt = "Chave API ativa" if tem_chave else "Chave API em falta"
        st.markdown(f"""
        <div style="padding:14px 4px 16px; border-bottom:1px solid rgba(255,255,255,.07);">
          <div style="font-size:9px; font-weight:700; letter-spacing:.1em;
                      color:rgba(255,255,255,.28); text-transform:uppercase; margin-bottom:10px;">
            Sistema
          </div>
          <div style="display:flex; align-items:center; gap:7px; margin-bottom:7px;">
            <div style="width:6px; height:6px; background:{GREEN};
                        border-radius:50%; flex-shrink:0;"></div>
            <span style="font-size:12px; color:rgba(255,255,255,.55);">{modelo}</span>
          </div>
          <div style="display:flex; align-items:center; gap:7px;">
            <div style="width:6px; height:6px; background:{cor_dot};
                        border-radius:50%; flex-shrink:0;"></div>
            <span style="font-size:12px; color:rgba(255,255,255,.55);">{chave_txt}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Destino
        st.markdown(f"""
        <div style="padding:14px 4px;">
          <div style="font-size:9px; font-weight:700; letter-spacing:.1em;
                      color:rgba(255,255,255,.28); text-transform:uppercase; margin-bottom:6px;">
            Destino JSON
          </div>
          <div style="font-size:10px; color:rgba(255,255,255,.28);
                      font-family:monospace; line-height:1.6; word-break:break-all;">
            .../partilha/campos.json
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Botão simular nova extração
        if st.button("↺ Simular nova extração", use_container_width=True, key="reset_btn"):
            for k in ("obj", "nome_ficheiro", "ts_extracao", "exportado"):
                st.session_state.pop(k, None)
            st.rerun()


def _passo(num, label, completo, ativo, exportado=False):
    if completo and not ativo:
        icone = (f'<div style="width:20px; height:20px; min-width:20px; background:{GREEN};'
                 f'border-radius:50%; display:flex; align-items:center; justify-content:center;">'
                 f'<span style="color:#fff; font-size:11px;">✓</span></div>')
        texto = (f'<span style="font-size:12px; color:rgba(255,255,255,.3); '
                 f'text-decoration:line-through;">{label}</span>')
    elif ativo:
        icone = (f'<div style="width:20px; height:20px; min-width:20px; background:{GOLD};'
                 f'border-radius:50%; display:flex; align-items:center; justify-content:center;">'
                 f'<span style="font-size:9px; font-weight:700; color:#fff;">{num}</span></div>')
        texto = f'<span style="font-size:12px; font-weight:600; color:#fff;">{label}</span>'
    elif exportado:
        icone = (f'<div style="width:20px; height:20px; min-width:20px; background:{GREEN};'
                 f'border-radius:50%; display:flex; align-items:center; justify-content:center;">'
                 f'<span style="color:#fff; font-size:11px;">✓</span></div>')
        texto = f'<span style="font-size:12px; font-weight:600; color:#4ADE80;">Exportado!</span>'
    else:
        icone = (f'<div style="width:20px; height:20px; min-width:20px; '
                 f'border:1px solid rgba(255,255,255,.15); border-radius:50%; '
                 f'display:flex; align-items:center; justify-content:center;">'
                 f'<span style="font-size:9px; font-weight:700; color:rgba(255,255,255,.22);">{num}</span></div>')
        texto = f'<span style="font-size:12px; color:rgba(255,255,255,.28);">{label}</span>'

    return f'<div style="display:flex; gap:10px; align-items:center; margin-bottom:10px;">{icone}{texto}</div>'


# ─────────────────────────────────────────────────────────────
# TOP BAR (chips)
# ─────────────────────────────────────────────────────────────
def render_topbar(obj):
    avisos_serios = [a for a in (obj.avisos or [])
                     if not any(p in a.lower() for p in PADROES_INFO)]
    n_avisos = len(avisos_serios)
    avisos_pill = ""
    if n_avisos > 0:
        avisos_pill = (
            f'<div style="margin-left:auto; background:{WARN_BG}; color:{WARN_LABEL};'
            f'font-size:11px; font-weight:600; padding:4px 10px; border-radius:20px;'
            f'border:1px solid {WARN_BORDER}; display:flex; align-items:center; gap:5px;">'
            f'⚠ {n_avisos} aviso{"s" if n_avisos != 1 else ""}</div>'
        )
    else:
        avisos_pill = (
            f'<div style="margin-left:auto; background:#DCFCE7; color:{GREEN};'
            f'font-size:11px; font-weight:600; padding:4px 10px; border-radius:20px;'
            f'border:1px solid #BBF7D0;">✓ Sem avisos</div>'
        )

    tipo = _tipo_humano(obj.mnemonica)
    data = _data_curta(getattr(obj, "data_escritura", None))
    verbete = getattr(obj, "verbete_numero", None) or "—"
    objeto = getattr(obj, "objeto", None) or "não definido"
    objeto_short = (objeto[:40] + "…") if len(objeto) > 40 else objeto

    def chip(label, valor, italic=False):
        cor = "#C4BDB5" if (valor == "—" or italic) else NAVY
        style_extra = "font-style:italic;" if italic else ""
        return (
            f'<div style="display:flex; align-items:center; gap:5px;">'
            f'<span style="font-size:11px; color:#9CA3AF;">{label}</span>'
            f'<span style="font-size:13px; font-weight:600; color:{cor}; {style_extra}">{valor}</span>'
            f'</div>'
        )

    sep = f'<div style="width:1px; height:18px; background:{BORDER_SOFT};"></div>'
    st.markdown(f"""
    <div style="background:#fff; border-bottom:1px solid {BORDER}; padding:0 26px;
                display:flex; align-items:center; gap:18px; height:50px;
                margin:0 -16px 16px; position:sticky; top:0; z-index:10;">
      {chip("Tipo", tipo)}
      {sep}
      {chip("Data", data)}
      {sep}
      {chip("Verbete", verbete)}
      {sep}
      {chip("Objeto", objeto_short, italic=(objeto == "não definido"))}
      {avisos_pill}
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# WARNINGS PANEL
# ─────────────────────────────────────────────────────────────
def render_warnings(obj):
    obj.avisos = obj.validar_e_avisar()
    avisos_serios = [a for a in obj.avisos
                     if not any(p in a.lower() for p in PADROES_INFO)]
    avisos_info = [a for a in obj.avisos if a not in avisos_serios]

    if avisos_serios:
        bullets = "".join(
            f'<div style="font-size:12px; color:{WARN_TEXT}; display:flex; '
            f'align-items:baseline; gap:6px; margin-bottom:4px;">'
            f'<span style="color:#D97706; font-weight:700;">·</span>{a}</div>'
            for a in avisos_serios
        )
        st.markdown(f"""
        <div style="background:{WARN_BG}; border:1px solid {WARN_BORDER};
                    border-radius:8px; padding:11px 14px; margin-bottom:14px;">
          <div style="font-size:10px; font-weight:700; color:{WARN_LABEL};
                      text-transform:uppercase; letter-spacing:.06em; margin-bottom:7px;">
            ⚠ Rever antes de exportar
          </div>
          {bullets}
        </div>
        """, unsafe_allow_html=True)

    if avisos_info:
        bullets = "".join(
            f'<div style="font-size:12px; color:{INFO_TEXT}; margin-bottom:3px;">· {a}</div>'
            for a in avisos_info
        )
        st.markdown(f"""
        <div style="background:{INFO_BG}; border:1px solid {INFO_BORDER};
                    border-radius:8px; padding:9px 14px; margin-bottom:14px;">
          {bullets}
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# EDITOR Outorgante (com avatar via container + button)
# ─────────────────────────────────────────────────────────────
def card_outorgante(prefixo, indice, o):
    """Card com avatar circular, nome, summary, badge NIF, e form expandível."""
    key_open = f"open_{prefixo}_{indice}"
    if key_open not in st.session_state:
        st.session_state[key_open] = (indice == 0)  # primeiro aberto por defeito

    bg_avatar, fg_avatar = _cor_avatar(o.nome)
    iniciais = _iniciais(o.nome)
    nif_show = _nif_format(o.nif)
    nif_ok = _nif_valido(o.nif)

    estado_label = (o.estado_civil.value if o.estado_civil else "—").capitalize()
    regime_label = (o.regime_bens.value.replace("_", " ") if o.regime_bens else "—").capitalize()
    quota = o.quota_parte or "1/1"
    summary = f"NIF {nif_show} · {estado_label} · {regime_label} · {quota}"

    nif_badge = (
        f'<span style="font-size:10px; font-weight:600; color:{GREEN}; '
        f'background:#DCFCE7; padding:2px 7px; border-radius:9px;">NIF ✓</span>'
        if nif_ok else
        f'<span style="font-size:10px; font-weight:600; color:#B91C1C; '
        f'background:#FEE2E2; padding:2px 7px; border-radius:9px;">NIF ⚠</span>'
    )

    aberto = st.session_state[key_open]
    seta = "⌃" if aberto else "⌄"

    # HTML card header (visual)
    st.markdown(f"""
    <div style="border:1px solid {BORDER}; border-radius:8px; overflow:hidden;
                margin-bottom:8px; background:#fff;">
      <div style="display:flex; align-items:center; gap:11px; padding:12px 14px;">
        <div style="width:34px; height:34px; min-width:34px; background:{bg_avatar};
                    border-radius:50%; display:flex; align-items:center;
                    justify-content:center;">
          <span style="font-size:11px; font-weight:700; color:{fg_avatar};">{iniciais}</span>
        </div>
        <div style="flex:1; min-width:0;">
          <div style="font-size:13px; font-weight:600; color:#1A1A1A;">{o.nome or '(sem nome)'}</div>
          <div style="font-size:11px; color:#6B7280; margin-top:2px;">{summary}</div>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          {nif_badge}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Botão toggle (Streamlit nativo, único click handler)
    btn_label = f"{'▴ Recolher' if aberto else '▾ Expandir'} {o.nome or '(sem nome)'}"
    if st.button(btn_label, key=f"btn_{key_open}", use_container_width=True):
        st.session_state[key_open] = not aberto
        st.rerun()

    if aberto:
        editar_outorgante(prefixo, indice, o)


def editar_outorgante(prefixo, indice, o):
    k = lambda c: f"{prefixo}_{indice}_{c}"

    c1, c2, c3 = st.columns([2, 4, 1])
    o.nif = _vazio_para_none(c1.text_input("NIF", o.nif or "", key=k("nif")))
    o.nome = _vazio_para_none(c2.text_input("Nome", o.nome or "", key=k("nome")))
    o.e_empresa = c3.checkbox("Empresa", o.e_empresa, key=k("emp"))

    c1, c2 = st.columns(2)
    estados = list(EstadoCivil)
    try:
        idx_ec = estados.index(o.estado_civil)
    except ValueError:
        idx_ec = estados.index(EstadoCivil.desconhecido)
    o.estado_civil = c1.selectbox(
        "Estado civil", estados, index=idx_ec,
        format_func=lambda e: e.value, key=k("ec"),
    )
    regimes = list(RegimeBens)
    try:
        idx_rb = regimes.index(o.regime_bens)
    except ValueError:
        idx_rb = regimes.index(RegimeBens.nao_aplicavel)
    o.regime_bens = c2.selectbox(
        "Regime de bens", regimes, index=idx_rb,
        format_func=lambda r: r.value, key=k("rb"),
    )

    c1, c2 = st.columns(2)
    o.conjuge_de_nif = _vazio_para_none(
        c1.text_input("Cônjuge NIF", o.conjuge_de_nif or "", key=k("cnj"))
    )
    o.quota_parte = _vazio_para_none(
        c2.text_input("Quota parte", o.quota_parte or "", key=k("qp"))
    )

    c1, c2 = st.columns(2)
    o.naturalidade = _vazio_para_none(
        c1.text_input("Naturalidade", o.naturalidade or "", key=k("nat"))
    )
    o.nacionalidade = _vazio_para_none(
        c2.text_input("Nacionalidade", o.nacionalidade or "", key=k("nac"))
    )

    o.morada = _vazio_para_none(st.text_input("Morada", o.morada or "", key=k("mor")))
    o.doc_identificacao = _vazio_para_none(
        st.text_input("Documento (CC / Título residência)",
                      o.doc_identificacao or "", key=k("doc"))
    )


def secao_outorgantes(titulo, lista, prefixo):
    if not lista:
        st.markdown(f'<div style="color:#9CA3AF; font-size:13px;">(nenhum/a detetado/a)</div>',
                    unsafe_allow_html=True)
        return
    n = len(lista)
    casal = n == 2 and all(o.conjuge_de_nif for o in lista)
    suf = "2 · casal" if casal else f"{n} pessoa{'s' if n > 1 else ''}"
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:7px; margin-bottom:11px;">
      <span style="font-size:10px; font-weight:700; color:#9CA3AF;
                   text-transform:uppercase; letter-spacing:.08em;">{titulo}</span>
      <span style="font-size:10px; background:{CREAM}; color:#6B7280;
                   padding:2px 7px; border-radius:9px; font-weight:600;">{suf}</span>
    </div>
    """, unsafe_allow_html=True)
    for i, o in enumerate(lista):
        card_outorgante(prefixo, i, o)


# ─────────────────────────────────────────────────────────────
# EDITOR Bem
# ─────────────────────────────────────────────────────────────
TIPOS_BEM = [("U", "Urbano"), ("R", "Rústico"), ("M", "Misto"), (None, "(n/a)")]


def card_bem(indice, b):
    tipo_letra = b.tipo or "?"
    tipo_label = {"U": "Urbano", "R": "Rústico", "M": "Misto"}.get(tipo_letra, "?")
    titulo = "Fração " + (b.designacao_fracao or "—") if b.designacao_fracao else (
        b.descricao_predial or b.freguesia or "Imóvel"
    )
    morada = b.morada or b.freguesia or ""

    st.markdown(f"""
    <div style="border:1px solid {BORDER}; border-radius:8px; overflow:hidden;
                margin-bottom:12px;">
      <div style="background:#F8F7F4; border-bottom:1px solid {BORDER_SOFT};
                  padding:10px 14px; display:flex; align-items:center; gap:8px;">
        <span style="background:{NAVY}; color:#fff; font-size:10px; font-weight:700;
                     padding:2px 7px; border-radius:4px;">{tipo_letra}</span>
        <span style="font-size:13px; font-weight:600; color:#1A1A1A;">{titulo}</span>
        <span style="font-size:12px; color:#9CA3AF;">· {morada}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    editar_bem(indice, b)


def editar_bem(indice, b):
    k = lambda c: f"bem_{indice}_{c}"

    c1, c2, c3 = st.columns([1, 1, 2])
    valores_tipo = [t[0] for t in TIPOS_BEM]
    try:
        idx_t = valores_tipo.index(b.tipo)
    except ValueError:
        idx_t = len(TIPOS_BEM) - 1
    b.tipo = c1.selectbox(
        "Tipo", valores_tipo, index=idx_t,
        format_func=lambda v: dict(TIPOS_BEM)[v], key=k("tipo"),
    )
    b.designacao_fracao = _vazio_para_none(
        c2.text_input("Fração", b.designacao_fracao or "", key=k("frac"))
    )
    b.valor_patrimonial = c3.number_input(
        "VPT (EUR)", value=float(b.valor_patrimonial or 0.0), step=100.0, key=k("vpt"),
    ) or None

    c1, c2 = st.columns(2)
    b.freguesia = _vazio_para_none(c1.text_input("Freguesia", b.freguesia or "", key=k("freg")))
    b.concelho = _vazio_para_none(c2.text_input("Concelho", b.concelho or "", key=k("conc")))

    c1, c2 = st.columns(2)
    b.descricao_predial = _vazio_para_none(
        c1.text_input("Descrição predial", b.descricao_predial or "", key=k("desc"))
    )
    b.artigo_matricial = _vazio_para_none(
        c2.text_input("Artigo matricial", b.artigo_matricial or "", key=k("art"))
    )

    b.certidao_predial = _vazio_para_none(
        st.text_input("Certidão Predial Permanente", b.certidao_predial or "", key=k("cert"))
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div style="font-size:10px; font-weight:600; color:#9CA3AF; text-transform:uppercase;
                    letter-spacing:.06em; margin-bottom:3px;">
          Código SIMN
          <span style="background:{WARN_BG}; color:#D97706; padding:1px 5px; border-radius:3px;
                       font-size:9px; font-weight:700; margin-left:4px;">PREENCHER</span>
        </div>
        """, unsafe_allow_html=True)
        b.codigo_simn = _vazio_para_none(
            st.text_input("Código SIMN", b.codigo_simn or "",
                          placeholder="Ex: 100108-U-1948",
                          key=k("simn"), label_visibility="collapsed")
        )
    with c2:
        b.morada = _vazio_para_none(st.text_input("Morada", b.morada or "", key=k("mor")))

    b.descricao_livre = _vazio_para_none(
        st.text_area("Descrição livre", b.descricao_livre or "", height=70, key=k("dlivre"))
    )


def secao_bens(lista):
    if not lista:
        st.markdown('<div style="color:#9CA3AF; font-size:13px;">(nenhum bem detetado)</div>',
                    unsafe_allow_html=True)
        return
    n = len(lista)
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:7px; margin-bottom:13px;">
      <span style="font-size:10px; font-weight:700; color:#9CA3AF;
                   text-transform:uppercase; letter-spacing:.08em;">Imóveis</span>
      <span style="font-size:10px; background:{CREAM}; color:#6B7280;
                   padding:2px 7px; border-radius:9px; font-weight:600;">
        {n} imóve{'is' if n > 1 else 'l'}
      </span>
    </div>
    """, unsafe_allow_html=True)
    for i, b in enumerate(lista):
        card_bem(i, b)


# ─────────────────────────────────────────────────────────────
# Tab Valores
# ─────────────────────────────────────────────────────────────
def tab_valores_cv(cv):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div style="border:1px solid {BORDER}; border-radius:8px; padding:18px;">
          <div style="font-size:10px; font-weight:600; color:#9CA3AF; text-transform:uppercase;
                      letter-spacing:.06em; margin-bottom:6px;">Preço da venda</div>
          <div style="font-size:26px; font-weight:700; color:{NAVY};
                      margin-bottom:10px; letter-spacing:-.5px;">{_euros(cv.preco_venda)}</div>
        </div>
        """, unsafe_allow_html=True)
        cv.preco_venda = st.number_input(
            "Editar preço (EUR)", value=float(cv.preco_venda or 0.0), step=1000.0,
            key="cv_preco", label_visibility="collapsed",
        ) or None
    with c2:
        st.markdown(f"""
        <div style="border:1px solid {BORDER}; border-radius:8px; padding:18px;">
          <div style="font-size:10px; font-weight:600; color:#9CA3AF; text-transform:uppercase;
                      letter-spacing:.06em; margin-bottom:6px;">Hipoteca nova</div>
          <div style="font-size:26px; font-weight:700; color:#9CA3AF;
                      margin-bottom:10px; letter-spacing:-.5px;">{_euros(cv.hipoteca)}</div>
        </div>
        """, unsafe_allow_html=True)
        cv.hipoteca = st.number_input(
            "Editar hipoteca (EUR)", value=float(cv.hipoteca or 0.0), step=1000.0,
            key="cv_hip", label_visibility="collapsed",
        )

    if cv.hipoteca_a_cancelar:
        st.markdown(f"""
        <div style="border:1px solid {DANGER_BORDER}; background:{DANGER_BG};
                    border-radius:8px; padding:14px 16px; margin-top:12px;">
          <div style="font-size:13px; font-weight:600; color:{DANGER_TEXT};">
            ⚠ Hipoteca antiga a cancelar
          </div>
          <div style="font-size:12px; color:#EF4444; margin-top:2px;">
            Confirmar tratamento no SIMN antes de avançar com o robô.
          </div>
        </div>
        """, unsafe_allow_html=True)
    cv.hipoteca_a_cancelar = st.checkbox(
        "Existe hipoteca antiga a cancelar", value=cv.hipoteca_a_cancelar,
    )


# ─────────────────────────────────────────────────────────────
# Tab DUCs
# ─────────────────────────────────────────────────────────────
COR_DUC = {
    "IMT": ("#DBEAFE", "#1E40AF"),
    "IS": ("#F3E8FF", "#7C3AED"),
    "TGIS": ("#F3E8FF", "#7C3AED"),
}


def tab_ducs(lista):
    if not lista:
        st.markdown('<div style="color:#9CA3AF; font-size:13px;">(nenhum DUC detetado)</div>',
                    unsafe_allow_html=True)
        return
    n = len(lista)
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:7px; margin-bottom:13px;">
      <span style="font-size:10px; font-weight:700; color:#9CA3AF;
                   text-transform:uppercase; letter-spacing:.08em;">DUCs</span>
      <span style="font-size:10px; background:{CREAM}; color:#6B7280;
                   padding:2px 7px; border-radius:9px; font-weight:600;">
        {n} documento{'s' if n > 1 else ''}
      </span>
    </div>
    """, unsafe_allow_html=True)

    for i, d in enumerate(lista):
        tipo = (d.tipo or "?").upper()
        bg, fg = COR_DUC.get(tipo, ("#E5E7EB", "#374151"))
        st.markdown(f"""
        <div style="border:1px solid {BORDER}; border-radius:8px; padding:13px; margin-bottom:8px;">
          <div style="display:inline-flex; align-items:center; background:{bg}; color:{fg};
                      font-size:11px; font-weight:700; padding:5px 10px;
                      border-radius:5px; margin-bottom:9px;">{tipo}</div>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 3, 2])
        d.tipo = _vazio_para_none(c1.text_input("Tipo", d.tipo or "", key=f"duc_{i}_tipo"))
        d.numero = _vazio_para_none(c2.text_input("Número", d.numero or "", key=f"duc_{i}_num"))
        d.montante = c3.number_input(
            "Montante (Finanças, EUR)", value=float(d.montante or 0.0), step=10.0,
            key=f"duc_{i}_mont",
        ) or None

    st.markdown(f"""
    <div style="background:{INFO_BG}; border:1px solid {INFO_BORDER}; border-radius:6px;
                padding:10px 12px; font-size:11px; color:{INFO_TEXT}; line-height:1.5;
                margin-top:8px;">
      O montante vem do Portal das Finanças, não da escritura. Preencher antes de exportar,
      ou deixar vazio se ainda não disponível.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# RENDERERS por tipo
# ─────────────────────────────────────────────────────────────
def render_cv(cv):
    tab_out, tab_bem, tab_val, tab_d = st.tabs([
        f"Outorgantes ({len(cv.vendedores) + len(cv.compradores)})",
        f"Bem ({len(cv.bens)})",
        "Valores",
        f"DUCs ({len(cv.ducs)})",
    ])
    with tab_out:
        secao_outorgantes("Vendedores", cv.vendedores, "vend")
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        secao_outorgantes("Compradores", cv.compradores, "comp")
    with tab_bem:
        secao_bens(cv.bens)
    with tab_val:
        tab_valores_cv(cv)
    with tab_d:
        tab_ducs(cv.ducs)


def render_doacao(d):
    tab_out, tab_bem, tab_val, tab_du = st.tabs([
        f"Outorgantes ({len(d.doadores) + len(d.donatarios)})",
        f"Bem ({len(d.bens)})",
        "Valor",
        f"DUCs ({len(d.ducs)})",
    ])
    with tab_out:
        secao_outorgantes("Doadores", d.doadores, "doa")
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        secao_outorgantes("Donatários", d.donatarios, "don")
    with tab_bem:
        secao_bens(d.bens)
    with tab_val:
        st.markdown(f"""
        <div style="border:1px solid {BORDER}; border-radius:8px; padding:18px; max-width:380px;">
          <div style="font-size:10px; font-weight:600; color:#9CA3AF; text-transform:uppercase;
                      letter-spacing:.06em; margin-bottom:6px;">Valor atribuído à doação</div>
          <div style="font-size:26px; font-weight:700; color:{NAVY};
                      margin-bottom:10px; letter-spacing:-.5px;">{_euros(d.valor_atribuido)}</div>
        </div>
        """, unsafe_allow_html=True)
        d.valor_atribuido = st.number_input(
            "Editar valor (EUR)", value=float(d.valor_atribuido or 0.0), step=1000.0,
            key="d_valor", label_visibility="collapsed",
        ) or None
        st.caption("Valor declarado para efeitos fiscais (Imposto do Selo).")
    with tab_du:
        tab_ducs(d.ducs)


def render_habilitacao(h):
    tab_geral, = st.tabs(["Outorgantes"])
    with tab_geral:
        c1, c2 = st.columns(2)
        h.data_obito = _vazio_para_none(
            c1.text_input("Data de óbito (AAAA-MM-DD)", h.data_obito or "")
        )
        h.com_testamento = c2.checkbox("Habilitação COM testamento", value=h.com_testamento)
        st.markdown("---")
        st.markdown("**Autor da Herança (falecido/a)**")
        if h.autor_heranca is None:
            h.autor_heranca = Outorgante()
        card_outorgante("autor", 0, h.autor_heranca)
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        secao_outorgantes("Herdeiros", h.herdeiros, "herd")
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        secao_outorgantes("Declarantes / testemunhas", h.declarantes, "decl")


def render_partilha(p):
    tab_out, tab_bem, tab_val = st.tabs([
        f"Partilhantes ({len(p.partilhantes)})",
        f"Bens ({len(p.bens)})",
        "Valores",
    ])
    with tab_out:
        c1, c2, c3 = st.columns(3)
        p.tipo_partilha = _vazio_para_none(
            c1.text_input("Tipo (hereditaria/divorcio)", p.tipo_partilha or "")
        )
        p.data_obito = _vazio_para_none(c2.text_input("Data de óbito", p.data_obito or ""))
        if p.tipo_partilha == "hereditaria":
            st.markdown("---")
            st.markdown("**Autor da Herança (falecido/a)**")
            if p.autor_heranca is None:
                p.autor_heranca = Outorgante()
            card_outorgante("autor_p", 0, p.autor_heranca)
            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        secao_outorgantes("Partilhantes", p.partilhantes, "part")
    with tab_bem:
        secao_bens(p.bens)
    with tab_val:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div style="border:1px solid {BORDER}; border-radius:8px; padding:18px;">
              <div style="font-size:10px; font-weight:600; color:#9CA3AF; text-transform:uppercase;
                          letter-spacing:.06em; margin-bottom:6px;">Valor total do acervo</div>
              <div style="font-size:26px; font-weight:700; color:{NAVY};
                          margin-bottom:10px; letter-spacing:-.5px;">{_euros(p.valor_total_acervo)}</div>
            </div>
            """, unsafe_allow_html=True)
            p.valor_total_acervo = st.number_input(
                "Editar valor acervo (EUR)", value=float(p.valor_total_acervo or 0.0),
                step=1000.0, key="p_acervo", label_visibility="collapsed",
            ) or None
        with c2:
            st.markdown(f"""
            <div style="border:1px solid {BORDER}; border-radius:8px; padding:18px;">
              <div style="font-size:10px; font-weight:600; color:#9CA3AF; text-transform:uppercase;
                          letter-spacing:.06em; margin-bottom:6px;">Tornas</div>
              <div style="font-size:26px; font-weight:700; color:#9CA3AF;
                          margin-bottom:10px; letter-spacing:-.5px;">{_euros(p.tornas)}</div>
            </div>
            """, unsafe_allow_html=True)
            p.tornas = st.number_input(
                "Editar tornas (EUR)", value=float(p.tornas or 0.0), step=100.0,
                key="p_tornas", label_visibility="collapsed",
            ) or None


RENDERERS = {
    CompraVenda: render_cv,
    Doacao: render_doacao,
    Habilitacao: render_habilitacao,
    Partilha: render_partilha,
}


# ─────────────────────────────────────────────────────────────
# Main flow
# ─────────────────────────────────────────────────────────────
obj = st.session_state.get("obj")
nome_ficheiro = st.session_state.get("nome_ficheiro")

render_sidebar(obj, nome_ficheiro)

# Upload (visível apenas quando não há ficheiro)
if obj is None:
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
    ficheiro = st.file_uploader(
        "Carregar escritura (.doc ou .docx)",
        type=["doc", "docx"],
        help="O ficheiro é processado localmente. Só o texto vai para a API.",
    )
    if ficheiro is None:
        st.markdown(f"""
        <div style="text-align:center; padding:32px; color:#9CA3AF;">
          <div style="font-size:13px; font-weight:500; color:#6B7280; margin-bottom:6px;">
            Carrega uma escritura para extrair os campos automaticamente.
          </div>
          <div style="font-size:12px;">
            O ficheiro é processado localmente. Só o texto vai para a API.
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    with st.status(f"A extrair campos de {ficheiro.name}...", expanded=True) as status:
        st.write("A ler o documento...")
        sufixo = os.path.splitext(ficheiro.name)[1].lower() or ".docx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
            tmp.write(ficheiro.read())
            caminho_tmp = tmp.name
        try:
            st.write("A chamar o modelo de linguagem...")
            st.session_state.obj = extrair_de_ficheiro(caminho_tmp)
            st.session_state.nome_ficheiro = ficheiro.name
            st.session_state.ts_extracao = (
                "Extraído às " + datetime.datetime.now().strftime("%H:%M · %d %b %Y").lower()
            )
            status.update(label="Extração concluída!", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Erro na extração: {e}")
            st.stop()
        finally:
            os.unlink(caminho_tmp)
    st.rerun()

# Estado: temos obj. Renderizar tudo.
render_topbar(obj)
render_warnings(obj)
RENDERERS[type(obj)](obj)

# JSON preview (toggle)
if st.session_state.get("show_json"):
    st.markdown(f"""
    <div style="background:#1A2A3F; border-radius:8px; padding:14px 16px; margin-top:16px;">
      <div style="font-size:9px; font-weight:700; color:rgba(255,255,255,.3);
                  text-transform:uppercase; letter-spacing:.08em; margin-bottom:10px;">
        Pré-visualização JSON · partilha/campos.json
      </div>
      <pre style="font-size:11px; color:#86EFAC; font-family:monospace;
                  white-space:pre-wrap; word-break:break-word; line-height:1.7;
                  margin:0; max-height:400px; overflow:auto;">{obj.model_dump_json(indent=2)}</pre>
    </div>
    """, unsafe_allow_html=True)

# Bottom bar (sticky)
st.markdown(f"""
<style>
  div.bottom-bar {{
    position:fixed; bottom:0; left:252px; right:0;
    background:#fff; border-top:1px solid {BORDER};
    padding:11px 26px; display:flex; align-items:center; justify-content:space-between;
    z-index:100;
  }}
  @media (max-width:768px) {{ div.bottom-bar {{ left:0; }} }}
</style>
<div class="bottom-bar" id="footer-anchor"></div>
""", unsafe_allow_html=True)

# Use Streamlit native buttons inside their own row, styled to sit at bottom
st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
with c1:
    if st.button("← Carregar outra escritura", key="reset_main"):
        for k in ("obj", "nome_ficheiro", "ts_extracao", "exportado", "show_json"):
            st.session_state.pop(k, None)
        st.rerun()
with c2:
    if st.button("{ } JSON", key="toggle_json"):
        st.session_state.show_json = not st.session_state.get("show_json", False)
        st.rerun()
with c3:
    if st.button("Exportar", key="export"):
        os.makedirs(os.path.dirname(CAMINHO_JSON), exist_ok=True)
        obj.avisos = obj.validar_e_avisar()
        with open(CAMINHO_JSON, "w", encoding="utf-8") as f:
            f.write(obj.model_dump_json(indent=2))
        st.session_state.exportado = True
        st.success(f"Exportado para {CAMINHO_JSON}")
with c4:
    if st.button("💾 Exportar JSON", type="primary", key="preencher_simn"):
        os.makedirs(os.path.dirname(CAMINHO_JSON), exist_ok=True)
        obj.avisos = obj.validar_e_avisar()
        with open(CAMINHO_JSON, "w", encoding="utf-8") as f:
            f.write(obj.model_dump_json(indent=2))
        st.session_state.exportado = True
        st.session_state.robo_lancado = True  # activa a secção "Preencher SIMN" em baixo

# Instruções para a funcionária quando lança o robô
if st.session_state.get("robo_lancado"):
    st.markdown(f"""
    <div style="background:#F0F9FF; border:2px solid #7DD3FC; border-radius:10px;
                padding:16px 20px; margin-top:12px;">
      <div style="font-size:14px; font-weight:700; color:#0369A1;
                  text-transform:uppercase; letter-spacing:.06em; margin-bottom:8px;">
        🤖 Preencher SIMN — instruções
      </div>
      <div style="font-size:13px; color:#075985; line-height:1.7;">
        <b>Para cada outorgante:</b>
        <ol style="margin:6px 0 0 20px;">
          <li>No <b>SIMN</b>: clica em <b>Adicionar</b> (Vendedor/Comprador/etc.) → <b>Novo Outorgante Singular</b> → form abre</li>
          <li>Clica no campo <b>Nº Contribuinte</b> do form</li>
          <li>Volta aqui, clica no botão azul do outorgante que queres preencher</li>
          <li>Contagem 8s → Alt+Tab ao SIMN → robô preenche sozinho</li>
          <li>Revê, clica <b>OK</b> no form do SIMN, passa ao próximo</li>
        </ol>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Construir a lista de outorgantes/partilhantes
    def _lista_para_botoes(cv_obj):
        items = []
        for tipo, lista_attr in [
            ("Vendedor", "vendedores"), ("Comprador", "compradores"),
            ("Doador", "doadores"), ("Donatário", "donatarios"),
            ("Herdeiro", "herdeiros"), ("Partilhante", "partilhantes"),
        ]:
            lista = getattr(cv_obj, lista_attr, None) or []
            for i, o in enumerate(lista, 1):
                items.append((f"{tipo} {i}", o))
        # autor_heranca (habilitacao/partilha)
        autor = getattr(cv_obj, "autor_heranca", None)
        if autor:
            items.append(("Autor da Herança", autor))
        return items

    outorgantes_disponiveis = _lista_para_botoes(obj)
    if outorgantes_disponiveis:
        # Mostrar resultado persistente do ultimo run (sobrevive a reruns)
        status = st.session_state.get("ultimo_robo_status")
        if status:
            if status["code"] == 0:
                st.success(f"✅ **{status['rotulo']} preenchido!** Revê no SIMN e clica OK. "
                           f"Depois avança para o próximo.")
            elif status["code"] == 2:
                st.error(f"❌ **SIMN não estava em foco** quando a contagem terminou. "
                         f"Faz isto pela ordem: (1) no SIMN, clica no campo Nº Contribuinte "
                         f"do form Vendedor(es). (2) Volta aqui e clica ▶ Preencher **outra vez**.")
            else:
                st.error(f"❌ Erro (código {status['code']}). Output do robô:")
                st.code(f"{status['stdout']}\n---STDERR---\n{status['stderr']}", language="text")
            if st.button("Dispensar mensagem", key="dispensar_status"):
                st.session_state.ultimo_robo_status = None
                st.rerun()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        for idx, (rotulo, outorgante) in enumerate(outorgantes_disponiveis):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(
                    f"**{rotulo}**  ·  {outorgante.nome or '?'}  ·  NIF `{outorgante.nif or '?'}`"
                )
            with c2:
                if st.button(f"▶ Preencher", key=f"preench_btn_{idx}", use_container_width=True):
                    import subprocess
                    import sys as _sys
                    caminho_robo = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "peca_b_robo", "robo.py")
                    )
                    # CREATE_NO_WINDOW = 0x08000000 (sem consola visível)
                    with st.spinner(f"Robô a preencher {rotulo}... Alt+Tab para o SIMN nos próximos 8s."):
                        try:
                            env = os.environ.copy()
                            env["PYTHONIOENCODING"] = "utf-8"
                            resultado = subprocess.run(
                                [_sys.executable, caminho_robo, "--idx", str(idx),
                                 os.path.abspath(CAMINHO_JSON)],
                                creationflags=0x08000000,
                                capture_output=True, text=True, timeout=120,
                                env=env, encoding="utf-8", errors="replace",
                            )
                            st.session_state.ultimo_robo_status = {
                                "rotulo": rotulo,
                                "code": resultado.returncode,
                                "stdout": (resultado.stdout or "")[-1500:],
                                "stderr": (resultado.stderr or "")[-1500:],
                            }
                        except subprocess.TimeoutExpired:
                            st.session_state.ultimo_robo_status = {
                                "rotulo": rotulo, "code": 99,
                                "stdout": "", "stderr": "Timeout (>120s). Processo preso.",
                            }
                        except Exception as e:
                            st.session_state.ultimo_robo_status = {
                                "rotulo": rotulo, "code": 98,
                                "stdout": "", "stderr": f"Erro a lançar robô: {e}",
                            }
                    st.rerun()
