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


def _data_simn(iso: Any) -> str:
    """Converte uma data para os campos de DATA do SIMN (mask AAAA/MM/DD).

    Devolve so os 8 digitos na ordem 'AAAAMMDD' (escrever isso enche o campo
    __/__/__). Testado no cartorio (2026-07-10): tanto a Data de Obito da
    habilitacao como a Data do registo de inscricao do bem usam esta ordem;
    escrever DDMMAAAA punha, p.ex., 25/04/2026 como '2504/20/26'.
    Aceita 'AAAA-MM-DD' (o formato do schema) ou 'DD/MM/AAAA'/'DD-MM-AAAA'.
    """
    import re
    if not iso:
        return ""
    s = str(iso).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        ano, mes, dia = m.groups()
        return f"{ano}{mes}{dia}"
    m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})$", s)  # DD/MM/AAAA
    if m:
        dia, mes, ano = m.groups()
        return f"{ano}{mes}{dia}"
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

    # ESTRANGEIRO (Rui, 2026-07-10): quando o Pais e' estrangeiro, o SIMN desativa
    # os campos Concelho e Freguesia (naturalidade E morada) - deixam de ser
    # paragens de Tab. O robo tem entao 2 Tabs A MENOS em cada bloco; se os contar
    # como num portugues, aterra cedo demais e as setas do Estado Civil caem no
    # dropdown do Pais (ficava "Quenia"). Deteta-se pela `nacionalidade` estar
    # preenchida (regra do notario: nacionalidade so se poe a estrangeiros).
    estrangeiro = bool(o.get("nacionalidade"))
    if estrangeiro:
        print(f"  -> Estrangeiro (nacionalidade={o.get('nacionalidade')!r}): "
              "salta Concelho/Freguesia (naturalidade e morada).")

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

    # Form "Autor da heranca" (habilitacao, calibrado 2026-07-10): tem 2 campos a
    # mais LOGO A SEGUIR AO NOME - Data de Obito (2) e Assento de Obito (3). So o
    # robo.py, no falecido, marca `_autor_heranca` e injecta data_obito/assento.
    if o.get("_autor_heranca"):
        escrever(_data_simn(o.get("data_obito")))  # 2. Data de Obito (mask AAAA/MM/DD)
        tab()
        escrever(o.get("assento_obito") or "")     # 3. Assento de Obito (texto)
        tab()

    # 2-4 (ou 4-6 no autor da heranca). Checkboxes - saltar
    tab(3)

    # 5. Naturalidade Concelho (dropdown de ESCRITA). Metodo do notario:
    # escrever -> Tab confirma (fecha o popup, e absorvido) -> Tab avanca.
    # Estrangeiro NAO tem concelho portugues: fica VAZIO, mas o campo continua a
    # ser paragem de Tab (os Tabs sao os MESMOS que num portugues).
    if o.get("naturalidade_concelho"):
        escrever_dropdown(o["naturalidade_concelho"])
        tab()  # confirma
    tab()      # avanca -> Freguesia
    # 6. Naturalidade Freguesia (dropdown de ESCRITA). Idem: vazia no estrangeiro.
    if o.get("naturalidade_freguesia"):
        escrever_dropdown(o["naturalidade_freguesia"])
        tab()  # confirma
    tab()      # avanca -> Pais
    # 7. Naturalidade Pais. Portugues: deixar (Portugal), so avancar. ESTRANGEIRO:
    # escrever o pais (a naturalidade dele E o pais, ex "Estados Unidos da America").
    # Igual aos outros dropdowns de escrita: escrever -> Tab confirma (absorvido).
    if estrangeiro and o.get("naturalidade"):
        escrever_dropdown(o["naturalidade"])
        tab()  # confirma
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

    # 14. Morada Concelho (dropdown de ESCRITA: escrever, Tab confirma, Tab avanca).
    # Estrangeiro fica VAZIO (mora fora), mas o campo continua a ser paragem de Tab.
    if o.get("morada_concelho"):
        escrever_dropdown(o["morada_concelho"])
        tab()  # confirma
    tab()      # avanca -> Morada Freguesia
    # 15. Morada Freguesia (dropdown de ESCRITA). Idem: vazia no estrangeiro.
    if o.get("morada_freguesia"):
        escrever_dropdown(o["morada_freguesia"])
        tab()  # confirma
    tab()      # avanca -> Morada Pais
    # O form "Autor da heranca" tem 1 stop A MAIS aqui (teste 2026-07-10, Rui): sem
    # este Tab, o robo chegava ao Estado Civil um campo cedo demais e as setas do
    # Estado Civil caiam no dropdown do Pais (ficava "Quenia"). So neste form.
    if o.get("_autor_heranca"):
        tab()
    # 16. Morada Pais. Portugues: deixar (Portugal). ESTRANGEIRO: escrever o pais
    # de residencia. Usamos o mesmo pais da naturalidade (no estrangeiro coincidem
    # quase sempre; a funcionaria corrige o caso raro em que difere).
    if estrangeiro and o.get("naturalidade"):
        escrever_dropdown(o["naturalidade"])
        tab()  # confirma
    tab()      # -> stop fantasma
    # 17. STOP FANTASMA (entre Morada Pais e Estado Civil)
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
# CALIBRADO 2026-07-09 (calibrar_form.py --campos 20). Marcadores visiveis:
#   00 NIPC | 01 Capital Social | 02 Tipo(dropdown) | 03 fantasma | 04 Nome |
#   05-08 radios(Publica/Privada/Central/Regional) + checkboxes(Contab/IVA) |
#   09 Sede Morada | 10 Localidade | 11 CP1(4dig) | 12 CP2(3dig) | 13 CP localidade |
#   14 Concelho(dropdown) | 15 Freguesia(dropdown) | 16 Pais | 18 Ident.Conservatoria.
# A CONFIRMAR no teste: os indices 14/15 (Concelho/Freguesia) sao inferidos pela
# posicao (marcadores em branco por serem dropdowns), como no Bem.
_EMPRESA_FORM_CALIBRADO = True


def preencher_empresa(o: dict[str, Any]) -> str:
    """Preenche o form 'Dados Empresa' (Outorgante Colectivo).

    Regra do Rui (2026-07-09): ~90% das empresas JA estao na base do SIMN, por
    isso basta o NIPC e o SIMN autopreenche. Deteta isso lendo o Nome (como no
    singular): se ja veio preenchido, para (reconhecida). Se nao (empresa NOVA),
    preenche Capital, Nome e Sede. O Tipo fica no default 'Soc. por quotas' e a
    Ident. Conservatoria fica para a funcionaria (dropdowns de selecao cuja ordem
    nao esta mapeada; sao raros e a funcionaria ajusta).

    Pre-condicao: cursor no 1o campo (NIPC) do form 'Dados Empresa'.
    """
    print(f"  A preencher empresa: {o.get('nome', '?')} (NIPC {o.get('nif', '?')})")

    # 00. NIPC (texto). O Tab dispara a consulta a base.
    escrever(o.get("nif", ""))
    tab()                        # 00 -> 01 Capital Social
    time.sleep(0.6)              # SIMN consulta a base pelo NIPC

    # 01. Capital Social (moeda, mask de centimos). Preencher ja: e' util tanto na
    # empresa nova como na reconhecida sem capital na base.
    if o.get("capital_social") is not None:
        escrever(_valor_simn(o["capital_social"]))
    tab(3)                       # 01 -> 04 Nome (passa Tipo(02, default) + fantasma(03))

    # 04. Nome: deteccao de reconhecimento (igual ao singular). Se o SIMN ja
    # preencheu, a empresa esta na base -> parar (Sede autopreenchida pela base).
    if ler_campo_atual():
        print("  -> Empresa reconhecida na base. Nada mais a preencher.")
        return "reconhecido"

    print("  -> Empresa nova (nao esta na base). A preencher Nome + Sede.")
    escrever(o.get("nome", ""))  # Nome / denominacao social
    tab(5)                       # 04 -> 09 Sede Morada (passa radios 05-08)

    # 09. Sede Morada (texto)
    escrever(o.get("morada", ""))
    tab()                        # 09 -> 10 Localidade
    # 10. Localidade (texto)
    escrever(o.get("morada_localidade", ""))
    tab()                        # 10 -> 11 Codigo Postal (1a caixa)

    # 11-12. Codigo Postal em 2 caixas (NNNN e NNN). 13 = localidade do CP (saltar).
    cp = (o.get("codigo_postal") or "").strip()
    cp1, cp2 = (cp.split("-", 1) + [""])[:2] if "-" in cp else (cp, "")
    escrever(cp1.strip())
    tab()                        # 11 -> 12 CP2
    escrever(cp2.strip())
    tab()                        # 12 -> 13 (localidade do CP)
    tab()                        # 13 -> 14 Concelho

    # 14. Concelho (dropdown de ESCRITA: escrever, Tab confirma, Tab avanca)
    if o.get("morada_concelho"):
        escrever_dropdown(o["morada_concelho"])
        tab()                    # confirma
    tab()                        # 14 -> 15 Freguesia
    # 15. Freguesia (dropdown de ESCRITA)
    if o.get("morada_freguesia"):
        escrever_dropdown(o["morada_freguesia"])
        tab()                    # confirma
    # Pais (Portugal) e Ident. Conservatoria: deixar para a funcionaria. Fim.
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
       04 Data registo inscricao (data)   <- SO se o Artigo comecar por "P"
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
    artigo = str(b.get("artigo_matricial") or "")
    escrever(artigo)
    tab()       # -> 01 Fraccao autonoma
    # 01 Fraccao autonoma (letra da fraccao, ex "P")
    escrever(b.get("designacao_fracao", ""))
    tab()       # -> 02 Seccao

    # 02,03: Seccao, Arvore -> saltar ate a Data do registo de inscricao (04).
    tab(2)      # 02 -> 04 (Data registo inscricao)

    # 04 Data do registo de inscricao (regra do notario 2026-07-10): SO obrigatoria
    # quando o Artigo comeca por "P" (predio participado/provisorio). Nesse caso o
    # valor e a data da inscricao no Servico de Financas (data_inscricao_matriz).
    if artigo.strip().upper().startswith("P") and b.get("data_inscricao_matriz"):
        escrever(_data_simn(b["data_inscricao_matriz"]))

    # 04..11: Afectacao, Tipo Regime, Tipo Direito, Ident. Conservatoria, 2
    # fantasmas, Data provisorio -> saltar ate ao Nº Registo.
    tab(8)      # 04 -> 12 (Nº Registo)

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
