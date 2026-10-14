from django.contrib import admin

from gestao.models import Projeto, Tarefa


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nome",
        "tipo_projeto",
        "cliente",
        "gerente",
        "inicio",
        "previsao_termino",
        "fim",
        "orcamento",
        "ativo",
    )
    list_filter = ("tipo_projeto", "ativo")
    search_fields = ("codigo", "nome", "cliente", "gerente")


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "projeto",
        "linguagem",
        "status",
        "prioridade",
        "responsavel",
        "criacao",
        "conclusao",
    )
    list_filter = ("status", "linguagem", "prioridade")
    search_fields = ("titulo", "responsavel", "projeto__codigo", "projeto__nome")
