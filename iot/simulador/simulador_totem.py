"""Simulador do totem: publica no MQTT as mesmas mensagens do ESP32 (docs/contratos.md).

Serve para testar o Node-RED e a API sem o Wokwi aberto e para reproduzir os cenários da demonstração.
É identificado como simulado no relatório: a fonte real é o ESP32 (esp32/ e wokwi/).

Uso:
  python simulador_totem.py --cenario normal          fila andando, 4 a 10 pessoas
  python simulador_totem.py --cenario cheia           chegada em massa até 30 pessoas, depois esvazia
  python simulador_totem.py --cenario ajuda           alguém se aproxima do totem e aperta "preciso de ajuda"
  python simulador_totem.py --cenario calor           temperatura sobe de 26 °C para 32 °C
  python simulador_totem.py --cenario invalido        leituras com erro (o Node-RED deve descartar)
  python simulador_totem.py --cenario todos
"""
from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER, PORTA = "broker.hivemq.com", 1883


class Totem:
    def __init__(self, unidade: str, totem: str, intervalo_s: float):
        self.unidade, self.totem, self.intervalo = unidade, totem, intervalo_s
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"vdp-sim-{random.randint(0, 99999)}")
        self.cliente.connect(BROKER, PORTA, keepalive=30)
        self.cliente.loop_start()
        self.pessoas = 0

    def publicar(self, topico: str, dados: dict):
        texto = json.dumps(dados, ensure_ascii=False)
        self.cliente.publish(topico, texto, qos=1).wait_for_publish(timeout=5)
        print(f"{datetime.now():%H:%M:%S}  {topico:32} {texto}")
        time.sleep(self.intervalo)

    def fila(self, pessoas: int):
        self.pessoas = max(0, pessoas)
        self.publicar(f"vdp/unidade/{self.unidade}/fila", {"unidade": self.unidade, "pessoas": self.pessoas,
                                                            "ts": datetime.now().isoformat(timespec="seconds")})

    def ambiente(self, temp_c: float, umidade: float):
        self.publicar(f"vdp/unidade/{self.unidade}/ambiente", {"unidade": self.unidade, "temp_c": temp_c, "umidade": umidade})

    def presenca(self, presente: bool):
        self.publicar(f"vdp/totem/{self.totem}/presenca", {"totem": self.totem, "presente": presente})

    def ajuda(self):
        self.publicar(f"vdp/totem/{self.totem}/ajuda", {"totem": self.totem, "ajuda": True})

    def fechar(self):
        self.cliente.loop_stop()
        self.cliente.disconnect()


def normal(t: Totem):
    print("\n== cenário: fila normal ==")
    for p in (4, 5, 7, 6, 8, 7, 5):
        t.fila(p)
    t.ambiente(25.5, 55)


def cheia(t: Totem):
    print("\n== cenário: fila cheia (chegada em massa) ==")
    for p in (8, 14, 20, 26, 30, 30):
        t.fila(p)
    for p in (24, 18, 12):  # esvazia e a fila volta ao normal
        t.fila(p)


def ajuda(t: Totem):
    print("\n== cenário: pedido de ajuda no totem ==")
    t.presenca(True)
    t.ajuda()
    t.presenca(False)


def calor(t: Totem):
    print("\n== cenário: calor na unidade ==")
    for temp in (26.0, 28.4, 30.2, 31.6, 32.1, 29.0, 27.5):
        t.ambiente(temp, 48)


def invalido(t: Totem):
    print("\n== cenário: leituras inválidas ==")
    t.publicar(f"vdp/unidade/{t.unidade}/fila", {"unidade": t.unidade, "pessoas": -3})
    t.publicar(f"vdp/unidade/{t.unidade}/fila", {"unidade": t.unidade, "pessoas": "muita gente"})
    t.publicar(f"vdp/unidade/{t.unidade}/ambiente", {"unidade": t.unidade, "temp_c": 999, "umidade": 50})


CENARIOS = {"normal": normal, "cheia": cheia, "ajuda": ajuda, "calor": calor, "invalido": invalido}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cenario", choices=[*CENARIOS, "todos"], default="todos")
    p.add_argument("--unidade", default="centro")
    p.add_argument("--totem", default="t1")
    p.add_argument("--intervalo", type=float, default=1.5, help="segundos entre mensagens")
    a = p.parse_args()
    totem = Totem(a.unidade, a.totem, a.intervalo)
    try:
        for nome in (CENARIOS if a.cenario == "todos" else [a.cenario]):
            CENARIOS[nome](totem)
    finally:
        totem.fechar()
