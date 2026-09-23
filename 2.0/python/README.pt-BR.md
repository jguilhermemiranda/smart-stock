# Smart Stock PC

Aplicativo desktop para Windows desenvolvido em Python com Tkinter, usando um banco SQLite local para registrar operação, gavetas, cartões RFID e inventário.

## Como executar

No diretório raiz do projeto:

```powershell
python .\2.0\python\main.py
```

A aplicação cria arquivos locais como `smartstock.db` e `smartstock.json` no diretório atual. Ela usa apenas a biblioteca padrão do Python e os módulos locais do projeto.

## Fluxo principal

1. Cadastre gavetas com coordenadas reais. A interface marca a gaveta como calibrada apenas quando os valores X/Y/Z forem preenchidos.
2. Cadastre itens e quantidades em cada gaveta. Reusar o mesmo item atualiza o valor em vez de criar duplicata.
3. Cadastre cartões RFID com UID hexadecimal. O UID é normalizado para maiúsculas.
4. Associe cartões às gavetas na seção "Quem pode retirar" para exibir os proprietários autorizados.
5. Configure `esp32_host` e `esp32_port` em `smartstock.json` quando o mDNS não resolver corretamente.
6. Sincronize os dados para enviar configuração da máquina, gavetas, inventário, cartões, permissões e o valor SHA-256 ao ESP32.
7. Use HOME e movimentos administrativos somente após confirmação explícita.

## Módulos de firmware

- `2.0/arduino/SmartStockArduino.ino` — controlador físico Arduino Mega com UART 9600
- `2.0/esp01/SmartStockBridge.ino` — ponte TCP na porta 8899 para UART 9600
- `2.0/esp32/SmartStockController.ino` — API HTTP, lógica RFID e armazenamento LittleFS

## Observações

Os sketches dependem das bibliotecas e cores corretas para cada placa. Este workspace não inclui `arduino-cli`, então a compilação deve ser feita no Arduino IDE com suporte para Arduino Mega, ESP8266 e ESP32, além de MFRC522 e ArduinoJson.

## Documentação relacionada

- [README.md](../../README.md) — visão geral do projeto em inglês
- [README.pt-BR.md](../../README.pt-BR.md) — visão geral em português
- [README.md](README.md) — este guia em inglês
