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

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    nacionalidade: Optional[str] = None
    morada: Optional[str] = None
    doc_identificacao: Optional[str] = Field(
        None, description="Nº de cartao de cidadao ou titulo de residencia."
    )
    quota_parte: Optional[str] = Field(None, description="Ex: '1/1', '1/2'.")

    @field_validator("estado_civil", mode="before")
    @classmethod
    def _val_estado_civil(cls, v):
        return _normalizar_estado_civil(v)

    @field_validator("regime_bens", mode="before")
    @classmethod
    def _val_regime_bens(cls, v):
        return _normalizar_regime_bens(v)


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
    (IMT e verba 1.1 da TGIS / Imposto do Selo). O MONTANTE vem das Financas,
    nao da escritura. A confirmar no video se entra no ambito do robo.
    """
    numero: Optional[str] = None
    tipo: Optional[str] = Field(None, description="'IMT' ou 'IS' (imposto do selo).")
    montante: Optional[float] = None


class CompraVenda(_Base):
    """Schema de uma escritura de Compra-venda, mapeado ao SIMN."""
    mnemonica: str = Field("CV", description="Constante para compra-venda.")

    data_escritura: Optional[str] = Field(None, description="Data, ex: '2026-06-22'.")

    vendedores: list[Outorgante] = Field(default_factory=list)
    compradores: list[Outorgante] = Field(default_factory=list)
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


class Doacao(_Base):
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


class Habilitacao(_Base):
    """
    Habilitacao Notarial: declaracao dos herdeiros de uma pessoa falecida.

    Pode ser com ou sem testamento. Quem assina sao normalmente herdeiros e
    duas/tres testemunhas (declarantes que confirmam o universo de herdeiros).
    """
    mnemonica: str = Field("HAB", description="Mnemonica para habilitacao notarial.")
    data_escritura: Optional[str] = None
    autor_heranca: Optional[Outorgante] = Field(
        None, description="O falecido (a 'pessoa de cujus'). Dados pessoais + data de obito."
    )
    data_obito: Optional[str] = Field(None, description="Data do obito do autor da heranca.")
    com_testamento: bool = Field(False, description="True se o ato menciona testamento ativo.")
    herdeiros: list[Outorgante] = Field(default_factory=list)
    declarantes: list[Outorgante] = Field(
        default_factory=list,
        description="Quem comparece e declara (pode incluir herdeiros e testemunhas).",
    )
    objeto: Optional[str] = None
    avisos: list[str] = Field(default_factory=list)

    def validar_e_avisar(self) -> list[str]:
        avisos = []
        if self.autor_heranca is None:
            avisos.append("Autor da heranca (falecido) nao detetado.")
        elif not self.autor_heranca.nif:
            avisos.append("Autor da heranca sem NIF, confirmar.")
        if not self.data_obito:
            avisos.append("Data de obito nao detetada, confirmar.")
        if not self.herdeiros:
            avisos.append("Nenhum herdeiro detetado.")
        avisos += _avisos_outorgantes("Herdeiro", self.herdeiros)
        if self.com_testamento:
            avisos.append("Habilitacao com testamento, confirmar interpretacao.")
        return avisos


class Partilha(_Base):
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
