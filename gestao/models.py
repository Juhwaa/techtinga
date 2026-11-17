from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone

from gestao.base import BaseModel
from gestao.enumerations import LinguagemProgramacao, Status, TipoProjeto
from gestao.managers import ProjetoManager, TarefaManager
from gestao.validators import (
    validar_criacao_depois_inicio,
    validar_inicio_nao_passado,
    validar_projeto_aberto,
)


class Projeto(BaseModel):
    codigo = models.CharField(
        max_length=20,
        unique=True,
        validators=[MinLengthValidator(5)],
    )
    nome = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(5)],
    )
    tipo_projeto = models.CharField(
        max_length=20,
        choices=TipoProjeto.choices,
    )
    cliente = models.CharField(
        max_length=50,
        validators=[MinLengthValidator(3)],
    )
    gerente = models.CharField(
        max_length=50,
        validators=[MinLengthValidator(3)],
    )
    inicio = models.DateField()
    previsao_termino = models.DateField()
    fim = models.DateField(null=True, blank=True)
    orcamento = models.DecimalField(max_digits=12, decimal_places=2)
    ativo = models.BooleanField(default=True)

    objects = ProjetoManager()

    def clean(self):
        super().clean()
        erros = {}

        inicio_valido = isinstance(self.inicio, date)
        previsao_valida = isinstance(self.previsao_termino, date)
        fim_valido = isinstance(self.fim, date)

        if self._state.adding:
            if inicio_valido:
                try:
                    validar_inicio_nao_passado(self.inicio)
                except ValidationError as erro:
                    erros["inicio"] = erro.messages

        if inicio_valido and previsao_valida:
            if self.previsao_termino <= self.inicio:
                erros["previsao_termino"] = (
                    "A previsão de término deve ser posterior à data de início."
                )

        if inicio_valido and fim_valido:
            if self.fim < self.inicio:
                erros["fim"] = "A data de fim não pode ser anterior à data de início."

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            self.cliente
            + " | "
            + self.nome
            + " | "
            + self.get_tipo_projeto_display()
            + " | R$ "
            + str(self.orcamento)
            + " | "
            + self.inicio.strftime("%d/%m/%Y")
            + " | "
            + self.previsao_termino.strftime("%d/%m/%Y")
        )


class Tarefa(BaseModel):
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name="tarefas",
    )
    titulo = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(5)],
    )
    descricao = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(1000)],
    )
    linguagem = models.CharField(
        max_length=20,
        choices=LinguagemProgramacao.choices,
    )
    estimativa_horas = models.IntegerField(validators=[MinValueValidator(0)])
    horas_registradas = models.IntegerField(validators=[MinValueValidator(0)])
    prioridade = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    responsavel = models.CharField(
        max_length=50,
        validators=[MinLengthValidator(3)],
    )
    criacao = models.DateTimeField()
    conclusao = models.DateTimeField(null=True, blank=True)

    objects = TarefaManager()

    def clean(self):
        super().clean()
        erros = {}

        criacao_valida = isinstance(self.criacao, datetime)
        conclusao_valida = isinstance(self.conclusao, datetime)

        if self.projeto_id is not None:
            projeto = self.projeto

            if self._state.adding:
                try:
                    validar_projeto_aberto(projeto)
                except ValidationError as erro:
                    erros["projeto"] = erro.messages

            if criacao_valida:
                try:
                    validar_criacao_depois_inicio(self.criacao, projeto)
                except ValidationError as erro:
                    erros["criacao"] = erro.messages

        if criacao_valida and conclusao_valida:
            if self.conclusao < self.criacao:
                erros["conclusao"] = (
                    "A data de conclusão não pode ser anterior à data de criação."
                )

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        criacao = self.criacao
        if timezone.is_aware(criacao):
            criacao = timezone.localtime(criacao)
        texto_criacao = criacao.strftime("%d/%m/%Y")

        texto_conclusao = "sem conclusão"
        if self.conclusao is not None:
            conclusao = self.conclusao
            if timezone.is_aware(conclusao):
                conclusao = timezone.localtime(conclusao)
            texto_conclusao = conclusao.strftime("%d/%m/%Y")

        return (
            self.responsavel
            + " | "
            + self.get_linguagem_display()
            + " | "
            + self.titulo
            + " | "
            + texto_criacao
            + " | "
            + texto_conclusao
            + " | "
            + str(self.estimativa_horas)
            + "h estimadas | "
            + self.get_status_display()
        )