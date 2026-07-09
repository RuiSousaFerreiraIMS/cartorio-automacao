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
    dropdown_por_setas,
    escrever,
    escrever_dropdown,
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

    Ordem de campos (MAPEADA com calibrar_form.py no cartorio, 2026-07-08):
       0. Nº Contribuinte           (texto)   <- escrevemos
       1. Nome                      (texto)   <- escrevemos
       2. Estatuto Emigrante        (checkbox, saltar)
       3. Contabilidade Organizada  (checkbox, saltar)
       4. IVA de caixa              (checkbox, saltar)
       5. Naturalidade Concelho     (DROPDOWN, saltar - funcionaria)
       6. Naturalidade Freguesia    (DROPDOWN, saltar - funcionaria)
       7. Naturalidade Pais         (DROPDOWN, saltar - funcionaria)
       8. *** STOP FANTASMA ***     (controlo invisivel; o calibrador provou que
                                     existe - Nome=stop1 e Morada=stop9, logo ha
                                     1 stop a mais aqui. Basta saltar com Tab.)
       9. Morada Morada             (texto)   <- escrevemos
      10. Morada Localidade         (texto, saltar)
      11. Codigo Postal 1 (4 dig)   (texto, saltar)
      12. Codigo Postal 2 (3 dig)   (texto, saltar)
      13. Localidade do CP          (texto, saltar)
      14. Morada Concelho           (DROPDOWN, saltar - funcionaria)
      15. Morada Freguesia          (DROPDOWN, saltar - funcionaria)
      16. Morada Pais               (DROPDOWN, saltar - funcionaria)
      17. Estado Civil              (DROPDOWN por letra) <- selecionamos, PARAMOS aqui
      18. Regime                    (DROPDOWN, so casado - FUNCIONARIA)
   19-21. *** 3 STOPS FANTASMA ***  (provaveis botoes; so aparecem com casado)
      22. NIF Conjuge               (texto, so ativo se casado - FUNCIONARIA)
      23. Nome Conjuge              (texto, SIMN puxa da base)
    NOTA: stops 18-23 mapeados pelo calibrador com Estado Civil=Casado pre-def.
    O NIF Conjuge esta no stop 22 (nao 19); ha 3 stops escondidos entre o Regime
    e ele. Alem disso os campos so ativam ao CONFIRMAR o Estado Civil. Por isso
    o robo para no Estado Civil e a funcionaria completa Regime + NIF Conjuge.

    DOIS TIPOS DE DROPDOWN (metodo do notario, teclado):
      - de ESCRITA (Naturalidade Concelho/Freguesia): escrever_dropdown(valor)
        escreve as letras -> Tab confirma (fecha o popup, absorvido) -> Tab avanca.
      - de SELECAO / cinzentos (Estado Civil, Regime): dropdown_por_setas(n) preme
        Down n vezes ate a opcao -> Tab confirma -> Tab avanca. A letra unica NAO
        serve ('s' ia para Separado em vez de Solteiro).
    escrever() (Ctrl+V/paste) SO nos campos de TEXTO (NIF, Nome, Morada, NIF Conj):
    paste num combo nao seleciona e desalinha tudo.
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

    # 5. Naturalidade Concelho (dropdown de ESCRITA). Metodo do notario:
    # escrever -> Tab confirma (fecha o popup, e absorvido) -> Tab avanca.
    if o.get("naturalidade_concelho"):
        escrever_dropdown(o["naturalidade_concelho"])
        tab()  # confirma
    tab()      # avanca -> Freguesia
    # 6. Naturalidade Freguesia (dropdown de ESCRITA)
    if o.get("naturalidade_freguesia"):
        escrever_dropdown(o["naturalidade_freguesia"])
        tab()  # confirma
    tab()      # avanca -> Pais
    # 7. Naturalidade Pais (deixar Portugal): so avancar
    tab()      # -> stop fantasma
    # 8. STOP FANTASMA (controlo invisivel entre a Naturalidade e a Morada)
    tab()      # -> Morada

    # 9. Morada Morada (texto livre - seguro escrever)
    escrever(o.get("morada", ""))
    tab()

    # 10-13. Localidade / CP1 / CP2 / LocCP (texto, saltar - endereco vai todo na Morada)
    tab(4)

    # 14-16. Morada Concelho / Freguesia / Pais (dropdowns, saltar - funcionaria)
    tab(3)

    # 17. Estado Civil (dropdown de SELECAO / cinzento). Metodo do notario: Down
    # navega ate a opcao -> Tab confirma -> Tab avanca. Ordem no SIMN:
    #   0 Casado(a)  1 Divorciado(a)  2 Separado(a)  3 Solteiro Maior
    #   4 Solteiro Menor  5 Viuvo(a).   (n_baixo = indice + 1)
    ec_idx = {
        "casado": 0, "divorciado": 1, "separado": 2,
        "solteiro": 3,  # -> Solteiro Maior
        "viuvo": 5,
    }.get(str(o.get("estado_civil", "")).lower())
    if ec_idx is not None:
        dropdown_por_setas(ec_idx + 1)
        time.sleep(0.3)  # deixar ativar Regime/Conjuge quando casado
        tab()  # confirma
    tab()      # avanca -> Regime (se casado)

    # Regime + NIF Conjuge so quando casado (senao ficam cinzentos e nao sao stops).
    if o.get("estado_civil") == "casado":
        # 18. Regime (dropdown de SELECAO). Ordem: 0 comunhao de adquiridos,
        #     1 comunhao geral de bens, 2 separacao de bens.
        rb_idx = {
            "comunhao_de_adquiridos": 0,
            "comunhao_geral": 1,
            "separacao_de_bens": 2,
        }.get(str(o.get("regime_bens", "")).lower())
        if rb_idx is not None:
            dropdown_por_setas(rb_idx + 1)
            tab()  # confirma
        tab()      # avanca -> stop 19
        tab(3)     # 19-21 stops fantasma -> stop 22 (NIF Conjuge)
        # 22. NIF Conjuge (texto)
        if o.get("conjuge_de_nif"):
            escrever(o["conjuge_de_nif"])
        # 23. Nome Conj.: deixar vazio, o SIMN puxa da base pelo NIF

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
