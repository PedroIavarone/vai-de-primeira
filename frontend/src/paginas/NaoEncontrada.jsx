import { Botao } from "../componentes/Basicos";

export default function NaoEncontrada() {
  return (
    <>
      <h1>Página não encontrada</h1>
      <p>O endereço pode estar errado ou a página mudou de lugar.</p>
      <Botao para="/">Voltar ao início</Botao>
    </>
  );
}
