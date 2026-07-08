"""
Le todos os JSONs em peca_a_extracao/saidas/ e produz um PNG com tabela
resumo de TODAS as escrituras processadas (CV, Doacao, Habilitacao, Partilha).

Uso:
    python gerar_relatorio_pai.py

Saida: relatorio_pai.png na raiz do projeto.
"""

from __future__ import annotations

import glob
import json
import os
import sys
import textwrap

import matplotlib.pyplot as plt

sys.path.insert(0, "peca_a_extracao")
from modelos import CompraVenda, Doacao, Habilitacao, Partilha  # noqa: E402

PASTA_SAIDAS = "peca_a_extracao/saidas"

# tipo na frente do nome do ficheiro -> classe + titulo amigavel
TIPO_SCHEMA = {
    "cv": (CompraVenda, "Compra-venda"),
    "doacao": (Doacao, "Doação"),
    "habilitacao": (Habilitacao, "Habilitação"),
    "partilha": (Partilha, "Partilha"),
}

_PADROES_INFO = ("casal detetado",)  # avisos que sao so informativos, nao alarme


def _euros(v) -> str:
    if v is None or v == 0:
        return "—"
    return f"{v:,.0f} €".replace(",", " ")


def fmt_outorgantes(lista) -> str:
    if not lista:
        return "—"
    linhas = []
    for o in lista:
        marca = "♥ " if o.conjuge_de_nif else ""
        partes = (o.nome or "?").split()
        nome = f"{partes[0]} {partes[-1]}" if len(partes) > 2 else " ".join(partes)
        linhas.append(f"{marca}{nome} ({o.nif or '?'})")
    return "\n".join(linhas)


def fmt_bens(bens) -> str:
    if not bens:
        return "—"
    if len(bens) > 1:
        primeiro = bens[0]
        onde = primeiro.freguesia or primeiro.concelho or "?"
        return f"{len(bens)} bens\n(1º: {onde})"
    b = bens[0]
    tipo = {"U": "Urbano", "R": "Rústico"}.get(b.tipo or "", b.tipo or "?")
    onde = b.freguesia or b.concelho or "?"
    extras = []
    if b.designacao_fracao:
        extras.append(f"Fração {b.designacao_fracao}")
    if b.valor_patrimonial:
        extras.append(f"VPT {b.valor_patrimonial:.0f}€")
    suf = "\n" + " | ".join(extras) if extras else ""
    return f"{tipo}, {onde}{suf}"


def fmt_avisos(obj) -> str:
    if not obj.avisos:
        return "Sem avisos"
    return "\n".join("• " + "\n  ".join(textwrap.wrap(a, 38)) for a in obj.avisos)


def linha_cv(cv: CompraVenda) -> list[str]:
    """Constroi uma linha da tabela para Compra-venda."""
    hipoteca = "Sem hipoteca"
    if cv.hipoteca and cv.hipoteca > 0:
        hipoteca = f"Nova\n{_euros(cv.hipoteca)}"
    elif cv.hipoteca_a_cancelar:
        hipoteca = "Antiga\na cancelar"
    return [
        fmt_outorgantes(cv.vendedores),
        fmt_outorgantes(cv.compradores),
        fmt_bens(cv.bens),
        _euros(cv.preco_venda),
        hipoteca,
        fmt_avisos(cv),
    ]


def linha_doacao(d: Doacao) -> list[str]:
    return [
        fmt_outorgantes(d.doadores),
        fmt_outorgantes(d.donatarios),
        fmt_bens(d.bens),
        _euros(d.valor_atribuido),
        "n/a",
        fmt_avisos(d),
    ]


def linha_habilitacao(h: Habilitacao) -> list[str]:
    autor = "—"
    if h.autor_heranca:
        partes = (h.autor_heranca.nome or "?").split()
        nome = f"{partes[0]} {partes[-1]}" if len(partes) > 2 else " ".join(partes)
        autor = f"Falecido:\n{nome}\n({h.autor_heranca.nif or '?'})"
        if h.data_obito:
            autor += f"\n†{h.data_obito}"
    bem_str = f"{'COM' if h.com_testamento else 'SEM'} testamento"
    return [
        autor,
        fmt_outorgantes(h.herdeiros),
        bem_str,
        "n/a",
        "n/a",
        fmt_avisos(h),
    ]


def linha_partilha(p: Partilha) -> list[str]:
    autor = "—"
    if p.autor_heranca:
        partes = (p.autor_heranca.nome or "?").split()
        nome = f"{partes[0]} {partes[-1]}" if len(partes) > 2 else " ".join(partes)
        autor = f"Falecido:\n{nome}\n({p.autor_heranca.nif or '?'})"
    valores = _euros(p.valor_total_acervo)
    if p.tornas:
        valores += f"\nTornas: {_euros(p.tornas)}"
    return [
        autor,
        fmt_outorgantes(p.partilhantes),
        fmt_bens(p.bens),
        valores,
        "n/a",
        fmt_avisos(p),
    ]


CONSTRUTORES = {
    "cv": linha_cv,
    "doacao": linha_doacao,
    "habilitacao": linha_habilitacao,
    "partilha": linha_partilha,
}


def carregar_todos() -> list[tuple[str, str, list[str], str]]:
    """Devolve lista de (tipo_amigavel, titulo, celulas, cor)."""
    resultados = []
    for caminho in sorted(glob.glob(os.path.join(PASTA_SAIDAS, "*.json"))):
        nome_ficheiro = os.path.basename(caminho)
        tipo = nome_ficheiro.split("__", 1)[0]
        if tipo not in TIPO_SCHEMA:
            continue
        Schema, tipo_amigavel = TIPO_SCHEMA[tipo]
        with open(caminho, encoding="utf-8") as f:
            obj = Schema(**json.load(f))
        obj.avisos = obj.validar_e_avisar()

        # Titulo amigavel = parte depois do "tipo__", em title case
        slug = nome_ficheiro.split("__", 1)[1].rsplit(".", 1)[0]
        titulo = slug.replace("_", " ").title()

        celulas = CONSTRUTORES[tipo](obj)
        # cor verde se nao ha avisos a serio; amarelo se ha algo para rever
        avisos_a_serio = [a for a in obj.avisos if not any(p in a.lower() for p in _PADROES_INFO)]
        cor = "#d4edda" if not avisos_a_serio else "#fff3cd"

        resultados.append((tipo_amigavel, titulo, celulas, cor))
    return resultados


def desenhar(linhas, saida="relatorio_pai.png"):
    cabecalho = [
        "Tipo / Escritura",
        "Lado A\n(vendedor / doador / falecido)",
        "Lado B\n(comprador / donatário / herdeiros)",
        "Bem(ns)",
        "Valor",
        "Hipoteca",
        "Avisos para a funcionária rever",
    ]
    larguras = [0.13, 0.16, 0.16, 0.13, 0.08, 0.08, 0.26]

    fig, ax = plt.subplots(figsize=(20, max(10, 1.3 * len(linhas) + 4)))
    ax.set_axis_off()
    fig.suptitle(
        f"Teste de extração automática (25 junho 2026) — {len(linhas)} escrituras processadas",
        fontsize=15, weight="bold", y=0.97,
    )
    fig.text(
        0.5, 0.93,
        "Verde = extração limpa.  Amarelo = funcionária revê os avisos antes de avançar.",
        ha="center", fontsize=10, style="italic", color="#555",
    )

    rows = [[f"{tipo}\n{titulo}"] + celulas for tipo, titulo, celulas, _ in linhas]
    cores_primeira_col = [cor for *_, cor in linhas]

    tabela = ax.table(
        cellText=rows,
        colLabels=cabecalho,
        colWidths=larguras,
        loc="center",
        cellLoc="left",
    )
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(9)
    tabela.scale(1, 4.5)

    for j in range(len(cabecalho)):
        c = tabela[0, j]
        c.set_facecolor("#2c3e50")
        c.set_text_props(color="white", weight="bold")
        c.set_height(0.07)

    for i, cor in enumerate(cores_primeira_col, start=1):
        tabela[i, 0].set_facecolor(cor)
        tabela[i, 0].set_text_props(weight="bold")

    for cell in tabela.get_celld().values():
        cell.set_edgecolor("#bdc3c7")
        cell.set_linewidth(0.5)
        cell.PAD = 0.04

    fig.text(
        0.5, 0.03,
        "♥ = pessoas marcadas como casal entre si  |  † = data de óbito  |  VPT = valor patrimonial",
        ha="center", fontsize=8, style="italic", color="#777",
    )

    plt.savefig(saida, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"OK: {saida} ({len(linhas)} linhas)")


if __name__ == "__main__":
    linhas = carregar_todos()
    if not linhas:
        print(f"Nenhum JSON encontrado em {PASTA_SAIDAS}. Corre 'python extrair_tudo.py' primeiro.")
        raise SystemExit(1)
    desenhar(linhas)
