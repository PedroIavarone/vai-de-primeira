// Comunicação MQTT do totem Vai de Primeira (ESP32).
//
// Publica nos tópicos de docs/contratos.md, no broker público broker.hivemq.com:1883.
// No Wokwi, a rede "Wokwi-GUEST" dá acesso à internet sem senha.
//
// Uso no sketch:
//   #include "mqtt_vdp.h"
//   setup():  vdp::conectar();
//   loop():   vdp::manter();
//             vdp::publicarFila(pessoas);           // quando a contagem mudar
//             vdp::publicarAmbiente(temp, umidade); // a cada 10 s
//             vdp::publicarPresenca(true/false);    // quando o PIR mudar
//             vdp::publicarAjuda();                 // quando o botão for apertado
//
// Bibliotecas (libraries.txt no Wokwi): PubSubClient
#pragma once

#include <WiFi.h>
#include <PubSubClient.h>

namespace vdp {

const char* WIFI_REDE = "Wokwi-GUEST";
const char* WIFI_SENHA = "";
const char* BROKER = "broker.hivemq.com";
const int BROKER_PORTA = 1883;
const char* UNIDADE = "centro";
const char* TOTEM = "t1";

WiFiClient rede;
PubSubClient mqtt(rede);
unsigned long ultimaTentativa = 0;

void conectarWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("Wi-Fi: conectando");
  WiFi.begin(WIFI_REDE, WIFI_SENHA, 6);
  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 15000) {
    delay(250);
    Serial.print(".");
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? " ok" : " falhou (nova tentativa no loop)");
}

bool conectarMqtt() {
  String id = "vdp-totem-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  if (mqtt.connect(id.c_str())) {
    Serial.println("MQTT: conectado a " + String(BROKER));
    return true;
  }
  Serial.println("MQTT: falhou (estado " + String(mqtt.state()) + "), nova tentativa em 3 s");
  return false;
}

void conectar() {
  conectarWifi();
  mqtt.setServer(BROKER, BROKER_PORTA);
  conectarMqtt();
}

// Chamar em todo loop(): reconecta sem travar o totem e processa a rede.
void manter() {
  if (WiFi.status() != WL_CONNECTED) conectarWifi();
  if (!mqtt.connected() && millis() - ultimaTentativa > 3000) {
    ultimaTentativa = millis();
    conectarMqtt();
  }
  mqtt.loop();
}

bool publicar(const String& topico, const String& conteudo) {
  bool ok = mqtt.connected() && mqtt.publish(topico.c_str(), conteudo.c_str());
  Serial.println((ok ? "MQTT > " : "MQTT (não enviado) > ") + topico + " " + conteudo);
  return ok;
}

bool publicarFila(int pessoas) {
  if (pessoas < 0) pessoas = 0;
  return publicar(String("vdp/unidade/") + UNIDADE + "/fila",
                  String("{\"unidade\":\"") + UNIDADE + "\",\"pessoas\":" + pessoas + "}");
}

bool publicarAmbiente(float tempC, float umidade) {
  if (isnan(tempC) || isnan(umidade)) {  // DHT22 às vezes falha na leitura: não publica lixo
    Serial.println("DHT22: leitura inválida, ignorada");
    return false;
  }
  return publicar(String("vdp/unidade/") + UNIDADE + "/ambiente",
                  String("{\"unidade\":\"") + UNIDADE + "\",\"temp_c\":" + String(tempC, 1) +
                  ",\"umidade\":" + String(umidade, 0) + "}");
}

bool publicarPresenca(bool presente) {
  return publicar(String("vdp/totem/") + TOTEM + "/presenca",
                  String("{\"totem\":\"") + TOTEM + "\",\"presente\":" + (presente ? "true" : "false") + "}");
}

bool publicarAjuda() {
  return publicar(String("vdp/totem/") + TOTEM + "/ajuda",
                  String("{\"totem\":\"") + TOTEM + "\",\"ajuda\":true}");
}

}  // namespace vdp
