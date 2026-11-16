// Totem da Central de Atendimento ao Cidadão
// ESP32 que conta as pessoas na porta da unidade e publica a fila por MQTT.
// Toda a comunicação MQTT fica em mqtt_vdp.h (não alterar aquele arquivo).

#include "mqtt_vdp.h"

// ---------------------------------------------------------------------------
// Pinos
// ---------------------------------------------------------------------------
const int PINO_TRIG_A = 5;    // sensor de passagem A (lado de fora da porta)
const int PINO_ECHO_A = 18;
const int PINO_TRIG_B = 19;   // sensor de passagem B (lado de dentro)
const int PINO_ECHO_B = 21;

// ---------------------------------------------------------------------------
// Parâmetros
// ---------------------------------------------------------------------------
const float DISTANCIA_ACIONADO_CM = 50.0;      // abaixo disso o sensor está "acionado"
const unsigned long JANELA_PASSAGEM_MS = 1500; // tempo máximo entre A e B (ou B e A)
const unsigned long INTERVALO_LEITURA_ULTRASSOM_MS = 60;  // ciclo recomendado do HC-SR04
const unsigned long TIMEOUT_ECO_US = 6000;     // cerca de 1 m; acima disso conta como "longe"

// ---------------------------------------------------------------------------
// Estado da contagem na porta
// ---------------------------------------------------------------------------
// A passagem é decidida pela ordem em que os sensores são acionados:
// A e depois B = entrada; B e depois A = saída.
enum EstadoPorta { OCIOSA, A_PRIMEIRO, B_PRIMEIRO };
EstadoPorta estadoPorta = OCIOSA;
unsigned long inicioPassagem = 0;   // quando o primeiro sensor foi acionado

bool aAcionadoAntes = false;        // leitura anterior, para detectar a borda de acionamento
bool bAcionadoAntes = false;
unsigned long ultimaLeituraUltrassom = 0;

int pessoas = 0;                    // pessoas dentro da unidade (nunca abaixo de 0)
int pessoasPublicadas = -1;         // último valor enviado; -1 força o primeiro envio

// ---------------------------------------------------------------------------
// Mede a distância de um HC-SR04 em centímetros.
// Devolve -1 quando o eco não volta dentro do tempo limite (nada perto).
// ---------------------------------------------------------------------------
float medirDistanciaCm(int pinoTrig, int pinoEcho) {
  digitalWrite(pinoTrig, LOW);
  delayMicroseconds(2);
  digitalWrite(pinoTrig, HIGH);
  delayMicroseconds(10);
  digitalWrite(pinoTrig, LOW);

  unsigned long duracao = pulseIn(pinoEcho, HIGH, TIMEOUT_ECO_US);
  if (duracao == 0) {
    return -1;
  }
  return duracao * 0.0343 / 2.0;  // velocidade do som: 0,0343 cm/us, ida e volta
}

bool estaAcionado(float distanciaCm) {
  return distanciaCm >= 0 && distanciaCm < DISTANCIA_ACIONADO_CM;
}

// ---------------------------------------------------------------------------
// Contagem de entrada e saída
// ---------------------------------------------------------------------------
void registrarEntrada() {
  pessoas++;
  Serial.printf("Porta: entrada (pessoas = %d)\n", pessoas);
}

void registrarSaida() {
  if (pessoas > 0) {
    pessoas--;
  }
  Serial.printf("Porta: saida (pessoas = %d)\n", pessoas);
}

void atualizarContagem() {
  unsigned long agora = millis();

  // Desiste da passagem se o segundo sensor não foi acionado a tempo
  if (estadoPorta != OCIOSA && agora - inicioPassagem > JANELA_PASSAGEM_MS) {
    estadoPorta = OCIOSA;
  }

  // Lê os dois sensores no ritmo recomendado pelo fabricante
  if (agora - ultimaLeituraUltrassom < INTERVALO_LEITURA_ULTRASSOM_MS) {
    return;
  }
  ultimaLeituraUltrassom = agora;

  bool aAcionado = estaAcionado(medirDistanciaCm(PINO_TRIG_A, PINO_ECHO_A));
  bool bAcionado = estaAcionado(medirDistanciaCm(PINO_TRIG_B, PINO_ECHO_B));

  // Só interessa o instante em que o sensor passa de "livre" para "acionado"
  bool aComecou = aAcionado && !aAcionadoAntes;
  bool bComecou = bAcionado && !bAcionadoAntes;
  aAcionadoAntes = aAcionado;
  bAcionadoAntes = bAcionado;

  switch (estadoPorta) {
    case OCIOSA:
      if (aComecou && !bComecou) {
        estadoPorta = A_PRIMEIRO;
        inicioPassagem = agora;
      } else if (bComecou && !aComecou) {
        estadoPorta = B_PRIMEIRO;
        inicioPassagem = agora;
      }
      break;

    case A_PRIMEIRO:
      if (bComecou) {
        registrarEntrada();
        estadoPorta = OCIOSA;
      } else if (aComecou) {
        inicioPassagem = agora;  // A acionado de novo: recomeça a janela
      }
      break;

    case B_PRIMEIRO:
      if (aComecou) {
        registrarSaida();
        estadoPorta = OCIOSA;
      } else if (bComecou) {
        inicioPassagem = agora;  // B acionado de novo: recomeça a janela
      }
      break;
  }

  // Publica a fila só quando o número muda
  if (pessoas != pessoasPublicadas) {
    vdp::publicarFila(pessoas);
    pessoasPublicadas = pessoas;
  }
}

// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);

  pinMode(PINO_TRIG_A, OUTPUT);
  pinMode(PINO_ECHO_A, INPUT);
  pinMode(PINO_TRIG_B, OUTPUT);
  pinMode(PINO_ECHO_B, INPUT);
  digitalWrite(PINO_TRIG_A, LOW);
  digitalWrite(PINO_TRIG_B, LOW);

  vdp::conectar();
}

void loop() {
  vdp::manter();  // mantém Wi-Fi e MQTT conectados; sempre primeiro

  atualizarContagem();

  delay(10);  // pausa curta para não ocupar a CPU à toa
}
