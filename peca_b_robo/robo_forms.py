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
    tab_ctrl,
)


def _valor_simn(euros: Any) -> str:
    """Formata um valor em euros para os campos de MOEDA do SIMN.

    Descoberta na calibracao (2026-07-09): estes campos enchem da DIREITA como
    centimos. Escrever '18' da 0,18 EUR; '28000000' da 280.000,00 EUR. Por isso
    convertemos euros -> string de centimos inteiros.
    """
    if euros is None:
        return ""
    try:
        return str(int(round(float(euros) * 100)))
    except (TypeError, ValueError):
        return ""


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

    # 1. Nome (texto) - verificar autopreenchimento.
    # Se o SIMN reconhece o NIF, autopreenche Nome + Morada + Localidade a partir
    # da base, MAS deixa vazios campos obrigatorios (Naturalidade, Estado Civil,
    # Concelho/Freguesia da morada). Antes o robo parava aqui; agora CONTINUA e
    # preenche esses obrigatorios, saltando apenas os que o SIMN ja encheu (para
    # nao lutar com a base). O `reconhecido` liga/desliga esses saltos.
    nome_atual = ler_campo_atual()
    reconhecido = bool(nome_atual)
    if reconhecido:
        print(f"  -> Cliente reconhecido na base: {nome_atual!r}. Completo obrigatorios.")
    else:
        print("  -> Cliente novo, a preencher form completo.")
        escrever(o.get("nome", ""))
    tab()      # move para fora do Nome (escrevemos ou nao)

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

    # 9. Morada (rua + numero) - texto. Se reconhecido, o SIMN ja o encheu: saltar.
    if not reconhecido:
        escrever(o.get("morada", ""))
    tab()      # -> Localidade

    # 10. Localidade - texto. Idem: se reconhecido, ja vem da base.
    if not reconhecido:
        escrever(o.get("morada_localidade", ""))
    tab()      # -> Codigo Postal 1

    # 11-13. Codigo Postal (CP1 / CP2 / localidade do CP) - saltar
    tab(3)     # -> Morada Concelho

    # 14. Morada Concelho (dropdown de ESCRITA: escrever, Tab confirma, Tab avanca)
    if o.get("morada_concelho"):
        escrever_dropdown(o["morada_concelho"])
        tab()  # confirma
    tab()      # avanca -> Morada Freguesia
    # 15. Morada Freguesia (dropdown de ESCRITA)
    if o.get("morada_freguesia"):
        escrever_dropdown(o["morada_freguesia"])
        tab()  # confirma
    tab()      # avanca -> Morada Pais
    # 16. Morada Pais (deixar Portugal): so avancar
    tab()      # -> stop fantasma
    # 17. STOP FANTASMA (entre Morada Pais e Estado Civil; era o que exigia o Tab extra)
    tab()      # -> Estado Civil

    # 17. Estado Civil (dropdown de SELECAO / cinzento). Metodo do notario: Down
    # navega ate a opcao -> Tab confirma -> Tab avanca. Ordem no SIMN:
    #   0 Casado(a)  1 Divorciado(a)  2 Separado(a)  3 Solteiro Maior
    #   4 Solteiro Menor  5 Viuvo(a).
    # n_baixo = indice + 2: medido no teste (viuva=idx5 com 6 setas caiu no idx4;
    # casado=idx0 com 1 seta ficou em branco). A 1a seta so ABRE o dropdown, a 2a
    # e que cai no primeiro item. Logo indice = setas - 2, ou setas = indice + 2.
    ec_idx = {
        "casado": 0, "divorciado": 1, "separado": 2,
        "solteiro": 3,  # -> Solteiro Maior
        "viuvo": 5,
    }.get(str(o.get("estado_civil", "")).lower())
    if ec_idx is not None:
        dropdown_por_setas(ec_idx + 2)
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
            dropdown_por_setas(rb_idx + 2)  # +2 igual ao Estado Civil (1a seta so abre)
            tab()  # confirma
        tab()      # avanca -> NIF Conjuge (logo a seguir ao Regime; NAO ha stops
                   # fantasma aqui - o calibrador enganou-se, a observacao do notario
                   # manda: Regime -> Tab confirma -> Tab -> NIF Conjuge).
        # NIF Conjuge (texto)
        if o.get("conjuge_de_nif"):
            escrever(o["conjuge_de_nif"])
        # 23. Nome Conj.: deixar vazio, o SIMN puxa da base pelo NIF

    return "reconhecido" if reconhecido else "preenchido"


# -----------------------------------------------------------------------------
# Form do OUTORGANTE COLECTIVO (empresa)
# -----------------------------------------------------------------------------
def preencher_empresa(o: dict[str, Any]) -> str:
    """Preenche o form 'Dados Empresa' (Outorgante Colectivo).

    Regra do Rui (2026-07-09): ~90% das empresas JA estao na base do SIMN, por
    isso basta escrever o NIPC no 1o campo e o SIMN autopreenche o resto (Nome,
    Sede, etc). Para os ~10% que nao estao, a funcionaria completa a mao (o form
    Colectivo completo ainda nao esta calibrado; se um dia for preciso, mapeia-se
    com calibrar_form.py como se fez ao Bem).

    Pre-condicao: cursor no 1o campo (NIPC) do form 'Dados Empresa'.
    """
    print(f"  A preencher empresa: {o.get('nome', '?')} (NIPC {o.get('nif', '?')})")

    # NIPC (texto) - mesmo mecanismo do outorgante singular reconhecido.
    escrever(o.get("nif", ""))
    tab()
    time.sleep(0.6)  # SIMN consulta a base pelo NIPC

    nome_atual = ler_campo_atual()
    if nome_atual:
        print(f"  -> Empresa reconhecida na base: {nome_atual!r}")
        return "reconhecido"
    print("  -> Empresa nao esta na base. A funcionaria completa o resto a mao.")
    return "preenchido"


# -----------------------------------------------------------------------------
# Form do BEM
# -----------------------------------------------------------------------------
def preencher_bem(b: dict[str, Any]) -> str:
    """Preenche o form do bem imovel.

    Ordem MAPEADA com calibrar_form.py no cartorio (2026-07-09, 2 corridas: uma
    do topo ate ficar presa no textarea Moradas; outra a comecar no Artigo).

    TOPO (Localizacao Fiscal):
       Concelho   (DROPDOWN de escrita)  <- escrevemos
       Freguesia  (DROPDOWN de escrita)  <- escrevemos
       Moradas    (TEXTAREA)             <- escrevemos, saimos com Ctrl+Tab
       Urbano/Rustico (RADIO)            <- seleccionamos
    A partir do Artigo, indices da corrida B (cursor no Artigo = 00):
       00 Artigo                 (texto)  <- escrevemos
       01 Fraccao autonoma       (texto)  <- escrevemos (letra da fraccao)
       02 Seccao                 (texto)  saltar
       03 Arvore/Colonia         (texto)  saltar
       04 Data registo inscricao (data)   saltar
       05 Afectacao              (texto)  saltar - funcionaria
       06 Tipo Regime            (texto)  saltar - funcionaria
       07 Tipo Direito           (DROPDOWN) saltar - funcionaria
       08 Ident. Conservatoria   (DROPDOWN) saltar - funcionaria
       09-10 *** STOPS FANTASMA ***       saltar
       11 Data registo provisorio (data)  saltar
       12 Nº Registo             (texto)  <- escrevemos (descricao predial; regra
                                           do notario: omisso => deixar vazio)
       13 Nº hipotecas anteriores (texto) saltar
       14 Núm. apresentacao p.h. (texto)  saltar
       15 Data apresentacao p.h. (data)   saltar
       16 Situacao Fiscal        (DROPDOWN, default "200 - Sujeito a IMT") saltar
       17 *** STOP FANTASMA ***           saltar
       18 Preco da venda         (MOEDA)  <- escrevemos (do preco da CV, se vier
                                           em b['preco_venda']; mask de centimos)

    Metodo dos campos, igual ao outorgante:
      - DROPDOWN de escrita (Concelho/Freguesia): escrever_dropdown -> Tab confirma
        (absorvido) -> Tab avanca.
      - TEXTAREA (Moradas): escrever -> Ctrl+Tab para SAIR (o Tab normal fica preso).
      - RADIO (Urbano/Rustico): radio_selecionar(0=Urbano, 1=Rustico).
      - Campos de texto/moeda: escrever + Tab.
      - Dropdowns cinzentos (Tipo Direito, Ident. Conservatoria, Situacao): NAO
        tocar, so passar com Tab (funcionaria trata). Como nao os abrimos, cada um
        conta 1 so stop, por isso as contagens do mapa mantem-se.

    A CONFIRMAR no teste: (1) apos o Ctrl+Tab do Moradas o foco cai no radio e 1
    Tab chega ao Artigo (pode haver stop a mais); (2) a seta/Space do radio.
    """
    print(f"  A preencher bem: {b.get('descricao_predial') or b.get('freguesia') or '?'}")

    # --- TOPO ---
    # Concelho (dropdown de escrita)
    if b.get("concelho"):
        escrever_dropdown(b["concelho"])
        tab()  # confirma
    tab()      # avanca -> Freguesia
    # Freguesia (dropdown de escrita)
    if b.get("freguesia"):
        escrever_dropdown(b["freguesia"])
        tab()  # confirma
    tab()      # avanca -> Moradas

    # Moradas (textarea): escrever e SAIR com Ctrl+Tab (o Tab normal fica preso la).
    escrever(b.get("morada", ""))
    tab_ctrl()  # -> Urbano (1o dos DOIS radio-stops)

    # Urbano/Rustico sao DOIS tab-stops SEPARADOS (nao um grupo de setas).
    # Teste 2026-07-09: o Space seleccionou o Urbano mas havia 1 stop a mais (o
    # Rustico) antes do Artigo, que empurrava tudo 1 campo (o "D" da fraccao caiu
    # no Artigo). Correccao: passar SEMPRE os dois radio-stops, com Space no certo.
    if b.get("tipo") == "R":
        tab()                       # Urbano -> Rustico
        pyautogui.press("space")    # selecciona Rustico
        tab()                       # Rustico -> Artigo
    else:
        pyautogui.press("space")    # selecciona Urbano (default)
        tab(2)                      # Urbano -> Rustico -> Artigo

    # 00 Artigo (texto). Regra do notario: so o numero, sem sufixo (ja normalizado).
    escrever(b.get("artigo_matricial", ""))
    tab()       # -> 01 Fraccao autonoma
    # 01 Fraccao autonoma (letra da fraccao, ex "P")
    escrever(b.get("designacao_fracao", ""))
    tab()       # -> 02 Seccao

    # 02..11: Seccao, Arvore, Data inscricao, Afectacao, Tipo Regime, Tipo Direito,
    # Ident. Conservatoria, 2 fantasmas, Data provisorio -> saltar ate ao Nº Registo.
    tab(10)     # 02 -> 12 (Nº Registo)

    # 12 Nº Registo (descricao predial). Regra do notario: omisso => campo vazio.
    desc = (b.get("descricao_predial") or "").strip()
    if desc and "omisso" not in desc.lower():
        escrever(desc)

    # 12 -> 18: Nº hipotecas, Núm. apresentacao, Data apresentacao, Situacao,
    # fantasma -> saltar ate ao Preco da venda.
    tab(6)      # 12 -> 18 (Preco da venda)

    # 18 Preco da venda (moeda, mask de centimos). Vem do preco da CV (injectado
    # pelo fluxo em b['preco_venda']), nao do proprio bem.
    if b.get("preco_venda") is not None:
        escrever(_valor_simn(b["preco_venda"]))

    return "preenchido"


# -----------------------------------------------------------------------------
# Form do DUC
# -----------------------------------------------------------------------------
def preencher_duc(duc: dict[str, Any]) -> str:
    """Preenche o form pequeno de DUC.

    Ordem MAPEADA (2026-07-09): 4 campos de texto consecutivos, 1 Tab entre cada,
    sem dropdowns nem stops fantasma (todos aceitaram os marcadores numericos):
       0. Numero      (texto)  <- escrevemos (o que temos hoje, e o essencial)
       1. Facto IMT   (texto)  saltar - funcionaria
       2. Montante    (MOEDA)  <- so se vier no JSON (mask de centimos). O notario
                                 vai passar a incluir o valor; ate la vem null.
       3. Data        (data)   saltar - nao obrigatorio (Rui confirmou)

    O cursor comeca no Numero. Paramos assim que der: nao ha vantagem em Tab-ar
    ate ao fim.
    """
    print(f"  A preencher DUC: {duc.get('tipo', '?')} nº {duc.get('numero', '?')}")

    # 0. Numero (texto)
    escrever(duc.get("numero", ""))
    tab()       # -> Facto IMT

    # 1. Facto IMT: saltar (funcionaria)
    tab()       # -> Montante

    # 2. Montante (moeda). So preencher se a escritura ja trouxe o valor.
    if duc.get("montante") is not None:
        escrever(_valor_simn(duc["montante"]))
    # 3. Data: nao obrigatorio, deixar para a funcionaria.
    return "preenchido"


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
