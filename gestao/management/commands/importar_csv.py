import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from gestao.models import Projeto, Tarefa
from gestao.validators import validar_criacao_depois_inicio

CAMPOS_PROJETO = [
    "projeto_codigo",
    "projeto_nome",
    "projeto_tipo_projeto",
    "projeto_cliente",
    "projeto_gerente",
    "projeto_inicio",
    "projeto_previsao_termino",
    "projeto_orcamento",
]

CAMPOS_TAREFA = [
    "tarefa_titulo",
    "tarefa_linguagem",
    "tarefa_estimativa_horas",
    "tarefa_horas_registradas",
    "tarefa_prioridade",
    "tarefa_status",
    "tarefa_responsavel",
    "tarefa_criacao",
]

CAMPOS_OPCIONAIS = [
    "projeto_fim",
    "projeto_ativo",
    "tarefa_descricao",
    "tarefa_conclusao",
]


class Command(BaseCommand):
    help = "Importa projetos e tarefas de um arquivo CSV. Exemplo: python manage.py importar_csv techtinga.csv"

    def add_arguments(self, parser):
        parser.add_argument("arquivo", type=str, help="Caminho do arquivo CSV.")
        parser.add_argument(
            "--limpar",
            action="store_true",
            help="Apaga todos os projetos e tarefas existentes antes de importar.",
        )

    def handle(self, *args, **options):
        caminho = options["arquivo"]

        if options["limpar"] == False:
            if Projeto.objects.exists():
                raise CommandError(
                    "Ja existem projetos no banco. Use --limpar para apagar e importar de novo."
                )

        # 1) Leitura do arquivo
        try:
            with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
                leitor = csv.DictReader(arquivo)
                colunas_do_arquivo = leitor.fieldnames
                linhas = list(leitor)
        except FileNotFoundError:
            raise CommandError("Arquivo nao encontrado: " + caminho)

        if colunas_do_arquivo is None:
            raise CommandError("O arquivo esta vazio.")

        colunas_faltando = []
        for coluna in CAMPOS_PROJETO + CAMPOS_TAREFA + CAMPOS_OPCIONAIS:
            if coluna not in colunas_do_arquivo:
                colunas_faltando.append(coluna)
        if len(colunas_faltando) > 0:
            raise CommandError(
                "Colunas ausentes no arquivo: " + ", ".join(colunas_faltando)
            )

        # 2) Validacao linha a linha (nada e gravado ainda)
        projetos = {}
        projetos_invalidos = []
        tarefas = []
        linhas_so_projeto = 0
        linhas_ignoradas = 0

        for numero, linha in enumerate(linhas, start=2):
            motivo = ""
            projeto = None

            # --- dados obrigatorios do projeto
            faltando_projeto = []
            for campo in CAMPOS_PROJETO:
                if (linha[campo] or "").strip() == "":
                    faltando_projeto.append(campo)

            if len(faltando_projeto) > 0:
                motivo = "faltam dados obrigatorios do projeto (" + ", ".join(faltando_projeto) + ")"
            else:
                codigo = linha["projeto_codigo"].strip()

                if codigo in projetos_invalidos:
                    motivo = "o projeto " + codigo + " possui dados invalidos"
                elif codigo in projetos:
                    # o arquivo repete os dados do projeto em cada tarefa:
                    # o projeto e criado uma unica vez, na primeira linha em que aparece
                    projeto = projetos[codigo]
                else:
                    try:
                        fim = None
                        if (linha["projeto_fim"] or "").strip() != "":
                            fim = date.fromisoformat(linha["projeto_fim"].strip())

                        ativo = True
                        texto_ativo = (linha["projeto_ativo"] or "").strip().lower()
                        if texto_ativo == "false":
                            ativo = False
                        elif texto_ativo != "" and texto_ativo != "true":
                            raise ValueError("valor invalido em projeto_ativo")

                        novo_projeto = Projeto(
                            codigo=codigo,
                            nome=linha["projeto_nome"].strip(),
                            tipo_projeto=linha["projeto_tipo_projeto"].strip(),
                            cliente=linha["projeto_cliente"].strip(),
                            gerente=linha["projeto_gerente"].strip(),
                            inicio=date.fromisoformat(linha["projeto_inicio"].strip()),
                            previsao_termino=date.fromisoformat(
                                linha["projeto_previsao_termino"].strip()
                            ),
                            fim=fim,
                            orcamento=Decimal(linha["projeto_orcamento"].strip()),
                            ativo=ativo,
                        )
                        novo_projeto.clean_fields()

                        if novo_projeto.previsao_termino <= novo_projeto.inicio:
                            raise ValueError("previsao_termino deve ser posterior ao inicio")
                        if novo_projeto.fim is not None:
                            if novo_projeto.fim < novo_projeto.inicio:
                                raise ValueError("fim nao pode ser anterior ao inicio")

                        projetos[codigo] = novo_projeto
                        projeto = novo_projeto
                    except (ValueError, InvalidOperation, ValidationError) as erro:
                        projetos_invalidos.append(codigo)
                        motivo = "projeto " + codigo + " invalido: " + str(erro)

            # --- dados da tarefa
            if motivo == "":
                faltando_tarefa = []
                for campo in CAMPOS_TAREFA:
                    if (linha[campo] or "").strip() == "":
                        faltando_tarefa.append(campo)

                if len(faltando_tarefa) == len(CAMPOS_TAREFA):
                    # linha so com projeto (projeto sem tarefas): o projeto fica, nao ha tarefa
                    linhas_so_projeto = linhas_so_projeto + 1
                elif len(faltando_tarefa) > 0:
                    motivo = "faltam dados obrigatorios da tarefa (" + ", ".join(faltando_tarefa) + ")"
                else:
                    try:
                        criacao = datetime.fromisoformat(linha["tarefa_criacao"].strip())
                        if timezone.is_naive(criacao):
                            criacao = timezone.make_aware(criacao)

                        conclusao = None
                        if (linha["tarefa_conclusao"] or "").strip() != "":
                            conclusao = datetime.fromisoformat(linha["tarefa_conclusao"].strip())
                            if timezone.is_naive(conclusao):
                                conclusao = timezone.make_aware(conclusao)

                        nova_tarefa = Tarefa(
                            projeto=projeto,
                            titulo=linha["tarefa_titulo"].strip(),
                            descricao=(linha["tarefa_descricao"] or "").strip(),
                            linguagem=linha["tarefa_linguagem"].strip(),
                            estimativa_horas=int(linha["tarefa_estimativa_horas"].strip()),
                            horas_registradas=int(linha["tarefa_horas_registradas"].strip()),
                            prioridade=int(linha["tarefa_prioridade"].strip()),
                            status=linha["tarefa_status"].strip(),
                            responsavel=linha["tarefa_responsavel"].strip(),
                            criacao=criacao,
                            conclusao=conclusao,
                        )
                        # valida tipos, limites e opcoes (enum) de cada campo
                        nova_tarefa.clean_fields(exclude=["projeto"])

                        if conclusao is not None:
                            if conclusao < criacao:
                                raise ValueError("conclusao anterior a criacao")

                        # a tarefa nao pode ser anterior ao inicio do projeto
                        validar_criacao_depois_inicio(criacao, projeto)

                        tarefas.append(nova_tarefa)
                    except (ValueError, ValidationError) as erro:
                        motivo = "tarefa invalida: " + str(erro)

            if motivo != "":
                linhas_ignoradas = linhas_ignoradas + 1
                self.stdout.write(
                    self.style.WARNING("Linha " + str(numero) + " ignorada: " + motivo)
                )

        # 3) Gravacao: tudo ou nada
        # Obs.: bulk_create nao chama save()/full_clean(). Isso e proposital: o arquivo traz
        # historico (projetos ja fechados e com inicio no passado), que as regras de criacao
        # de novos registros (projeto inicia a partir de hoje, tarefa so em projeto aberto)
        # recusariam. Os dados ja foram validados linha a linha acima.
        with transaction.atomic():
            if options["limpar"]:
                Tarefa.objects.all().delete()
                Projeto.objects.all().delete()
            Projeto.objects.bulk_create(list(projetos.values()))
            Tarefa.objects.bulk_create(tarefas)

        self.stdout.write(self.style.SUCCESS("Importacao concluida."))
        self.stdout.write("Linhas lidas: " + str(len(linhas)))
        self.stdout.write("Projetos importados: " + str(len(projetos)))
        self.stdout.write("Tarefas importadas: " + str(len(tarefas)))
        self.stdout.write("Linhas so com projeto (sem tarefa): " + str(linhas_so_projeto))
        self.stdout.write("Linhas ignoradas: " + str(linhas_ignoradas))