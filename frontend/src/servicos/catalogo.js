// Serviços cobertos pelo Vai de Primeira. Informações tiradas das fontes oficiais da base de
// conhecimento (genai/fontes/fontes.csv). Para dúvidas fora deste resumo, o app manda ao assistente,
// que responde citando a fonte.

export const SERVICOS = {
  cin: {
    id: "cin",
    nome: "Carteira de Identidade Nacional (CIN)",
    curto: "Identidade nova (CIN)",
    gratuito: true,
    custo: "A primeira via e as renovações são gratuitas.",
    levar: ["Certidão de nascimento ou de casamento (original, legível, sem reflexo na foto)", "CPF"],
    onde: "Posto de atendimento de identificação do seu estado (em São Paulo, no Poupatempo), com agendamento.",
    conferir: true,
    fontes: [
      { nome: "gov.br · Carteira de Identidade Nacional", url: "https://www.gov.br/gestao/pt-br/identidade-nacional" },
      { nome: "Poupatempo · Carteira de Identidade Nacional", url: "https://www.poupatempo.sp.gov.br/carta/D97C3844-A2D9-4C9E-B364-CB4FEB26A1FB" },
    ],
  },
  cnh: {
    id: "cnh",
    nome: "Renovação da CNH",
    curto: "Renovar a CNH",
    gratuito: false,
    custo: "Tem custo: exame médico e, se quiser a CNH impressa, a taxa de emissão.",
    levar: ["CNH atual", "Comprovante de residência", "Exame médico (as categorias C, D e E também pedem exame toxicológico)"],
    onde: "Pela internet no Detran ou no Poupatempo. A clínica do exame médico é credenciada pelo Detran.",
    conferir: true,
    fontes: [
      { nome: "Poupatempo · Renovação da CNH", url: "https://www.poupatempo.sp.gov.br/carta/F8D2DBE7-66BE-4AEC-9B0F-25912922D566" },
      { nome: "Detran-SP · Dúvidas sobre renovação", url: "http://mobile.detran.sp.gov.br/wps/wcm/connect/portaldetran/detran/duvidasFrequentes/SA-CNH-Habilitacao/SA-Renovacao/" },
    ],
  },
  cadunico: {
    id: "cadunico",
    nome: "Cadastro Único",
    curto: "Cadastro Único",
    gratuito: true,
    custo: "É gratuito. Ninguém pode cobrar para fazer ou atualizar o cadastro.",
    levar: [
      "CPF (de preferência) ou título de eleitor de quem vai responder pela família",
      "Comprovante de residência",
      "Pelo menos um documento de cada pessoa da família que mora junto",
    ],
    onde: "No CRAS ou no posto do Cadastro Único da sua cidade.",
    conferir: true,
    fontes: [
      { nome: "gov.br · Inscrever-se no Cadastro Único", url: "https://www.gov.br/pt-br/servicos/inscrever-se-no-cadastro-unico-para-programas-sociais-do-governo-federal" },
      { nome: "MDS · Cadastro Único", url: "https://www.gov.br/mds/pt-br/acoes-e-programas/cadastro-unico" },
    ],
  },
  bpc: {
    id: "bpc",
    nome: "Benefício de Prestação Continuada (BPC)",
    curto: "Entender o BPC",
    gratuito: true,
    custo: "O pedido é gratuito e não precisa de intermediário.",
    levar: [
      "Cadastro Único feito e atualizado",
      "Documento com foto e CPF de quem vai pedir",
    ],
    onde: "Pelo aplicativo ou site Meu INSS, ou pela Central 135 do INSS. O CRAS ajuda a entender se você pode ter direito.",
    regra: "É para pessoas com 65 anos ou mais, ou com deficiência, com renda por pessoa da família igual ou menor que 1/4 do salário mínimo. Só o INSS decide quem tem direito.",
    conferir: false,
    fontes: [
      { nome: "gov.br · Solicitar o benefício assistencial ao idoso", url: "https://www.gov.br/pt-br/servicos/solicitar-beneficio-assistencial-ao-idoso" },
      { nome: "INSS · BPC à pessoa idosa", url: "https://www.gov.br/inss/pt-br/direitos-e-deveres/beneficios-assistenciais/beneficio-assistencial-a-pessoa-idosa-bpc-loas" },
    ],
  },
};

export const LISTA_SERVICOS = Object.values(SERVICOS);

export const STATUS = {
  nao_iniciado: "Não iniciado",
  em_andamento: "Em andamento",
  concluido: "Concluído",
};

export const FAIXAS = {
  pronta: "Pronta para ir",
  quase: "Quase lá",
  nao_pronta: "Ainda não está pronta",
};

// Documentos que a conferência por foto procura em cada serviço (mesma regra de api/prontidao.py).
export const DOCUMENTOS_DO_SERVICO = {
  cin: ["certidao", "cpf"],
  cnh: ["cnh", "comprovante_residencia"],
  cadunico: ["cpf", "comprovante_residencia"],
};

export const TIPOS_DOCUMENTO = {
  cin: "Documento de identidade",
  cnh: "CNH",
  cpf: "CPF",
  certidao: "Certidão de nascimento ou casamento",
  comprovante_residencia: "Comprovante de residência",
  desconhecido: "Documento não reconhecido",
};

export const QUALIDADES = {
  ok: "Foto boa",
  borrado: "Foto borrada",
  reflexo: "Foto com reflexo",
  cortado: "Documento cortado",
};
