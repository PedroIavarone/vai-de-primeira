# Teste de campo com documentos fictícios brasileiros

20 imagens · limiar do detector 0.5

| Arquivo | Tipo | Condição | Confiança do detector | Detectado | Qualidade (melhor recorte) | Tipo (OCR) |
|---|---|---|---|---|---|---|
| certidao_borrado_1.jpg | certidao | borrado | 0.939 | sim | borrado | desconhecido |
| certidao_borrado_2.jpg | certidao | borrado | 0.000 | não | - | - |
| certidao_cortado_1.jpg | certidao | cortado | 0.955 | sim | ok | certidao |
| certidao_ok_1.jpg | certidao | ok | 0.961 | sim | ok | certidao |
| certidao_reflexo_1.jpg | certidao | reflexo | 0.955 | sim | cortado | desconhecido |
| certidao_reflexo_2.jpg | certidao | reflexo | 0.963 | sim | reflexo | certidao |
| cin_borrado_1.jpg | cin | borrado | 0.967 | sim | borrado | desconhecido |
| cin_borrado_2.jpg | cin | borrado | 0.949 | sim | borrado | desconhecido |
| cin_cortado_1.jpg | cin | cortado | 0.964 | sim | ok | desconhecido |
| cin_cortado_2.jpg | cin | cortado | 0.967 | sim | ok | cin |
| cin_ok_1.jpg | cin | ok | 0.973 | sim | ok | cin |
| cin_ok_2.jpg | cin | ok | 0.975 | sim | ok | cin |
| cin_reflexo_1.jpg | cin | reflexo | 0.971 | sim | reflexo | cin |
| cnh_borrado_1.jpg | cnh | borrado | 0.953 | sim | borrado | desconhecido |
| cnh_cortado_1.jpg | cnh | cortado | 0.959 | sim | ok | cnh |
| cnh_cortado_2.jpg | cnh | cortado | 0.970 | sim | ok | desconhecido |
| cnh_ok_1.jpg | cnh | ok | 0.959 | sim | ok | cnh |
| cnh_ok_2.jpg | cnh | ok | 0.963 | sim | ok | cnh |
| cnh_reflexo_1.jpg | cnh | reflexo | 0.964 | sim | reflexo | cnh |
| cnh_reflexo_2.jpg | cnh | reflexo | 0.963 | sim | reflexo | cnh |

```json
{
  "imagens": 20,
  "limiar_detector": 0.5,
  "detectados_no_limiar": 19,
  "conf_detector_mediana": 0.963,
  "qualidade_certa_entre_detectados": 13,
  "qualidade_certa_no_melhor_recorte": 13,
  "tipo_certo_entre_detectados": 12,
  "qualidade_prevista_no_melhor_recorte": {
    "borrado": 4,
    "null": 1,
    "ok": 10,
    "cortado": 1,
    "reflexo": 4
  }
}
```
