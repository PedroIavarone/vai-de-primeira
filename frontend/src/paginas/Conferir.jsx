import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Aviso, Selo } from "../componentes/Basicos";
import CartaoProntidao from "../componentes/CartaoProntidao";
import { buscarFila, calcularProntidao, checarDocumento } from "../servicos/api";
import { salvarServico, usuarioAtual } from "../servicos/armazenamento";
import { DOCUMENTOS_DO_SERVICO, LISTA_SERVICOS, QUALIDADES, SERVICOS, TIPOS_DOCUMENTO } from "../servicos/catalogo";

const SERVICOS_CONFERIR = LISTA_SERVICOS.filter((s) => s.conferir);

export default function Conferir() {
  const [parametros, setParametros] = useSearchParams();
  const servicoId = SERVICOS[parametros.get("servico")]?.conferir ? parametros.get("servico") : "cin";
  const [unidades, setUnidades] = useState([]);
  const [unidadeId, setUnidadeId] = useState("");
  const [documentos, setDocumentos] = useState({}); // tipo -> {tipo, qualidade, dica, confianca}
  const [ultimaFoto, setUltimaFoto] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [simulado, setSimulado] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [dica, setDica] = useState("");
  const [semTipo, setSemTipo] = useState(null);

  function confirmarTipo(tipo) {
    if (!tipo) return;
    setDocumentos((atual) => ({ ...atual, [tipo]: { ...semTipo, tipo, informadoPelaPessoa: true } }));
    setSemTipo(null);
  }

  const registro = usuarioAtual()?.servicos.find((s) => s.id === servicoId);
  const orientado = Boolean(registro?.orientado);

  useEffect(() => {
    buscarFila()
      .then((f) => {
        setUnidades(f.unidades);
        setUnidadeId((atual) => atual || f.unidades[0]?.id || "");
      })
      .catch(() => setUnidades([]));
  }, []);

  // Sempre que algo muda, o índice é recalculado na API (regra explicável em api/prontidao.py).
  useEffect(() => {
    const pedido = {
      servico: servicoId,
      unidade_id: unidadeId || null,
      orientado,
      documentos: Object.values(documentos).map(({ tipo, qualidade }) => ({ tipo, qualidade })),
    };
    calcularProntidao(pedido)
      .then((r) => {
        setResultado(r);
        salvarServico(servicoId, {
          indice: r.indice,
          faixa: r.faixa,
          status: registro?.status === "concluido" ? "concluido" : "em_andamento",
        });
      })
      .catch((e) => setErro(e.message));
    // registro muda a cada gravação; o cálculo depende só destes campos
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [servicoId, unidadeId, orientado, documentos]);

  async function enviarFoto(e) {
    const arquivo = e.target.files?.[0];
    e.target.value = "";
    if (!arquivo) return;
    setErro("");
    setDica("");
    setCarregando(true);
    setUltimaFoto(URL.createObjectURL(arquivo)); // a foto fica só na memória desta tela, não é salva
    try {
      const r = await checarDocumento(arquivo);
      setSimulado(r.simulado);
      const encontrados = r.documentos.filter((d) => d.tipo !== "desconhecido");
      // A foto tem um documento, mas o texto não deu para ler: a pessoa diz qual é, e a qualidade conferida vale.
      const semTipo = r.documentos.find((d) => d.tipo === "desconhecido");
      setSemTipo(encontrados.length ? null : semTipo || null);
      if (!r.documentos.length) {
        setDica(r.dica || "Não reconheci nenhum documento. Coloque o documento inteiro na foto, sobre uma mesa.");
      }
      setDocumentos((atual) => {
        const novo = { ...atual };
        encontrados.forEach((d) => {
          novo[d.tipo] = d;
        });
        return novo;
      });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  }

  const trocarServico = (id) => {
    setParametros({ servico: id });
    setDocumentos({});
    setUltimaFoto(null);
    setSemTipo(null);
  };

  return (
    <>
      <h1>Conferir documentos</h1>
      <p className="secundario">
        Tire uma foto de cada documento. A conferência avisa se a foto está borrada, com reflexo ou cortada, e o
        Índice de Prontidão mostra a chance de resolver na primeira ida.
      </p>

      <div className="grade">
        <div className="campo">
          <label htmlFor="servico">Serviço</label>
          <select id="servico" value={servicoId} onChange={(e) => trocarServico(e.target.value)}>
            {SERVICOS_CONFERIR.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="unidade">Unidade onde pretende ir</label>
          <select id="unidade" value={unidadeId} onChange={(e) => setUnidadeId(e.target.value)}>
            {unidades.length === 0 && <option value="">Sem dados de fila agora</option>}
            {unidades.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nome}: cerca de {u.espera_min} min de espera
              </option>
            ))}
          </select>
        </div>
      </div>

      <CartaoProntidao resultado={resultado} />

      <section className="cartao" aria-labelledby="fotos">
        <h2 id="fotos" style={{ marginTop: 0 }}>
          Fotos dos documentos
        </h2>
        <p>
          Documentos pedidos: <strong>{SERVICOS[servicoId].levar.join("; ")}</strong>
        </p>
        <label className="botao" htmlFor="foto" style={{ marginBottom: "1rem" }}>
          {carregando ? "Conferindo a foto..." : "Tirar ou escolher uma foto"}
        </label>
        <input
          id="foto"
          className="visualmente-oculto"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          onChange={enviarFoto}
          disabled={carregando}
        />
        <Aviso tipo="erro">{erro}</Aviso>
        <Aviso>{dica}</Aviso>
        {semTipo && (
          <div className="aviso" role="status">
            <p>
              Encontrei um documento na foto ({QUALIDADES[semTipo.qualidade]?.toLowerCase() || semTipo.qualidade}), mas não
              consegui ler qual é. Qual documento você fotografou?
            </p>
            <div className="linha">
              {DOCUMENTOS_DO_SERVICO[servicoId].map((tipo) => (
                <button key={tipo} type="button" className="botao botao--secundario" onClick={() => confirmarTipo(tipo)}>
                  {TIPOS_DOCUMENTO[tipo]}
                </button>
              ))}
            </div>
          </div>
        )}
        {simulado && (
          <p className="pequeno secundario">Conferência em modo de demonstração (o modelo de visão não está ligado nesta API).</p>
        )}

        {Object.keys(documentos).length > 0 && (
          <ul className="limpa">
            {Object.values(documentos).map((d) => (
              <li key={d.tipo} className="cartao">
                <p className="linha" style={{ marginBottom: d.dica ? "0.5rem" : 0 }}>
                  <strong>{TIPOS_DOCUMENTO[d.tipo] || d.tipo}</strong>
                  {d.informadoPelaPessoa && <span className="pequeno secundario">(tipo informado por você)</span>}
                  <Selo tipo={d.qualidade === "ok" ? "ok" : "erro"}>{QUALIDADES[d.qualidade] || d.qualidade}</Selo>
                </p>
                {d.dica && <p style={{ margin: 0 }}>{d.dica}</p>}
              </li>
            ))}
          </ul>
        )}
        {ultimaFoto && <img src={ultimaFoto} alt="Última foto enviada" style={{ maxWidth: "100%", maxHeight: 280, borderRadius: 8 }} />}
        <p className="pequeno secundario">
          As fotos não são guardadas: são conferidas e descartadas. A conferência é uma ajuda, quem confirma o
          documento é sempre o atendente.
        </p>
      </section>
    </>
  );
}
