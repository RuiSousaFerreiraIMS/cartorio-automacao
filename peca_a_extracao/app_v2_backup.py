"""
Interface mediadora v2 (Streamlit) - Peça A.

Fluxo:
  1. funcionaria carrega o .doc/.docx da escritura
  2. extrator deteta tipo (CV/Doacao/Habilitacao/Partilha) e chama o LLM
  3. campos aparecem editaveis em seccoes colapsaveis, com avisos no topo
  4. funcionaria revee/corrige  <- VALIDACAO HUMANA
  5. botao "Exportar" grava partilha/campos.json (o robo le este ficheiro)

Correr localmente:
  $env:GOOGLE_API_KEY = "..."          # ou GROQ_API_KEY se usares Groq
  streamlit run app_v2_backup.py
"""

from __future__ import annotations

import json
import os
import tempfile

import streamlit as st

from extrator import extrair_de_ficheiro
from modelos import (
    Bem, CompraVenda, DUC, Doacao, EstadoCivil, Habilitacao,
    Outorgante, Partilha, RegimeBens,
)

# -----------------------------------------------------------------------------
# Configuracao da pagina
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Cartório — Extração de Escrituras",
    layout="wide",
)

CAMINHO_JSON = os.path.join("..", "partilha", "campos.json")
PADROES_INFO = ("casal detetado",)


# -----------------------------------------------------------------------------
# Sidebar: estado do sistema
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Estado")
    provedor = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provedor == "groq":
        modelo = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        tem_chave = bool(os.environ.get("GROQ_API_KEY"))
    else:
        modelo = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        tem_chave = bool(os.environ.get("GOOGLE_API_KEY"))
    st.write(f"**Provedor:** `{provedor}`")
    st.write(f"**Modelo:** `{modelo}`")
    if tem_chave:
        st.success("Chave API configurada")
    else:
        st.error("Chave API em falta")
    st.divider()
    st.caption(f"Destino do JSON:\n`{os.path.abspath(CAMINHO_JSON)}`")


# -----------------------------------------------------------------------------
# Cabecalho + upload
# -----------------------------------------------------------------------------
st.title("Extração de Escrituras → SIMN")
st.caption(
    "Carrega uma escritura, revee os campos extraídos, exporta para o robô. "
    "Validação humana obrigatória antes de exportar."
)

ficheiro = st.file_uploader("Carregar escritura (.doc ou .docx)", type=["doc", "docx"])

if ficheiro is None:
    st.info("Carrega um ficheiro para começar.")
    st.stop()


# -----------------------------------------------------------------------------
# Extracao (com cache na session_state)
# -----------------------------------------------------------------------------
chave_cache = ficheiro.name
if st.session_state.get("nome_ficheiro") != chave_cache:
    with st.spinner(f"A extrair campos de {ficheiro.name}..."):
        sufixo = os.path.splitext(ficheiro.name)[1].lower() or ".docx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
            tmp.write(ficheiro.read())
            caminho_tmp = tmp.name
        try:
            st.session_state.obj = extrair_de_ficheiro(caminho_tmp)
            st.session_state.nome_ficheiro = chave_cache
        except Exception as e:
            st.error(f"Erro na extração: {e}")
            st.stop()
        finally:
            os.unlink(caminho_tmp)

obj = st.session_state.obj


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _vazio_para_none(v):
    """Streamlit text_input devolve '' quando vazio; queremos None nesses campos."""
    return v if v else None


def render_avisos(obj):
    """Mostra avisos do schema: distingue info (azul) de aviso a serio (amarelo)."""
    obj.avisos = obj.validar_e_avisar()
    avisos_serios = [a for a in obj.avisos if not any(p in a.lower() for p in PADROES_INFO)]
    avisos_info = [a for a in obj.avisos if a not in avisos_serios]
    if not obj.avisos:
        st.success("Sem avisos. Revee na mesma antes de exportar.")
    for a in avisos_serios:
        st.warning(a)
    for a in avisos_info:
        st.info(a)


# -----------------------------------------------------------------------------
# Componente: editor de Outorgante
# -----------------------------------------------------------------------------
def editar_outorgante(prefixo: str, indice: int, o: Outorgante):
    """Mostra todos os campos do Outorgante, editaveis. Modifica em place."""
    k = lambda campo: f"{prefixo}_{indice}_{campo}"  # noqa: E731

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
        c1.text_input("Cônjuge NIF (se casal)", o.conjuge_de_nif or "", key=k("cnj"))
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
        st.text_input("Documento (CC/Título residencia)", o.doc_identificacao or "", key=k("doc"))
    )


def secao_outorgantes(titulo: str, lista: list[Outorgante], prefixo: str):
    """Secção expansivel com cabeçalho + cada outorgante editavel."""
    with st.expander(f"{titulo} — {len(lista)} pessoa(s)", expanded=True):
        if not lista:
            st.caption("(nenhum/a detetado/a)")
            return
        for i, o in enumerate(lista):
            st.markdown(f"**{i+1}. {o.nome or '(sem nome)'}**  ·  NIF `{o.nif or '?'}`")
            editar_outorgante(prefixo, i, o)
            if i < len(lista) - 1:
                st.divider()


# -----------------------------------------------------------------------------
# Componente: editor de Bem
# -----------------------------------------------------------------------------
TIPOS_BEM = [("U", "Urbano"), ("R", "Rústico"), ("M", "Misto"), (None, "(n/a)")]


def editar_bem(indice: int, b: Bem):
    k = lambda campo: f"bem_{indice}_{campo}"  # noqa: E731

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
        "VPT (EUR)", value=float(b.valor_patrimonial or 0.0), step=100.0,
        key=k("vpt"),
    ) or None

    c1, c2 = st.columns(2)
    b.freguesia = _vazio_para_none(c1.text_input("Freguesia", b.freguesia or "", key=k("freg")))
    b.concelho = _vazio_para_none(c2.text_input("Concelho", b.concelho or "", key=k("conc")))

    c1, c2 = st.columns(2)
    b.descricao_predial = _vazio_para_none(
        c1.text_input("Descrição predial (nº / freguesia)", b.descricao_predial or "", key=k("desc"))
    )
    b.artigo_matricial = _vazio_para_none(
        c2.text_input("Artigo matricial", b.artigo_matricial or "", key=k("art"))
    )

    c1, c2 = st.columns(2)
    b.certidao_predial = _vazio_para_none(
        c1.text_input("Certidão predial (PP-...)", b.certidao_predial or "", key=k("cert"))
    )
    b.codigo_simn = _vazio_para_none(
        c2.text_input("Código SIMN (preencher se vazio)", b.codigo_simn or "", key=k("simn"))
    )

    b.morada = _vazio_para_none(st.text_input("Morada", b.morada or "", key=k("mor")))
    b.descricao_livre = _vazio_para_none(
        st.text_area("Descrição livre", b.descricao_livre or "", height=80, key=k("dlivre"))
    )


def secao_bens(lista: list[Bem]):
    with st.expander(f"Bens — {len(lista)} imóvel/eis", expanded=True):
        if not lista:
            st.caption("(nenhum bem detetado)")
            return
        for i, b in enumerate(lista):
            sub = b.morada or b.freguesia or b.descricao_predial or "?"
            st.markdown(f"**Bem {i+1}** · {sub}")
            editar_bem(i, b)
            if i < len(lista) - 1:
                st.divider()


# -----------------------------------------------------------------------------
# Componente: editor de DUCs
# -----------------------------------------------------------------------------
def secao_ducs(lista: list[DUC]):
    with st.expander(f"DUCs — {len(lista)} documento(s)"):
        if not lista:
            st.caption("(nenhum DUC detetado)")
            return
        for i, d in enumerate(lista):
            c1, c2, c3 = st.columns(3)
            d.numero = _vazio_para_none(c1.text_input("Número", d.numero or "", key=f"duc_{i}_num"))
            d.tipo = _vazio_para_none(c2.text_input("Tipo (IMT/IS/TGIS)", d.tipo or "", key=f"duc_{i}_tipo"))
            d.montante = c3.number_input(
                "Montante (EUR)", value=float(d.montante or 0.0), step=10.0, key=f"duc_{i}_mont",
            ) or None
        st.caption("Montante normalmente preenchido à mão das Finanças.")


# -----------------------------------------------------------------------------
# Renderers por tipo
# -----------------------------------------------------------------------------
def render_cv(cv: CompraVenda):
    st.subheader("Compra-venda")
    c1, c2 = st.columns(2)
    cv.data_escritura = _vazio_para_none(
        c1.text_input("Data da escritura (AAAA-MM-DD)", cv.data_escritura or "")
    )
    cv.objeto = _vazio_para_none(c2.text_input("Objeto", cv.objeto or ""))

    secao_outorgantes("Vendedor(es)", cv.vendedores, "vend")
    secao_outorgantes("Comprador(es)", cv.compradores, "comp")
    secao_bens(cv.bens)

    with st.expander("Valores", expanded=True):
        c1, c2 = st.columns(2)
        cv.preco_venda = c1.number_input(
            "Preço da venda (EUR)", value=float(cv.preco_venda or 0.0), step=1000.0,
        ) or None
        cv.hipoteca = c2.number_input(
            "Hipoteca NOVA (EUR, 0 se não aplicável)",
            value=float(cv.hipoteca or 0.0), step=1000.0,
        )
        cv.hipoteca_a_cancelar = st.checkbox(
            "Existe hipoteca antiga a cancelar", value=cv.hipoteca_a_cancelar,
        )

    secao_ducs(cv.ducs)


def render_doacao(d: Doacao):
    st.subheader("Doação")
    c1, c2 = st.columns(2)
    d.data_escritura = _vazio_para_none(
        c1.text_input("Data da escritura", d.data_escritura or "")
    )
    d.objeto = _vazio_para_none(c2.text_input("Objeto", d.objeto or ""))

    secao_outorgantes("Doador(es)", d.doadores, "doa")
    secao_outorgantes("Donatário(s)", d.donatarios, "don")
    secao_bens(d.bens)

    with st.expander("Valor", expanded=True):
        d.valor_atribuido = st.number_input(
            "Valor atribuído à doação (EUR)",
            value=float(d.valor_atribuido or 0.0), step=1000.0,
        ) or None
        st.caption("Valor declarado para efeitos fiscais (Imposto do Selo).")

    secao_ducs(d.ducs)


def render_habilitacao(h: Habilitacao):
    st.subheader("Habilitação Notarial")
    c1, c2 = st.columns(2)
    h.data_escritura = _vazio_para_none(
        c1.text_input("Data da escritura", h.data_escritura or "")
    )
    h.objeto = _vazio_para_none(c2.text_input("Objeto", h.objeto or ""))

    c1, c2 = st.columns(2)
    h.data_obito = _vazio_para_none(
        c1.text_input("Data de óbito (AAAA-MM-DD)", h.data_obito or "")
    )
    h.com_testamento = c2.checkbox("Habilitação COM testamento", value=h.com_testamento)

    with st.expander("Autor da Herança (falecido/a)", expanded=True):
        if h.autor_heranca is None:
            h.autor_heranca = Outorgante()
        editar_outorgante("autor", 0, h.autor_heranca)

    secao_outorgantes("Herdeiros", h.herdeiros, "herd")
    secao_outorgantes("Declarantes / testemunhas", h.declarantes, "decl")


def render_partilha(p: Partilha):
    st.subheader("Partilha")
    c1, c2, c3 = st.columns(3)
    p.data_escritura = _vazio_para_none(
        c1.text_input("Data da escritura", p.data_escritura or "")
    )
    p.tipo_partilha = _vazio_para_none(
        c2.text_input("Tipo (hereditaria/divorcio)", p.tipo_partilha or "")
    )
    p.data_obito = _vazio_para_none(
        c3.text_input("Data de óbito", p.data_obito or "")
    )
    p.objeto = _vazio_para_none(st.text_input("Objeto", p.objeto or ""))

    if p.tipo_partilha == "hereditaria":
        with st.expander("Autor da Herança (falecido/a)", expanded=True):
            if p.autor_heranca is None:
                p.autor_heranca = Outorgante()
            editar_outorgante("autor", 0, p.autor_heranca)

    secao_outorgantes("Partilhantes", p.partilhantes, "part")
    secao_bens(p.bens)

    with st.expander("Valores", expanded=True):
        c1, c2 = st.columns(2)
        p.valor_total_acervo = c1.number_input(
            "Valor total do acervo (EUR)",
            value=float(p.valor_total_acervo or 0.0), step=1000.0,
        ) or None
        p.tornas = c2.number_input(
            "Tornas (EUR)", value=float(p.tornas or 0.0), step=100.0,
        ) or None


RENDERERS = {
    CompraVenda: render_cv,
    Doacao: render_doacao,
    Habilitacao: render_habilitacao,
    Partilha: render_partilha,
}


# -----------------------------------------------------------------------------
# Cabecalho da escritura + avisos + editor
# -----------------------------------------------------------------------------
tipo_humano = {
    "CV": "Compra-venda", "DOAC": "Doação",
    "HAB": "Habilitação Notarial", "PART": "Partilha",
}.get(obj.mnemonica, obj.mnemonica)

st.subheader(f"Tipo detetado: **{tipo_humano}** ({obj.mnemonica})")

render_avisos(obj)

st.divider()

RENDERERS[type(obj)](obj)


# -----------------------------------------------------------------------------
# Exportar
# -----------------------------------------------------------------------------
st.divider()
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown(f"**Destino:** `{os.path.abspath(CAMINHO_JSON)}`")
    st.caption("O robô (Peça B) vai ler este ficheiro para preencher o SIMN.")
with c2:
    if st.button("Exportar para o robô", type="primary", use_container_width=True):
        os.makedirs(os.path.dirname(CAMINHO_JSON), exist_ok=True)
        obj.avisos = obj.validar_e_avisar()
        with open(CAMINHO_JSON, "w", encoding="utf-8") as f:
            f.write(obj.model_dump_json(indent=2))
        st.success(f"Exportado para `{CAMINHO_JSON}`.")
        st.balloons()

# Preview do JSON final (debug, util para a funcionaria ver tudo)
with st.expander("Pré-visualizar JSON final"):
    st.json(json.loads(obj.model_dump_json()))
