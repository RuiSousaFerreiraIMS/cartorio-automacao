"""
Extrator: le uma escritura e devolve um schema CompraVenda preenchido.

Le tanto .docx (Word moderno) como .doc (Word 97-2003 antigo). As escrituras
do cartorio sao .doc, por isso isto e essencial.

Estrategia:
  - le o texto do ficheiro (local)
  - usa a Claude API com structured output para extrair os campos
  - valida o resultado com Pydantic
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from google import genai
from google.genai import types

from modelos import CompraVenda, Doacao, Habilitacao, Partilha


def _log(msg: str) -> None:
    """Imprime no stderr com timestamp para nao poluir o stdout do JSON."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def _ler_docx(caminho: str) -> str:
    """Le um .docx com python-docx."""
    from docx import Document
    doc = Document(caminho)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


_CANDIDATOS_SOFFICE = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]
_CANDIDATOS_ANTIWORD = [
    r"C:\Program Files\Git\mingw64\bin\antiword.exe",
    r"C:\Program Files (x86)\Git\mingw64\bin\antiword.exe",
]


def _encontrar(nome: str, candidatos: list[str]) -> str | None:
    """Procura primeiro no PATH, depois em locais standard do Windows."""
    achado = shutil.which(nome)
    if achado:
        return achado
    for c in candidatos:
        if os.path.isfile(c):
            return c
    return None


def _ler_doc_antigo(caminho: str) -> str:
    """
    Le um .doc antigo (Word 97-2003). Tenta, por ordem:
      1. LibreOffice headless (mais fiavel; converte para txt)
      2. antiword (se instalado, vem com Git for Windows)
    """
    soffice = _encontrar("soffice", _CANDIDATOS_SOFFICE) or _encontrar("libreoffice", [])
    if soffice:
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "txt:Text",
                 caminho, "--outdir", tmpdir],
                check=True, capture_output=True, timeout=90,
            )
            base = os.path.splitext(os.path.basename(caminho))[0]
            txt_path = os.path.join(tmpdir, base + ".txt")
            with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

    antiword = _encontrar("antiword", _CANDIDATOS_ANTIWORD)
    if antiword:
        out = subprocess.run([antiword, caminho], check=True,
                             capture_output=True, timeout=90)
        # antiword sai em latin-1 por defeito (acentos viram bytes 0xE7 etc.)
        return out.stdout.decode("latin-1", errors="replace")

    raise RuntimeError(
        "Nao foi possivel ler .doc: instalar LibreOffice (recomendado) "
        "ou garantir que o Git for Windows esta instalado (traz antiword)."
    )


def ler_documento(caminho: str) -> str:
    """Le .docx ou .doc e devolve texto simples."""
    ext = os.path.splitext(caminho)[1].lower()
    _log(f"A ler {os.path.basename(caminho)} ({ext})...")
    t0 = time.time()
    if ext == ".docx":
        texto = _ler_docx(caminho)
    elif ext == ".doc":
        texto = _ler_doc_antigo(caminho)
    else:
        raise ValueError(f"Formato nao suportado: {ext}. Usar .doc ou .docx.")
    _log(f"  lidos {len(texto)} caracteres em {time.time()-t0:.1f}s")
    return texto


PROMPT_SISTEMA = """Es um extrator de dados de escrituras notariais portuguesas de COMPRA E VENDA.
Recebes o texto de uma escritura e devolves APENAS um objeto JSON valido
(sem texto antes ou depois, sem ```), com esta estrutura:

{
  "mnemonica": "CV",
  "data_escritura": "AAAA-MM-DD",
  "vendedores": [{"nif": "...", "nome": "...", "e_empresa": false,
                  "estado_civil": "casado", "regime_bens": "comunhao_de_adquiridos",
                  "conjuge_de_nif": "...", "naturalidade_concelho": "...",
                  "naturalidade_freguesia": "...", "nacionalidade": "...",
                  "morada": "...", "morada_localidade": "...", "morada_concelho": "...",
                  "morada_freguesia": "...", "codigo_postal": "...",
                  "capital_social": null, "tipo_sociedade": null, "conservatoria_registo": null,
                  "doc_identificacao": "...", "quota_parte": "1/1"}],
  "compradores": [ ... igual aos vendedores ... ],
  "bens": [{"designacao_fracao": "P", "descricao_predial": "...",
            "certidao_predial": "...", "artigo_matricial": "...",
            "freguesia": "...", "concelho": "...", "tipo": "U",
            "valor_patrimonial": 100504.66, "morada": "...",
            "codigo_simn": null, "descricao_livre": "..."}],
  "objeto": "...",
  "preco_venda": 280000.0,
  "hipoteca": 0.0,
  "hipoteca_a_cancelar": false,
  "ducs": [{"numero": "...", "tipo": "IMT", "montante": null}],
  "verbete_numero": null,
  "avisos": []
}

Regras importantes:
- Os outorgantes aparecem em blocos "Primeiro:", "Segundo:", etc. QUEM VENDE sao os
  vendedores, QUEM COMPRA/ACEITA sao os compradores. Identifica pelo papel ("vendem ao
  segundo outorgante" => o primeiro bloco e vendedor), nao pela ordem cega.
- CASAL: cria dois outorgantes SO se AMBOS forem parte do ato (ambos vendem/compram). Ex
  "FULANO e mulher BELTRANA vendem, NIF X e Y respectivamente" -> dois outorgantes, cada um
  com o seu NIF e o conjuge_de_nif a apontar para o outro. Mas se SO UM dos conjuges e parte
  do ato e o outro e apenas mencionado como conjuge (ex "BELTRANA, casada com FULANO,
  compra") -> cria SO UM outorgante (BELTRANA) com conjuge_de_nif = NIF do FULANO. NAO cries
  o conjuge que nao e parte do ato como outorgante separado.
- EMPRESA (sociedade/entidade): mete e_empresa=true e IGNORA os campos de pessoa
  (estado_civil, regime_bens, conjuge_de_nif, naturalidade, doc_identificacao: deixa-os null
  ou no default). Preenche:
    * nome = denominacao social completa (ex "CONSTRUCOES FULANO, LDA").
    * nif = o NIPC (9 digitos, sem espacos).
    * capital_social = capital social em euros se mencionado ("capital social de cinco mil
      euros" -> 5000.0); senao null.
    * tipo_sociedade = infere da forma juridica: "..., Lda"/"por quotas" -> "soc_quotas";
      "... Unipessoal Lda" -> "soc_unipessoal"; "..., S.A."/"anonima" -> "soc_anonima". Se
      nao der para saber, null.
    * conservatoria_registo = a Conservatoria do Registo Comercial onde esta matriculada, se
      mencionada ("matriculada na Conservatoria do Registo Comercial de Alcobaca" ->
      "Alcobaca"); senao null.
    * A SEDE da empresa vai nos MESMOS campos da morada: morada (rua+numero), morada_localidade,
      morada_concelho, morada_freguesia, codigo_postal.
- NIF: remove espacos (ex "222 350 245" -> "222350245").
- estado_civil: solteiro/casado/divorciado/viuvo/uniao_de_facto/desconhecido. OBRIGATORIO no
  SIMN, esforca-te sempre por o obter.
- regime_bens: comunhao_de_adquiridos/comunhao_geral/separacao_de_bens/nao_aplicavel.
- naturalidade_concelho e naturalidade_freguesia: a escritura diz "natural da freguesia de X,
  concelho de Y" (ou so "natural de X"). Preenche os DOIS. Se so vier a freguesia (ex "natural
  de Turquel"), INFERE o concelho a que pertence (Turquel -> Alcobaca). Se so vier o concelho,
  poe so o concelho. NUNCA metas a freguesia no campo do concelho. E OBRIGATORIO no SIMN.
- morada / morada_localidade / morada_concelho / morada_freguesia: a morada vem toda junta
  (ex "Largo da Escola, n.o 25, Vale de Maceira, Alfeizerao, Alcobaca"). SEPARA: morada = rua +
  numero ("Largo da Escola, n.o 25"); morada_localidade = o lugar/localidade ("Vale de Maceira");
  morada_concelho = o concelho ("Alcobaca"); morada_freguesia = a freguesia ("Alfeizerao"). Infere
  o concelho a partir da freguesia se preciso. Localidade/Concelho/Freguesia OBRIGATORIOS no SIMN.
- preco_venda: o valor por extenso na escritura (ex "DUZENTOS E OITENTA MIL EUROS" = 280000.0).
- valor_patrimonial: o VPT da fracao se mencionado.
- hipoteca_a_cancelar: true se o texto fala em cancelamento de hipoteca existente.
- ducs: extrai os "Documento numero ..." do Arquivo (IMT e TGIS/imposto do selo). O
  montante normalmente NAO esta na escritura: deixa null.
- codigo_simn: deixa SEMPRE null (e interno do SIMN, nao vem da escritura).
- Se nao encontrares um campo, poe null. NUNCA inventes.
"""


# Guarda a ultima resposta crua do LLM para debug em caso de falha de validacao.
ultimo_raw: dict | None = None


def _chamar_gemini(texto: str, prompt_sistema: str, modelo: str | None = None) -> dict:
    """Chamada generica a Gemini com JSON-mode."""
    modelo = modelo or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    _log(f"A chamar Gemini (modelo: {modelo}, ~{len(texto)} chars de input)...")
    t0 = time.time()
    resposta = client.models.generate_content(
        model=modelo,
        contents=texto,
        config=types.GenerateContentConfig(
            system_instruction=prompt_sistema,
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    _log(f"  resposta recebida em {time.time()-t0:.1f}s ({len(resposta.text)} chars)")
    return json.loads(resposta.text)


def _groq_call(client, modelo: str, prompt_sistema: str, texto: str, max_tokens: int) -> str:
    """Chamada bruta a Groq, devolve o texto da resposta.

    Timeout de 45s para nao prender indefinidamente no free tier quando o pool esta frio.
    """
    resposta = client.with_options(timeout=45.0).chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": texto},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=max_tokens,
    )
    return resposta.choices[0].message.content


def _chamar_groq(texto: str, prompt_sistema: str, modelo: str | None = None) -> dict:
    """Chamada generica a Groq com JSON-mode + fallback automatico para inputs grandes.

    Free tier do Llama 3.3 70B aceita ate ~6K tokens por request. Se apanhar 413,
    trunca o input e baixa max_tokens para caber, e retenta.
    """
    from groq import Groq  # import tardio para nao obrigar quem so usa Gemini
    modelo = modelo or os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    _log(f"A chamar Groq (modelo: {modelo}, ~{len(texto)} chars de input)...")
    t0 = time.time()

    try:
        texto_resp = _groq_call(client, modelo, prompt_sistema, texto, max_tokens=8000)
    except Exception as e:
        msg = str(e)
        if "413" not in msg and "too large" not in msg.lower():
            raise
        # Free tier estourou. Trunca para ~3500 chars e baixa max_tokens.
        # Mantemos o inicio do documento (cabecalho + outorgantes + primeiros bens).
        novo_tam = 3500
        _log(f"  413 (request grande demais). A truncar input para {novo_tam} chars e retentar...")
        texto_curto = texto[:novo_tam] + "\n\n[NOTA: documento truncado por limite de free tier]"
        texto_resp = _groq_call(client, modelo, prompt_sistema, texto_curto, max_tokens=2500)
        _log("  AVISO: extracao parcial (input cortado).")

    _log(f"  resposta recebida em {time.time()-t0:.1f}s ({len(texto_resp)} chars)")
    return json.loads(texto_resp)


def _extrair_json(texto: str) -> str:
    """Isola o objeto JSON de uma resposta que possa vir com ``` ou texto a envolver.

    Claude devolve JSON puro quando instruido, mas isto e uma rede de seguranca
    caso apareca uma fence de markdown ou uma frase antes/depois.
    """
    t = texto.strip()
    if t.startswith("```"):
        # tira a primeira linha (``` ou ```json) e a fence de fecho
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
        t = t.strip()
    if not t.startswith("{"):
        inicio, fim = t.find("{"), t.rfind("}")
        if inicio != -1 and fim > inicio:
            t = t[inicio:fim + 1]
    return t


def _chamar_claude(texto: str, prompt_sistema: str, modelo: str | None = None) -> dict:
    """Chamada a Claude (Anthropic). Devolve o dict extraido.

    Modelo por defeito: claude-haiku-4-5 (barato e preciso para extracao).
    Trocar via env var ANTHROPIC_MODEL (ex: claude-sonnet-5, claude-opus-4-8).
    """
    import anthropic  # import tardio: so obriga a instalar quem usa Claude
    modelo = modelo or os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
    # .strip(): se a chave foi setada com um \n ou espacos no fim, o SDK rebenta
    # com "Illegal header value" antes de tocar na rede. Limpamos por seguranca.
    client = anthropic.Anthropic(api_key=(os.environ.get("ANTHROPIC_API_KEY") or "").strip())
    _log(f"A chamar Claude (modelo: {modelo}, ~{len(texto)} chars de input)...")
    t0 = time.time()

    # Nao passamos temperature: os modelos Claude mais recentes (Opus 4.8, Sonnet 5)
    # rejeitam esse parametro. Para extracao o resultado ja e estavel sem ele.
    # timeout=60 + sem retries: por defeito o SDK espera ate 10 min e re-tenta 2x,
    # o que parece "pendurado" se a rede bloquear api.anthropic.com. Assim o erro
    # aparece em <1 min e diz-nos o que se passa.
    resposta = client.with_options(timeout=60.0, max_retries=0).messages.create(
        model=modelo,
        max_tokens=8000,
        system=(
            prompt_sistema
            + "\n\nIMPORTANTE: responde APENAS com o objeto JSON pedido, sem texto "
              "antes ou depois e sem blocos ``` de markdown."
        ),
        messages=[{"role": "user", "content": texto}],
    )
    texto_resp = "".join(b.text for b in resposta.content if b.type == "text")
    _log(f"  resposta recebida em {time.time()-t0:.1f}s ({len(texto_resp)} chars)")
    return json.loads(_extrair_json(texto_resp))


def _chamar_llm(texto: str, prompt_sistema: str, modelo: str | None = None) -> dict:
    """Dispatcher: escolhe o provedor pelo env var LLM_PROVIDER (default: gemini).

    Valores aceites: 'gemini' (default), 'groq', 'claude' (alias 'anthropic').
    """
    global ultimo_raw
    provedor = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provedor == "groq":
        dados = _chamar_groq(texto, prompt_sistema, modelo)
    elif provedor in ("claude", "anthropic"):
        dados = _chamar_claude(texto, prompt_sistema, modelo)
    elif provedor == "gemini":
        dados = _chamar_gemini(texto, prompt_sistema, modelo)
    else:
        raise ValueError(
            f"LLM_PROVIDER desconhecido: {provedor!r}. Usar 'gemini', 'groq' ou 'claude'."
        )
    ultimo_raw = dados
    return dados


def extrair_compra_venda(texto: str, modelo: str | None = None) -> CompraVenda:
    dados = _chamar_llm(texto, PROMPT_SISTEMA, modelo)
    _log("A validar com schema Pydantic...")
    cv = CompraVenda(**dados)
    cv.avisos = cv.validar_e_avisar()
    _log(f"  validacao OK. {len(cv.avisos)} aviso(s) gerado(s).")
    return cv


PROMPT_DOACAO = """Es um extrator de dados de escrituras notariais portuguesas de DOACAO.
Devolves APENAS um objeto JSON valido, sem texto antes/depois e sem ```:

{
  "mnemonica": "DOAC",
  "data_escritura": "AAAA-MM-DD",
  "doadores": [{"nif": "...", "nome": "...", "e_empresa": false,
                "estado_civil": "...", "regime_bens": "...", "conjuge_de_nif": "...",
                "naturalidade_concelho": "...", "naturalidade_freguesia": "...",
                "nacionalidade": "...", "morada": "...",
                "doc_identificacao": "...", "quota_parte": "1/1"}],
  "donatarios": [ ... igual aos doadores ... ],
  "bens": [{"designacao_fracao": null, "descricao_predial": "...",
            "certidao_predial": "...", "artigo_matricial": "...",
            "freguesia": "...", "concelho": "...", "tipo": "U",
            "valor_patrimonial": 100000.0, "morada": "...",
            "codigo_simn": null, "descricao_livre": "..."}],
  "valor_atribuido": 50000.0,
  "objeto": "...",
  "ducs": [{"numero": "...", "tipo": "IS", "montante": null}],
  "avisos": []
}

Regras:
- DOADORES: quem doa (gratuitamente). DONATARIOS: quem recebe.
- Identifica pelo papel ("doa a sua filha" => filha e donataria).
- Casais: dois outorgantes SO se ambos forem parte do ato; se so um for parte, UM outorgante
  com conjuge_de_nif a apontar para o conjuge (NAO cries o conjuge como outorgante separado).
- naturalidade_concelho / naturalidade_freguesia: separa Concelho e Freguesia; se so vier a
  freguesia, infere o concelho. estado_civil e naturalidade sao obrigatorios no SIMN.
- valor_atribuido: valor declarado para efeitos fiscais (Imposto do Selo).
- Se nao encontrares, poe null. Nunca inventes.
"""


def extrair_doacao(texto: str, modelo: str | None = None) -> Doacao:
    dados = _chamar_llm(texto, PROMPT_DOACAO, modelo)
    _log("A validar com schema Doacao...")
    d = Doacao(**dados)
    d.avisos = d.validar_e_avisar()
    _log(f"  validacao OK. {len(d.avisos)} aviso(s) gerado(s).")
    return d


PROMPT_HABILITACAO = """Es um extrator de dados de escrituras notariais portuguesas de HABILITACAO NOTARIAL.
Devolves APENAS um objeto JSON valido, sem texto antes/depois e sem ```:

{
  "mnemonica": "HAB",
  "data_escritura": "AAAA-MM-DD",
  "autor_heranca": {"nif": "...", "nome": "...", "e_empresa": false,
                    "estado_civil": "...", "naturalidade_concelho": "...",
                    "naturalidade_freguesia": "...", "nacionalidade": "...",
                    "morada": "...", "doc_identificacao": null},
  "data_obito": "AAAA-MM-DD",
  "com_testamento": false,
  "herdeiros": [ ... mesma estrutura de outorgantes ... ],
  "declarantes": [ ... outorgantes que comparecem e declaram ... ],
  "objeto": "...",
  "avisos": []
}

Regras:
- autor_heranca: a pessoa falecida (a 'pessoa de cujus'). Inclui dados pessoais.
- data_obito: a data em que faleceu.
- com_testamento: true se a escritura menciona testamento ativo (cedula testamentaria).
- herdeiros: lista dos herdeiros identificados (cnjuge, filhos, herdeiros universais).
- declarantes: quem comparece e declara perante o notario (pode incluir herdeiros e/ou testemunhas).
- Outorgantes (autor_heranca, herdeiros, declarantes): naturalidade em naturalidade_concelho +
  naturalidade_freguesia (infere o concelho a partir da freguesia se preciso).
- Se nao encontrares, poe null. Nunca inventes.
"""


def extrair_habilitacao(texto: str, modelo: str | None = None) -> Habilitacao:
    dados = _chamar_llm(texto, PROMPT_HABILITACAO, modelo)
    _log("A validar com schema Habilitacao...")
    h = Habilitacao(**dados)
    h.avisos = h.validar_e_avisar()
    _log(f"  validacao OK. {len(h.avisos)} aviso(s) gerado(s).")
    return h


PROMPT_PARTILHA = """Es um extrator de dados de escrituras notariais portuguesas de PARTILHA.
Devolves APENAS um objeto JSON valido, sem texto antes/depois e sem ```:

{
  "mnemonica": "PART",
  "data_escritura": "AAAA-MM-DD",
  "tipo_partilha": "hereditaria",
  "autor_heranca": {"nif": "...", "nome": "...", ...},
  "data_obito": "AAAA-MM-DD",
  "partilhantes": [ ... outorgantes ... ],
  "bens": [ ... mesma estrutura que CV ... ],
  "valor_total_acervo": 250000.0,
  "tornas": 0.0,
  "objeto": "...",
  "avisos": []
}

Regras:
- tipo_partilha: "hereditaria" (apos obito) ou "divorcio" ou outro.
- Para hereditaria, autor_heranca = o falecido (com NIF, nome, estado_civil,
  naturalidade_concelho, naturalidade_freguesia, morada, etc), data_obito = data do obito.
- partilhantes: TODOS os que participam na partilha (conjuge, filhos, herdeiros).
  Para CADA partilhante preenche TODOS os campos pessoais disponiveis no texto:
  NIF, nome, estado_civil, regime_bens, naturalidade_concelho, naturalidade_freguesia,
  nacionalidade, morada,
  doc_identificacao, quota_parte. NAO uses null se a informacao estiver no documento.
- bens: lista UM-A-UM todos os imoveis partilhados. Para CADA bem preenche o
  maximo de campos possivel: descricao_predial (numero/freguesia), artigo_matricial,
  freguesia, concelho, tipo ('U' urbano/'R' rustico), valor_patrimonial, morada,
  descricao_livre (texto do bem como aparece). NAO deixes bens vazios (todos null) -
  se nao tens certeza de um campo, deixa esse campo null mas preenche os outros.
- valor_total_acervo: soma dos valores atribuidos aos bens, se mencionada.
- tornas: compensacao monetaria entre partilhantes (se alguem leva mais bens e paga a diferenca).
- Se nao encontrares um campo concreto, poe esse campo a null. Nunca inventes.
"""


def extrair_partilha(texto: str, modelo: str | None = None) -> Partilha:
    dados = _chamar_llm(texto, PROMPT_PARTILHA, modelo)
    _log("A validar com schema Partilha...")
    p = Partilha(**dados)
    p.avisos = p.validar_e_avisar()
    _log(f"  validacao OK. {len(p.avisos)} aviso(s) gerado(s).")
    return p


def detetar_tipo(caminho: str) -> str:
    """Deteta o tipo de ato pelo nome do ficheiro. Devolve 'cv'|'doacao'|'habilitacao'|'partilha'."""
    nome = os.path.basename(caminho).lower()
    if "habilita" in nome:
        return "habilitacao"
    if "doaç" in nome or "doac" in nome:
        return "doacao"
    if "partilha" in nome:
        return "partilha"
    return "cv"  # default


_DISPATCHERS = {
    "cv": extrair_compra_venda,
    "doacao": extrair_doacao,
    "habilitacao": extrair_habilitacao,
    "partilha": extrair_partilha,
}


def extrair_de_ficheiro(caminho: str):
    """Conveniencia: ficheiro .doc/.docx -> objeto validado (CV/Doacao/Habilitacao/Partilha)."""
    tipo = detetar_tipo(caminho)
    _log(f"Tipo detetado pelo nome: {tipo}")
    texto = ler_documento(caminho)
    return _DISPATCHERS[tipo](texto)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python extrator.py <caminho_para_escritura.doc(x)> [saida.json]")
        raise SystemExit(1)
    caminho_entrada = sys.argv[1]
    caminho_saida = sys.argv[2] if len(sys.argv) >= 3 else "saida.json"

    resultado = extrair_de_ficheiro(caminho_entrada)

    # Escrever sempre em UTF-8 (PowerShell '>' usa UTF-16 e estraga acentos).
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(resultado.model_dump_json(indent=2))

    print(f"Extracao OK ({resultado.mnemonica}). JSON gravado em: {caminho_saida}")
    if resultado.avisos:
        print("AVISOS:")
        for a in resultado.avisos:
            print(f"  - {a}")
