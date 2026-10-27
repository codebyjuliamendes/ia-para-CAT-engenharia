# SafeCAT AI

[![CI](https://github.com/codebyjuliamendes/ia-para-CAT-engenharia/actions/workflows/ci.yml/badge.svg)](https://github.com/codebyjuliamendes/ia-para-CAT-engenharia/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)

> **Projeto Campeão de Hackathon (SESMT & Indústria 4.0).**

Aplicação web para o SESMT registrar acidentes de trabalho com os dados que o evento
**S-2210 (CAT)** do eSocial exige, investigar a causa raiz (5 Porquês) com apoio de IA e
acompanhar indicadores de segurança.

O SafeCAT **não transmite** a CAT ao eSocial. O PDF que ele gera é um *documento auxiliar*.
A CAT oficial é o evento S-2210 que o empregador envia.

---

## Sumário

- [Problema](#problema)
- [Solução](#solução)
- [Fluxo](#fluxo)
- [IA real e modo demonstração](#ia-real-e-modo-demonstração)
- [Enquadramento eSocial (S-2210)](#enquadramento-esocial-s-2210)
- [Privacidade e LGPD](#privacidade-e-lgpd)
- [Como rodar](#como-rodar)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Arquitetura](#arquitetura)
- [Testes e qualidade](#testes-e-qualidade)
- [Limitações conhecidas](#limitações-conhecidas)

---

## Problema

- Preencher a CAT exige classificar parte do corpo, agente causador, situação geradora e
  natureza da lesão pelas tabelas do eSocial, além de transcrever o atestado (CID-10,
  emitente, dias de tratamento). Erros e atrasos geram retrabalho e penalidades.
- Depois do envio, muitas ocorrências não passam por uma investigação de causa raiz e pelo
  plano de ação, e a organização perde a chance de evitar um acidente mais grave.

## Solução

| Recurso | O que faz |
|---|---|
| Registro da CAT | Formulário com os principais campos do S-2210. Valida CPF e PIS/NIT pelos dígitos verificadores, formato de CID-10, conselho e UF do emitente, e a coerência das datas (nada no futuro; atendimento e óbito depois do acidente). |
| Pendências do S-2210 | Lista os campos que o leiaute exige e ainda faltam, sem impedir o registro interno. |
| Leitura do atestado | PDF com texto: lido com `pypdf`. Imagem ou PDF escaneado: lidos pela visão do LLM quando há chave configurada. Sem chave, o usuário digita os campos. Nenhum campo é preenchido sem vir do arquivo. |
| 5 Porquês + hierarquia de controles | Sugestão automática a partir do relato, que o SESMT edita, revisa e assina. |
| Histórico persistente | Banco SQL (SQLite por padrão, PostgreSQL suportado), CPF mascarado na listagem, exclusão definitiva. |
| Painel HSE | Indicadores calculados do banco: ocorrências por setor, parte do corpo, gravidade, tipo e mês; dias perdidos; mapa corporal; taxas de frequência e gravidade (NBR 14280) com as horas-homem que o usuário informa. |
| Documento auxiliar em PDF | Contém só os dados informados e validados; campo ausente sai como "não informado". Leva marca d'água e o rodapé "Documento auxiliar — a CAT oficial é transmitida pelo eSocial (S-2210)". O empregador vem da configuração. |

## Fluxo

```mermaid
flowchart TD
    A[Atestado: PDF ou imagem] -->|PDF com texto| B[pypdf: texto real do arquivo]
    A -->|imagem / PDF escaneado| C{Chave da IA configurada?}
    C -->|sim| D[Visão do LLM: transcrição estruturada]
    C -->|não| E[Usuário digita os campos]
    B --> F[Campos pré-preenchidos para conferência]
    D --> F
    E --> F
    F --> G[Formulário da CAT + validações de domínio]
    R[Relato da ocorrência] --> H{Provedor de análise}
    H -->|LLM| I[5 Porquês + controles: JSON validado, evidências conferidas no relato]
    H -->|demonstração| J[Perguntas dos 5 Porquês + controles genéricos para verificar]
    I --> K[Revisão e edição pelo SESMT]
    J --> K
    G --> L[(Banco SQL)]
    K --> L
    L --> M[Histórico com CPF mascarado]
    L --> N[Painel HSE]
    L --> O[PDF: documento auxiliar]
    O -.->|transmissão oficial fora do sistema| P[eSocial S-2210]
```

## IA real e modo demonstração

O provedor é escolhido na inicialização (`safecat.ai.build_analyzer`). Os dois seguem a
interface `Analyzer` e a UI e o PDF sempre informam qual deles gerou a sugestão.

**LLM real (com `ANTHROPIC_API_KEY`)**

- Usa o SDK oficial `anthropic` com o modelo `claude-opus-5-5` por padrão (configurável em
  `SAFECAT_LLM_MODEL`).
- A saída é estruturada: um JSON Schema gerado a partir dos modelos Pydantic, validado na
  volta.
- A chamada tem timeout e um número limitado de novas tentativas (o SDK repete 408/409/429/5xx
  e falhas de conexão). Recusas, truncamentos e respostas fora do schema viram mensagens claras
  na tela, sem expor o relato.
- O fallback no servidor (`fallbacks: "default"`) fica ligado e reenvia a outro modelo uma
  solicitação recusada pelo modelo principal. Para desligar: `SAFECAT_LLM_SERVER_FALLBACK=false`.
- Mitigação de prompt injection:
  - o prompt de sistema é fixo;
  - o relato e o atestado vão em blocos delimitados e são tratados como dados;
  - delimitadores que aparecem no texto do usuário são neutralizados;
  - toda "evidência" que a IA cita é conferida contra o relato. Se o trecho não estiver lá, a
    resposta daquele nível é descartada.

**Modo demonstração (sem chave)**

- É determinístico e não usa rede.
- Monta as perguntas dos 5 Porquês **sem respondê-las** e não propõe causa raiz.
- Aponta lacunas do relato (horário, local, EPI, testemunhas, tarefa...).
- Sugere controles genéricos pela hierarquia (eliminação → EPI), escritos como itens a
  verificar. Cada sugestão cita a palavra do relato que a motivou.
- Fica rotulado na barra lateral, na análise e no PDF.

Em qualquer modo, a análise é **sugestão automática** e precisa da revisão do SESMT. O
registro guarda se ela foi revisada e por quem.

## Enquadramento eSocial (S-2210)

### O que foi confirmado e onde

A referência é o schema oficial do evento S-2210, `evtCAT.xsd`, do leiaute **S-1.3** (pacote
de schemas do eSocial). Ele foi consultado no espelho público mantido em
[`nfephp-org/sped-esocial`](https://github.com/nfephp-org/sped-esocial/tree/master/schemes/v_S_01_03_00),
porque o portal gov.br não estava acessível no ambiente de desenvolvimento. As versões S-1.0,
S-1.1 e S-1.2 têm as mesmas referências de tabela.

| Campo do S-2210 | Tabela exigida pelo schema |
|---|---|
| `parteAtingida/codParteAting` | **Tabela 13** (parte do corpo atingida), mais `lateralidade` (0 não aplicável, 1 esquerda, 2 direita, 3 ambas) |
| `agenteCausador/codAgntCausador` | **Tabela 14** se `dtAcid` ≥ 22/01/2024 e o tipo for típico ou trajeto; **Tabela 14 ou 15** se o acidente for anterior ou o tipo for doença |
| `codSitGeradora` | **Tabela 15**, segundo a documentação do XSD (ver nota abaixo) |
| `atestado/dscLesao` (natureza da lesão) | **Tabela 17** |
| `atestado/codCID` | CID-10, 3 ou 4 caracteres, sem ponto (ex.: `S52`, `S525`) |

Todos os códigos das Tabelas 13 a 17 têm 9 dígitos numéricos. O sistema também segue os
domínios do schema para `tpCat` (1 inicial, 2 reabertura, 3 óbito), `tpAcid` (1 típico,
2 doença, 3 trajeto), `tpLocal`, `ideOC` (CRM/CRO/RMS) e as regras de hora do acidente, óbito
e datas.

A versão anterior deste projeto chamava a parte do corpo de "Tabela 24" e usava códigos
como `100000000`. As duas coisas estavam erradas e foram removidas.

### O que precisa de validação

> ⚠️ **As tabelas 13, 14, 15, 16 e 17 vêm vazias.** Não consegui confirmar o conteúdo
> oficial (códigos e descrições) em fonte primária, e um código inventado geraria uma CAT
> errada. Enquanto a tabela não for importada, a tela pede o código de 9 dígitos e a descrição
> conforme a tabela oficial vigente.

- **Conteúdo das tabelas:** importe a versão oficial vigente (instruções abaixo).
- **Tabela 16 e situação geradora:** a documentação do XSD S-1.3 cita a Tabela 15 para
  `codSitGeradora`. Materiais de apoio costumam chamar a Tabela 16 de "situação geradora do
  acidente de trabalho". O campo aceita as duas, e os títulos em `TabelaESocial.titulo`
  precisam ser conferidos com o MOS/leiaute vigente.
- **CID-10:** o arquivo `src/safecat/data/cid10/cid10.csv` (14.233 categorias e subcategorias)
  foi convertido para UTF-8 a partir dos CSVs da CID-10 do DATASUS (versão 2008), obtidos no
  espelho [`cleytonferrari/CidDataSus`](https://github.com/cleytonferrari/CidDataSus). As
  descrições dos códigos mais usados no projeto foram conferidas nesse arquivo:

  | Código | Descrição |
  |---|---|
  | S52 | Fratura do antebraço |
  | S62 | Fratura ao nível do punho e da mão |
  | S93 | Luxação, entorse e distensão das articulações e dos ligamentos ao nível do tornozelo e do pé |
  | T20 | Queimadura e corrosão da cabeça e pescoço |
  | S09 | Outros traumatismos da cabeça e os não especificados |
  | M75 | Lesões do ombro |
  | S53 | Luxação, entorse e distensão das articulações e dos ligamentos do cotovelo |
  | T14 | Traumatismo de região não especificada do corpo |

  Ainda falta comparar o arquivo com a publicação vigente do DATASUS.

### Como importar uma tabela oficial

1. Na [documentação técnica do eSocial](https://www.gov.br/esocial/pt-br/documentacao-tecnica),
   abra as *Tabelas do eSocial* do leiaute vigente.
2. Copie a tabela para uma planilha com duas colunas, `codigo` e `descricao`, e exporte como
   CSV com `;` como separador e codificação UTF-8:
   ```
   codigo;descricao
   <código de 9 dígitos>;<descrição oficial>
   ```
3. Importe. O comando valida os códigos antes de gravar:
   ```bash
   uv run safecat import-table 13 tabela13.csv --destino ./data-local/tabelas
   export SAFECAT_TABLES_DIR=./data-local/tabelas
   ```
   No Docker, o diretório padrão é `/data/tabelas`, dentro do volume:
   ```bash
   docker compose run --rm --entrypoint safecat -v "$PWD/tabela13.csv:/tmp/t.csv:ro" safecat import-table 13 /tmp/t.csv
   ```
4. Depois de validar, você pode versionar a tabela em `src/safecat/data/esocial/tabelaNN.csv`,
   no mesmo formato. Com a tabela carregada, o formulário passa a buscar por texto, sem
   diferenciar acentos.

## Privacidade e LGPD

CPF, nome e PIS são dados pessoais. CID, atestado e relato da lesão são **dados pessoais
sensíveis** (art. 11 da Lei 13.709/2018).

- **Minimização na tela:**
  - a listagem do Histórico mostra o CPF mascarado (`***.456.789-**`) e não mostra relato nem
    CID;
  - CPF completo, relato e CID só aparecem quando o usuário liga a opção, registro a registro;
  - os indicadores usam colunas que não identificam o trabalhador.
- **Logs:** registram apenas IDs. O código não registra relato, CID nem atestado, e um filtro
  mascara qualquer CPF que apareça numa mensagem.
- **Exclusão:** o Histórico permite excluir um registro definitivamente. No SQLite,
  `secure_delete` fica ligado.
- **Retenção:** é a organização que define, com base na sua obrigação legal de guarda. Para
  configurar:
  1. defina `SAFECAT_RETENTION_DAYS` com o número de dias;
  2. agende `safecat purge` (por exemplo, num CronJob), que exclui CATs com acidente mais
     antigo que esse prazo.

  O padrão é `0`, ou seja, sem expurgo automático.
- **IA:** com a chave configurada, o relato e o atestado enviados para análise vão para a API
  da Anthropic. Antes de habilitar, confirme a base legal, o contrato e a política de retenção
  do provedor. Sem chave, nada sai do servidor.
- **Infraestrutura (responsabilidade de quem implanta):**
  - criptografia do volume ou do banco em repouso;
  - HTTPS no Ingress ou proxy;
  - autenticação na frente da aplicação. O Streamlit não autentica usuários, então use SSO, um
    proxy com OIDC ou uma rede restrita.

## Como rodar

### Local (uv)

```bash
uv sync                      # Python 3.12+, dependências do uv.lock
uv run safecat migrate       # cria/atualiza o banco (o app também migra ao iniciar)
uv run streamlit run streamlit_app.py
```

Abra <http://localhost:8501>. Sem `ANTHROPIC_API_KEY`, o app abre em modo demonstração. Para
configurar, copie `.env.example` para `.env`.

### Docker

```bash
docker compose up --build
```

Abra <http://localhost:8502>. A imagem é multi-stage (uv → `python:3.12-slim`), roda com
usuário sem privilégios (UID 10001) e guarda os dados no volume `/data`. O contêiner aplica as
migrações ao iniciar e tem `HEALTHCHECK` em `/_stcore/health`. O compose não monta o código,
usa sistema de arquivos read-only e tmpfs para `/tmp`.

### Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml
kubectl -n safecat create secret generic safecat-secrets --from-literal=ANTHROPIC_API_KEY=...   # opcional
kubectl apply -k k8s/
kubectl -n safecat port-forward svc/safecat 8502:80
```

- O deployment roda **1 réplica** com estratégia `Recreate`, porque o SQLite fica num PVC
  `ReadWriteOnce`.
- O contêiner roda sem root, com root filesystem read-only, sem capabilities e com seccomp
  `RuntimeDefault`. Tem probes de startup, readiness e liveness.
- A chave da API vem de um Secret que não é versionado (há um exemplo em
  `k8s/secret.example.yaml`).
- Para mais de uma réplica, aponte `SAFECAT_DATABASE_URL` para um PostgreSQL. A imagem já
  inclui o `psycopg`. Configure também afinidade de sessão no Ingress, porque o Streamlit
  mantém estado por conexão.
- Antes de implantar, ajuste a imagem em `k8s/deployment.yaml` para o registry e a tag que
  vocês usam.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SAFECAT_DATABASE_URL` | `sqlite:///./safecat.db` (Docker: `sqlite:////data/safecat.db`) | URL SQLAlchemy. PostgreSQL: `postgresql+psycopg://usuario:senha@host/db` |
| `SAFECAT_TABLES_DIR` | — (Docker: `/data/tabelas`) | Diretório com tabelas eSocial importadas, que sobrepõem as empacotadas |
| `ANTHROPIC_API_KEY` | — | Habilita a IA. Sem ela, o app roda em modo demonstração |
| `SAFECAT_LLM_MODEL` | `claude-opus-5-5` | Modelo usado |
| `SAFECAT_LLM_EFFORT` | `medium` | `low`, `medium`, `high`, `xhigh` ou `max` |
| `SAFECAT_LLM_TIMEOUT_SECONDS` | `60` | Timeout por requisição |
| `SAFECAT_LLM_MAX_RETRIES` | `2` | Novas tentativas automáticas (0–5) |
| `SAFECAT_LLM_MAX_TOKENS` | `8000` | Limite de saída |
| `SAFECAT_LLM_SERVER_FALLBACK` | `true` | Fallback no servidor quando o modelo recusa |
| `SAFECAT_FORCE_DEMO` | `false` | Força o modo demonstração mesmo com chave |
| `SAFECAT_EMPREGADOR_RAZAO_SOCIAL`, `_CNPJ`, `_CNAE`, `_ENDERECO` | — | Empregador impresso no PDF. O CNPJ é validado |
| `SAFECAT_RETENTION_DAYS` | `0` | Retenção usada por `safecat purge` |
| `SAFECAT_LOG_LEVEL` | `INFO` | Nível de log |

## Arquitetura

```
streamlit_app.py            entrada do Streamlit
src/safecat/
├── domain/                 modelos Pydantic v2 da CAT (S-2210) e validadores (CPF, PIS, CNPJ, CID, UF)
├── esocial/                carga das tabelas (CSV versionado ou importado) e busca sem acentos
├── ai/                     Analyzer (Protocol); AnthropicAnalyzer (LLM); DemoAnalyzer; extração do atestado
├── store/                  SQLAlchemy 2 + Alembic (migrations/), repositório com minimização de dados
├── pdf/                    documento auxiliar em PDF (ReportLab)
├── analytics.py            indicadores do painel (funções puras)
├── cli.py                  safecat migrate | import-table | purge
├── data/                   tabelas eSocial (vazias até a importação) e CID-10
└── ui/                     páginas Streamlit (sem HTML customizado)
```

A regra de negócio fica fora da UI. As páginas só coletam dados, chamam o domínio e o
repositório e exibem o resultado. O tema claro e o escuro são definidos em
`.streamlit/config.toml` e seguem a preferência do sistema.

## Testes e qualidade

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest
```

- **Domínio:** validações de CPF, PIS/NIT, CNPJ, CID-10, datas, óbito e pendências do S-2210.
  Cobertura de 100%.
- **Tabelas:** carga, importação e busca. Também conferem as descrições da CID-10.
- **Modo demonstração:** confirma que nenhuma causa é inventada.
- **Analisador LLM:** usa o SDK real com transporte HTTP simulado (`httpx2.MockTransport`) e
  **nunca chama a rede**. Cobre o formato da requisição, os erros 4xx/5xx, as novas tentativas,
  timeout, recusa, truncamento, schema inválido, prompt injection e evidências fora do relato.
- **Repositório:** migrações, minimização de dados, exclusão, expurgo e logs sem CPF ou relato.
- **PDF:** gera bytes válidos com e sem campos opcionais, sem dados fictícios e escapando a
  marcação digitada pelo usuário.
- **UI:** fluxos principais com o `AppTest` do Streamlit.
- **CI (GitHub Actions):** roda ruff, mypy `--strict` e pytest em Python 3.12 e 3.13. Depois
  faz o build da imagem e um smoke test (health, migração, usuário não-root, raiz read-only).
  A cobertura mínima é de 85%.

## Limitações conhecidas

- Não gera o XML nem transmite o S-2210. O documento auxiliar não substitui a CAT oficial.
- As tabelas 13 a 17 do eSocial precisam ser importadas da fonte oficial (ver
  [O que precisa de validação](#o-que-precisa-de-validação)).
- A leitura de atestados sem IA usa regras simples sobre o texto do PDF. Imagens e PDFs
  escaneados precisam da IA ou de digitação manual.
- O mapa corporal agrupa as ocorrências por palavras da descrição da parte atingida. É uma
  aproximação visual, e o código exato continua no registro.
- As taxas de frequência e gravidade dependem das horas-homem que o usuário informa e
  consideram todos os registros do banco, sem filtro de período.
- Não há autenticação nem controle de acesso na aplicação. Proteja o acesso na
  infraestrutura.
- Os campos do grupo `ideVinculo`, a CAT de origem (`nrRecCatOrig`) e o endereço completo do
  local (CEP, código IBGE) ainda não estão no formulário.
- A licença (MIT) está declarada no `pyproject.toml`, mas falta adicionar o arquivo `LICENSE`.
