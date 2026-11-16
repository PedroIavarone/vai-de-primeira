// Totem da Central de Atendimento ao Cidadão
// ESP32 que conta as pessoas na porta da unidade, percebe quem chega ao totem,
// mede temperatura e umidade e atende o botão "preciso de ajuda".
// Toda a comunicação MQTT fica em mqtt_vdp.h (não alterar aquele arquivo).

#include <DHT.h>
#include "mqtt_vdp.h"

// ---------------------------------------------------------------------------
// Pinos
// ---------------------------------------------------------------------------
const int PINO_TRIG_A = 5;    // sensor de passagem A (lado de fora da porta)
const int PINO_ECHO_A = 18;
const int PINO_TRIG_B = 19;   // sensor de passagem B (lado de dentro)
const int PINO_ECHO_B = 21;
const int PINO_PIR    = 27;   // presença no totem
const int PINO_DHT    = 15;   // temperatura e umidade
const int PINO_BOTAO  = 4;    // botão "preciso de ajuda" (INPUT_PULLUP: apertado = LOW)
const int PINO_LED    = 2;    // LED de ajuda
const int PINO_BUZZER = 23;   // aviso sonoro

// ---------------------------------------------------------------------------
// Parâmetros
// ---------------------------------------------------------------------------
const float DISTANCIA_ACIONADO_CM = 50.0;      // abaixo disso o sensor está "acionado"
const unsigned long JANELA_PASSAGEM_MS = 1500; // tempo máximo entre A e B (ou B e A)
const unsigned long INTERVALO_LEITURA_ULTRASSOM_MS = 60;  // ciclo recomendado do HC-SR04
const unsigned long TIMEOUT_ECO_US = 6000;     // cerca de 1 m; acima disso conta como "longe"
const unsigned long INTERVALO_AMBIENTE_MS = 10000;        // leitura do DHT22 a cada 10 s
const unsigned long DEBOUNCE_BOTAO_MS = 50;
const unsigned long DURACAO_AVISO_AJUDA_MS = 1000;        // LED e buzzer ligados por 1 s
const int FREQUENCIA_BUZZER_HZ = 1000;

DHT dht(PINO_DHT, DHT22);

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
// Estado dos outros sensores
// ---------------------------------------------------------------------------
bool presencaAntes = false;
unsigned long ultimaLeituraAmbiente = 0;

int leituraBotaoAntes = HIGH;       // leitura crua anterior do botão
int estadoBotaoEstavel = HIGH;      // estado do botão depois do debounce
unsigned long ultimaMudancaBotao = 0;

bool avisoAjudaLigado = false;
unsigned long inicioAvisoAjuda = 0;

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
// Temperatura e umidade a cada 10 s
// ---------------------------------------------------------------------------
void atualizarAmbiente() {
  unsigned long agora = millis();
  if (agora - ultimaLeituraAmbiente < INTERVALO_AMBIENTE_MS) {
    return;
  }
  ultimaLeituraAmbiente = agora;

  float temperatura = dht.readTemperature();
  float umidade = dht.readHumidity();
  vdp::publicarAmbiente(temperatura, umidade);  // a função ignora leitura NaN
}

// ---------------------------------------------------------------------------
// Presença no totem (PIR): publica quando o estado muda
// ---------------------------------------------------------------------------
void atualizarPresenca() {
  bool presenca = digitalRead(PINO_PIR) == HIGH;
  if (presenca != presencaAntes) {
    presencaAntes = presenca;
    Serial.printf("Totem: presenca = %s\n", presenca ? "sim" : "nao");
    vdp::publicarPresenca(presenca);
  }
}

// ---------------------------------------------------------------------------
// Botão de ajuda com debounce de 50 ms; LED e buzzer por 1 s, sem delay
// ---------------------------------------------------------------------------
void atualizarBotaoAjuda() {
  unsigned long agora = millis();
  int leitura = digitalRead(PINO_BOTAO);

  if (leitura != leituraBotaoAntes) {
    ultimaMudancaBotao = agora;  // a leitura mudou: espera estabilizar
    leituraBotaoAntes = leitura;
  }

  if (agora - ultimaMudancaBotao >= DEBOUNCE_BOTAO_MS && leitura != estadoBotaoEstavel) {
    estadoBotaoEstavel = leitura;
    if (estadoBotaoEstavel == LOW) {  // acabou de ser apertado
      Serial.println("Totem: botao de ajuda apertado");
      vdp::publicarAjuda();
      digitalWrite(PINO_LED, HIGH);
      tone(PINO_BUZZER, FREQUENCIA_BUZZER_HZ);
      avisoAjudaLigado = true;
      inicioAvisoAjuda = agora;
    }
  }

  // Desliga o LED e o buzzer depois de 1 s
  if (avisoAjudaLigado && agora - inicioAvisoAjuda >= DURACAO_AVISO_AJUDA_MS) {
    digitalWrite(PINO_LED, LOW);
    noTone(PINO_BUZZER);
    avisoAjudaLigado = false;
  }
}

// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);

  pinMode(PINO_TRIG_A, OUTPUT);
  pinMode(PINO_ECHO_A, INPUT);
  pinMode(PINO_TRIG_B, OUTPUT);
  pinMode(PINO_ECHO_B, INPUT);
  pinMode(PINO_PIR, INPUT);
  pinMode(PINO_BOTAO, INPUT_PULLUP);
  pinMode(PINO_LED, OUTPUT);
  pinMode(PINO_BUZZER, OUTPUT);
  digitalWrite(PINO_TRIG_A, LOW);
  digitalWrite(PINO_TRIG_B, LOW);
  digitalWrite(PINO_LED, LOW);

  dht.begin();
  vdp::conectar();

  // Primeira leitura de ambiente sai logo depois de conectar
  ultimaLeituraAmbiente = millis() - INTERVALO_AMBIENTE_MS;
}

void loop() {
  vdp::manter();  // mantém Wi-Fi e MQTT conectados; sempre primeiro

  atualizarContagem();
  atualizarPresenca();
  atualizarBotaoAjuda();
  atualizarAmbiente();

  delay(10);  // pausa curta para não ocupar a CPU à toa
}
