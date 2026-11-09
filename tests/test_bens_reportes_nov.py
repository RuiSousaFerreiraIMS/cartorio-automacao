"""
Testes das correcoes dos bens (2a leva de reportes, nov/2026).

Correr na raiz do repo:  python -m pytest tests -q
Nao chamam o LLM nem o SIMN: testam so as regras deterministicas.
"""
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "peca_a_extracao"))
sys.path.insert(0, os.path.join(RAIZ, "peca_b_robo"))

# O extrator importa o SDK da Gemini e o robo o pyautogui; aqui nao sao precisos.
try:
    from google import genai  # noqa: F401
except Exception:
    _g = types.ModuleType("google")
    _g.genai = types.ModuleType("google.genai")
    _g.genai.types = None
    sys.modules["google"] = _g
    sys.modules["google.genai"] = _g.genai
sys.modules.setdefault("pyautogui", types.ModuleType("pyautogui"))

from extrator import artigos_no_texto, corrigir_bens, descricao_da_certidao  # noqa: E402
from modelos import Bem, CompraVenda, Doacao  # noqa: E402
from robo_actions import freguesia_simn  # noqa: E402


def test_doacao_descricao_texto_vai_buscar_numero_a_certidao():
    # reporte 20261104_094917: texto na descricao_predial, numero no codigo_simn
    d = Doacao(bens=[Bem(
        descricao_predial="Fração Autónoma correspondente ao primeiro andar",
        certidao_predial="PP-3522-60025-101102-005288",
        artigo_matricial="8608", codigo_simn="5288/Nazaré",
    )])
    corrigir_bens(d, "--- inscrito na matriz sob o artigo 8608.º, com o valor ...")
    b = d.bens[0]
    assert b.descricao_predial == "5288"
    assert b.codigo_simn is None
    assert b.descricao_livre.startswith("Fração")


def test_descricao_com_freguesia_fica_so_numero():
    cv = CompraVenda(bens=[Bem(descricao_predial="1746/Cela", artigo_matricial="2594.º")])
    corrigir_bens(cv, "")
    assert cv.bens[0].descricao_predial == "1746"
    assert cv.bens[0].artigo_matricial == "2594"


def test_varios_artigos_avisa_o_que_falta():
    # reporte 20261104_115115: predio com 2 artigos, so veio 1 bem
    texto = ("--- Metade do Prédio rústico ... inscrito  na  matriz  sob  os  artigos  2594.º  e\n"
             "2595.º, com os valores patrimoniais de 138,82 E e 138,82 E.")
    assert artigos_no_texto(texto) == ["2594", "2595"]
    cv = CompraVenda(bens=[Bem(artigo_matricial="2594", descricao_predial="1746")])
    corrigir_bens(cv, texto)
    assert any("2595" in a for a in cv.validar_e_avisar())


def test_artigo_de_origem_e_codigo_penal_nao_contam():
    texto = ("--- inscrito na matriz sob o artigo 2963.º (que proveio do artigo urbano 146.º),"
             " omisso na Conservatória.\n--- prevista no artigo 348.º do Código Penal.")
    assert artigos_no_texto(texto) == ["2963"]


def test_seccao_do_rustico():
    # reporte 20261109_102255: 'artigo 30.º secção P1-P2'
    texto = "--- Prédio Rústico ... inscrito na matriz sob o artigo 30.º secção P1-P2, com o valor"
    cv = CompraVenda(bens=[Bem(artigo_matricial="30", descricao_predial="3006", tipo="R")])
    corrigir_bens(cv, texto)
    assert cv.bens[0].seccao == "P1-P2"
    assert artigos_no_texto(texto) == ["30"]


def test_omisso_corrige_descricao_inventada():
    # reporte 20261109_135239: bens omissos, o LLM pos o artigo como descricao
    texto = ("--- UM - Prédio rústico ... inscrito na matriz sob o artigo 3549.º, com o valor "
             "de 70,74 E, omisso na Conservatória do Registo Predial de Alcobaça;\n"
             "--- DOIS - Prédio rústico ... sob o artigo 3559.º, com o valor de 88,42 E, "
             "omisso na Conservatória do Registo Predial de Alcobaça.")
    cv = CompraVenda(bens=[Bem(artigo_matricial="3549", descricao_predial="3549"),
                           Bem(artigo_matricial="3559", descricao_predial="3559")])
    corrigir_bens(cv, texto)
    assert [b.descricao_predial for b in cv.bens] == ["omisso", "omisso"]


def test_descrito_nao_vira_omisso():
    texto = ("--- descrito na Conservatória com o número mil e trezentos, inscrito na matriz sob "
             "o artigo 2554.º, com o valor patrimonial de 6.420,00 E.")
    cv = CompraVenda(bens=[Bem(artigo_matricial="2554", descricao_predial="1302")])
    corrigir_bens(cv, texto)
    assert cv.bens[0].descricao_predial == "1302"


def test_bem_em_comum_avisa_heranca():
    texto = "registada a aquisição a seu favor, em comum  e  sem determinação de parte ou direito"
    cv = CompraVenda(bens=[Bem(artigo_matricial="30", descricao_predial="3006")])
    corrigir_bens(cv, texto)
    assert cv.bem_em_comum
    assert any("em comum" in a for a in cv.validar_e_avisar())


def test_descricao_da_certidao():
    assert descricao_da_certidao("PP-3527-17696-100109-001615") == "1615"
    assert descricao_da_certidao(None) is None


def test_freguesia_uniao_robo_nao_escreve():
    # reportes 20261105_095616 / 20261109_093322: caia na freguesia extinta
    assert freguesia_simn("Alcobaça e Vestiaria") is None
    assert freguesia_simn("Coz, Alpedriz e Montes") is None
    assert freguesia_simn("União das freguesias de Pataias e Martingança") is None
    # freguesias simples (e com hifen/espacos) ficam iguais
    assert freguesia_simn("Valado dos Frades") == "Valado dos Frades"
    assert freguesia_simn("Caldas da Rainha - Nossa Senhora do Pópulo") == \
        "Caldas da Rainha - Nossa Senhora do Pópulo"
    assert freguesia_simn("Benedita") == "Benedita"
    assert freguesia_simn(None) is None


def test_freguesia_uniao_avisa_funcionaria():
    cv = CompraVenda(bens=[Bem(freguesia="Alcobaça e Vestiaria", artigo_matricial="2554",
                               descricao_predial="1302")])
    assert any("uniao" in a for a in cv.validar_e_avisar())
    cv2 = CompraVenda(bens=[Bem(freguesia="Benedita", artigo_matricial="1",
                                descricao_predial="2")])
    assert not any("uniao" in a for a in cv2.validar_e_avisar())


def _erro_404():
    import httpx
    import anthropic
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.NotFoundError("model not found", response=httpx.Response(404, request=req),
                                   body=None)


def test_claude_cai_na_reserva_se_modelo_indisponivel(monkeypatch):
    import pytest
    pytest.importorskip("anthropic")
    import extrator
    pedidos = []

    def falso(client, modelo, prompt, texto, timeout):
        pedidos.append(modelo)
        if modelo == extrator.MODELO_CLAUDE:
            raise _erro_404()
        return '{"ok": 1}'

    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.setattr(extrator, "_pedido_claude", falso)
    assert extrator._chamar_claude("texto", "prompt") == {"ok": 1}
    assert pedidos == [extrator.MODELO_CLAUDE, extrator.MODELO_CLAUDE_RESERVA]
    assert extrator.ultimo_modelo == extrator.MODELO_CLAUDE_RESERVA


def test_claude_erro_de_rede_nao_mascara(monkeypatch):
    import pytest
    anthropic = pytest.importorskip("anthropic")
    import httpx
    import extrator

    def falso(client, modelo, prompt, texto, timeout):
        raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://x"))

    monkeypatch.setattr(extrator, "_pedido_claude", falso)
    with pytest.raises(anthropic.APIConnectionError):
        extrator._chamar_claude("texto", "prompt")
