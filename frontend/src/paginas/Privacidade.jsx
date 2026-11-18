import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Aviso, Botao } from "../componentes/Basicos";
import { apagarMeusDados, mudarConsentimento, usuarioAtual } from "../servicos/armazenamento";
import { SERVICOS } from "../servicos/catalogo";

const formatarData = (iso) => (iso ? new Date(iso).toLocaleDateString("pt-BR", { timeZone: "UTC" }) : "—");

export default function Privacidade() {
  const [usuario, setUsuario] = useState(usuarioAtual);
  const [confirmando, setConfirmando] = useState(false);
  const [mensagem, setMensagem] = useState("");
  const navegar = useNavigate();

  function alternarAvisos(e) {
    if (e.target.checked && !usuario.email) {
      setMensagem("Para receber avisos é preciso ter um e-mail no cadastro.");
      return;
    }
    setUsuario(mudarConsentimento(e.target.checked));
    setMensagem(e.target.checked ? "Pronto: você vai receber avisos." : "Pronto: você não vai mais receber avisos.");
  }

  function apagar() {
    apagarMeusDados();
    navegar("/login", { replace: true });
  }

  return (
    <>
      <h1>Meus dados</h1>
      <div className="cartao">
        <h2 style={{ marginTop: 0 }}>O que guardamos e por quê</h2>
        <p>Guardamos só o necessário para mostrar seus serviços e lembrar você de prazos, e tudo fica neste aparelho.</p>
        <p>O CPF não é guardado por inteiro, a senha fica embaralhada e as fotos dos documentos não são salvas.</p>
        <p>Você pode parar de receber avisos ou apagar tudo a qualquer momento, nesta página.</p>
      </div>

      <div className="cartao">
        <h2 style={{ marginTop: 0 }}>Dados guardados neste aparelho</h2>
        <dl>
          <dt><strong>Nome</strong></dt>
          <dd>{usuario.nome}</dd>
          <dt><strong>CPF</strong></dt>
          <dd>{usuario.cpfExibicao}</dd>
          <dt><strong>Data de nascimento</strong></dt>
          <dd>{formatarData(usuario.nascimento)}</dd>
          <dt><strong>Cidade</strong></dt>
          <dd>{usuario.municipio}</dd>
          <dt><strong>E-mail</strong></dt>
          <dd>{usuario.email || "Não informado"}</dd>
          <dt><strong>Serviços</strong></dt>
          <dd>{usuario.servicos.map((s) => SERVICOS[s.id].curto).join(", ") || "Nenhum"}</dd>
        </dl>
      </div>

      <div className="cartao">
        <h2 style={{ marginTop: 0 }}>Avisos</h2>
        <div className="caixa-marcar">
          <input id="avisos" type="checkbox" checked={usuario.aceitaAvisos} onChange={alternarAvisos} />
          <label htmlFor="avisos">Aceito receber avisos sobre meus documentos</label>
        </div>
        {usuario.consentimentoEm && <p className="secundario pequeno">Autorizado em {new Date(usuario.consentimentoEm).toLocaleString("pt-BR")}.</p>}
        <Aviso tipo="ok">{mensagem}</Aviso>
      </div>

      <div className="cartao">
        <h2 style={{ marginTop: 0 }}>Apagar meus dados</h2>
        <p>Apaga seu cadastro, seus serviços e suas preferências deste aparelho. Não dá para desfazer.</p>
        {confirmando ? (
          <div role="alertdialog" aria-labelledby="confirmar-titulo">
            <p id="confirmar-titulo"><strong>Tem certeza? Tudo será apagado.</strong></p>
            <div className="linha">
              <Botao variante="perigo" onClick={apagar} autoFocus>
                Sim, apagar tudo
              </Botao>
              <Botao variante="secundario" onClick={() => setConfirmando(false)}>
                Cancelar
              </Botao>
            </div>
          </div>
        ) : (
          <Botao variante="perigo" onClick={() => setConfirmando(true)}>
            Apagar meus dados
          </Botao>
        )}
      </div>
    </>
  );
}
