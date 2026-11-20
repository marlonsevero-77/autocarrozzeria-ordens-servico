// Botão "olho" para mostrar ou ocultar a senha digitada.
// Arquivo externo (sem script embutido) para respeitar a Content-Security-Policy.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".btn-mostrar-senha").forEach((botao) => {
    const campo = document.getElementById(botao.dataset.alvo);
    const icone = botao.querySelector("i");
    if (!campo) return;

    botao.addEventListener("click", () => {
      const mostrar = campo.type === "password";
      campo.type = mostrar ? "text" : "password";
      const texto = mostrar ? "Ocultar senha" : "Mostrar senha";
      botao.setAttribute("aria-pressed", String(mostrar));
      botao.setAttribute("aria-label", texto);
      botao.title = texto;
      icone.className = mostrar ? "bi bi-eye-slash" : "bi bi-eye";
      campo.focus();
    });

    // Por segurança, a senha volta a ficar oculta ao enviar o formulário.
    campo.form?.addEventListener("submit", () => {
      campo.type = "password";
    });
  });
});
