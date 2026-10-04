"""
Triagem dos reportes de problema recebidos das funcionarias.

A funcionaria carrega em "Reportar problema" -> chega-me um email com um ZIP
(DESCRICAO, DIAGNOSTICO, campos.json, texto_extraido, a escritura). Guardam-se
esses ZIP numa pasta e esta ferramenta:
  1. extrai cada ZIP para uma subpasta (para eu abrir a escritura/campos),
  2. le a descricao + diagnostico de cada um,
  3. separa CRASH (rebentou, tem traceback) de DADOS (extraiu mal),
  4. escreve um resumo priorizado em reportes/TRIAGEM.md.

Uso:
    python triagem_reportes.py                 # le reportes/recebidos/
    python triagem_reportes.py <pasta>         # le outra pasta
"""
from __future__ import annotations

import glob
import os
import re
import sys
import zipfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_DEFEITO = os.path.join(RAIZ, "reportes", "recebidos")


def _campo(diag: str, etiqueta: str) -> str:
    m = re.search(rf"^{re.escape(etiqueta)}\s*(.*)$", diag, re.MULTILINE)
    return (m.group(1).strip() if m else "").strip()


def _ler_zip(caminho: str) -> dict:
    """Le um ZIP de reporte e devolve um dicionario com o essencial."""
    info = {"zip": os.path.basename(caminho), "pasta": "", "descricao": "",
            "ficheiro": "", "tipo": "", "versao": "", "pc": "", "data": "",
            "crash": False, "erro_1a_linha": ""}
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        if "DESCRICAO_DA_FUNCIONARIA.txt" in nomes:
            info["descricao"] = z.read("DESCRICAO_DA_FUNCIONARIA.txt").decode("utf-8", "replace").strip()
        diag = ""
        if "DIAGNOSTICO.txt" in nomes:
            diag = z.read("DIAGNOSTICO.txt").decode("utf-8", "replace")
        info["data"] = _campo(diag, "Data/hora:")
        info["versao"] = _campo(diag, "Versao da app:")
        info["ficheiro"] = _campo(diag, "Ficheiro:")
        info["tipo"] = _campo(diag, "Tipo de ato:")
        info["pc"] = _campo(diag, "PC / utilizador:")
        if "ERRO TECNICO" in diag:
            info["crash"] = True
            # ultima linha nao vazia do traceback = a mensagem do erro
            cauda = diag.split("ERRO TECNICO", 1)[1].strip().splitlines()
            cauda = [l for l in cauda if l.strip() and not set(l.strip()) <= {"-"}]
            info["erro_1a_linha"] = cauda[-1].strip() if cauda else ""
        # extrair para subpasta (para inspecao manual)
        destino = os.path.join(os.path.dirname(caminho),
                               os.path.splitext(os.path.basename(caminho))[0])
        os.makedirs(destino, exist_ok=True)
        z.extractall(destino)
        info["pasta"] = os.path.relpath(destino, RAIZ).replace("\\", "/")
    return info


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else PASTA_DEFEITO
    zips = sorted(glob.glob(os.path.join(pasta, "*.zip")))
    if not zips:
        print(f"Nenhum ZIP em {pasta}")
        print("Descarrega os anexos dos emails de reporte para essa pasta e corre outra vez.")
        return

    itens = [_ler_zip(z) for z in zips]
    crashes = [i for i in itens if i["crash"]]
    dados = [i for i in itens if not i["crash"]]

    # contagem por tipo de ato
    por_tipo: dict[str, int] = {}
    for i in itens:
        por_tipo[i["tipo"] or "?"] = por_tipo.get(i["tipo"] or "?", 0) + 1

    linhas = [
        "# Triagem dos reportes",
        "",
        f"Total: **{len(itens)}**  |  Crashes (rebentou): **{len(crashes)}**  |  "
        f"Dados (extraiu mal): **{len(dados)}**",
        "",
        "Por tipo de ato: " + ", ".join(f"{k}={v}" for k, v in sorted(por_tipo.items())),
        "",
        "---",
        "",
        "## 1) CRASHES (prioridade — a app rebentou)",
        "",
    ]
    if not crashes:
        linhas.append("_(nenhum)_\n")
    for i in crashes:
        linhas += [
            f"### {i['zip']}",
            f"- **Tipo:** {i['tipo'] or '?'}  |  **Ficheiro:** {i['ficheiro'] or '?'}  |  "
            f"**Versao:** {i['versao']}  |  **PC:** {i['pc']}  |  {i['data']}",
            f"- **Erro:** `{i['erro_1a_linha']}`",
            f"- **Descricao:** {i['descricao'] or '(vazia)'}",
            f"- **Pasta:** `{i['pasta']}`",
            "",
        ]

    linhas += ["---", "", "## 2) DADOS (extraiu/preencheu mal)", ""]
    if not dados:
        linhas.append("_(nenhum)_\n")
    for i in dados:
        linhas += [
            f"### {i['zip']}",
            f"- **Tipo:** {i['tipo'] or '?'}  |  **Ficheiro:** {i['ficheiro'] or '?'}  |  "
            f"**Versao:** {i['versao']}  |  **PC:** {i['pc']}  |  {i['data']}",
            f"- **Descricao:** {i['descricao'] or '(vazia)'}",
            f"- **Pasta:** `{i['pasta']}`",
            "",
        ]

    saida = os.path.join(RAIZ, "reportes", "TRIAGEM.md")
    with open(saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print(f"OK: {len(itens)} reportes lidos ({len(crashes)} crashes, {len(dados)} dados).")
    print(f"Resumo escrito em: {os.path.relpath(saida, RAIZ)}")
    print(f"Escrituras/campos extraidos em subpastas de: {os.path.relpath(pasta, RAIZ)}")


if __name__ == "__main__":
    main()
