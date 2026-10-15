# OutSystems: Agentic Systems Engineering e Enterprise Context Graph

Nota de conhecimento consolidada em 2026-10-15 a partir de fontes públicas (press releases,
blog OutSystems, documentação ODC, cobertura de imprensa). A página oficial
https://www.outsystems.com/platform/agentic-systems-engineering não pôde ser lida directamente
(bloqueada pela rede da sessão). Marcar como CONFIRMADO só o que vem de fonte OutSystems.

## Contexto de quem usa esta nota

- João Carreiro, Indigo (Diligent Consulting), Luxemburgo. Indigo é OutSystems Gold Partner.
  Indigo implementa soluções com OutSystems. Indigo = "nós".
- Oportunidade: POST Luxembourg, app de digital banking "eboo", hoje em Apache Cordova.
- Incumbente provável: Intec, parceira da POST, equipa React Native. É quem deverá ganhar
  a modernização mobile.
- Posicionamento desejado pela Indigo: solução COMPLEMENTAR à equipa React Native da Intec.
  Nunca "ou eles ou nós". Argumentos devem somar valor, não contrapor.
- Backend da POST: core banking Infosys Finacle, em arquitectura headless. Frontend fala
  com BFF / API gateway (REST). Gateway fala com Finacle via REST, gRPC (Finacle Flex
  microservices), SOAP (Finacle Integrator) e standards BIAN / ISO 20022. CQRS com
  "silver copy" (FEEM) para leituras. Eventos via Kafka, push ao frontend via WebSockets.

## Cronologia (CONFIRMADO, fontes OutSystems e press releases)

- 2026-03-31: OutSystems anuncia "Agentic Systems Engineering", assente no Enterprise
  Context Graph e na nova geração do Mentor. Early access no Q2 2026.
- 2026-06-02/03 (ONE Conference, Amesterdão): "Agentic Systems Platform", powered by the
  Enterprise Context Graph. Camada "Agent Experience" (ferramentas MCP e A2A).
  "Agentic Enterprise Orchestration" = próxima geração do Agent Workbench, com Amazon Bedrock.
  Integração com Kiro (AWS) e análise de legados com AWS Transform (ambos em EAP / preview).
  "Legacy Modernization Services": converte COBOL e Lotus Notes em apps OutSystems (preview);
  página de parceria AWS também lista Java e .NET como alvos.
- 2026-10-07: "Agent Experience" fica GA (World Tour Las Vegas). Abre a plataforma e o
  Context Graph a qualquer coding agent: Claude Code, Cursor, Codex, Kiro.

## O que é o Enterprise Context Graph (CONFIRMADO em termos gerais)

- Grafo de conhecimento persistente e auto-actualizado do "application estate" de uma
  organização: aplicações, dados, workflows, agentes e as relações entre eles.
- Construído a partir dos metadados da plataforma OutSystems ("two decades of platform
  metadata intelligence"). Vive no ODC (documentação em ODC > Agentic development).
- Serve de camada de contexto e guardrails para agentes (Mentor e agentes externos).
- É exposto a agentes externos pelo Agent Experience, em três categorias de serviços em
  linguagem natural via MCP:
  1. Context Services: o agente consulta o estate, schemas e relações antes de gerar ou
     alterar código.
  2. Platform Services: o agente dispara deploy, rollback e validações de qualidade, sob
     fluxos de aprovação do ODC Portal.
  3. Terceira categoria: não confirmada nas fontes (provavelmente operações / agentes).
- Governança: logging, tracing, identity propagation, approval gates, audit trail.
- Também existe o OutSystems MCP (GA em todos os tenants ODC) e o O11 MCP (Service Studio,
  local; leitura GA, escrita em beta) para Claude Code, Cursor, Copilot, Kiro.

## O que NÃO está confirmado (verificar com a OutSystems antes de prometer)

- Se o Context Graph indexa código que não é OutSystems (React Native, Java, .NET de um BFF).
  As fontes descrevem o estate OutSystems. A análise de legado externo vem via AWS Transform
  (COBOL, Java) em EAP, e alimenta o Mentor para gerar apps OutSystems, não código externo.
- Onde corre o Context Graph em ODC Self-Hosted (ver secção abaixo). Provavelmente no control
  plane OutSystems, não no cluster do cliente. Confirmar com a OutSystems.
- Disponibilidade do Context Graph / Agent Experience em O11 self-managed: não confirmada.
  Tudo o que é publicado aponta para ODC. O11 tem só o O11 MCP local (Service Studio).
- Suporte a JavaScript / Cordova como fonte de legacy analysis: não encontrado.

## Opções de deployment ODC (CONFIRMADO, 2026-10)

- ODC "clássico": SaaS gerido pela OutSystems em AWS. Regiões UE: Frankfurt, Irlanda, Londres.
  Escolha de região para residência de dados.
- ODC Self-Hosted (anunciado 2026-03-31): apps, dados e agentes correm no Kubernetes do
  cliente (on-prem, cloud privada ou pública). Os serviços de plataforma (build, deploy,
  portal, gestão) continuam geridos pela OutSystems. É um modelo híbrido: runtime no cliente,
  control plane na OutSystems. Não é "on-prem" no sentido O11.
- Soberania UE: parceria com StackIT (Schwarz Group) e "outros fornecedores de cloud soberana
  UE a seguir", segundo a OutSystems.
- Terminologia correcta para a POST: "ODC Self-Hosted", nunca "ODC self-managed" nem
  "on-premise ODC". "Self-managed" é vocabulário O11.
- A proposta eboo fala em "on-premise OutSystems Context Graph": substituir por
  "ODC Self-Hosted, runtime e dados em infraestrutura POST no Luxemburgo, control plane
  OutSystems em região UE". Confirmar com a OutSystems onde corre o Context Graph nesse modelo.

## Mensagem do champion POST (2026-10-15)

- Champion: Data Governance and Digital Program Manager da POST. A proposta eboo publicada
  no ai.studio foi gerada pela IA dele ("l'approche imaginée par mon IA"). Logo, as
  incoerências (on-prem Context Graph, O11/ODC, Cordova como legacy backend) são dele, não
  da Indigo. Corrigir com tacto, sem o contradizer publicamente.
- Condição que ele põe: relevância da OutSystems depende do "support des frameworks Apache
  Cordova, React Native 0.76 et React 19". Resposta técnica: OutSystems não executa nem gera
  esses frameworks; relaciona-se com eles por APIs REST (framework-agnóstico) e, ao nível dos
  agentes, pelo MCP / Agent Experience consultado pelo Claude Code ou Cursor dos devs React
  Native. Mentor gera apps OutSystems, não código React Native.
- Ele vai abordar o conceito numa sexta-feira (2026-10-17) e, havendo interesse, marca
  reunião para descrever a situação. Não contornar as primeiras conversas com Fabrice C.
  Retorno previsto na semana de 2026-10-20.

## Implicações práticas para o caso eboo / POST

- O Context Graph só dá contexto sobre o que existe em OutSystems. Se a POST não tiver nada
  em OutSystems, o grafo está vazio e "Claude Code grounded by the Context Graph" não
  acrescenta nada ao código React Native da Intec.
- Logo, a jogada complementar da Indigo é construir a camada que VIVE em OutSystems e que
  passa a ser o conteúdo do grafo: entidades e contratos que mapeiam os 40+ endpoints
  Finacle, experience APIs tipadas (OpenAPI) para a app React Native, workflows longos
  (onboarding, crédito, disputas), back-office Tier-3, e agentes (Agent Workbench).
- A Intec continua dona da UI nativa. Os seus devs com Claude Code / Cursor consultam o
  Context Graph via MCP para obter contratos e schemas antes de gerar ecrãs.
- Platform Services (deploy, rollback, quality gates) governam artefactos OutSystems, não o
  repositório React Native da Intec. O SAST / CI deles continua a ser deles.

## Integrações ODC relevantes (estado em 2026-10)

- REST: nativo (consumir e expor). SOAP: nativo para consumir. BIAN / ISO 20022: só payloads.
- gRPC: NÃO suportado nativamente (nem O11). Opções: fachada REST no gateway (MuleSoft,
  Apigee, Envoy transcoder) ou External Logic em C# com cliente gRPC para chamadas unárias.
  No desenho da POST o gRPC fica entre gateway e Finacle Flex; o frontend nunca o usa.
- Kafka: sem consumer nativo. Forge "Kafka Connector (ODC)" faz polling, não suportado.
  Padrão: Kafka Connect HTTP sink a chamar REST exposto pelo ODC.
- WebSockets: sem suporte nativo. Push via Firebase / APNs, ou Forge "PubSub WebSocket (ODC)"
  sobre Azure Web PubSub.
- Bases externas: ODC lê Oracle, SQL Server, PostgreSQL, etc. Pode ler a "silver copy" FEEM.
- Apps mobile OutSystems (O11 e ODC) são híbridas via MABS (Cordova / WebView). Não
  entregam "native 60fps" face a React Native.

## Fontes

- https://www.outsystems.com/low-code-platform/agentic-systems-engineering
- https://www.outsystems.com/blog/posts/enterprise-ai-future
- https://www.businesswire.com/news/home/20260331236008/en/OutSystems-Introduces-Agentic-Systems-Engineering-to-Power-Governed-Open-Enterprise-AI
- https://www.outsystems.com/news/outsystems-announces-agentic-systems-platform
- https://www.businesswire.com/news/home/20260602075123/en/OutSystems-Announces-New-AI-Capabilities-with-AWS-to-Deliver-Agentic-Systems-for-the-Enterprise
- https://www.outsystems.com/blog/posts/outsystems-q2-2026-innovation-lookback
- https://www.outsystems.com/news/outsystems-launches-agent-experience
- https://www.outsystems.com/blog/posts/coding-agents-legacy-system-modernization
- https://www.outsystems.com/platform/agent-experience
- https://www.outsystems.com/blog/posts/agentic-guardrails-and-context
- https://www.outsystems.com/blog/posts/outsystems-enterprise-agentic-ai-governance
- https://success.outsystems.com/documentation/outsystems_developer_cloud/agentic_development/architecture/
- https://success.outsystems.com/documentation/outsystems_developer_cloud/agentic_development/outsystems_mcp/
- https://github.com/OutSystems/outsystems-mcp
- https://github.com/OutSystems/outsystems11-mcp
- https://www.outsystems.com/partners/technology-alliance/aws
