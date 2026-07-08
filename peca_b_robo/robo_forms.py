"""
Peca B - Preenchedores de forms individuais do SIMN.

Cada funçao aqui aceita um dict com os dados de UM item (outorgante, bem, DUC)
e preenche o form respectivo campo-a-campo. Nao clica em botoes de abrir/OK -
isso e' responsabilidade dos fluxos (robo_fluxos.py).

Pre-condiçao para cada funçao: o cursor tem de estar no PRIMEIRO campo do form.
Pos-condiçao: o cursor esta a seguir ao ultimo campo. Ainda nao clicou OK.
"""

from __future__ import annotations

import time
from typing import Any

import pyautogui

from robo_actions import (
    dropdown_por_letra,
    escrever,
    ler_campo_atual,
    tab,
)


# -----------------------------------------------------------------------------
# Form do OUTORGANTE (Vendedor, Comprador, Doador, Donatario, Herdeiro, etc)
# -----------------------------------------------------------------------------
def preencher_outorgante(o: dict[str, Any]) -> str:
    """Preenche o form pessoal de um outorgante.

    Devolve:
      - "reconhecido" se SIMN autopreencheu (cliente ja na base)
      - "preenchido" se preencheu tudo do JSON

    Ordem de campos (validada nos videos do cartorio):
       1. Nº Contribuinte
       2. Nome
       3. Estatuto Emigrante (checkbox, saltamos)
       4. Contabilidade Organizada (checkbox, saltamos)
       5. IVA de caixa (checkbox, saltamos)
       6. Naturalidade Concelho (dropdown)
       7. Naturalidade Freguesia
       8. Naturalidade Pais (dropdown, default Portugal)
       9. Morada Morada
      10. Morada Localidade
      11. Morada Codigo Postal 1 (4 digitos)
      12. Morada Codigo Postal 2 (3 digitos)
      13. Morada Localidade do CP
      14. Morada Concelho (dropdown)
      15. Morada Freguesia
      16. Morada Pais (dropdown, default Portugal)
      17. Estado Civil (dropdown)
      18. Regime (dropdown, so se casado)
      19. NIF Conjuge
      20. Nome Conjuge
    """
    print(f"  A preencher outorgante: {o.get('nome', '?')} (NIF {o.get('nif', '?')})")
    nacionalidade = (o.get("nacionalidade") or "").lower()
    e_estrangeiro = bool(nacionalidade) and "portug" not in nacionalidade

    # 1. NIF
    escrever(o.get("nif", ""))
    tab()
    time.sleep(0.6)  # SIMN pode consultar base

    # 2. Nome - verificar autopreenchimento
    nome_atual = ler_campo_atual()
    if nome_atual:
        print(f"  -> Cliente reconhecido na base: {nome_atual!r}")
        return "reconhecido"

    print("  -> Cliente novo, a preencher form completo.")
    escrever(o.get("nome", ""))
    tab()

    # 3-5. Checkboxes: Estatuto Emigrante / Contab / IVA (saltar)
    tab(3)

    # 6. Naturalidade Concelho
    if e_estrangeiro:
        tab()  # saltar - naturalidade vai no campo Pais
    else:
        naturalidade = o.get("naturalidade") or ""
        if naturalidade:
            escrever(naturalidade)
        tab()

    # 7. Naturalidade Freguesia (deixar vazio, funcionaria completa)
    tab()

    # 8. Naturalidade Pais
    if e_estrangeiro:
        pais = o.get("naturalidade") or o.get("nacionalidade") or ""
        escrever(pais)
    tab()

    # 9. Morada Morada
    escrever(o.get("morada", ""))
    tab()

    # 10-13. Localidade / CP1 / CP2 / LocCP (saltar - vem no campo Morada)
    tab(4)

    # 14-16. Morada Concelho / Freguesia / Pais (deixar defaults)
    tab(3)

    # 17. Estado Civil
    ec_letra = {
        "solteiro": "s", "casado": "c", "divorciado": "d",
        "viuvo": "v", "uniao_de_facto": "u",
    }.get(str(o.get("estado_civil", "")).lower(), "")
    if ec_letra:
        dropdown_por_letra(ec_letra)
    tab()

    # 18. Regime de Bens (so se casado)
    if o.get("estado_civil") == "casado":
        rb_letra = {
            "comunhao_de_adquiridos": "c",
            "comunhao_geral": "c",  # pode precisar de 2x
            "separacao_de_bens": "s",
        }.get(str(o.get("regime_bens", "")).lower(), "")
        if rb_letra:
            dropdown_por_letra(rb_letra)
    tab()

    # 19. NIF Conjuge
    if o.get("conjuge_de_nif"):
        escrever(o["conjuge_de_nif"])
    tab()

    # 20. Nome Conj. - deixar em branco, SIMN puxa da base pelo NIF
    return "preenchido"


# -----------------------------------------------------------------------------
# Form do BEM
# -----------------------------------------------------------------------------
def preencher_bem(b: dict[str, Any]) -> str:
    """Preenche o form do bem imovel.

    ORDEM DE CAMPOS AINDA POR MAPEAR — vai ser preenchida quando o Rui trouxer
    screenshots + notas do bloco 3 da CHECKLIST_CARTORIO.md.

    Estrutura esperada (do screenshot 110826):
       - Localizaçao Fiscal: Concelho (dropdown), Freguesia, Moradas
       - Identificaçao Matricial: Urbano/Rustico (radio), Artigo, Secçao,
         Arvore/Colonia, Fracçao autonoma, Data do registo de inscriçao
       - Descricao: Afectaçao, Tipo Regime, Tipo Direito
       - Conservatoria: Ident., Nº Registo, Nº hipotecas ant., Datas
       - Situaçao Fiscal: Situaçao (default "200 - Sujeito a IMT")
       - Importancias: Preço da venda / Valor bens Imoveis
    """
    print(f"  A preencher bem: {b.get('descricao_predial') or b.get('freguesia') or '?'}")
    print("  ⚠️  PREENCHIMENTO DO BEM ainda por mapear. Vai preencher parcialmente.")

    # Placeholder: preencher so o que sabemos com certeza do video
    # (Concelho -> Freguesia -> Moradas -> Rustico/Urbano -> Artigo)

    # 1. Concelho (dropdown)
    concelho = b.get("concelho") or ""
    if concelho:
        escrever(concelho)
    tab()
    # 2. Freguesia
    freguesia = b.get("freguesia") or ""
    if freguesia:
        escrever(freguesia)
    tab()
    # 3. Moradas (textarea)
    escrever(b.get("morada", ""))
    tab()

    # 4. Urbano/Rustico (radio) - ainda sem forma clara de escolher
    # Nota: radios em Java Swing costumam responder a Space quando focados
    if b.get("tipo") == "R":
        pyautogui.press("space")  # assume Rustico e' o segundo
    # else: Urbano por defeito (assumido)

    # ... continua quando tivermos os screenshots
    return "parcial"


# -----------------------------------------------------------------------------
# Form do DUC
# -----------------------------------------------------------------------------
def preencher_duc(duc: dict[str, Any]) -> str:
    """Preenche o form pequeno de DUC.

    AINDA POR MAPEAR — bloco 4 da checklist. Estrutura provavel: Numero, Tipo,
    Montante (opcional).
    """
    print(f"  A preencher DUC: {duc.get('tipo', '?')} {duc.get('numero', '?')}")
    print("  ⚠️  FORM DE DUC ainda por mapear.")

    escrever(duc.get("numero", ""))
    tab()
    if duc.get("tipo"):
        escrever(duc["tipo"])
    tab()
    if duc.get("montante"):
        escrever(str(duc["montante"]))
    return "parcial"


# -----------------------------------------------------------------------------
# Form da RELAÇAO
# -----------------------------------------------------------------------------
def preencher_relacao(vendedor_nif: str, bem_id: str, comprador_nif: str,
                      quota_v: str = "1/1", quota_c: str = "1/1") -> str:
    """Cria uma relaçao entre um vendedor, um bem e um comprador.

    AINDA POR MAPEAR — bloco 5 da checklist. Estrutura provavel: 3 dropdowns
    (vendedor, bem, comprador) + quota-parte em cada lado.
    """
    print(f"  A criar relaçao: V:{vendedor_nif} -> B:{bem_id} -> C:{comprador_nif}")
    print("  ⚠️  FORM DE RELAÇAO ainda por mapear.")
    return "parcial"
