# AutoCarrozzeria Di Girolamo – Ordens de Serviço

MVP desenvolvido no Projeto de Software do curso de Análise e Desenvolvimento de Sistemas (ADS).

O sistema organiza as ordens de serviço de uma oficina familiar de chapeação e pintura. Hoje, tudo o que é combinado com o cliente e o andamento de cada carro ficam apenas na memória da equipe. O MVP registra cada ordem de serviço e mostra, em um painel, em que etapa está cada carro, quem é o responsável e quais carros estão perto do prazo ou atrasados.

**ODS relacionado:** ODS 8 – Trabalho Decente e Crescimento Econômico (metas 8.2 e 8.3).

> Projeto em desenvolvimento. As funcionalidades são adicionadas por Pull Requests.

## Tecnologias

| Recurso | Versão | Uso |
|---|---|---|
| Python | 3.13 | Linguagem |
| Django | 5.2 LTS | Framework web (padrão MVT) |
| PostgreSQL | 16 | Banco de dados (local e Neon) |
| psycopg | 3.2 | Driver do PostgreSQL |
| django-axes | 8.x | Bloqueio após tentativas de login |
| Gunicorn | 23 | Servidor de aplicação (Render) |
| WhiteNoise | 6.x | Arquivos estáticos |
| Bootstrap / Bootstrap Icons | 5.3 / 1.11 | Interface |
| GitHub Actions | – | Integração Contínua |
