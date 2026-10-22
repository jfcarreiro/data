# Contexto para UX/UI

Este documento é ponto de partida para a conversa com UX/UI, não uma especificação. A
interface em `tracker/static/index.html` serve só para validar dados e fluxos. Não é uma
proposta visual.

## O problema, nas palavras do cliente

O diretor de uma Maison Relais em Mersch tem cerca de 300 crianças e diz que **nunca sabe
onde elas estão**: em que sala, no campo de futebol, no pátio. As crianças não fogem, mas
é crítico saber onde andam e se o número bate certo.

## Quem usa

| Perfil | Contexto | O que precisa |
|---|---|---|
| **Educador no terreno** | De pé, com o telemóvel ou tablet numa mão e crianças à volta. Ambiente barulhento e com interrupções | Saber em segundos se o seu grupo está completo e onde está a criança X. Ver e reagir a alertas |
| **Diretor / coordenação** | Gabinete ou em movimento | Visão geral do local: quantas crianças, onde, alertas abertos. Confiança de que está tudo bem |
| **Pais** *(fase 2, a decidir)* | Fora da Maison Relais | Provavelmente só notificações de entrada e saída, não localização em tempo real (RGPD, guarda parental, ansiedade) |

## Momentos-chave

1. **Início do dia ou chegada da escola**: as crianças vão chegando. Quem já está, quem
   falta?
2. **Procurar uma criança**: um pai chega para a buscar, ou um educador precisa dela.
   Onde está, agora?
3. **Alerta "não detetado"**: a criança deixou de ser ouvida (pode ter tirado a pulseira).
   Quem trata? Como se fecha o alerta?
4. **Alerta "na saída"**: uma criança está junto à porta de saída. A reação tem de ser
   imediata.
5. **Mudança de atividade**: um grupo passa da sala para o campo de futebol. A contagem
   bate certo?
6. **Evacuação ou simulacro**: quantas e quais crianças ainda estão dentro do edifício?
7. **Fim do dia**: registar saídas e confirmar que não fica nenhuma por sair.

## Dados disponíveis (ver `docs/api.md`)

- Por criança: nome, grupo, estado (ausente, presente, em falta, saiu), zona atual,
  piso, desde quando está na zona, última deteção e percurso do dia.
- Por zona: ocupação e lista de crianças. As zonas têm tipo: sala, transição (escadas),
  exterior, saída.
- Totais: presentes, dentro do edifício, no exterior, por piso, em falta.
- Alertas, com o estado "visto".

## Restrições a ter em conta

- **A precisão é por zona** e às vezes confunde salas vizinhas. A interface não deve
  prometer mais do que isso, por exemplo com pontos exatos num mapa.
- **Atraso** de alguns segundos depois de cada deslocação.
- **Dados de menores (RGPD)**: mostrar o mínimo necessário a cada perfil. O histórico de
  localização é apagado ao fim de poucos dias.
- Línguas no Luxemburgo: **francês, alemão e luxemburguês**, possivelmente português e
  inglês.

## Perguntas para UX/UI

- Mapa ou planta do edifício, ou listas e cartões por zona? O que é mais rápido para um
  educador?
- Como mostrar "o meu grupo" em vez das 300 crianças?
- Como dar o alerta para que seja visto no meio do barulho, sem banalizar (fadiga de
  alertas)?
- Que ecrã fica num tablet fixo à entrada ou no gabinete?
- Que modo especial faz sentido para a evacuação?
