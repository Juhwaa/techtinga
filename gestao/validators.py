from datetime import date

from django.core.exceptions import ValidationError
from django.utils import timezone


def validar_inicio_nao_passado(inicio):
    if isinstance(inicio, date):
        if inicio < date.today():
            raise ValidationError("A data de início não pode ser anterior a hoje.")
    else:
        raise ValidationError("Informe uma data de início válida.")


def validar_projeto_aberto(projeto):
    projeto_fechado = False
    if projeto.ativo == False:
        projeto_fechado = True
    if projeto.fim is not None:
        projeto_fechado = True
    if projeto_fechado:
        raise ValidationError(
            "Não é possível criar tarefas em um projeto fechado (inativo ou com data de fim informada)."
        )


def validar_criacao_depois_inicio(criacao, projeto):
    if timezone.is_aware(criacao):
        criacao = timezone.localtime(criacao)
    data_criacao = criacao.date()
    if data_criacao < projeto.inicio:
        raise ValidationError(
            "A data de criação da tarefa não pode ser anterior ao início do projeto."
        )