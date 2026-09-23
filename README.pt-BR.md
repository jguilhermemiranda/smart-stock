# Smart Stock

Smart Stock é um projeto de automação para estoque e operação de gavetas, combinando um aplicativo desktop local, controlador ESP32, ponte ESP-01 e sistema de movimento em Arduino.

## Estrutura do projeto

- `2.0/` — versão atual em desenvolvimento
- `ORIGINAL/` — materiais originais preservados para referência e rollback

## Componentes principais

- `2.0/python/` — aplicação desktop em Python com Tkinter, SQLite e sincronização via API
- `2.0/esp32/` — firmware do controlador ESP32 e lógica HTTP/JSON
- `2.0/esp01/` — ponte TCP para UART
- `2.0/arduino/` — controlador de movimento Arduino para os eixos X/Y/Z

## Visão geral rápida

- Calibração de gavetas e gestão de inventário
- Cadastro de cartões RFID e permissões por usuário
- Banco local com sincronização para o controlador
- Status de operação, movimento e diagnósticos de hardware

## Documentação

- Inglês: [README.md](README.md)
- Português: [README.pt-BR.md](README.pt-BR.md)
- Guia da aplicação Python: [2.0/python/README.md](2.0/python/README.md)
- Guia em português da aplicação: [2.0/python/README.pt-BR.md](2.0/python/README.pt-BR.md)

## Observações

O projeto continua em evolução. Os materiais legados foram preservados na pasta `ORIGINAL/`, enquanto a arquitetura atual está em `2.0/`.
