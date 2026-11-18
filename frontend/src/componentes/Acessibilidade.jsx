import { createContext, useContext, useEffect, useState } from "react";
import { gravarPreferencias, lerPreferencias } from "../servicos/armazenamento";

const Contexto = createContext(null);
export const useAcessibilidade = () => useContext(Contexto);

// Lê em voz alta (Web Speech API, voz pt-BR). Devolve false se o navegador não tiver voz.
export function falar(texto) {
  if (!("speechSynthesis" in window) || !texto) return false;
  window.speechSynthesis.cancel();
  const fala = new SpeechSynthesisUtterance(texto);
  fala.lang = "pt-BR";
  fala.rate = 0.95;
  const voz = window.speechSynthesis.getVoices().find((v) => v.lang?.toLowerCase().startsWith("pt"));
  if (voz) fala.voice = voz;
  window.speechSynthesis.speak(fala);
  return true;
}

export function ProvedorAcessibilidade({ children }) {
  const [preferencias, setPreferencias] = useState(lerPreferencias);

  useEffect(() => {
    const raiz = document.documentElement;
    raiz.dataset.contraste = preferencias.contraste ? "alto" : "normal";
    raiz.style.fontSize = `${preferencias.escala}%`;
    gravarPreferencias(preferencias);
  }, [preferencias]);

  const valor = {
    ...preferencias,
    alternarContraste: () => setPreferencias((p) => ({ ...p, contraste: !p.contraste })),
    mudarEscala: (passo) =>
      setPreferencias((p) => ({ ...p, escala: Math.min(150, Math.max(100, p.escala + passo)) })),
  };
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function BarraAcessibilidade() {
  const { contraste, escala, alternarContraste, mudarEscala } = useAcessibilidade();
  const [lendo, setLendo] = useState(false);

  function ouvirPagina() {
    if (lendo) {
      window.speechSynthesis?.cancel();
      setLendo(false);
      return;
    }
    const texto = document.getElementById("conteudo")?.innerText;
    if (falar(texto)) {
      setLendo(true);
      const fim = setInterval(() => {
        if (!window.speechSynthesis.speaking) {
          setLendo(false);
          clearInterval(fim);
        }
      }, 500);
    }
  }

  return (
    <div className="barra-acessibilidade" role="group" aria-label="Acessibilidade">
      <button type="button" onClick={() => mudarEscala(-10)} disabled={escala <= 100} aria-label="Diminuir a letra">
        A−
      </button>
      <button type="button" onClick={() => mudarEscala(10)} disabled={escala >= 150} aria-label="Aumentar a letra">
        A+
      </button>
      <button type="button" onClick={alternarContraste} aria-pressed={contraste}>
        Alto contraste
      </button>
      <button type="button" onClick={ouvirPagina} aria-pressed={lendo}>
        {lendo ? "Parar leitura" : "Ouvir esta página"}
      </button>
    </div>
  );
}
