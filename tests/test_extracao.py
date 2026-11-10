from datetime import date

from legalflow.extracao import extrair_departamento, extrair_prazo, extrair_solicitante, extrair_texto_documento, ler_email, somar_dias_uteis
from legalflow.config import RAIZ_PROJETO

HOJE = date(2026, 11, 10)  # terça-feira


def test_data_explicita_com_gatilho():
    achado = extrair_prazo("Prazo para contestação até 20/11/2026.", HOJE)
    assert achado.data == date(2026, 11, 20)
    assert achado.trecho == "Prazo para contestação até 20/11/2026"


def test_data_sem_gatilho_e_ignorada():
    assert extrair_prazo("HISTÓRICO DE ATENDIMENTO\n03/10/2026 — cliente ligou", HOJE) is None


def test_mais_de_uma_data_vale_a_mais_proxima():
    assert extrair_prazo("prazo até 25/11/2026; audiência em 18/11/2026", HOJE).data == date(2026, 11, 18)


def test_data_por_extenso_sem_ano():
    assert extrair_prazo("audiência marcada para 3 de dezembro", HOJE).data == date(2026, 12, 3)


def test_dias_uteis_e_corridos():
    assert extrair_prazo("Prazo de 5 dias úteis", HOJE).data == date(2026, 11, 17)
    assert extrair_prazo("Prazo para resposta: 10 dias", HOJE).data == date(2026, 11, 20)
    assert extrair_prazo("responder em 48 horas", HOJE).data == date(2026, 11, 12)


def test_somar_dias_uteis_pula_fim_de_semana():
    assert somar_dias_uteis(date(2026, 11, 13), 1) == date(2026, 11, 16)  # sexta -> segunda


def test_campos_rotulados():
    texto = "Solicitante: Ana Souza\nDepartamento: Compras\n"
    assert extrair_solicitante(texto) == "Ana Souza"
    assert extrair_departamento(texto) == "Compras"


def test_ler_email_de_exemplo():
    lido = ler_email((RAIZ_PROJETO / "exemplos" / "email_notificacao_procon.eml").read_bytes())
    assert lido.remetente_email == "renata.oliveira@exemplo.com.br"
    assert "Procon" in lido.assunto
    assert [a.nome for a in lido.anexos] == ["historico_atendimento.txt"]


def test_texto_de_documento_txt_e_imagem():
    assert extrair_texto_documento("a.txt", "olá".encode()) == "olá"
    assert extrair_texto_documento("a.png", b"\x89PNG") == ""
