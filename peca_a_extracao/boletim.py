"""
Gera o PDF do BOLETIM de participacao de testamento (Modelo 54, Tip. Tipomar).

O formulario e' PRE-IMPRESSO (esta na bandeja da impressora), 130mm x 180mm. Este
PDF tem SO os dados, nas posicoes certas, para cair por cima das linhas do
formulario. A funcionaria imprime este PDF nessa bandeja, a 100% (tamanho real).

CALIBRACAO: as posicoes sao estimativas do layout. Depois de um teste de impressao
(imprimir numa folha branca e sobrepor ao formulario), se estiver tudo desviado
mexe-se em OFFSET_X / OFFSET_Y (mm); se um campo em concreto estiver torto, mexe-se
a sua posicao em POSICOES.
"""
from __future__ import annotations

import io

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

FORM_W_MM = 130.0
FORM_H_MM = 180.0

# Ajuste GLOBAL apos o teste de impressao (mm). +X = direita, +Y = baixo.
OFFSET_X = 0.0
OFFSET_Y = 0.0

FONTE = "Helvetica"
TAMANHO = 9

# Posicoes de cada campo: (x da esquerda, y a partir do TOPO), em mm.
POSICOES = {
    "ult_apelido":   (26, 22),
    "outros_apel":  (100, 22),
    "nome_prop":     (26, 37),
    "estado":        (22, 45),
    "nasc_dia":      (74, 45),
    "nasc_mes":      (86, 45),
    "nasc_ano":      (96, 45),
    "nat_freg":      (40, 54),
    "nat_conc":      (16, 62),
    "nat_pais":      (95, 62),
    "nacionalidade": (42, 70),
    "resid_freg":    (42, 78),
    "resid_conc":    (16, 86),
    "pai":           (40, 95),
    "mae":           (18, 103),
    "especie":       (52, 111),
    "cartorio":      (58, 128),
    "a_cargo":       (30, 136),
}


def _iso_para_ddmmaaaa(iso):
    """'AAAA-MM-DD' -> ('DD','MM','AAAA'). Devolve ('','','') se nao der."""
    import re
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso or "").strip())
    if m:
        ano, mes, dia = m.groups()
        return dia, mes, ano
    return "", "", ""


def valores_boletim(t) -> dict:
    """Mapeia um Testamento -> valores de cada campo do boletim."""
    td = t.testador
    nome = ((td.nome if td else None) or "").strip()
    partes = nome.split()
    ult = partes[-1] if partes else ""
    prop = partes[0] if partes else ""
    outros = " ".join(partes[1:-1]) if len(partes) > 2 else ""

    dia, mes, ano = _iso_para_ddmmaaaa(getattr(td, "data_nascimento", None) if td else None)
    d_dia, d_mes, d_ano = _iso_para_ddmmaaaa(t.data_escritura)
    data_acto = f"{d_dia}/{d_mes}/{d_ano}" if d_dia else ""
    especie = f"{t.especie or 'Testamento público'} - {data_acto}".rstrip(" -")

    estado = ""
    if td and td.estado_civil:
        estado = td.estado_civil.value.capitalize()

    return {
        "ult_apelido": ult,
        "outros_apel": outros,
        "nome_prop": prop,
        "estado": estado,
        "nasc_dia": dia, "nasc_mes": mes, "nasc_ano": ano,
        # Naturalidade: freg/conc SO se portugues; pais SO se estrangeiro (o (*) no form).
        "nat_freg": (td.naturalidade_freguesia if td else "") or "",
        "nat_conc": (td.naturalidade_concelho if td else "") or "",
        "nat_pais": (td.naturalidade_pais if td else "") or "",
        "nacionalidade": (td.nacionalidade if td else "") or "",
        "resid_freg": (td.morada_freguesia if td else "") or "",
        "resid_conc": (td.morada_concelho if td else "") or "",
        "pai": (td.nome_pai if td else "") or "",
        "mae": (td.nome_mae if td else "") or "",
        "especie": especie,
        "cartorio": "Alcobaça",
        "a_cargo": "Rui Sérgio Heleno Ferreira",
    }


def gerar_boletim_pdf(t) -> bytes:
    """Devolve os bytes de um PDF 130x180mm com os dados do testamento posicionados."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(FORM_W_MM * mm, FORM_H_MM * mm))
    c.setFont(FONTE, TAMANHO)
    valores = valores_boletim(t)
    for campo, (x, y) in POSICOES.items():
        texto = str(valores.get(campo, "") or "").strip()
        if not texto:
            continue
        px = (x + OFFSET_X) * mm
        py = (FORM_H_MM - y + OFFSET_Y) * mm   # reportlab conta o y de BAIXO
        c.drawString(px, py, texto)
    c.showPage()
    c.save()
    return buf.getvalue()
