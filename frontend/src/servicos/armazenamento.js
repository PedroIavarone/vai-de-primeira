// Tudo que o app lê ou grava no navegador (localStorage) passa por aqui.
//
// Proteção de dados:
// - o CPF nunca é guardado por inteiro: a chave da conta é o hash SHA-256 do CPF
//   e, para exibir, guardamos só a versão mascarada (***.456.789-**);
// - a senha é guardada como hash SHA-256 com um sal aleatório por conta;
// - "Apagar meus dados" remove tudo o que o app gravou.
import { cpfParaExibir, somenteDigitos } from "./cpf";

const PREFIXO = "vdp:";
const CONTAS = `${PREFIXO}contas`;
const SESSAO = `${PREFIXO}sessao`;
const PREFERENCIAS = `${PREFIXO}preferencias`;

function ler(chave, padrao) {
  try {
    const valor = localStorage.getItem(chave);
    return valor ? JSON.parse(valor) : padrao;
  } catch {
    return padrao;
  }
}

function gravar(chave, valor) {
  try {
    localStorage.setItem(chave, JSON.stringify(valor));
  } catch {
    /* navegador sem armazenamento: o app continua, só não lembra */
  }
}

async function sha256(texto) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

const chaveDoCpf = (cpf) => sha256(`vdp-cpf:${somenteDigitos(cpf)}`);

function novoSal() {
  return [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ---------------------------------------------------------------- contas
export async function cadastrar({ nome, cpf, nascimento, municipio, email, senha, aceitaAvisos }) {
  const contas = ler(CONTAS, {});
  const id = await chaveDoCpf(cpf);
  if (contas[id]) throw new Error("Já existe um cadastro com este CPF neste aparelho. Use a opção Entrar.");
  const sal = novoSal();
  contas[id] = {
    nome: nome.trim(),
    cpfExibicao: cpfParaExibir(cpf),
    nascimento,
    municipio: municipio.trim(),
    email: email.trim(),
    aceitaAvisos: Boolean(aceitaAvisos),
    consentimentoEm: aceitaAvisos ? new Date().toISOString() : null,
    sal,
    senhaHash: await sha256(`${sal}:${senha}`),
    servicos: [],
    criadoEm: new Date().toISOString(),
  };
  gravar(CONTAS, contas);
  gravar(SESSAO, { id });
  return id;
}

export async function entrar(cpf, senha) {
  const contas = ler(CONTAS, {});
  const id = await chaveDoCpf(cpf);
  const conta = contas[id];
  // Mesma mensagem para CPF ou senha errados: não revela qual dos dois está certo.
  if (!conta || conta.senhaHash !== (await sha256(`${conta.sal}:${senha}`))) {
    throw new Error("CPF ou senha não conferem. Confira e tente de novo.");
  }
  gravar(SESSAO, { id });
  return id;
}

export function sair() {
  localStorage.removeItem(SESSAO);
}

export function idDaSessao() {
  return ler(SESSAO, null)?.id ?? null;
}

export function usuarioAtual() {
  const id = idDaSessao();
  if (!id) return null;
  const conta = ler(CONTAS, {})[id];
  if (!conta) return null;
  const { sal, senhaHash, ...publico } = conta; // nunca expõe sal e hash para as telas
  return { id, ...publico };
}

export function atualizarUsuario(mudancas) {
  const id = idDaSessao();
  const contas = ler(CONTAS, {});
  if (!id || !contas[id]) return null;
  contas[id] = { ...contas[id], ...mudancas };
  gravar(CONTAS, contas);
  return usuarioAtual();
}

export function mudarConsentimento(aceita) {
  return atualizarUsuario({ aceitaAvisos: aceita, consentimentoEm: aceita ? new Date().toISOString() : null });
}

// ---------------------------------------------------------------- serviços do usuário
export function salvarServico(servicoId, mudancas = {}) {
  const usuario = usuarioAtual();
  if (!usuario) return null;
  const servicos = [...usuario.servicos];
  const i = servicos.findIndex((s) => s.id === servicoId);
  const atual = i >= 0 ? servicos[i] : { id: servicoId, status: "nao_iniciado", indice: null, orientado: false };
  const novo = { ...atual, ...mudancas, atualizadoEm: new Date().toISOString() };
  if (i >= 0) servicos[i] = novo;
  else servicos.push(novo);
  return atualizarUsuario({ servicos });
}

export function removerServico(servicoId) {
  const usuario = usuarioAtual();
  if (!usuario) return null;
  return atualizarUsuario({ servicos: usuario.servicos.filter((s) => s.id !== servicoId) });
}

// ---------------------------------------------------------------- apagar tudo
export function apagarMeusDados() {
  const id = idDaSessao();
  const contas = ler(CONTAS, {});
  if (id) delete contas[id];
  if (Object.keys(contas).length) gravar(CONTAS, contas);
  else localStorage.removeItem(CONTAS);
  localStorage.removeItem(SESSAO);
  localStorage.removeItem(PREFERENCIAS);
}

// ---------------------------------------------------------------- preferências de acessibilidade
export const lerPreferencias = () => ler(PREFERENCIAS, { contraste: false, escala: 100 });
export const gravarPreferencias = (p) => gravar(PREFERENCIAS, p);
