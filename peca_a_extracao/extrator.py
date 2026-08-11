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

from modelos import CompraVenda, Convencao, Doacao, Habilitacao, Justificacao, Partilha


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
                  "naturalidade_freguesia": "...", "naturalidade_pais": null,
                  "nacionalidade": "...",
                  "morada": "...", "morada_localidade": "...", "morada_concelho": "...",
                  "morada_freguesia": "...", "morada_pais": null, "codigo_postal": "...",
                  "capital_social": null, "tipo_sociedade": null, "conservatoria_registo": null,
                  "doc_identificacao": "...", "quota_parte": "1/1"}],
  "compradores": [ ... igual aos vendedores ... ],
  "heranca": null,
  "bens": [{"designacao_fracao": "P", "descricao_predial": "...",
            "certidao_predial": "...", "artigo_matricial": "...",
            "data_inscricao_matriz": null,
            "freguesia": "...", "concelho": "...", "tipo": "U",
            "valor_patrimonial": 100504.66, "morada": "...",
            "codigo_simn": null, "descricao_livre": "..."}],
  "objeto": "...",
  "preco_venda": 280000.0,
  "hipoteca": 0.0,
  "hipoteca_a_cancelar": false,
  "ducs": [{"numero": "...", "tipo": "IMT", "montante": null, "data": null}],
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
- naturalidade_pais: SO quando a pessoa e' natural de FORA de Portugal (ex "natural de Franca",
  "natural e de nacionalidade belga"). Nesse caso poe aqui o PAIS (ex "França", "Bélgica") e deixa
  naturalidade_concelho E naturalidade_freguesia a NULL. Para naturais de Portugal, deixa
  naturalidade_pais null.
- morada / morada_localidade / morada_concelho / morada_freguesia: a morada vem toda junta
  (ex "Largo da Escola, n.o 25, Vale de Maceira, Alfeizerao, Alcobaca"). SEPARA: morada = rua +
  numero ("Largo da Escola, n.o 25"); morada_localidade = o lugar/localidade ("Vale de Maceira");
  morada_concelho = o concelho ("Alcobaca"); morada_freguesia = a freguesia ("Alfeizerao"). Infere
  o concelho a partir da freguesia se preciso. Localidade/Concelho/Freguesia OBRIGATORIOS no SIMN.
- morada_pais: SO quando a pessoa MORA fora de Portugal (ex "residente em Alsembergsteenweg 1027,
  1652 Beersel, Belgica"). Nesse caso poe aqui o PAIS (ex "Bélgica") e deixa morada_concelho e
  morada_freguesia a NULL (a rua fica na morada, a localidade estrangeira em morada_localidade).
  DECIDE pela MORADA, nao pela nacionalidade: um PORTUGUES pode morar fora (naturalidade em
  Portugal, mas morada_pais preenchido). Para quem mora em Portugal, deixa morada_pais null.
- descricao_predial: o NUMERO com que o predio/fracao esta descrito na Conservatoria. Vem quase
  sempre POR EXTENSO ("descrito na Conservatoria... com o numero seis mil duzentos e setenta e
  um" = "6271"). CONVERTE para digitos. Se a escritura disser que o predio e OMISSO/nao descrito,
  poe "omisso". E OBRIGATORIO no SIMN (campo Nº Registo), esforca-te por o obter.
- data_inscricao_matriz: SO relevante quando o artigo matricial comeca por "P" (ex "P11040"),
  que significa predio participado/provisorio ainda em inscricao. Nesse caso a escritura diz algo
  como "declaracao para inscricao ... apresentada no Servico de Financas de X em DD/MM/AAAA, com
  o registo numero N". Extrai essa DATA no formato AAAA-MM-DD (ex "2026-04-25"). Se o artigo NAO
  comeca por P, ou nao ha essa data, poe null.
- tipo: "U" se a escritura disser predio URBANO ou for uma FRACAO autonoma (as fracoes sao
  sempre de predios urbanos em propriedade horizontal); "R" se disser predio RUSTICO; "M" se
  misto. LE a designacao real do predio ("Predio rustico sito em..." -> "R"; "Predio urbano..."
  ou "Fracao Autonoma..." -> "U"). NUNCA assumas "U" por defeito: se diz rustico, e' "R".
- designacao_fracao: SO preencher se a escritura designar EXPLICITAMENTE uma fracao autonoma
  ("Fracao Autonoma designada pela letra X" -> "X"). Se for um predio (urbano ou rustico) SEM
  fracao, poe null. NUNCA inventes nem deduzas uma letra.
- preco_venda: o valor por extenso na escritura (ex "DUZENTOS E OITENTA MIL EUROS" = 280000.0).
- valor_patrimonial: o VPT da fracao se mencionado.
- hipoteca_a_cancelar: true se o texto fala em cancelamento de hipoteca existente.
- ducs: extrai os "Documento numero ..." do Arquivo (IMT e TGIS/imposto do selo). Para cada
  DUC: numero (o nº do documento), tipo ("IMT" ou "IS"), montante (o valor em euros SE a
  escritura o indicar, senao null) e data (data do documento, se indicada). O notario passou a
  incluir o valor do DUC, por isso EXTRAI o montante quando aparecer; se nao aparecer, null.
- codigo_simn: deixa SEMPRE null (e interno do SIMN, nao vem da escritura).
- heranca: se a escritura referir "NIF da Heranca - XXX" (ou "NIF heranca"), preenche aqui UM
  outorgante que representa a heranca indivisa: nif = o numero (so digitos, sem espacos); nome =
  "Heranca" seguido do nome do falecido se aparecer no texto (ex "Heranca de Carlota da Conceicao
  Serra"); e_empresa = false (o sistema corrige sozinho pela regra do NIF). Deixa os campos
  pessoais (estado_civil, naturalidade, morada, etc) null. Se NAO houver "NIF da Heranca", poe null.
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
    cv.herdar_heranca_do_primeiro()  # heranca: naturalidade/morada/estado civil do 1o outorgante
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
  "obitos": [
    {
      "autor_heranca": {"nif": null, "nome": "...", "e_empresa": false,
                        "estado_civil": "casado", "regime_bens": "comunhao_geral",
                        "naturalidade_concelho": "...", "naturalidade_freguesia": "...",
                        "nacionalidade": "...", "morada": "...", "morada_localidade": "...",
                        "morada_concelho": "...", "morada_freguesia": "...", "doc_identificacao": null},
      "data_obito": "AAAA-MM-DD",
      "assento_obito": "...",
      "com_testamento": false,
      "herdeiros": [ ... mesma estrutura de outorgantes ... ]
    }
  ],
  "declarantes": [ ... outorgantes que comparecem e declaram ... ],
  "objeto": "...",
  "avisos": []
}

Regras:
- obitos: UMA entrada por cada pessoa FALECIDA. MUITO IMPORTANTE: uma habilitacao pode ter
  VARIOS falecidos (titulo "HABILITACOES"), ex "faleceu o pai... deixou herdeiros X, Y, Z;
  posteriormente faleceu a mae... deixou herdeiro Z". Cria UM objeto em `obitos` por cada
  falecido, com os herdeiros DESSE falecido. NAO juntes tudo num so.
- Em cada obito:
  - autor_heranca: a pessoa FALECIDA (a 'pessoa de cujus'), NAO a outorgante/cabeca de casal.
    "faleceu FULANO, natural de..., ultima residencia habitual em..., no estado de casado com...
    sob o regime de...". Preenche o MAXIMO: nome, naturalidade_concelho/freguesia, estado_civil,
    regime_bens, e a morada (= ULTIMA RESIDENCIA HABITUAL). O NIF do falecido normalmente NAO
    aparece: deixa null.
  - data_obito: a data em que ESTE faleceu (por extenso -> AAAA-MM-DD).
  - assento_obito: o nº da certidao do assento de obito DESTE falecido (no Arquivo aparecem os
    varios: "assentos de obito (2517-7249-3048 e 6772-9645-9421)"; associa cada um ao falecido
    respetivo, pela ordem). Se nao der para associar com certeza, deixa null.
  - com_testamento: true se ESTE obito menciona testamento ativo.
  - herdeiros: os herdeiros DESTE falecido (conjuge, filhos, etc), com NIF, nome, estado_civil,
    naturalidade, morada quando disponivel. Um herdeiro que ja faleceu tambem se lista (a
    heranca dele pode gerar outro obito).
- declarantes: quem comparece e declara perante o notario (a cabeca de casal e/ou testemunhas).
- Outorgantes: naturalidade em naturalidade_concelho + naturalidade_freguesia (infere o concelho
  a partir da freguesia se preciso).
- MORADA de CADA outorgante (falecido, herdeiros, declarantes): a morada vem toda junta (ex "Rua
  da Boavista, n.o 17, Benedita, Alcobaca"). SEPARA SEMPRE: morada = rua + numero; morada_localidade
  = o lugar/localidade; morada_concelho = o concelho; morada_freguesia = a freguesia. Se a freguesia
  nao vier explicita mas a localidade a identificar, INFERE-A (ex "Benedita, Alcobaca" -> freguesia
  Benedita, concelho Alcobaca). Concelho e Freguesia sao OBRIGATORIOS no SIMN, nao os deixes null.
- PAIS (naturalidade_pais / morada_pais): SO quando e' fora de Portugal. Se um outorgante for
  natural de fora (ex "natural de França"), poe o pais em naturalidade_pais e deixa
  naturalidade_concelho/freguesia null. Se morar fora, poe em morada_pais e deixa
  morada_concelho/freguesia null. Naturalidade e morada sao independentes. Portugueses: null nos dois.
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


PROMPT_CONVENCAO = """Es um extrator de dados de escrituras notariais portuguesas de CONVENCAO ANTENUPCIAL.
Devolves APENAS um objeto JSON valido, sem texto antes/depois e sem ```:

{
  "mnemonica": "CONV",
  "data_escritura": "AAAA-MM-DD",
  "outorgantes": [ ... os DOIS nubentes, mesma estrutura de outorgantes ... ],
  "regime_convencionado": "comunhao_de_adquiridos",
  "objeto": "...",
  "avisos": []
}

Regras:
- outorgantes: os DOIS nubentes (noivos) que comparecem. Para CADA um preenche TODOS os campos
  pessoais do texto: nif, nome, estado_civil (normalmente "solteiro"), naturalidade_concelho,
  naturalidade_freguesia, nacionalidade, morada, morada_localidade, morada_concelho,
  morada_freguesia, doc_identificacao.
- ESTRANGEIRO: se um nubente for natural de fora de Portugal, preenche nacionalidade (ex
  "francesa") e poe o PAIS em naturalidade_pais (ex "França"), deixando naturalidade_concelho e
  naturalidade_freguesia a null. A MORADA e' tratada em separado: se mora em Portugal, preenche
  morada_concelho/morada_freguesia (portugueses) e deixa morada_pais null; se mora fora, poe o
  pais em morada_pais e deixa morada_concelho/freguesia null. Naturalidade e morada podem estar
  em paises diferentes, nao os confundas.
- regime_convencionado: o regime de bens que acordam para o casamento: "comunhao_de_adquiridos",
  "comunhao_geral" ou "separacao_de_bens" (ou o texto tal e qual se for atipico).
- NIF: remove espacos. Se nao encontrares um campo, poe null. NUNCA inventes.
"""


def extrair_convencao(texto: str, modelo: str | None = None) -> Convencao:
    dados = _chamar_llm(texto, PROMPT_CONVENCAO, modelo)
    _log("A validar com schema Convencao...")
    c = Convencao(**dados)
    c.avisos = c.validar_e_avisar()
    _log(f"  validacao OK. {len(c.avisos)} aviso(s) gerado(s).")
    return c


PROMPT_JUSTIFICACAO = """Es um extrator de dados de escrituras notariais portuguesas de JUSTIFICACAO NOTARIAL (usucapiao).
Devolves APENAS um objeto JSON valido, sem texto antes/depois e sem ```:

{
  "mnemonica": "JUST",
  "data_escritura": "AAAA-MM-DD",
  "justificantes": [ ... outorgantes que dizem ser donos por usucapiao ... ],
  "confirmantes": [ ... outorgantes que confirmam (testemunhas) ... ],
  "bens": [ ... mesma estrutura que CV ... ],
  "objeto": "...",
  "avisos": []
}

Regras:
- justificantes: os PRIMEIROS outorgantes, que declaram ser donos e legitimos possuidores do bem
  (frequentemente um casal). Para CADA um preenche TODOS os campos pessoais: nif, nome,
  estado_civil, regime_bens, naturalidade_concelho, naturalidade_freguesia, morada,
  morada_localidade, morada_concelho, morada_freguesia, doc_identificacao.
- confirmantes: os SEGUNDOS outorgantes (as testemunhas que confirmam). MUITAS VEZES NAO tem NIF,
  so cartao de cidadao ou bilhete de identidade: nesse caso deixa nif=null e poe o numero em
  doc_identificacao. Preenche nome, estado_civil, naturalidade e morada quando disponiveis.
- bens: o bem que esta a ser justificado (normalmente rustico OMISSO na Conservatoria). Preenche
  descricao_predial ("omisso" se o texto disser omisso), artigo_matricial, freguesia, concelho,
  tipo ("R" se rustico, "U" se urbano), valor_patrimonial, morada, descricao_livre.
- NIF: remove espacos. Se nao encontrares um campo, poe null. NUNCA inventes.
"""


def extrair_justificacao(texto: str, modelo: str | None = None) -> Justificacao:
    dados = _chamar_llm(texto, PROMPT_JUSTIFICACAO, modelo)
    _log("A validar com schema Justificacao...")
    j = Justificacao(**dados)
    j.avisos = j.validar_e_avisar()
    _log(f"  validacao OK. {len(j.avisos)} aviso(s) gerado(s).")
    return j


import unicodedata as _ud


def _sem_acentos(s: str) -> str:
    return "".join(c for c in _ud.normalize("NFD", s) if _ud.category(c) != "Mn")


# Tipos de ato: mnemonica interna -> nome legivel (a app usa para escolher/corrigir).
TIPOS_ATO = [
    ("cv", "Compra e Venda"),
    ("doacao", "Doação"),
    ("habilitacao", "Habilitação"),
    ("partilha", "Partilha"),
    ("convencao", "Convenção Antenupcial"),
    ("justificacao", "Justificação"),
]


def detetar_tipo_por_texto(texto: str) -> str:
    """Deteta o tipo de ato pelo CONTEUDO do texto. Devolve
    'cv'|'doacao'|'habilitacao'|'partilha' (default 'cv').

    Porque nao pelo nome do ficheiro: a app grava a escritura num temporario com
    nome ALEATORIO, por isso a deteccao pelo nome dava sempre 'cv'. A funcionaria
    pode sempre corrigir o tipo na app.
    """
    t = _sem_acentos((texto or "").lower())
    titulo = t.lstrip()[:200]  # o TITULO do ato esta sempre no inicio (1a linha)

    # 1. Pelo TITULO, que e' explicito e fiavel. Tem PRIORIDADE sobre o corpo: uma
    #    COMPRA E VENDA que menciona uma heranca/falecido NAO e' uma habilitacao.
    if "compra e venda" in titulo:
        return "cv"
    if "convencao antenupcial" in titulo or "antenupcial" in titulo:
        return "convencao"
    if "justificacao" in titulo:
        return "justificacao"
    if "habilitacao" in titulo or "habilita" in titulo:
        return "habilitacao"
    if "partilha" in titulo:
        return "partilha"
    if "doacao" in titulo:
        return "doacao"

    # 2. Fallback pelo CORPO, so quando o titulo nao chega (raro).
    if "faleceu" in t and ("cabeca de casal" in t or "herdeir" in t or "de cujus" in t):
        return "habilitacao"
    if "usucapiao" in t and "justificante" in t:
        return "justificacao"
    if "adjudica" in t and ("quinhao" in t or "acervo" in t):
        return "partilha"
    if "donatari" in t:
        return "doacao"
    return "cv"


def detetar_tipo(caminho: str) -> str:
    """(Legado, usado pela CLI.) Deteta o tipo pelo NOME do ficheiro."""
    nome = os.path.basename(caminho).lower()
    if "habilita" in nome:
        return "habilitacao"
    if "doaç" in nome or "doac" in nome:
        return "doacao"
    if "partilha" in nome:
        return "partilha"
    return "cv"


_DISPATCHERS = {
    "cv": extrair_compra_venda,
    "doacao": extrair_doacao,
    "habilitacao": extrair_habilitacao,
    "partilha": extrair_partilha,
    "convencao": extrair_convencao,
    "justificacao": extrair_justificacao,
}


def extrair_texto(texto: str, tipo: str, modelo: str | None = None):
    """Extrai a partir de TEXTO ja lido, com um tipo EXPLICITO. A app usa isto
    para re-extrair quando a funcionaria corrige o tipo, sem reler o ficheiro."""
    if tipo not in _DISPATCHERS:
        raise ValueError(f"Tipo de ato desconhecido: {tipo!r}")
    return _DISPATCHERS[tipo](texto, modelo)


def extrair_de_ficheiro(caminho: str, tipo: str | None = None):
    """Ficheiro .doc/.docx -> objeto validado. Se `tipo` for None, deteta pelo
    CONTEUDO (nao pelo nome, que na app e' um temporario aleatorio)."""
    texto = ler_documento(caminho)
    if tipo is None:
        tipo = detetar_tipo_por_texto(texto)
        _log(f"Tipo detetado pelo conteudo: {tipo}")
    else:
        _log(f"Tipo indicado: {tipo}")
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
