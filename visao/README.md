# Conferência por vídeo

Avalia, por imagem ou vídeo, se os documentos do cidadão estão legíveis antes da ida à unidade. Faz triagem: a conferência final continua sendo do atendente.

**Responsável:** Pedro Iavarone Custódio

## Funcionalidades
- Localização do documento no quadro com YOLO.
- Classificação de qualidade: ok, borrado, reflexo ou cortado.
- Identificação do tipo (CNH, CIN, certidão, comprovante) por OCR.
- Processamento contínuo de vídeo, com confiança por detecção.

## Integração
Saída no formato de `POST /checar-documento` em [docs/contratos.md](../docs/contratos.md). Treinado e testado apenas com documentos fictícios (dataset público MIDV-2020 e modelos espécime). Datasets e pesos grandes não são versionados.

## Próximos passos
- [ ] Preparação dos dados com divisão por imagem original
- [ ] Treino do detector e do classificador
- [ ] Métricas: mAP, precisão, recall, F1, matriz de confusão, latência e FPS
- [ ] Análise de erros e escolha do limiar de confiança
