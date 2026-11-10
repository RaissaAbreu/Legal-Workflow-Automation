"""Classificação da demanda por área jurídica — motor de regras (modo demonstração).

Cada área tem uma lista de termos com pesos. A área com maior pontuação vence.
A confiança é a fatia da pontuação total que ficou com a área vencedora.
Nenhum dado é enviado a serviços externos.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constantes import AREA_NAO_CLASSIFICADA
from .texto import contem_termo, normalizar

MOTOR = "Modo demonstração (regras)"

# termo -> peso (3 = muito característico da área, 1 = indício fraco)
TERMOS_POR_AREA: dict[str, dict[str, int]] = {
    "Trabalhista": {
        "reclamação trabalhista": 3, "reclamatória": 3, "justiça do trabalho": 3, "vara do trabalho": 3,
        "trt": 3, "tst": 3, "clt": 2, "horas extras": 2, "hora extra": 2, "verbas rescisórias": 3,
        "rescisão do contrato de trabalho": 3, "fgts": 2, "ex-funcionário": 2, "ex-empregado": 2,
        "ex-colaborador": 2, "empregado": 1, "funcionário": 1, "colaborador": 1, "demissão": 2,
        "justa causa": 3, "assédio moral": 2, "vínculo empregatício": 3, "insalubridade": 2,
        "periculosidade": 2, "ministério do trabalho": 3, "mpt": 3, "sindicato": 2,
        "convenção coletiva": 2, "acordo coletivo": 2, "salário": 1, "férias": 1, "ctps": 2,
    },
    "Cível": {
        "ação de indenização": 3, "indenização": 2, "danos morais": 1, "danos materiais": 2,
        "vara cível": 3, "ação cível": 3, "execução": 2, "título executivo": 3, "ação monitória": 3,
        "cobrança judicial": 2, "usucapião": 3, "responsabilidade civil": 3, "petição inicial": 2,
        "acidente": 2, "despejo": 3, "locação": 2, "imóvel": 1, "protesto": 2, "penhora": 2,
        "inventário": 3, "condomínio": 2, "citação": 1, "tribunal de justiça": 2,
    },
    "Consumidor": {
        "procon": 3, "consumidor": 2, "código de defesa do consumidor": 3, "cdc": 3,
        "reclame aqui": 3, "consumidor.gov": 3, "cliente": 1, "produto com defeito": 3,
        "defeito": 2, "vício do produto": 3, "troca": 1, "devolução": 2, "reembolso": 2,
        "estorno": 2, "cobrança indevida": 3, "negativação": 2, "serasa": 2, "spc": 2,
        "garantia": 1, "atraso na entrega": 2, "juizado especial": 1, "sac": 2, "recall": 3,
    },
    "Contratual": {
        "contrato": 2, "minuta": 3, "aditivo": 3, "cláusula": 2, "revisão contratual": 3,
        "acordo de confidencialidade": 3, "nda": 3, "fornecedor": 1, "prestação de serviços": 2,
        "rescisão contratual": 3, "multa contratual": 3, "distrato": 3, "renovação": 2,
        "sla": 2, "parceria": 1, "assinatura": 1, "termo de uso": 2, "proposta comercial": 2,
        "licenciamento": 2, "cessão": 2, "reajuste": 1,
    },
    "Regulatória": {
        "anpd": 3, "lgpd": 3, "anatel": 3, "anvisa": 3, "aneel": 3, "ans": 2, "bacen": 3,
        "banco central": 3, "cvm": 3, "susep": 3, "cade": 3, "agência reguladora": 3,
        "regulatório": 3, "regulatória": 3, "compliance": 2, "auto de infração": 3, "autuação": 3,
        "ofício": 2, "fiscalização": 2, "alvará": 2, "licença de funcionamento": 2,
        "resolução normativa": 3, "consulta pública": 3, "incidente de segurança": 3,
        "vazamento de dados": 3, "dados pessoais": 2, "receita federal": 2, "norma": 1,
    },
}


@dataclass
class ResultadoClassificacao:
    area: str
    confianca: float
    termos: dict[str, list[str]] = field(default_factory=dict)  # área -> termos encontrados
    pontuacoes: dict[str, int] = field(default_factory=dict)
    motor: str = MOTOR

    @property
    def termos_da_area(self) -> list[str]:
        return self.termos.get(self.area, [])


def classificar(texto: str) -> ResultadoClassificacao:
    norm = normalizar(texto)
    pontuacoes: dict[str, int] = {}
    termos: dict[str, list[str]] = {}
    for area, pesos in TERMOS_POR_AREA.items():
        total = 0
        encontrados = []
        for termo, peso in pesos.items():
            ocorrencias = contem_termo(norm, termo)
            if ocorrencias:
                # ocorrências repetidas contam, mas com teto, para um termo não dominar sozinho
                total += peso * min(ocorrencias, 3)
                encontrados.append(termo)
        pontuacoes[area] = total
        if encontrados:
            termos[area] = encontrados

    soma = sum(pontuacoes.values())
    if soma == 0:
        return ResultadoClassificacao(AREA_NAO_CLASSIFICADA, 0.0, termos, pontuacoes)

    vencedora = max(pontuacoes, key=lambda a: pontuacoes[a])
    confianca = round(pontuacoes[vencedora] / soma, 2)
    return ResultadoClassificacao(vencedora, confianca, termos, pontuacoes)
