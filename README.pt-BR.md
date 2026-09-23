# Smart Stock

Smart Stock é um projeto de automação para estoque e operação de gavetas, combinando um aplicativo desktop local, controlador ESP32, ponte ESP-01 e sistema de movimento em Arduino.

## Sobre o projeto

O Smart Stock automatiza parte do processo de armazenamento e movimentação de materiais em um estoque. O projeto combina microcontroladores, leitores RFID, comunicação sem fio e controle de movimento para identificar materiais, determinar seus destinos e movimentá-los por meio de um mecanismo automatizado.

A ideia principal é simples: identificar um material, determinar para onde ele deve ir e controlar o sistema mecânico responsável por movimentá-lo.

## Estrutura do projeto

- `2.0/` — versão atual em desenvolvimento
- `ORIGINAL/` — materiais originais preservados para referência e rollback

## Componentes principais

- `2.0/python/` — aplicação desktop em Python com Tkinter, SQLite e sincronização via API
- `2.0/esp32/` — firmware do controlador ESP32 e lógica HTTP/JSON
- `2.0/esp01/` — ponte TCP para UART
- `2.0/arduino/` — controlador de movimento Arduino para os eixos X/Y/Z

## Como funciona

O sistema é dividido em três controladores principais, cada um responsável por uma parte diferente do processo.

- O ESP32 lê os cartões RFID e envia comandos sem fio.
- O ESP8266/ESP-01 recebe esses comandos e os encaminha ao Arduino principal.
- O Arduino controla os motores e o movimento mecânico do estoque.

```text
Cartão RFID
	|
	v
ESP32
	|
	| ESP-NOW
	v
ESP8266 / ESP-01
	|
	| Serial
	v
Arduino
	|
	v
Mecanismo automatizado
```

Essa separação permite que cada controlador se concentre em uma tarefa específica, sem depender de um único microcontrolador para todo o sistema.

## Principais recursos

- Identificação de materiais por RFID
- Comunicação sem fio usando ESP-NOW
- Comunicação serial entre os controladores
- Controle automatizado dos motores
- Movimento nos eixos X, Y e Z
- Detecção de fins de curso
- Homing automático
- Rastreamento e correção de posição
- Modos de operação manual e automático
- Calibração de gavetas e gestão de inventário
- Sincronização do banco local com o controlador
- Status de operação, controle de movimento e diagnósticos de hardware

## Hardware

A versão atual do projeto utiliza:

- ESP32
- ESP8266 / ESP-01
- Arduino
- Leitor RFID MFRC522
- Motores de passo
- Drivers de motor
- Sensores de fim de curso
- Estrutura mecânica para movimentação de materiais

O hardware pode mudar durante o desenvolvimento conforme novos testes e melhorias forem realizados.

## Software

O firmware dos dispositivos embarcados é desenvolvido no Arduino IDE, enquanto a aplicação desktop é executada em Python.

O firmware do ESP32 utiliza principalmente as seguintes bibliotecas:

```cpp
#include <WiFi.h>
#include <esp_now.h>
#include <SPI.h>
#include <MFRC522.h>
```

O ESP32 é responsável pelo leitor RFID e pela comunicação ESP-NOW.

O ESP8266/ESP-01 funciona como receptor sem fio e se comunica com o Arduino por conexão serial.

O Arduino executa a lógica principal de movimento e posicionamento.

## Sistema RFID

Cada cartão RFID cadastrado no sistema é associado a um comando específico.

Quando um cartão é detectado, o ESP32 lê seu UID e verifica se ele está cadastrado. Se o UID for reconhecido, o comando correspondente é enviado ao ESP8266/ESP-01. O fluxo básico é:

```text
Cartão RFID detectado
	|
	v
Leitura do UID
	|
	v
Verificação dos cartões cadastrados
	|
	v
Determinação do comando
	|
	v
Envio do comando via ESP-NOW
	|
	v
ESP8266 recebe o comando
	|
	v
Arduino executa o comando
```

Cartões que não estão cadastrados no sistema são ignorados.

## Controle de movimento

O Arduino é responsável por controlar o movimento do mecanismo automatizado.

O sistema de controle atual utiliza três eixos:

- Eixo X
- Eixo Y
- Eixo Z

Sensores de fim de curso são usados para determinar as posições de referência e evitar movimentos indesejados. O sistema também inclui um procedimento automático de homing e rastreamento de posição para manter o mecanismo sincronizado com a posição esperada.

## Documentação

- Inglês: [README.md](README.md)
- Português: [README.pt-BR.md](README.pt-BR.md)
- Guia da aplicação Python: [2.0/python/README.md](2.0/python/README.md)
- Guia em português da aplicação: [2.0/python/README.pt-BR.md](2.0/python/README.pt-BR.md)

## Estrutura do repositório

```text
SmartStock/
│
├── 2.0/
│   ├── python/
│   ├── esp32/
│   ├── esp01/
│   └── arduino/
│
├── ORIGINAL/
│
├── README.md
├── README.pt-BR.md
└── .gitignore
```

## Primeiros passos

Para trabalhar com o projeto, instale o Arduino IDE e os pacotes de placa necessários para Arduino, ESP8266, ESP32 e a ponte ESP-01.

Para o ESP32, instale a biblioteca MFRC522 e selecione a placa ESP32 correta antes de compilar o firmware.

Para o ESP8266/ESP-01, instale o pacote de placas ESP8266 e selecione a configuração de placa apropriada.

O firmware do Arduino deve ser compilado para a placa específica utilizada no projeto.

Os três controladores devem ser configurados de acordo com o hardware e a comunicação do sistema.

## Desenvolvimento

O projeto continua em evolução. Os materiais legados foram preservados na pasta `ORIGINAL/`, enquanto a arquitetura atual está em `2.0/`.

O projeto está sendo desenvolvido e testado como parte do TCC e de melhorias contínuas de hardware e software. Por isso, tanto o hardware quanto o software podem mudar durante o desenvolvimento. O repositório documenta a implementação atual em `2.0/` e os materiais legados mantidos em `ORIGINAL/`.

## Projeto acadêmico

Este projeto foi desenvolvido como parte de um Trabalho de Conclusão de Curso (TCC), reunindo conceitos de:

- Sistemas embarcados
- Automação
- Robótica
- RFID
- Comunicação sem fio
- Programação de microcontroladores
- Controle de motores

## Autores

- Gabriel Curti da Silva Moura Diniz
- Hugo de Paula Martins
- João Guilherme de Oliveira Miranda
- Pedro Lucas Vieira Monteiro Vicente

GitHub: [@pedrolucashub (Pedro Lucas)](https://github.com/pedrolucashub)

GitHub: [@joaoguilhermeomiranda](https://github.com/jguilhermemiranda)

## Licença

Este projeto é destinado atualmente a fins acadêmicos e educacionais.

Uma licença formal de código aberto poderá ser adicionada no futuro.

## Observações

O projeto continua em evolução. Os materiais legados originais permanecem na pasta `ORIGINAL/`, enquanto a arquitetura atual está em `2.0/`.
