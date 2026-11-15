# AutoCarrozzeria Di Girolamo – Ordens de Serviço

[![CI](https://github.com/marlonsevero-77/autocarrozzeria-ordens-servico/actions/workflows/ci.yml/badge.svg)](https://github.com/marlonsevero-77/autocarrozzeria-ordens-servico/actions/workflows/ci.yml)

MVP desenvolvido no Projeto de Software do curso de Análise e Desenvolvimento de Sistemas (ADS).

## O problema

Na AutoCarrozzeria Di Girolamo, oficina familiar de chapeação e pintura fundada em 1997, tudo o que é combinado com o cliente (tipo de atendimento, serviço e prazo) e o andamento de cada carro ficam apenas na memória da equipe. Com 4 a 5 carros passando por cinco etapas ao mesmo tempo, é difícil saber onde está cada carro, quem está com ele e quais estão perto do prazo.

## A solução (MVP)

Aplicação web que registra cada ordem de serviço e mostra, em um painel, a etapa e o responsável de cada carro.

| Requisito | Funcionalidade | Prioridade |
|---|---|---|
| RF01 | Login e logout, com bloqueio após tentativas repetidas | Obrigatório |
| RF02 | Cadastro da ordem de serviço, com busca do veículo pela placa | Obrigatório |
| RF03 | Avanço para a próxima etapa, com histórico e marcação de entrega | Obrigatório |
| RF04 | Painel com os carros em andamento por etapa | Obrigatório |
| RF05 | Alertas "Perto do prazo" (até 2 dias) e "Atrasado" | Desejável |
| RF06 | Pesquisa por placa com histórico completo | Desejável (próxima versão) |

**Usuário direto:** Riccardo, membro da equipe. **Beneficiados:** equipe, donos e clientes da oficina.
**ODS relacionado:** ODS 8 – Trabalho Decente e Crescimento Econômico (metas 8.2 e 8.3).

### Etapas da oficina

1. Desmontagem – Giuseppe
2. Alinhamento do reparo – Fabio
3. Fundo e massa – Filippo e Riccardo
4. Mascaramento e pintura – Davide
5. Revisão e montagem – Giuseppe

As etapas ficam em uma tabela própria e podem ser alteradas pelos donos no Django Admin, sem mudar o código.

## Arquitetura

Monolito em camadas no padrão **MVT do Django**:

```
config/              configurações (variáveis de ambiente), URLs e WSGI
oficina/
  models.py          entidades e regras ligadas aos dados (camada Model)
  forms.py           validação das entradas no servidor
  views.py           regras de negócio de cada tela (camada View)
  templates/         telas em HTML (camada Template)
  middleware.py      cabeçalho Content-Security-Policy
  tests/             testes unitários e de integração
templates/           layout base, login e páginas de erro
static/              CSS do projeto, Bootstrap e Bootstrap Icons
.github/workflows/   Integração Contínua (GitHub Actions)
```

**Modelo de dados:** Usuário (Django) · Cliente · Veículo · Etapa · Ordem de serviço · Histórico de etapa.

## Tecnologias

| Recurso | Versão | Uso |
|---|---|---|
| Python | 3.13 | Linguagem |
| Django | 5.2 LTS | Framework web (MVT, ORM, autenticação, Admin, testes) |
| PostgreSQL | 16 | Banco de dados (local e Neon) |
| psycopg | 3.3 | Driver do PostgreSQL |
| django-axes | 8.3 | Bloqueio por 15 min após 5 falhas de login |
| Gunicorn | 23 | Servidor de aplicação (Render) |
| WhiteNoise | 6.12 | Arquivos estáticos compactados |
| Bootstrap / Bootstrap Icons | 5.3 / 1.11 | Interface (servidos localmente) |
| GitHub Actions | – | Integração Contínua |

## Como rodar localmente

Pré-requisitos: Python 3.13 e PostgreSQL instalados.

```bash
git clone https://github.com/marlonsevero-77/autocarrozzeria-ordens-servico.git
cd autocarrozzeria-ordens-servico

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
# edite o .env: DEBUG=True, SECRET_KEY e dados do PostgreSQL

createdb oficina                 # ou crie o banco "oficina" pelo pgAdmin
python manage.py migrate         # cria as tabelas e as 5 etapas
python manage.py createsuperuser # usuário dos donos (acesso ao Admin)
python manage.py runserver
```

Acesse `http://127.0.0.1:8000`. Usuários da equipe são criados pelo Admin (`/admin/`).

### Dados fictícios para demonstração

```bash
python manage.py carregar_dados_demo --usuario NOME_DO_USUARIO
```

Cria cinco ordens fictícias (sem dados reais de clientes), incluindo um carro perto do prazo e um atrasado.

## Testes e Integração Contínua

```bash
python manage.py test
```

São 41 testes unitários e de integração, cobrindo:

- modelo de dados (placa única e normalizada, uma ordem em andamento por carro, prazos e alertas);
- login, mensagem genérica de erro, bloqueio após 5 tentativas, hash PBKDF2 e acesso ao Admin;
- cadastro (validações, reaproveitamento por placa, CSRF, injeção de SQL e XSS);
- avanço de etapa (histórico, entrega, POST obrigatório, CSRF, 404) e painel (alertas e número fixo de consultas).

A cada push e Pull Request, o **GitHub Actions** executa: `check`, verificação de migrações pendentes, todos os testes com PostgreSQL 16, `check --deploy` com configuração de produção e auditoria de dependências com `pip-audit`.

## Segurança

- Senhas armazenadas apenas como hash **PBKDF2-SHA256** com salt (nunca em texto ou MD5/SHA-1).
- Bloqueio de 15 minutos após 5 tentativas de login erradas (django-axes) e sessão de 8 horas.
- Todas as telas exigem login; alterações só por POST com token CSRF.
- Consultas pelo ORM (parametrizadas), validação no servidor e escape automático nos templates.
- Cabeçalho **Content-Security-Policy** restrito ao próprio domínio.
- Em produção: `DEBUG=False`, HTTPS obrigatório, cookies seguros, HSTS e segredos só em variáveis de ambiente.

## Implantação (Render + Neon)

1. Crie o banco PostgreSQL no **Neon** e copie a `DATABASE_URL`.
2. No **Render**, crie um Web Service a partir deste repositório (o `render.yaml` já define os comandos).
3. Defina as variáveis `SECRET_KEY` e `DATABASE_URL` no painel do Render.

Limites do plano gratuito do Render: o serviço é suspenso após 15 minutos sem acesso e leva cerca de um minuto para voltar.

## Fluxo de trabalho no Git

- `main` contém apenas código revisado e com CI aprovado.
- Cada funcionalidade é desenvolvida em um branch (`feat/...`, `fix/...`) e entra por **Pull Request** com checklist de auto-revisão.
- Commits seguem o padrão **Conventional Commits**: `feat`, `fix`, `test`, `docs`, `ci`, `chore`.

## Acessibilidade

Rótulos sempre visíveis, botões com área mínima de 44 × 44 px, foco visível, mensagens de erro com ícone e texto ao lado do campo, alertas de prazo que não dependem só da cor e layout responsivo.
