from datetime import date, datetime

from django.db import models

from gestao.enumerations import LinguagemProgramacao


class ProjetoManager(models.Manager):
    def listar_projetos_linguagem(self, inicio, fim, linguagem):
        """
        Projetos que possuem tarefas iniciadas (campo criacao) entre as datas
        informadas (inclusive) e realizadas na linguagem de programacao informada.
        """
        if isinstance(inicio, date):
            if isinstance(inicio, datetime):
                inicio = inicio.date()
        else:
            raise ValueError("O parametro inicio deve ser uma data (date).")

        if isinstance(fim, date):
            if isinstance(fim, datetime):
                fim = fim.date()
        else:
            raise ValueError("O parametro fim deve ser uma data (date).")

        if inicio > fim:
            raise ValueError("A data de inicio nao pode ser posterior a data de fim.")

        if isinstance(linguagem, str):
            if linguagem not in LinguagemProgramacao.values:
                raise ValueError("Linguagem de programacao invalida: " + linguagem)
        else:
            raise ValueError("O parametro linguagem deve ser um texto (LinguagemProgramacao).")

        # todas as condicoes no mesmo filter(): precisam valer para a MESMA tarefa
        return (
            self.filter(
                tarefas__criacao__date__gte=inicio,
                tarefas__criacao__date__lte=fim,
                tarefas__linguagem=linguagem,
            )
            .distinct()
            .order_by("codigo")
        )
