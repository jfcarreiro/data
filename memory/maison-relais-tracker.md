# Projeto: localização de crianças em Maisons Relais (tracker)

Nota de contexto iniciada em 2026-10-22. Código e documentação em `tracker/`.

## Problema

- Diretor de uma Maison Relais em Mersch (cerca de 300 crianças): "nunca sabemos onde
  estão as crianças" (que sala, campo de futebol, pátio). Saber também se o número bate
  certo e se alguma saiu.
- Objetivo: solução tecnológica da Indigo. A interface final será em OutSystems, por
  alguém da equipa, em paralelo com o protótipo. UX/UI a envolver.

## Decisões até agora

- Tecnologia: **pulseiras BLE + recetores por zona** (não RFID UHF: leitores caros, o
  corpo absorve o sinal, não cobre o exterior; não UWB: caro; não câmaras/biometria: RGPD).
- Precisão por zona. **Confundir de vez em quando salas vizinhas é aceitável** (dito pelo
  João).
- Edifícios com vários pisos: suportado (zona com piso; escadas = zona `transit`).
- Primeiro passo: **protótipo em casa do João (4 pisos)**, com ESP32 + ESPresense +
  Mosquitto + motor em Python. Hardware ~180–400 €. Ainda não há Raspberry Pi (comprar,
  ou usar portátil).
- Ordem de grandeza na escola (300 crianças): ~8–15 k€ de hardware por Maison Relais.
- Pais: começar por notificações de entrada e saída, não localização em tempo real
  (RGPD, guarda parental). Localização de menores exige DPIA (CNPD).

## Valor adicional identificado

Contagem para evacuação, rácios de enquadramento (educadores com pulseira), presenças e
faturação do Chèque-Service Accueil, autorizações de recolha. Escala: gestores (ASBL,
comunas) com várias Maisons Relais.
