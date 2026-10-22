# API para OutSystems

A interface final será feita em OutSystems, em paralelo com o protótipo. Este documento é
o contrato entre os dois lados. A especificação OpenAPI gerada automaticamente está em
`/openapi.json`, e a documentação interativa em `/docs`.

## Como trabalhar já, sem hardware

Correr o tracker em simulação. Gera 300 crianças que se deslocam, alertas de "não
detetado" e de "saída":

```bash
python -m tracker --config config/house.yaml --simulate 300
```

O OutSystems (cloud) precisa de chegar à API. Durante o protótipo há duas opções:

- correr a simulação numa VM pequena com IP público;
- expor o portátil com um túnel (por exemplo Cloudflare Tunnel ou ngrok).

A API **ainda não tem autenticação**, por isso só se usa com dados simulados.

Notas para o import no OutSystems:

- O FastAPI gera **OpenAPI 3.1**. Se o import do Service Studio/ODC não aceitar o
  ficheiro, criar os métodos à mão a partir dos exemplos abaixo.
- Todos os tempos (`ts`, `last_seen`, `zone_since`) estão em **segundos Unix (UTC)**.
- O protótipo atualiza por polling a cada 2 s. Em OutSystems, polling de 2–5 s é
  suficiente para começar.

## Endpoints

### `GET /api/site`

Estrutura do local: pisos, zonas e recetores. Pedir uma vez no arranque.

```json
{
  "name": "Casa (protótipo)",
  "floors": [{ "id": 0, "name": "Piso 0" }],
  "zones": [{ "id": "sala", "name": "Sala", "floor": 0, "kind": "room" }],
  "gateways": [{ "id": "sala", "zone": "sala" }]
}
```

`kind`: `room` | `transit` (escadas, corredores entre pisos; `floor` = null) | `outdoor` |
`exit`.

### `GET /api/children?q=&status=`

Lista de crianças com a zona atual. `q` filtra pelo nome (contém, sem distinguir
maiúsculas). `status` filtra pelo estado.

```json
[{
  "tag_id": "iBeacon:e2c5...-1-1",
  "name": "Manuel",
  "group": "Grupo A",
  "status": "present",
  "zone": "sala",
  "zone_name": "Sala",
  "floor": 0,
  "zone_since": 1792674508.7,
  "last_seen": 1792674685.1
}]
```

`status`:

| Valor | Significado |
|---|---|
| `absent` | Ainda não detetada hoje |
| `present` | No local |
| `missing` | Estava presente e deixou de ser ouvida (gera alerta) |
| `checked_out` | Saída registada |

### `GET /api/children/{tag_id}`

Uma criança, no mesmo formato. Devolve 404 se não existir. Codificar o `tag_id` no URL,
porque pode conter `:`.

### `GET /api/children/{tag_id}/events?limit=100`

Percurso da criança: eventos mais recentes primeiro (ver `/api/events`).

### `POST /api/children/{tag_id}/checkout`

Regista a saída. A criança deixa de ser seguida e de gerar alertas. Devolve a criança.

### `POST /api/children/{tag_id}/reset`

Volta a `absent`, e a próxima deteção faz check-in. Devolve a criança.

### `GET /api/zones`

Ocupação por zona, para o ecrã "por piso".

```json
[{
  "id": "sala", "name": "Sala", "floor": 0, "kind": "room", "count": 12,
  "children": [{ "tag_id": "...", "name": "Manuel", "status": "present" }]
}]
```

### `GET /api/headcount`

Totais para o cabeçalho e para o modo evacuação.

```json
{
  "registered": 300, "absent": 0, "present": 295, "missing": 5, "checked_out": 0,
  "inside": 249, "outdoor": 46,
  "by_floor": { "0": 136, "1": 89, "2": 32, "3": 42, "transit": 3 }
}
```

### `GET /api/alerts?active=true`

Alertas ativos, ou todos com `active=false`. Um alerta deixa de estar ativo quando é
marcado como visto ou quando se resolve sozinho: a criança voltou a ser detetada, ou saiu
da zona de saída.

```json
[{
  "id": 7, "ts": 1792674592.8, "kind": "missing",
  "tag_id": "...", "name": "Manuel", "zone": "cozinha",
  "acked": false, "resolved": false
}]
```

`kind`: `missing` (não detetada há `missing_after_s` segundos; `zone` é a última zona
conhecida) | `exit` (detetada numa zona `exit`).

### `POST /api/alerts/{id}/ack`

Marca o alerta como visto. Devolve `{ "ok": true }`, ou 404.

### `GET /api/events?since=&limit=200`

Registo de eventos, mais recentes primeiro. `since` (segundos Unix) devolve só os
eventos posteriores, útil para polling incremental. Máximo de 1000 por pedido.

```json
[{
  "id": 1933, "ts": 1792674621.6, "type": "zone_enter",
  "tag_id": "...", "name": "Mia", "zone": "escritorio", "from_zone": "quarto1"
}]
```

`type`: `checked_in`, `zone_enter` (com `from_zone`), `zone_exit`, `missing`, `found`,
`alert` (com `alert_id` e `alert_kind`), `checked_out`, `reset`.

### `GET /api/health`

Diagnóstico da instalação: última leitura de cada recetor, beacons ouvidos mas não
registados e recetores não configurados.
