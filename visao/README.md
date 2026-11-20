# Conferência por vídeo

Avalia, por imagem ou vídeo, se os documentos do cidadão estão legíveis antes da ida à unidade de atendimento. O sistema faz **triagem**: a conferência final continua sendo do atendente.

## Como funciona
```
imagem ou quadro de vídeo
  → detector (YOLO11n): localiza o documento
  → recorte da caixa
  → qualidade (YOLO11n-cls): ok, borrado, reflexo ou cortado
  → tipo (OCR + palavras-chave): CNH, CIN, certidão, CPF ou comprovante
  → orientação para o cidadão
```
O código fica em [`src/conferencia.py`](src/conferencia.py). A API usa esse mesmo módulo em `POST /checar-documento`.

## Dados
Dataset público **MIDV-2020** (subconjunto `photo`): 1.000 fotos de celular de 1.000 documentos fictícios únicos, em 10 tipos e 8 condições de captura (pouca luz, reflexo de luz, luz externa, distorção projetiva e fundos variados). Licença CC BY-SA 2.5; rostos gerados pelo Generated Photos.

- **Divisão por documento**, estratificada por tipo e condição: 640 treino, 180 validação e 180 teste. Todas as variações de uma foto ficam no mesmo conjunto. Uma verificação automática confirma que não há vazamento entre os conjuntos.
- **Detector:** imagens redimensionadas para no máximo 1024 px, com uma caixa por documento a partir dos 4 cantos anotados.
- **Qualidade:** recorte da caixa do documento com margem aleatória de 0 a 8% (o mesmo tipo de recorte que o detector entrega), redimensionado para 448×288 px. As classes borrado, reflexo e cortado são geradas com intensidade aleatória. As fotos da condição "reflexo de luz" entram como reflexo real e não são usadas como exemplo "ok".

## Resultados (conjunto de teste)
| Avaliação | Métricas |
|---|---|
| Detector | precisão 0,9997 · recall 1,000 · mAP@0,5 0,995 · mAP@0,5:0,95 0,994 |
| Qualidade | acurácia 0,997 · F1 macro 0,997 (2 erros em 700) |
| **Ponta a ponta** em fotos reais (detector → recorte → qualidade) | **100%** (180 de 180), em todas as 8 condições |

**Como ler os 100%:** as 180 fotos reais só têm dois casos reais (160 ok e 20 com reflexo); borrado e cortado existem só como degradação sintética. Zero erros em 180 não é erro zero: pela regra do três, o erro real pode chegar a cerca de 1,7% no geral e a 15% no reflexo, com 95% de confiança. Com documentos brasileiros, o número que vale é o do teste de campo, abaixo.

Curvas de treino: [`resultados/treino_detector_curvas.png`](resultados/treino_detector_curvas.png) (50 épocas, 34 min) e [`resultados/treino_qualidade_curvas.png`](resultados/treino_qualidade_curvas.png) (30 épocas, 10 min), no Apple M4.

### Uma correção que a avaliação de ponta a ponta revelou
Na primeira versão, o classificador foi treinado com o documento retificado pelos 4 cantos. Sozinho ele tinha 99,6% de acurácia, mas **de ponta a ponta caía para 85,6%**, porque o detector entrega uma caixa retangular, com um pouco de fundo. Nas fotos com o documento inclinado, os triângulos de fundo eram confundidos com "cortado" ou "reflexo". Treinar com o mesmo tipo de recorte usado na inferência levou o resultado de ponta a ponta para 100%.

### Análise de erros
- **Cortado classificado como ok (2 casos, ambos com fundo de tecido escuro):** a faixa escura que simula a parte fora da foto se confunde com o fundo, e o modelo não percebe onde o documento termina. Veja `resultados/qualidade_erros.jpg`.
- **Condições reais mais difíceis:** pouca luz e distorção projetiva foram as que mais erraram na primeira versão. Na versão final, as duas ficaram com 100%.

### Limites
- Cada foto do MIDV-2020 tem um único documento grande e bem enquadrado, o que facilita a detecção.
- Borrado e cortado são avaliados só com degradações sintéticas. De ponta a ponta, apenas ok e reflexo têm rótulo real.
- Os documentos do dataset são estrangeiros. O teste com documentos brasileiros está na seção abaixo.

## Teste de campo com documentos brasileiros
20 imagens de CIN, CNH e certidão brasileiras fictícias, com marca de espécime, em 4 condições ([`teste_campo/`](teste_campo/)). Resultado em [`resultados/teste_campo.md`](resultados/teste_campo.md) e [`resultados/teste_campo_ajustado.md`](resultados/teste_campo_ajustado.md).

| Detector | Documento encontrado (limiar 0,50) | Confiança mediana | Qualidade certa | Tipo certo (OCR) | MIDV-2020 (mAP@0,5 · ponta a ponta) |
|---|---|---|---|---|---|
| Treinado só no MIDV-2020 | **1 de 20** | 0,011 | 1 de 1 | 1 de 1 | 0,995 · 100% |
| Ajustado com documentos brasileiros sintéticos | **19 de 20** | 0,963 | 13 de 19 | 12 de 19 | 0,995 · 100% |

- **Causa:** mudança de domínio. O detector nunca tinha visto o layout, as cores e as proporções dos documentos brasileiros. Imagens grandes pioravam: reduzir para 512 px de largura subia de 1 para 7 de 20.
- **Correção:** [`src/gerar_documentos_br.py`](src/gerar_documentos_br.py) gera 750 fotos sintéticas de documentos brasileiros fictícios (CIN, CNH, CPF, certidão e conta de energia) sobre fundos procedurais, com perspectiva, rotação, reflexo, desfoque e compressão. Os fundos não imitam o fundo das imagens do teste, para o teste continuar medindo generalização. O detector foi ajustado por 30 épocas com MIDV-2020 + essas imagens (`datasets/misto_br.yaml`). O detector anterior ficou em `modelos/detector_midv.pt`.
- **O que ainda erra:** a qualidade "cortado" foi lida como "ok" em 5 casos, porque o recorte do teste deixa o documento só um pouco para fora da foto; e o OCR não identifica o tipo nos documentos borrados, o que é esperado. Quando o tipo não é lido, o app pergunta à pessoa qual documento ela fotografou.
- **Vídeo com documentos brasileiros:** o vídeo de 30 s do teste de campo (CIN, certidão e CNH passando pela câmera) foi processado com o detector ajustado e o OCR a cada 15 quadros ([`resultados/video_documentos_br_anotado.mp4`](resultados/video_documentos_br_anotado.mp4), quadro a quadro em `video_documentos_br_anotado.csv`). O documento foi detectado em todos os 900 quadros; o tipo foi lido como CIN, certidão e CNH na ordem em que aparecem; "cortado" aparece justamente quando o documento está entrando ou saindo da imagem. Com OCR, a média cai para 5 FPS, porque o OCR roda na CPU; sem OCR, 31 FPS neste vídeo.
- **Limite:** o ajuste e o teste usam documentos gerados por computador, por ferramentas diferentes. Falta testar com fotos de celular de documentos espécime impressos.

## Desempenho
Apple M4, 16 GB de RAM, inferência na GPU (MPS). Entrada de 576×1024 px, redimensionada para 640 px no detector e 224 px na qualidade. Medido em 100 imagens do teste, depois do aquecimento.

| Etapa | Média | Mediana | p95 |
|---|---|---|---|
| Detector | 14,3 ms | 15,3 ms | 20,3 ms |
| Qualidade | 6,4 ms | 6,1 ms | 7,2 ms |
| **Modo vídeo** (detector + qualidade) | **20,7 ms · 48 FPS** | 21,5 ms | 27,6 ms |
| OCR do tipo (CPU, uma vez por documento) | 428 ms | 399 ms | 685 ms |

No processamento contínuo de uma sequência de 360 quadros, a média foi de 49 FPS (`resultados/sequencia_anotada.mp4`). O OCR não roda em todos os quadros: ele é chamado na foto enviada ou, no vídeo, a cada N quadros.

## Limiares e escolhas
| Escolha | Valor | Por quê |
|---|---|---|
| Confiança mínima do detector | 0,50 | Na validação, o menor valor de um documento verdadeiro foi 0,938, e nenhuma caixa falsa passou de 0,25. Há margem para fotos reais mais difíceis sem aceitar falsos positivos. |
| Confiança mínima da qualidade | 0,60 | Abaixo disso o sistema não afirma o defeito: pede uma nova foto com boa luz. Na validação, só 1 de 700 ficou abaixo do limiar. |
| Modelos | YOLO11n e YOLO11n-cls | Versões leves (5 MB e 3 MB), que rodam em tempo real em notebook e servidor modesto. A tarefa (um documento grande por foto) não exige modelos maiores. |
| Tamanho de entrada | 640 px / 224 px | Padrão dos modelos pré-treinados. Equilibra velocidade e detalhe suficiente para perceber desfoque e reflexo. |

## Execução
```bash
# dados: baixar ftp://smartengines.com/midv-2020/dataset/photo.tar (4,0 GB) e extrair em datasets/photo
python src/preparar_dados.py --origem datasets/photo --destino datasets/preparado
python src/verificar_divisao.py --preparado datasets/preparado

# treino (pesos finais copiados para modelos/)
python src/treinar_detector.py --dados datasets/preparado/deteccao/dados.yaml
python src/treinar_qualidade.py --dados datasets/preparado/qualidade

# avaliação
cd src
python avaliar_ponta_a_ponta.py
python medir_desempenho.py --imagens 100
python processar_video.py --entrada meu_video.mp4 --saida ../resultados/video_anotado.mp4
```
Dependências: `ultralytics`, `opencv-python`, `easyocr`, `scikit-learn` e `matplotlib`.

## Integração
`POST /checar-documento` (veja [docs/contratos.md](../docs/contratos.md)) carrega `modelos/detector.pt` e `modelos/qualidade.pt` na primeira chamada. Sem os pesos ou com `VDP_MODO_DEMO=1`, a API responde com dados de demonstração.

No app, a tela **Conferir documentos** (`/conferir`) desenha a caixa sobre a foto enviada e mostra a qualidade, a confiança do modelo (documento e qualidade) e a dica.

## Próximos passos
- [x] Preparação dos dados com divisão por documento
- [x] Treino do detector e do classificador
- [x] Métricas, análise de erros, latência e FPS
- [x] Pipeline integrado à API
- [ ] Validação com fotos reais de documentos brasileiros fictícios e vídeo gravado pela equipe

## Entrega
- **Vídeo de demonstração:** https://youtu.be/wS1gNGfawLw
- **Relatório (PDF):** [Relatorio_Tecnico_Conferencia_por_Video.pdf](Relatorio_Tecnico_Conferencia_por_Video.pdf)

## Equipe
Pedro Iavarone Custódio (RM567638) · Rodrigo Ferreira Nery (RM568246)
