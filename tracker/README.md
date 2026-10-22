# Tracker: localização de crianças em Maisons Relais (protótipo)

Protótipo para responder a um problema concreto, identificado pelo diretor de uma Maison
Relais em Mersch (cerca de 300 crianças): **não se sabe, a cada momento, onde está cada
criança**, nem se falta alguma.

A solução usa uma pulseira BLE (Bluetooth Low Energy) por criança e recetores baratos
em cada sala, corredor e zona exterior. O sistema não calcula coordenadas exatas: diz
**em que zona** está cada criança. Confundir de vez em quando duas salas vizinhas é
aceitável. O que importa é:

- ver quem está onde, por piso e por zona;
- receber alertas de criança **não detetada** há X minutos;
- receber alertas de criança **na zona de saída**;
- saber quantas crianças estão **dentro** do edifício e quantas no exterior, para uma
  evacuação.

Esta pasta contém o primeiro passo: um **protótipo para montar em casa (4 pisos)**, que
corre também **sem hardware** em modo simulação.

## Arquitetura

```
Pulseiras BLE ──► Recetores ESP32 (ESPresense) ──► MQTT (Mosquitto) ──► tracker ──► Interface web / OutSystems
 (1 por criança)    (1+ por zona)                                      │
                                                                        ├─ motor de localização (zona por criança, alertas)
                                                                        ├─ SQLite (só eventos: entrou/saiu de zona, alertas)
                                                                        └─ API REST  (/api/..., /docs)
```

- **Motor** (`tracker/engine.py`): suaviza o sinal (RSSI) por recetor e escolhe a zona
  com o sinal mais forte. Só muda de zona quando a nova ganha por uma margem, durante
  alguns segundos e com várias leituras, para evitar saltos entre salas e entre pisos.
  Os parâmetros estão em `engine:` no ficheiro de configuração.
- **Vários pisos**: cada zona tem um piso. As lajes atenuam bastante o sinal, por isso o
  recetor do próprio piso tende a ganhar. As escadas são uma zona `transit` com recetor
  próprio.
- **Simulador** (`tracker/simulator.py`): gera crianças virtuais que se deslocam pela
  casa, com um modelo simples de sinal. Serve para testar a carga (300 crianças) e para a
  equipa de OutSystems e UX trabalhar já, sem hardware.
- **Dados guardados**: só eventos (mudanças de zona e alertas), nunca as leituras brutas.
  Por defeito são apagados ao fim de 7 dias (RGPD).

## Arrancar em simulação (sem hardware)

```bash
cd tracker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m tracker --config config/house.yaml --simulate 300
```

Abrir <http://localhost:8000> (interface) ou <http://localhost:8000/docs> (API).

Ou com Docker, incluindo o broker MQTT:

```bash
TRACKER_ARGS="--simulate 300" docker compose up -d --build
```

## Arrancar com hardware real

1. Comprar e montar o kit: ver [docs/hardware.md](docs/hardware.md).
2. `docker compose up -d --build` no computador que fica ligado (Raspberry Pi ou portátil).
3. Configurar cada ESP32 com o IP desse computador como servidor MQTT e o nome da zona
   como "Room".
4. Ligar as pulseiras. Os ids aparecem na interface em **Diagnóstico > Beacons não
   registados**. Copiá-los para `tags:` em `config/house.yaml` e reiniciar
   (`docker compose restart tracker`).

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `config/house.yaml` | Pisos, zonas, recetores, pulseiras e parâmetros do motor |
| `tracker/engine.py` | Motor de localização, eventos e alertas |
| `tracker/mqtt_source.py` | Leitura MQTT (formato ESPresense e formato genérico) |
| `tracker/simulator.py` | Simulador de crianças e de sinal |
| `tracker/api.py` | API REST e ciclos de fundo |
| `tracker/static/index.html` | Interface simples do protótipo |
| `docs/hardware.md` | Lista de compras, montagem e calibração |
| `docs/api.md` | Contrato da API para o desenvolvimento em OutSystems |
| `docs/ux-brief.md` | Contexto para a conversa com UX/UI |

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Inclui um teste ponta a ponta: com o simulador na casa de 4 pisos, o motor coloca as
crianças na zona certa em mais de 85 % das amostras. Com 300 crianças simuladas deu
cerca de 94 %, contando com o atraso natural depois de cada deslocação.

## Limitações conhecidas (é um protótipo)

- **Sem autenticação** na API nem no MQTT. Só deve correr na rede de casa.
- **Estado em memória**: um reinício esquece a zona atual (o histórico fica no SQLite).
- **Check-in automático** na primeira deteção. A saída (check-out) é manual, pela
  interface ou pela API.
- O simulador não substitui o teste real: corpos a bloquear o sinal, 300 pulseiras na
  mesma sala e grandes áreas exteriores só se validam na Maison Relais.
