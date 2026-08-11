"""
Schemas Pydantic: definem EXATAMENTE que campos tem cada tipo de ato.

Este e o alicerce do projeto. Define-se o schema primeiro, antes de extrair
seja o que for, porque forca a pensar no problema e garante que o JSON de saida
tem sempre os campos certos com os tipos certos.

VERSAO 2: refinado com base numa escritura real de compra-venda de fracao.
Campos novos descobertos no documento real estao marcados com "# real".
"""

from __future__ import annotations

import unicodedata
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _heranca_e_coletivo(nif) -> bool:
    """Regra do notario (2026-08-11) para o NIF de uma heranca indivisa: se for
    >= 751000000 entra no formulario COLETIVO (Outorgante Colectivo); abaixo disso
    (ex 7500xxxxx / 747xxxxxx) entra no SINGULAR. e' so o formulario que muda."""
    digs = "".join(c for c in str(nif or "") if c.isdigit())
    return len(digs) == 9 and int(digs) >= 751_000_000


class _Base(BaseModel):
    """Base comum: re-valida em cada reassignment (importante para a app Streamlit)."""
    model_config = ConfigDict(validate_assignment=True)


def _sem_acentos(s: str) -> str:
    """Remove acentos: 'separação' -> 'separacao'."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _normalizar_estado_civil(v):
    """Mapeia variantes femininas/com acentos para o enum.
    'solteira' -> 'solteiro', 'viúva' -> 'viuvo', etc.
    """
    if v is None or v == "":
        return "desconhecido"
    if not isinstance(v, str):
        return v
    s = _sem_acentos(v).strip().lower().replace(" ", "_")
    # mapeamento feminino -> masculino (forma do enum)
    mapa = {
        "solteira": "solteiro",
        "casada": "casado",
        "divorciada": "divorciado",
        "viuva": "viuvo",
        "viuvo": "viuvo",  # ja correto (com acento removido)
    }
    return mapa.get(s, s)


def _normalizar_regime_bens(v):
    """Mapeia variantes para o enum. None -> nao_aplicavel."""
    if v is None or v == "":
        return "nao_aplicavel"
    if not isinstance(v, str):
        return v
    s = _sem_acentos(v).strip().lower().replace(" ", "_")
    mapa = {
        "comunhao_de_adquiridos": "comunhao_de_adquiridos",
        "comunhao_adquiridos": "comunhao_de_adquiridos",
        "comunhao_geral_de_bens": "comunhao_geral",
        "comunhao_geral": "comunhao_geral",
        "separacao_de_bens": "separacao_de_bens",
        "separacao_bens": "separacao_de_bens",
        "separacao": "separacao_de_bens",
        "nao_aplicavel": "nao_aplicavel",
        "n/a": "nao_aplicavel",
    }
    return mapa.get(s, s)


def _normalizar_tipo_sociedade(v):
    """Infere o tipo de sociedade a partir do texto/denominacao. None se vazio.

    O SIMN pede um dropdown (default 'Soc. por quotas'). Aceitamos tanto o valor
    do enum como a forma juridica escrita ('Lda', 'Unipessoal', 'S.A.') e a
    denominacao completa (ex 'FULANO UNIPESSOAL LDA' -> unipessoal).
    """
    if v is None or v == "":
        return None
    if not isinstance(v, str):
        return v
    s = _sem_acentos(v).strip().lower()
    # tokens alfanumericos: 'ACME, S.A.' -> ['acme', 's', 'a']; 'zeca, sa' -> ['zeca', 'sa']
    import re
    tokens = re.findall(r"[a-z0-9]+", s)
    if "unipessoal" in s:
        return "soc_unipessoal"
    if "anonim" in s or "sa" in tokens or tokens[-2:] == ["s", "a"]:
        return "soc_anonima"
    if "quota" in s or "lda" in s or "limitada" in s:
        return "soc_quotas"
    return {
        "soc_quotas": "soc_quotas",
        "soc_unipessoal": "soc_unipessoal",
        "soc_anonima": "soc_anonima",
        "outra": "outra",
    }.get(s.replace(" ", "_"), "outra")


class EstadoCivil(str, Enum):
    solteiro = "solteiro"
    casado = "casado"
    divorciado = "divorciado"
    viuvo = "viuvo"
    uniao_de_facto = "uniao_de_facto"
    desconhecido = "desconhecido"


class RegimeBens(str, Enum):
    comunhao_adquiridos = "comunhao_de_adquiridos"
    comunhao_geral = "comunhao_geral"
    separacao = "separacao_de_bens"
    nao_aplicavel = "nao_aplicavel"


class TipoSociedade(str, Enum):
    """Forma juridica da empresa (dropdown 'Tipo' no form Dados Empresa do SIMN).

    Default do SIMN e 'Soc. por quotas'. So preenchemos se a denominacao deixar
    claro (Lda / Unipessoal / S.A.); caso contrario None e o SIMN fica no default.
    """
    quotas = "soc_quotas"           # Sociedade por quotas (Lda)
    unipessoal = "soc_unipessoal"   # Sociedade unipessoal por quotas
    anonima = "soc_anonima"         # Sociedade anonima (S.A.)
    outra = "outra"


class Outorgante(_Base):
    """
    Uma pessoa (ou entidade) que intervem na escritura.

    Na escritura real, os outorgantes aparecem em blocos "Primeiro:", "Segundo:".
    Um bloco pode conter um CASAL (dois NIFs juntos: "NIF X e Y respectivamente").
    O extrator tem de separar o casal em dois Outorgantes.
    """
    nif: Optional[str] = Field(None, description="NIF/NIPC sem espacos. Campo-chave para o SIMN.")
    nome: Optional[str] = Field(None, description="Nome completo ou denominacao social.")
    e_empresa: bool = Field(False, description="True se for sociedade/entidade, nao pessoa.")

    # --- Campos de EMPRESA (Outorgante Colectivo). So preenchidos se e_empresa=True.
    #     A sede reutiliza os campos morada/morada_localidade/morada_concelho/
    #     morada_freguesia/codigo_postal ja existentes (sao os mesmos no SIMN). ---
    capital_social: Optional[float] = Field(
        None, description="Capital social em euros (form Dados Empresa). So empresa."
    )
    tipo_sociedade: Optional[TipoSociedade] = Field(
        None,
        description="Forma juridica (Lda/Unipessoal/S.A.). None => SIMN fica no default "
                    "'Soc. por quotas'. So empresa.",
    )
    conservatoria_registo: Optional[str] = Field(
        None,
        description="Conservatoria onde a sociedade esta matriculada (Ident. Conservatoria "
                    "no SIMN). So empresa.",
    )

    estado_civil: EstadoCivil = EstadoCivil.desconhecido
    regime_bens: RegimeBens = RegimeBens.nao_aplicavel
    conjuge_de_nif: Optional[str] = Field(
        None, description="Se casado e o conjuge tambem e outorgante, o NIF do conjuge."
    )
    naturalidade: Optional[str] = None  # legado (campo unico); usar os dois abaixo
    naturalidade_concelho: Optional[str] = Field(
        None,
        description="Concelho de naturalidade (o SIMN pede o Concelho em separado). "
                    "Se a escritura so der a freguesia, inferir o concelho a que pertence.",
    )
    naturalidade_freguesia: Optional[str] = Field(
        None, description="Freguesia de naturalidade."
    )
    naturalidade_pais: Optional[str] = Field(
        None,
        description="Pais de naturalidade SO quando e' fora de Portugal (ex 'Bélgica'). "
                    "Para naturais de Portugal fica null (o SIMN assume Portugal). Quando "
                    "esta preenchido, o Concelho/Freguesia de naturalidade ficam vazios.",
    )
    nacionalidade: Optional[str] = None
    morada: Optional[str] = None  # rua + numero (a parte "Morada" no SIMN)
    morada_localidade: Optional[str] = Field(
        None, description="Localidade / lugar da morada (o SIMN pede em separado)."
    )
    morada_concelho: Optional[str] = Field(
        None, description="Concelho da morada (dropdown no SIMN)."
    )
    morada_freguesia: Optional[str] = Field(
        None, description="Freguesia da morada (dropdown no SIMN)."
    )
    morada_pais: Optional[str] = Field(
        None,
        description="Pais da morada SO quando a pessoa mora fora de Portugal (ex 'Bélgica'). "
                    "Independente da naturalidade: um portugues pode morar fora. Para quem mora "
                    "em Portugal fica null. Quando preenchido, o Concelho/Freguesia da morada "
                    "ficam vazios.",
    )
    codigo_postal: Optional[str] = Field(
        None, description="Codigo postal 'NNNN-NNN'. Usado na sede da empresa; no form "
                          "pessoal o SIMN salta-o."
    )
    doc_identificacao: Optional[str] = Field(
        None, description="Nº de cartao de cidadao ou titulo de residencia."
    )
    quota_parte: Optional[str] = Field(None, description="Ex: '1/1', '1/2'.")

    # Campos usados no boletim de TESTAMENTO (Modelo 54). So aparecem no testamento.
    data_nascimento: Optional[str] = Field(
        None, description="Data de nascimento 'AAAA-MM-DD' (testamento: pedido no boletim)."
    )
    nome_pai: Optional[str] = Field(None, description="Nome do pai (filiacao; boletim testamento).")
    nome_mae: Optional[str] = Field(None, description="Nome da mae (filiacao; boletim testamento).")

    # Outorgantes EXTERNOS: a funcionaria marca quem entra pelo form simples de
    # "Outorgantes Externos" (grelha NIF/Nome/Data/Livro/Folhas/Natureza/Qualidade).
    e_externo: bool = Field(
        False, description="True se este outorgante entra como EXTERNO (form simples)."
    )
    qualidade: Optional[str] = Field(
        None, description="Qualidade em que interveio (so externos): ex 'Procurador', "
                          "'Consentimento', 'Cedente'. Dropdown de escrita no SIMN."
    )

    @field_validator("estado_civil", mode="before")
    @classmethod
    def _val_estado_civil(cls, v):
        return _normalizar_estado_civil(v)

    @field_validator("regime_bens", mode="before")
    @classmethod
    def _val_regime_bens(cls, v):
        return _normalizar_regime_bens(v)

    @field_validator("tipo_sociedade", mode="before")
    @classmethod
    def _val_tipo_sociedade(cls, v):
        return _normalizar_tipo_sociedade(v)


class Bem(_Base):
    """
    O imovel/bem transacionado.

    Na escritura real apareceram: descricao predial (nº na Conservatoria),
    artigo matricial, freguesia, valor patrimonial, e o tipo (fracao/predio).
    O 'codigo_simn' (ex: 100108 - U - 1948) e interno do SIMN e NAO aparece
    na escritura: a confirmar no video como a funcionaria o obtem.
    """
    designacao_fracao: Optional[str] = Field(
        None, description="Letra da fracao autonoma, ex: 'P'. None se predio inteiro."
    )
    descricao_predial: Optional[str] = Field(
        None, description="Nº de descricao predial na Conservatoria."
    )
    certidao_predial: Optional[str] = Field(
        None, description="Codigo da Certidao Predial Permanente, ex: PP-...."
    )
    artigo_matricial: Optional[str] = Field(None, description="Artigo matricial, ex: '2363'.")
    freguesia: Optional[str] = None
    concelho: Optional[str] = None
    tipo: Optional[str] = Field(None, description="'U' urbano, 'R' rustico.")
    data_inscricao_matriz: Optional[str] = Field(
        None,
        description="Data da inscricao na matriz (Serv. Financas), ex '2026-04-25'. So "
                    "obrigatoria no SIMN quando o artigo comeca por 'P' (predio participado, "
                    "ainda provisorio). Vem de 'apresentada no Servico de Financas ... em DATA'.",
    )
    valor_patrimonial: Optional[float] = Field(None, description="VPT em euros.")
    morada: Optional[str] = None
    codigo_simn: Optional[str] = Field(
        None, description="Identificador interno SIMN. Quase nunca vem da escritura."
    )
    descricao_livre: Optional[str] = Field(
        None, description="Texto descritivo do bem como aparece na escritura."
    )

    @field_validator("artigo_matricial", mode="before")
    @classmethod
    def _val_artigo(cls, v):
        """Predios mistos vem como dict {'urbano': '207', 'rustico': '741'}.
        Achatamos numa string legivel.
        """
        if isinstance(v, dict):
            partes = [f"{k.upper()[0]}:{val}" for k, val in v.items() if val]
            return " / ".join(partes) if partes else None
        return v

    @field_validator("valor_patrimonial", mode="before")
    @classmethod
    def _val_vpt(cls, v):
        """Predios mistos vem como dict {'urbano': 10237.32, 'rustico': 282.06}.
        Somamos os componentes (= VPT total do predio).
        """
        if isinstance(v, dict):
            try:
                return sum(float(x) for x in v.values() if x is not None)
            except (TypeError, ValueError):
                return None
        return v


class DUC(_Base):
    """
    DUC = Documento Unico de Cobranca (pagamento de impostos).
    Na escritura aparecem como 'Documento numero ... obtido via Internet'
    (IMT e verba 1.1 da TGIS / Imposto do Selo).

    Regra ATUALIZADA 2026-07-09: o notario passa a incluir o valor do DUC na
    escritura, por isso o montante ja NAO e sempre null; extrai-o se aparecer.
    Form SIMN: Numero, Facto IMT (tipo), Montante, Data.
    """
    numero: Optional[str] = None
    tipo: Optional[str] = Field(None, description="'IMT' ou 'IS' (imposto do selo).")
    montante: Optional[float] = Field(
        None, description="Valor do DUC em euros. Se a escritura o indicar, extrai-o."
    )
    data: Optional[str] = Field(None, description="Data do DUC, ex '2026-06-22'.")


class _Acto(_Base):
    """Base dos ATOS (nao dos sub-modelos). Traz os campos comuns aos Outorgantes
    Externos, que QUALQUER ato pode ter. Livro/Folhas/Natureza sao IGUAIS para todos
    os externos da escritura (a funcionaria mete o Livro/Folhas uma vez); a Data vem
    da data_escritura de cada ato; a Qualidade e' de cada externo (no Outorgante)."""
    livro: Optional[str] = Field(None, description="Livro da escritura (ex '263A'). Externos.")
    folhas: Optional[str] = Field(None, description="Folhas da escritura (ex '33'). Externos.")
    natureza_acto: Optional[str] = Field(
        None, description="Natureza do acto para os externos (dropdown de escrita no SIMN)."
    )


class CompraVenda(_Acto):
    """Schema de uma escritura de Compra-venda, mapeado ao SIMN."""
    mnemonica: str = Field("CV", description="Constante para compra-venda.")

    data_escritura: Optional[str] = Field(None, description="Data, ex: '2026-06-22'.")

    vendedores: list[Outorgante] = Field(default_factory=list)
    compradores: list[Outorgante] = Field(default_factory=list)
    heranca: Optional[Outorgante] = Field(
        None,
        description="Heranca indivisa como outorgante, quando a escritura refere 'NIF da "
                    "Heranca'. e_empresa e' definido pela regra do NIF (>=751000000 -> coletivo).",
    )
    bens: list[Bem] = Field(default_factory=list)

    objeto: Optional[str] = Field(None, description="Texto do campo Objeto no SIMN.")
    preco_venda: Optional[float] = Field(None, description="Preco da venda em euros.")

    hipoteca: float = Field(0.0, description="Valor de hipoteca nova; muitas vezes 0.")
    hipoteca_a_cancelar: bool = Field(
        False, description="True se a escritura menciona cancelamento de hipoteca existente."
    )

    ducs: list[DUC] = Field(default_factory=list)
    verbete_numero: Optional[str] = None

    avisos: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _regra_heranca(self):
        """Define e_empresa da heranca pela regra do NIF (nao confiar no LLM)."""
        if self.heranca and self.heranca.nif:
            self.heranca.e_empresa = _heranca_e_coletivo(self.heranca.nif)
        return self

    def herdar_heranca_do_primeiro(self) -> None:
        """Regra do notario (2026-08-11): a naturalidade, morada e estado civil da
        heranca (ou a SEDE, no form coletivo) sao SEMPRE as do PRIMEIRO outorgante da
        escritura, mesmo que o texto nao de esses dados do falecido. Chamar UMA vez
        apos a extracao (nao num validator, senao sobrescreveria edicoes da funcionaria).
        """
        if not (self.heranca and self.heranca.nif):
            return
        origem = (self.vendedores or self.compradores or [None])[0]
        if origem is None:
            return
        for campo in ("estado_civil", "regime_bens", "nacionalidade",
                      "naturalidade_concelho", "naturalidade_freguesia",
                      "morada", "morada_localidade", "morada_concelho",
                      "morada_freguesia", "codigo_postal"):
            setattr(self.heranca, campo, getattr(origem, campo))

    def validar_e_avisar(self) -> list[str]:
        """Gera avisos para a funcionaria rever antes do RUN. Nunca bloqueia.

        Distingue 3 cenarios para multiplos outorgantes do mesmo lado:
          - 1 so:     normal, sem aviso.
          - casal:    todos com conjuge_de_nif preenchido entre si (= info, nao alarme).
          - multiplos sem conjuge_de_nif: herdeiros / co-titulares (= confirmar).
        """
        avisos: list[str] = []
        if not self.vendedores:
            avisos.append("Nenhum vendedor detetado.")
        if not self.compradores:
            avisos.append("Nenhum comprador detetado.")

        for lado, lista in (("Vendedores", self.vendedores), ("Compradores", self.compradores)):
            if len(lista) <= 1:
                continue
            tem_conjuge = all(o.conjuge_de_nif for o in lista)
            if tem_conjuge and len(lista) == 2:
                avisos.append(f"{lado}: casal detetado (entra no SIMN pelo botao Casado).")
            else:
                avisos.append(
                    f"{lado}: {len(lista)} pessoas detetadas (provavelmente co-titulares, "
                    f"ex: herdeiros ou socios). Confirmar a relacao."
                )

        for lado, lista in (("Vendedor", self.vendedores), ("Comprador", self.compradores)):
            for o in lista:
                if not o.nif:
                    avisos.append(f"{lado} sem NIF: {o.nome or 'desconhecido'}.")
                elif not (o.nif.isdigit() and len(o.nif) == 9):
                    avisos.append(f"{lado} com NIF mal formatado ({o.nif}), confirmar.")

        if self.heranca and self.heranca.nif:
            forma = "COLETIVO" if self.heranca.e_empresa else "singular"
            avisos.append(
                f"Herança detetada (NIF {self.heranca.nif}): entra no form {forma}."
            )
            if self.vendedores:
                avisos.append(
                    "Se a Herança é o vendedor, os vendedores (herdeiros) podem entrar como "
                    "EXTERNOS (marca-os no painel de Externos)."
                )

        if not self.bens:
            avisos.append("Nenhum bem detetado.")
        for b in self.bens:
            if b.descricao_predial and "omisso" in b.descricao_predial.lower():
                avisos.append("Bem omisso na Conservatoria detetado, confirmar como entra no SIMN.")

        if self.preco_venda is None:
            avisos.append("Preco da venda nao detetado.")
        if self.hipoteca_a_cancelar:
            avisos.append("Hipoteca antiga a cancelar mencionada, confirmar tratamento no SIMN.")
        if self.hipoteca and self.hipoteca > 0:
            avisos.append(f"Hipoteca nova de {self.hipoteca:.0f} EUR (entra como Mutuo c/ Hipoteca no SIMN).")
        return avisos


# --- Schemas leves para os restantes tipos de ato (versao inicial, a refinar) ---


def _avisos_outorgantes(lado: str, lista: list[Outorgante]) -> list[str]:
    """Avisos comuns para qualquer lista de outorgantes."""
    avisos: list[str] = []
    if len(lista) > 1:
        tem_conjuge = all(o.conjuge_de_nif for o in lista)
        if tem_conjuge and len(lista) == 2:
            avisos.append(f"{lado}: casal detetado (entra no SIMN pelo botao Casado).")
    for o in lista:
        if not o.nif:
            avisos.append(f"{lado} sem NIF: {o.nome or 'desconhecido'}.")
        elif not (o.nif.isdigit() and len(o.nif) == 9):
            avisos.append(f"{lado} com NIF mal formatado ({o.nif}), confirmar.")
    return avisos


class Doacao(_Acto):
    """Doacao: doador(es) transfere(m) gratuitamente bem(ns) a donatario(s)."""
    mnemonica: str = Field("DOAC", description="Mnemonica para doacao.")
    data_escritura: Optional[str] = None
    doadores: list[Outorgante] = Field(default_factory=list)
    donatarios: list[Outorgante] = Field(default_factory=list)
    bens: list[Bem] = Field(default_factory=list)
    valor_atribuido: Optional[float] = Field(
        None, description="Valor declarado para efeitos fiscais (IS), normalmente proximo do VPT."
    )
    objeto: Optional[str] = None
    ducs: list[DUC] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)

    def validar_e_avisar(self) -> list[str]:
        avisos = []
        if not self.doadores:
            avisos.append("Nenhum doador detetado.")
        if not self.donatarios:
            avisos.append("Nenhum donatario detetado.")
        avisos += _avisos_outorgantes("Doador", self.doadores)
        avisos += _avisos_outorgantes("Donatario", self.donatarios)
        if not self.bens:
            avisos.append("Nenhum bem detetado.")
        if self.valor_atribuido is None:
            avisos.append("Valor atribuido a doacao nao detetado, confirmar (afeta Imposto do Selo).")
        return avisos


class Obito(_Base):
    """
    Um falecido dentro de uma habilitacao. Uma habilitacao pode ter VARIOS obitos
    (ex: falece o pai e depois a mae), cada um com o SEU falecido, data, assento e
    conjunto de herdeiros. No SIMN preenche-se um de cada vez.
    """
    autor_heranca: Optional[Outorgante] = Field(
        None, description="O falecido (a 'pessoa de cujus'). Dados pessoais."
    )
    data_obito: Optional[str] = Field(None, description="Data do obito.")
    assento_obito: Optional[str] = Field(
        None, description="Nº da certidao do assento de obito (campo 'Assento de Obito' do SIMN)."
    )
    com_testamento: bool = Field(False, description="True se este obito menciona testamento ativo.")
    herdeiros: list[Outorgante] = Field(
        default_factory=list, description="Os herdeiros DESTE falecido."
    )


class Habilitacao(_Acto):
    """
    Habilitacao Notarial: declaracao dos herdeiros de uma ou mais pessoas
    falecidas. Quando ha mais que um falecido o titulo vem no plural
    ("HABILITACOES"). Quem assina sao normalmente herdeiros e/ou testemunhas
    (declarantes que confirmam o universo de herdeiros).
    """
    mnemonica: str = Field("HAB", description="Mnemonica para habilitacao notarial.")
    data_escritura: Optional[str] = None
    obitos: list[Obito] = Field(
        default_factory=list,
        description="UM ou VARIOS falecidos, cada um com o seu autor/data/assento/herdeiros.",
    )
    declarantes: list[Outorgante] = Field(
        default_factory=list,
        description="Quem comparece e declara (cabeca de casal e/ou testemunhas).",
    )
    objeto: Optional[str] = None
    avisos: list[str] = Field(default_factory=list)

    @property
    def plural(self) -> bool:
        """True se ha mais que um obito (titulo 'Habilitacoes')."""
        return len(self.obitos) > 1

    def validar_e_avisar(self) -> list[str]:
        avisos = []
        if not self.obitos:
            avisos.append("Nenhum obito detetado.")
        for k, ob in enumerate(self.obitos, 1):
            pref = f"Obito {k}" if len(self.obitos) > 1 else "Obito"
            if ob.autor_heranca is None:
                avisos.append(f"{pref}: falecido nao detetado.")
            if not ob.data_obito:
                avisos.append(f"{pref}: data de obito nao detetada, confirmar.")
            if not ob.herdeiros:
                avisos.append(f"{pref}: nenhum herdeiro detetado.")
            avisos += _avisos_outorgantes(f"{pref} herdeiro", ob.herdeiros)
            if ob.com_testamento:
                avisos.append(f"{pref}: com testamento, confirmar interpretacao.")
        return avisos


class Partilha(_Acto):
    """
    Partilha (hereditaria ou por divorcio): divide bens entre os partilhantes.
    Pode envolver tornas (compensacoes monetarias entre partilhantes).
    """
    mnemonica: str = Field("PART", description="Mnemonica para partilha.")
    data_escritura: Optional[str] = None
    tipo_partilha: Optional[str] = Field(
        None, description="'hereditaria' ou 'divorcio' ou outro."
    )
    autor_heranca: Optional[Outorgante] = Field(
        None, description="Para partilha hereditaria: o falecido."
    )
    data_obito: Optional[str] = None
    partilhantes: list[Outorgante] = Field(default_factory=list)
    bens: list[Bem] = Field(default_factory=list)
    valor_total_acervo: Optional[float] = Field(
        None, description="Valor total atribuido ao conjunto dos bens partilhados."
    )
    tornas: Optional[float] = Field(
        None, description="Montante de tornas (compensacao entre partilhantes), se mencionado."
    )
    objeto: Optional[str] = None
    avisos: list[str] = Field(default_factory=list)

    def validar_e_avisar(self) -> list[str]:
        avisos = []
        if not self.partilhantes:
            avisos.append("Nenhum partilhante detetado.")
        avisos += _avisos_outorgantes("Partilhante", self.partilhantes)
        if not self.bens:
            avisos.append("Nenhum bem detetado.")
        elif len(self.bens) > 5:
            avisos.append(f"{len(self.bens)} bens detetados, confirmar lista completa.")
        if self.tipo_partilha == "hereditaria" and not self.autor_heranca:
            avisos.append("Partilha hereditaria sem autor da heranca identificado.")
        if self.tornas and self.tornas > 0:
            avisos.append(f"Tornas de {self.tornas:.0f} EUR mencionadas, confirmar quem paga a quem.")
        return avisos


class Convencao(_Acto):
    """
    Convencao antenupcial: dois nubentes acordam o regime de bens do futuro
    casamento. Nao ha vendedor/comprador nem bem imovel, so os dois outorgantes e
    o regime convencionado. Um dos nubentes pode ser estrangeiro.
    """
    mnemonica: str = Field("CONV", description="Mnemonica para convencao antenupcial.")
    data_escritura: Optional[str] = None
    outorgantes: list[Outorgante] = Field(
        default_factory=list, description="Os dois nubentes (noivos)."
    )
    regime_convencionado: Optional[str] = Field(
        None,
        description="Regime de bens acordado: comunhao_de_adquiridos / comunhao_geral / "
                    "separacao_de_bens (ou outro texto se atipico).",
    )
    objeto: Optional[str] = None
    avisos: list[str] = Field(default_factory=list)

    def validar_e_avisar(self) -> list[str]:
        avisos = []
        if not self.outorgantes:
            avisos.append("Nenhum outorgante (nubente) detetado.")
        elif len(self.outorgantes) != 2:
            avisos.append(f"{len(self.outorgantes)} nubentes detetados (esperava 2), confirmar.")
        avisos += _avisos_outorgantes("Nubente", self.outorgantes)
        if not self.regime_convencionado:
            avisos.append("Regime convencionado nao detetado, confirmar.")
        return avisos


class Justificacao(_Acto):
    """
    Justificacao notarial (usucapiao): os justificantes declaram ser donos de um
    bem por usucapiao; os confirmantes (testemunhas) confirmam. Detetar TODOS os
    outorgantes e o bem. Os confirmantes muitas vezes so tem cartao de cidadao,
    sem NIF, por isso nao se avisa da falta de NIF deles.
    """
    mnemonica: str = Field("JUST", description="Mnemonica para justificacao notarial.")
    data_escritura: Optional[str] = None
    justificantes: list[Outorgante] = Field(
        default_factory=list, description="Quem declara ser dono por usucapiao (o casal, etc)."
    )
    confirmantes: list[Outorgante] = Field(
        default_factory=list,
        description="Testemunhas que confirmam as declaracoes (podem nao ter NIF).",
    )
    bens: list[Bem] = Field(default_factory=list)
    objeto: Optional[str] = None
    avisos: list[str] = Field(default_factory=list)

    def validar_e_avisar(self) -> list[str]:
        avisos = []
        if not self.justificantes:
            avisos.append("Nenhum justificante detetado.")
        avisos += _avisos_outorgantes("Justificante", self.justificantes)
        if not self.confirmantes:
            avisos.append("Nenhum confirmante (testemunha) detetado, confirmar.")
        if not self.bens:
            avisos.append("Nenhum bem detetado.")
        return avisos


class Testamento(_Acto):
    """
    Testamento: um so outorgante (o testador) faz as suas disposicoes de ultima
    vontade. O objetivo desta app NAO e' o SIMN mas sim preencher o boletim de
    participacao ao Registo Geral de Testamentos (Modelo 54) e imprimi-lo. Por isso
    o testador tem de trazer TODOS os dados que o boletim pede: nome, filiacao
    (pai/mae), data de nascimento, naturalidade (freg/conc/pais), nacionalidade,
    estado civil, residencia (freg/conc).
    """
    mnemonica: str = Field("TEST", description="Mnemonica para testamento.")
    data_escritura: Optional[str] = None
    testador: Optional[Outorgante] = Field(None, description="Quem faz o testamento.")
    especie: Optional[str] = Field(
        "Testamento público", description="Especie do acto para o boletim (ex 'Testamento público')."
    )
    objeto: Optional[str] = Field(None, description="Resumo das disposicoes (legados, etc).")
    avisos: list[str] = Field(default_factory=list)

    def validar_e_avisar(self) -> list[str]:
        avisos = []
        t = self.testador
        if t is None:
            avisos.append("Testador nao detetado.")
            return avisos
        faltam = [nome for nome, val in (
            ("data de nascimento", t.data_nascimento),
            ("nome do pai", t.nome_pai),
            ("nome da mae", t.nome_mae),
            ("naturalidade", t.naturalidade_concelho or t.naturalidade_pais),
            ("estado civil", t.estado_civil.value if t.estado_civil else None),
        ) if not val]
        if faltam:
            avisos.append("Boletim: confirmar/adicionar " + ", ".join(faltam) + ".")
        return avisos
