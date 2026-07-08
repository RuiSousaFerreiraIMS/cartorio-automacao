"""
Corre o extrator em todos os ficheiros da pasta exemplos/ e grava os JSONs
em peca_a_extracao/saidas/. Util para regenerar o lote completo numa so corrida.

Uso:
    python extrair_tudo.py        # processa todos os ficheiros em exemplos/
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, "peca_a_extracao")
import extrator  # noqa: E402
from extrator import extrair_de_ficheiro, detetar_tipo  # noqa: E402

PASTA_ENTRADA = "exemplos"
PASTA_SAIDA = "peca_a_extracao/saidas"

# Ficheiros a ignorar (nao sao escrituras)
IGNORAR = {"tipos de ato.docx"}


def slug(nome: str) -> str:
    """Transforma 'CV Mútuo Hip urbano.doc' em 'cv_mutuo_hip_urbano'."""
    base = os.path.splitext(nome)[0].lower()
    base = (
        base.replace("á", "a").replace("ã", "a").replace("â", "a").replace("à", "a")
            .replace("é", "e").replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o").replace("ô", "o").replace("õ", "o")
            .replace("ú", "u")
            .replace("ç", "c")
    )
    return "".join(c if c.isalnum() else "_" for c in base).strip("_")


def _eh_erro_temporario(msg: str) -> bool:
    """503 (UNAVAILABLE), 429 (rate limit) e timeouts contam como temporarios."""
    msg_low = msg.lower()
    return any(t in msg_low for t in ("503", "unavailable", "429", "rate", "timeout", "deadline"))


def main() -> None:
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    ficheiros = sorted(
        f for f in os.listdir(PASTA_ENTRADA)
        if f.lower().endswith((".doc", ".docx")) and f.lower() not in IGNORAR
    )
    print(f"Encontrados {len(ficheiros)} ficheiros para processar.\n")

    sucessos: list[tuple[str, str, str]] = []
    saltados: list[str] = []
    falhas: list[tuple[str, str]] = []

    for i, nome in enumerate(ficheiros, 1):
        caminho_in = os.path.join(PASTA_ENTRADA, nome)
        tipo = detetar_tipo(caminho_in)
        caminho_out = os.path.join(PASTA_SAIDA, f"{tipo}__{slug(nome)}.json")

        print(f"[{i}/{len(ficheiros)}] {nome}")

        # Idempotencia: salta o que ja foi extraido com sucesso.
        if os.path.exists(caminho_out) and os.path.getsize(caminho_out) > 100:
            print(f"  ja existe em {caminho_out}, a saltar.")
            saltados.append(nome)
            sucessos.append((nome, tipo, caminho_out))
            continue

        # Tentativa com retry exponencial para erros temporarios (503/429)
        max_tentativas = 4
        for tentativa in range(1, max_tentativas + 1):
            t0 = time.time()
            try:
                resultado = extrair_de_ficheiro(caminho_in)
                with open(caminho_out, "w", encoding="utf-8") as f:
                    f.write(resultado.model_dump_json(indent=2))
                sucessos.append((nome, tipo, caminho_out))
                print(f"  OK em {time.time()-t0:.1f}s ({len(resultado.avisos)} aviso(s))")
                # pequena pausa entre sucessos para nao stressar a API
                time.sleep(2)
                break
            except Exception as e:
                erro = str(e).strip().split("\n")[0][:200]
                if _eh_erro_temporario(erro) and tentativa < max_tentativas:
                    espera = 30 * (2 ** (tentativa - 1))  # 30s, 60s, 120s
                    print(f"  erro temporario ({erro[:80]}...), a esperar {espera}s antes de tentar de novo ({tentativa}/{max_tentativas-1})")
                    time.sleep(espera)
                    continue
                falhas.append((nome, erro))
                print(f"  FALHOU definitivamente: {erro[:120]}")
                # Para erros de validacao do schema, guardar raw + erro completo
                # para podermos arranjar o schema/prompt.
                if "validation error" in str(e).lower() and extrator.ultimo_raw is not None:
                    base = os.path.join(PASTA_SAIDA, f"_DEBUG__{tipo}__{slug(nome)}")
                    with open(base + "_raw.json", "w", encoding="utf-8") as f:
                        json.dump(extrator.ultimo_raw, f, indent=2, ensure_ascii=False)
                    with open(base + "_erro.txt", "w", encoding="utf-8") as f:
                        f.write(f"Ficheiro: {nome}\nTipo: {tipo}\n\nErro completo:\n{e}\n")
                    print(f"  debug: guardado raw + erro em {base}_*.txt/json")
                break

    print(f"\n=== Resumo: {len(sucessos)} OK ({len(saltados)} ja existiam), {len(falhas)} falhas ===")
    for nome, tipo, caminho in sucessos:
        marca = "  " if nome not in saltados else "skip"
        print(f"  [{tipo:>11}] {marca}  {nome}")
    if falhas:
        print("\nFalhas (re-corre o script para tentar de novo, vai saltar os que ja existem):")
        for nome, erro in falhas:
            print(f"  {nome}: {erro[:150]}")


if __name__ == "__main__":
    main()
