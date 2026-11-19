import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Aviso, Botao, CampoTexto } from "../componentes/Basicos";
import { cadastrar } from "../servicos/armazenamento";
import { cpfValido, mascararDigitacao } from "../servicos/cpf";

const VAZIO = { nome: "", cpf: "", nascimento: "", municipio: "", email: "", senha: "", aceitaAvisos: false };

function validar(dados) {
  const erros = {};
  if (dados.nome.trim().split(/\s+/).length < 2) erros.nome = "Escreva o nome e o sobrenome.";
  if (!cpfValido(dados.cpf)) erros.cpf = "Este CPF não é válido. Confira os números.";
  if (!dados.nascimento) erros.nascimento = "Informe a data de nascimento.";
  else if (new Date(dados.nascimento) > new Date()) erros.nascimento = "A data não pode ser no futuro.";
  if (!dados.municipio.trim()) erros.municipio = "Informe a cidade onde você mora.";
  if (dados.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(dados.email)) erros.email = "Este e-mail não parece certo.";
  if (dados.aceitaAvisos && !dados.email) erros.email = "Para receber avisos, informe um e-mail.";
  if (dados.senha.length < 6) erros.senha = "A senha precisa ter pelo menos 6 caracteres.";
  return erros;
}

export function Cadastro() {
  const [dados, setDados] = useState(VAZIO);
  const [erros, setErros] = useState({});
  const [erroGeral, setErroGeral] = useState("");
  const navegar = useNavigate();
  const mudar = (campo) => (e) =>
    setDados((d) => ({
      ...d,
      [campo]: campo === "cpf" ? mascararDigitacao(e.target.value) : campo === "aceitaAvisos" ? e.target.checked : e.target.value,
    }));

  async function enviar(e) {
    e.preventDefault();
    const encontrados = validar(dados);
    setErros(encontrados);
    setErroGeral("");
    if (Object.keys(encontrados).length) {
      setErroGeral("Alguns campos precisam de ajuste. Veja as mensagens em vermelho.");
      return;
    }
    try {
      await cadastrar(dados);
      navegar("/meus-servicos", { replace: true });
    } catch (falha) {
      setErroGeral(falha.message);
    }
  }

  return (
    <div style={{ maxWidth: 560, margin: "0 auto" }}>
      <h1>Criar cadastro</h1>
      <p className="secundario">
        Os dados ficam só neste aparelho. O CPF não é guardado por inteiro e a senha é guardada embaralhada.
      </p>
      <form className="cartao" onSubmit={enviar} noValidate>
        <CampoTexto rotulo="Nome completo" autoComplete="name" value={dados.nome} onChange={mudar("nome")} erro={erros.nome} />
        <CampoTexto
          rotulo="CPF"
          inputMode="numeric"
          placeholder="000.000.000-00"
          value={dados.cpf}
          onChange={mudar("cpf")}
          erro={erros.cpf}
        />
        <CampoTexto rotulo="Data de nascimento" type="date" value={dados.nascimento} onChange={mudar("nascimento")} erro={erros.nascimento} />
        <CampoTexto rotulo="Cidade onde mora" autoComplete="address-level2" value={dados.municipio} onChange={mudar("municipio")} erro={erros.municipio} />
        <CampoTexto
          rotulo={dados.aceitaAvisos ? "E-mail" : "E-mail (opcional)"}
          type="email"
          autoComplete="email"
          dica={
            dados.aceitaAvisos
              ? "Obrigatório, porque você marcou que quer receber avisos."
              : "Só é obrigatório se você marcar, abaixo, que quer receber avisos."
          }
          value={dados.email}
          onChange={mudar("email")}
          erro={erros.email}
        />
        <CampoTexto
          rotulo="Senha"
          type="password"
          autoComplete="new-password"
          dica="Pelo menos 6 caracteres."
          value={dados.senha}
          onChange={mudar("senha")}
          erro={erros.senha}
        />
        <div className="caixa-marcar">
          <input id="aceita-avisos" type="checkbox" checked={dados.aceitaAvisos} onChange={mudar("aceitaAvisos")} />
          <label htmlFor="aceita-avisos">
            Aceito receber avisos sobre meus documentos (por exemplo, quando a CNH estiver perto de vencer). Posso
            cancelar quando quiser.
          </label>
        </div>
        <Aviso tipo="erro">{erroGeral}</Aviso>
        <Botao type="submit">Criar cadastro</Botao>
      </form>
      <p>
        Já tem cadastro? <Link to="/login">Entrar</Link>
      </p>
    </div>
  );
}
