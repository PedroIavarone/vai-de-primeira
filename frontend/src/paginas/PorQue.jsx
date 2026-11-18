import { Botao } from "../componentes/Basicos";

const ODS = [
  {
    numero: 10,
    nome: "Redução das desigualdades",
    texto:
      "Quem mais perde viagens por falta de um documento é quem mora longe, lê com dificuldade e tem menos dinheiro para a passagem. O Vai de Primeira avisa antes, explica em linguagem simples e confere os documentos, para que essas pessoas resolvam na primeira ida.",
  },
  {
    numero: 9,
    nome: "Indústria, inovação e infraestrutura",
    texto:
      "Usamos inteligência artificial e sensores para que o serviço público procure o cidadão: conferência de documentos pela câmera, assistente com fontes oficiais e fila real medida na porta da unidade.",
  },
  {
    numero: 4,
    nome: "Educação de qualidade",
    texto:
      "Cada resposta ensina o caminho: o que levar, onde ir, o que é gratuito e como reconhecer um site falso. Quem aprende uma vez consegue ajudar a família e os vizinhos.",
  },
  {
    numero: 11,
    nome: "Cidades e comunidades sustentáveis",
    texto:
      "Menos viagens perdidas é menos ônibus lotado, menos fila e menos tempo de espera. A fila ao vivo e os avisos ajudam a distribuir melhor as pessoas entre as unidades.",
  },
];

export default function PorQue() {
  return (
    <>
      <h1>Por que existimos</h1>
      <p>
        Dona Francisca, 67 anos, mora na zona rural e gasta 1h30 de ônibus até a central de atendimento. Já perdeu duas
        viagens: na primeira faltou um documento, na segunda a certidão estava ilegível. O Vai de Primeira existe para
        que ninguém perca uma viagem por falta de informação.
      </p>
      <h2>Objetivos de Desenvolvimento Sustentável</h2>
      <ul className="limpa">
        {ODS.map((o) => (
          <li key={o.numero} className="cartao">
            <h3>
              ODS {o.numero} · {o.nome}
            </h3>
            <p style={{ margin: 0 }}>{o.texto}</p>
          </li>
        ))}
      </ul>
      <Botao para="/totem" variante="secundario">
        Ver o modo totem
      </Botao>
    </>
  );
}
