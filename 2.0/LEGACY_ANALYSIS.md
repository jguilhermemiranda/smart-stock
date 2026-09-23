# Smart Stock: engenharia reversa inicial

## A. Sistema legado comprovado

### Arduino Mega
- `Serial1` para o ESP-01, 9600 baud; `Serial` também em 9600 para monitor/testes.
- A4988: X STEP 54, DIR 55, ENABLE 38; Y STEP 60, DIR 61, ENABLE 56; Z STEP 46, DIR 48, ENABLE 62.
- ENABLE é ativo em LOW. Fins de curso: X no pino 3 e Y no pino 14, ambos com `INPUT_PULLUP` e ativos em LOW.
- `decoderY` está no pino 11 com pull-up. O código apenas incrementa `encoderY` em 10 enquanto o pino está LOW; isso não comprova encoder incremental, quadratura ou unidade física.
- Homing legado: Y move em DIR HIGH até `endY`, depois X em DIR HIGH até `endX`; ao terminar zera X, Y e `encoderY`. Z não participa do homing.
- O movimento legado usa contadores locais e comandos fixos: `G=1` move Y 50 passos e X 50 em `M=0`; `G=1` move Y 30 em `M=1`; `G=50` executa teste de 200 pulsos nos três eixos; `G=7002` desabilita X e, se Y estiver no fim, Y.
- O timeout de 5 s apenas imprime uma mensagem e reinicia o relógio; não bloqueia movimentos. Não existe máquina de estados, validação robusta, resposta determinística ou watchdog de comunicação.

### ESP32
- RFID MFRC522: SS 5, RST 27; LED 2; SPI padrão da placa.
- Usa ESP-NOW, com MAC do ESP-01 fixo no firmware.
- Mantém 19 UIDs hardcoded. Os primeiros 18 viram comandos 1..18; o último alterna `M` via comando 0. Cartões desconhecidos são negados apenas por log/LED.
- Envia pacote binário `{int32_t G, int32_t M}` a 115200 baud no console. Não há API HTTP, persistência, hash, permissões ou operação PUT/GET.

### ESP-01/ESP8266
- Usa ESP-NOW como receptor e UART em 9600 baud para o Arduino.
- Recebe `{int G, bool M, int reserved}`. Comandos 1..6 são repassados; 7..18 passam por uma tabela de mapeamento; 0 alterna modo; 28 é repassado.
- Há um erro de sintaxe no código legado: `or` foi usado em C++ em vez de `||`.
- Não há Wi-Fi de rede, TCP, mDNS, AP de configuração, fallback de IP ou bridge transparente. O heartbeat é apenas texto no console/UART e não é um PING do Arduino.

## B. Diferenças para a arquitetura nova

| Área | Legado | Nova arquitetura |
|---|---|---|
| Transporte | ESP-NOW e pacote binário | TCP/IP ESP32 -> ESP-01 -> UART |
| Arduino | `G=`/`M=`, lógica global | `MOVE`, `HOME`, `JOG`, `PING`, `STATUS?` |
| Inteligência | UID e mapeamento em firmware | Access Manager e dados sincronizados no ESP32 |
| Persistência | Nenhuma | SQLite no PC e `LittleFS/data.json` no ESP32 |
| Gaveta | Implícita no número G | ID separado de posição calibrada |
| Segurança | Timeout não impede movimento | BUSY/ERROR, timeout bloqueia novo MOVE, sem retry cego |
| Rede | MAC fixo | configuração externa, mDNS e IP de fallback |

## C. Plano de migração

1. Atualizar o Arduino mantendo pinagem, polaridade, baud de UART e sequência física de homing.
2. Validar o protocolo textual em bancada sem conectar cargas mecânicas; confirmar PING, STATUS, HOME e erros.
3. Implementar no ESP-01 a ponte TCP/UART transparente, sem interpretar comandos.
4. Implementar no ESP32 os managers, `data.json`, API, hash e timeout de operação.
5. Implementar o aplicativo Python e sincronização administrativa.
6. Só liberar movimentos de gaveta com posição calibrada e confirmação explícita em diagnóstico.

## D. Riscos e decisões necessárias

- **[HARDWARE — NECESSÁRIO CONFIRMAR]** o tipo físico e a unidade de `decoderY`; o legado não permite concluir isso.
- **[DECISÃO NECESSÁRIA]** cursos máximos de X/Y/Z e se coordenadas negativas são permitidas; o firmware só conhece fins de curso X/Y, não limites de avanço nem Z.
- **[DECISÃO NECESSÁRIA]** significado operacional de PUT e GET; o legado tem `M`, mas não implementa um fluxo físico completo.
- **[DECISÃO NECESSÁRIA]** se ENABLE deve permanecer ativo durante idle para manter torque ou ser desligado; o legado mantém os três ativos em LOW.
- O código legado executa movimentos longos de forma bloqueante, permitindo perda de comunicação sem interrupção. A nova implementação deve pulsar incrementalmente e testar o estado em cada ciclo.

## E. Estrutura final proposta

```text
arduino/
  SmartStockArduino.ino
  protocol.h
  motion_controller.h
esp01/
  SmartStockBridge.ino
  wifi_config.h
  tcp_uart_bridge.h
esp32/
  SmartStockController.ino
  access_manager.h
  drawer_manager.h
  position_manager.h
  motion_controller.h
  operational_store.h
  http_api.h
python/
  main.py
  database/
  models/
  services/
  api/
  gui/
  sync/
  config/
```

As fases de Arduino, ESP-01, ESP32 e o primeiro aplicativo Python agora possuem implementações novas nos diretórios `arduino/`, `esp01/`, `esp32/` e `python/`. Os três arquivos legados permanecem intactos para comparação e rollback.
