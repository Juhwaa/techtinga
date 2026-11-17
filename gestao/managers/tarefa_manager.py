from django.db import models


class TarefaManager(models.Manager):
    def listar_tarefas_projeto(self, projeto):
        """
        Tarefas do projeto informado, ordenadas por responsavel, status e data de criacao.
        """
        # o modelo do projeto vem do proprio relacionamento, sem importar models.py
        modelo_projeto = self.model._meta.get_field("projeto").related_model

        if isinstance(projeto, modelo_projeto):
            return self.filter(projeto=projeto).order_by("responsavel", "status", "criacao")
        else:
            raise ValueError("O parametro projeto deve ser um Projeto.")

    def listar_tarefas_colaborador(self, responsavel):
        """
        Tarefas atribuidas ao colaborador informado, agrupadas por status
        e ordenadas por data de criacao.
        """
        if isinstance(responsavel, str):
            responsavel = responsavel.strip()
            if responsavel == "":
                raise ValueError("O parametro responsavel nao pode ser vazio.")
        else:
            raise ValueError("O parametro responsavel deve ser um texto.")

        return self.filter(responsavel__iexact=responsavel).order_by("status", "criacao")