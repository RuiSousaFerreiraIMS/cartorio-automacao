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

    Ordem de campos (validada no video 150041 do cartorio):
       0. Nº Contribuinte           (texto)   <- escrevemos
       1. Nome                      (texto)   <- escrevemos
       2. Estatuto Emigrante        (checkbox, saltar)
       3. Contabilidade Organizada  (checkbox, saltar)
       4. IVA de caixa              (checkbox, saltar)
       5. Naturalidade Concelho     (DROPDOWN, saltar - funcionaria)
       6. Naturalidade Freguesia    (DROPDOWN, saltar - funcionaria)
       7. Naturalidade Pais         (DROPDOWN, saltar - funcionaria)
       8. Morada Morada             (texto)   <- escrevemos
       9. Morada Localidade         (texto, saltar)
      10. Codigo Postal 1 (4 dig)   (texto, saltar)
      11. Codigo Postal 2 (3 dig)   (texto, saltar)
      12. Localidade do CP          (texto, saltar)
      13. Morada Concelho           (DROPDOWN, saltar - funcionaria)
      14. Morada Freguesia          (DROPDOWN, saltar - funcionaria)
      15. Morada Pais               (DROPDOWN, saltar - funcionaria)
      16. Estado Civil              (DROPDOWN por letra) <- selecionamos
      17. Regime                    (DROPDOWN por letra, so casado)
      18. NIF Conjuge               (texto)   <- escrevemos
      19. Nome Conjuge              (texto, SIMN puxa da base)

    REGRA DE OURO (aprendida no video 150041): NUNCA escrever com escrever()
    num DROPDOWN. Despejar uma string longa num combo Java Swing dispara o
    autocomplete (escolhe item errado) E abre o popup, que engole os Tabs
    seguintes e desalinha TODO o form a jusante. Foi o que aconteceu:
    "Aljubarrota (Prazeres)" foi para Naturalidade Concelho, o popup abriu, e a
    Morada acabou despejada no dropdown Morada Concelho. Por isso so escrevemos
    em campos de TEXTO; os dropdowns de Concelho/Freguesia/Pais ficam para a
    funcionaria. Os unicos dropdowns que tocamos (Estado Civil / Regime) sao de
    letra unica e ficam no fim, onde nao ha nada a seguir para desalinhar.
    """
    print(f"  A preencher outorgante: {o.get('nome', '?')} (NIF {o.get('nif', '?')})")

    # 0. NIF (texto)
    escrever(o.get("nif", ""))
    tab()
    time.sleep(0.6)  # SIMN pode consultar base

    # 1. Nome (texto) - verificar autopreenchimento
    nome_atual = ler_campo_atual()
    if nome_atual:
        print(f"  -> Cliente reconhecido na base: {nome_atual!r}")
        return "reconhecido"

    print("  -> Cliente novo, a preencher form completo.")
    escrever(o.get("nome", ""))
    tab()

    # 2-4. Checkboxes (Estatuto Emigrante / Contab / IVA) - saltar
    tab(3)

    # 5-7. Naturalidade Concelho / Freguesia / Pais - TODOS dropdowns.
    # NAO escrever: abriria o popup e desalinharia tudo (bug do video 150041).
    # A funcionaria preenche a naturalidade a mao. 3 Tabs limpos.
    print("  -> Naturalidade deixada em branco (dropdowns; funcionaria completa).")
    tab(3)

    # 8. Morada Morada (texto livre - seguro escrever)
    escrever(o.get("morada", ""))
    tab()

    # 9-12. Localidade / CP1 / CP2 / LocCP (texto, saltar - endereco vai todo na Morada)
    tab(4)

    # 13-15. Morada Concelho / Freguesia / Pais (dropdowns, saltar - funcionaria)
    tab(3)

    # 16. Estado Civil (dropdown de letra unica - so 1 opcao por letra, seguro)
    ec_letra = {
        "solteiro": "s", "casado": "c", "divorciado": "d",
        "viuvo": "v", "uniao_de_facto": "u",
    }.get(str(o.get("estado_civil", "")).lower(), "")
    if ec_letra:
        dropdown_por_letra(ec_letra)
    tab()

    # 17. Regime de Bens (so se casado)
    if o.get("estado_civil") == "casado":
        rb_letra = {
            "comunhao_de_adquiridos": "c",
            "comunhao_geral": "c",  # pode precisar de 2x
            "separacao_de_bens": "s",
        }.get(str(o.get("regime_bens", "")).lower(), "")
        if rb_letra:
            dropdown_por_letra(rb_letra)
    tab()

    # 18. NIF Conjuge (texto)
    if o.get("conjuge_de_nif"):
        escrever(o["conjuge_de_nif"])
    tab()

    # 19. Nome Conj. - deixar em branco, SIMN puxa da base pelo NIF
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
