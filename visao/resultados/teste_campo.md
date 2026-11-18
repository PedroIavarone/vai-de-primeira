# Teste de campo com documentos fictícios brasileiros

20 imagens · limiar do detector 0.5

| Arquivo | Tipo | Condição | Confiança do detector | Detectado | Qualidade (melhor recorte) | Tipo (OCR) |
|---|---|---|---|---|---|---|
| certidao_borrado_1.jpg | certidao | borrado | 0.000 | não | - | - |
| certidao_borrado_2.jpg | certidao | borrado | 0.000 | não | - | - |
| certidao_cortado_1.jpg | certidao | cortado | 0.011 | não | ok | - |
| certidao_ok_1.jpg | certidao | ok | 0.000 | não | - | - |
| certidao_reflexo_1.jpg | certidao | reflexo | 0.000 | não | - | - |
| certidao_reflexo_2.jpg | certidao | reflexo | 0.000 | não | - | - |
| cin_borrado_1.jpg | cin | borrado | 0.011 | não | borrado | - |
| cin_borrado_2.jpg | cin | borrado | 0.000 | não | - | - |
| cin_cortado_1.jpg | cin | cortado | 0.000 | não | - | - |
| cin_cortado_2.jpg | cin | cortado | 0.000 | não | - | - |
| cin_ok_1.jpg | cin | ok | 0.384 | não | ok | - |
| cin_ok_2.jpg | cin | ok | 0.035 | não | ok | - |
| cin_reflexo_1.jpg | cin | reflexo | 0.095 | não | reflexo | - |
| cnh_borrado_1.jpg | cnh | borrado | 0.049 | não | borrado | - |
| cnh_cortado_1.jpg | cnh | cortado | 0.000 | não | - | - |
| cnh_cortado_2.jpg | cnh | cortado | 0.073 | não | ok | - |
| cnh_ok_1.jpg | cnh | ok | 0.759 | sim | ok | cnh |
| cnh_ok_2.jpg | cnh | ok | 0.165 | não | ok | - |
| cnh_reflexo_1.jpg | cnh | reflexo | 0.399 | não | reflexo | - |
| cnh_reflexo_2.jpg | cnh | reflexo | 0.493 | não | reflexo | - |

```json
{
  "imagens": 20,
  "limiar_detector": 0.5,
  "detectados_no_limiar": 1,
  "conf_detector_mediana": 0.011,
  "qualidade_certa_entre_detectados": 1,
  "qualidade_certa_no_melhor_recorte": 9,
  "tipo_certo_entre_detectados": 1,
  "qualidade_prevista_no_melhor_recorte": {
    "null": 9,
    "ok": 6,
    "borrado": 2,
    "reflexo": 3
  }
}
```
