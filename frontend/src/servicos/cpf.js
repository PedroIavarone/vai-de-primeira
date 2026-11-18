// CPF: máscara, validação dos dígitos verificadores e exibição mascarada.

export const somenteDigitos = (texto) => (texto || "").replace(/\D/g, "").slice(0, 11);

export function mascararDigitacao(texto) {
  const d = somenteDigitos(texto);
  return d
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d{1,2})$/, ".$1-$2");
}

export function cpfValido(texto) {
  const d = somenteDigitos(texto);
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  const digito = (base) => {
    const soma = [...base].reduce((total, n, i) => total + Number(n) * (base.length + 1 - i), 0);
    const resto = (soma * 10) % 11;
    return resto === 10 ? 0 : resto;
  };
  return digito(d.slice(0, 9)) === Number(d[9]) && digito(d.slice(0, 10)) === Number(d[10]);
}

// Depois do cadastro, a tela só mostra o meio do CPF: ***.456.789-**
export function cpfParaExibir(texto) {
  const d = somenteDigitos(texto);
  return `***.${d.slice(3, 6)}.${d.slice(6, 9)}-**`;
}
