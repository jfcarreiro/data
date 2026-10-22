# Hardware: protótipo em casa (4 pisos)

## Lista de compras

Preços indicativos (Amazon, AliExpress, Kubii, Pi-Shop.lu…). Confirmar antes de comprar.

| # | Item | Qtd. | Preço aprox. | Notas |
|---|---|---|---|---|
| 1 | **Placa ESP32 DevKit** (ESP32-WROOM-32, ou ESP32-C3/S3) | 10 | 60–100 € | 9 zonas em `config/house.yaml` + 1 de reserva. Packs de 3–5 saem mais baratos |
| 2 | Carregador USB 5 V / 1 A + cabo (micro-USB ou USB-C, conforme a placa) | 10 | 0–60 € | Servem carregadores de telemóvel antigos |
| 3 | **Pulseira BLE beacon** (iBeacon/Eddystone) | 5–6 | 60–120 € | Ver requisitos abaixo |
| 4 | Raspberry Pi 5 (4 GB) + fonte oficial + microSD de 32 GB + caixa | 1 | ~100–120 € | O "servidor". Alternativa: um portátil ou mini-PC que fique ligado |
| 5 | *Opcional:* 1 gateway BLE comercial com PoE | 1 | 60–150 € | Para comparar com o tipo de equipamento que iria para a escola |
| | **Total** | | **~180–400 €** | Depende do que já houver em casa (carregadores, PC) |

### Requisitos das pulseiras (o que procurar)

Pesquisar por "BLE beacon wristband iBeacon". Confirmar que a pulseira tem:

- protocolo **iBeacon** (ou Eddystone);
- **intervalo de anúncio configurável**, idealmente 1000 ms;
- **potência de emissão configurável**;
- **pilha substituível** (CR2032 ou semelhante) ou recarregável, com autonomia anunciada
  de 6 meses ou mais a 1 s de intervalo;
- resistência à água (IP67) e fecho difícil de abrir por uma criança;
- uma app do fabricante para configurar.

**Não usar AirTags, Tiles ou SmartTags**: mudam de endereço por privacidade e são
fechadas. Um telemóvel com a app *nRF Connect* (separador "Advertiser") pode fazer de
pulseira extra para testes.

## Onde pôr os recetores (casa de 4 pisos)

| Zona (`config/house.yaml`) | Piso | Colocação |
|---|---|---|
| `entrada` (zona de saída) | 0 | Perto da porta da rua, do lado de dentro |
| `sala`, `cozinha` | 0 | Centro da divisão, 1–1,5 m de altura |
| `jardim` (exterior) | 0 | Junto a uma janela ou porta para o jardim, numa tomada protegida |
| `escadas` | — | Num patamar intermédio. Com 4 pisos, pode valer a pena ter 2 recetores (ver abaixo) |
| `quarto1`, `escritorio` | 1 | Centro da divisão |
| `quarto2` | 2 | Centro da divisão |
| `sotao` | 3 | Centro da divisão |

Regras práticas:

- Longe de objetos metálicos grandes (frigorífico, radiadores, armários metálicos) e
  de micro-ondas.
- Evitar pôr o recetor encostado à parede que dá para a divisão vizinha.
- **Uma zona pode ter vários recetores.** Basta acrescentar outro gateway com a mesma
  `zone:` (por exemplo `escadas-p1` e `escadas-p3`, ambos com `zone: escadas`). É assim
  que se cobre uma sala grande ou um campo de futebol.

## Montar os recetores ESP32 (ESPresense)

[ESPresense](https://espresense.com) é um firmware open-source que faz exatamente o que
precisamos: cada ESP32 ouve os beacons BLE à volta e publica no MQTT. Não é preciso
escrever firmware.

1. **Instalar o firmware**: no Chrome ou no Edge, abrir a página de instalação do
   ESPresense (secção *Firmware*/*Install* do site), ligar o ESP32 por USB e seguir o
   instalador web. Escolher a variante que corresponde à placa.
2. **Wi-Fi**: depois de instalado, o ESP32 cria uma rede Wi-Fi própria (`espresense-…`).
   Ligar a essa rede e indicar a rede de casa.
3. **Configurar** (página web do ESP32, no IP que o router lhe der):
   - **Room**: o id da zona, exatamente como em `config/house.yaml` (por exemplo `sala`);
   - **MQTT server**: o IP do computador onde corre o `docker compose` (porta 1883, sem
     utilizador e sem password no protótipo).
4. Repetir para cada placa e dar-lhe o nome da zona onde vai ficar. Convém pôr uma
   etiqueta física em cada placa.

O tracker escuta `espresense/devices/<id-do-beacon>/<room>`. Se uma pulseira não aparecer
em **Diagnóstico**, rever as opções de filtro de dispositivos do ESPresense (listas
*include*/*known*).

Um gateway comercial também serve, desde que publique no MQTT. Se não falar o formato
ESPresense, basta publicar em `tracker/readings` com
`{"tag": "...", "gateway": "...", "rssi": -70}`.

## Configurar as pulseiras

Na app do fabricante:

- **Intervalo de anúncio: 1000 ms.** Mais rápido reage mais depressa mas gasta mais
  pilha; mais lento poupa pilha mas atrasa os alertas.
- **Potência**: começar no valor por defeito (0 dBm ou próximo). Se as salas vizinhas se
  confundirem muito, baixar a potência.
- Anotar o UUID/major/minor de cada pulseira. O id no ESPresense é do género
  `iBeacon:<uuid>-<major>-<minor>`.

## Plano de teste em casa (1–2 semanas)

1. **Arranque**: confirmar que todos os recetores aparecem em Diagnóstico com "Última"
   abaixo de alguns segundos.
2. **Registo**: copiar os ids das pulseiras de Diagnóstico para `tags:` e reiniciar.
3. **Precisão por divisão**: andar com uma pulseira e anotar, em cada divisão, o tempo
   que a interface demora a acertar e se salta para a divisão vizinha ou para outro piso.
4. **Escadas e pisos**: subir e descer. Ver se o piso fica certo e se há saltos quando se
   está junto às escadas.
5. **Exterior**: até onde no jardim é detetado e quando dispara o "não detetado".
6. **Alertas**: tapar a pulseira com a mão ou pô-la numa caixa metálica (deve dar "não
   detetado" ao fim de 60 s). Ir à porta da rua (deve dar "na saída").
7. **Pilhas**: registar a percentagem no início e no fim do teste para estimar a
   autonomia real.
8. **Afinar** `engine:` em `config/house.yaml`, conforme o que se observar:
   - `switch_margin_db` e `switch_hold_s` para menos saltos (à custa de mais atraso);
   - `missing_after_s` para equilibrar falsos alertas com a rapidez de deteção.
