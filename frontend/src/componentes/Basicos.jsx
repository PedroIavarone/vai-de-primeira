import { useId } from "react";
import { Link } from "react-router-dom";

export function Botao({ variante, grande, para, children, ...resto }) {
  const classe = ["botao", variante && `botao--${variante}`, grande && "botao--grande"].filter(Boolean).join(" ");
  if (para) {
    return (
      <Link className={classe} to={para} {...resto}>
        {children}
      </Link>
    );
  }
  return (
    <button type="button" className={classe} {...resto}>
      {children}
    </button>
  );
}

export function CampoTexto({ rotulo, dica, erro, ...resto }) {
  const id = useId();
  const descricao = [dica && `${id}-dica`, erro && `${id}-erro`].filter(Boolean).join(" ") || undefined;
  return (
    <div className="campo">
      <label htmlFor={id}>{rotulo}</label>
      {dica && (
        <span id={`${id}-dica`} className="dica">
          {dica}
        </span>
      )}
      <input id={id} aria-invalid={Boolean(erro)} aria-describedby={descricao} {...resto} />
      {erro && (
        <span id={`${id}-erro`} className="erro">
          {erro}
        </span>
      )}
    </div>
  );
}

export function Selo({ tipo, children }) {
  return <span className={`selo selo--${tipo}`}>{children}</span>;
}

// Mensagens que mudam na tela são anunciadas pelo leitor de tela (aria-live).
export function Aviso({ tipo, children }) {
  if (!children) return <div aria-live="polite" />;
  return (
    <div className={`aviso${tipo ? ` aviso--${tipo}` : ""}`} role={tipo === "erro" ? "alert" : "status"} aria-live="polite">
      {children}
    </div>
  );
}
