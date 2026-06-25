// auth-mode.js — en modo federado, la pantalla de login muestra "Entrar con Lockatus" y oculta
// el form de contraseña por nivel (la identidad y el rol los gestiona el hub). Va como archivo
// externo (no inline) porque la CSP de Escriba no permite scripts inline ('self' only).
(function () {
  var mode = (document.querySelector('meta[name="esc-auth-mode"]') || {}).content || "local";
  if (mode !== "federado") return;
  function apply() {
    var f = document.querySelector(".login-form");
    if (!f) return;
    ["#loginPass", ".pass-wrap", "#loginBtn", ".roles-hint", ".login-label"].forEach(function (s) {
      var e = f.querySelector(s); if (e) e.style.display = "none";
    });
    var sso = document.getElementById("loginSSO"); if (sso) sso.style.display = "block";
    var p = f.querySelector("p"); if (p) p.textContent = "Acceso unificado de la Suite Escriba.";
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply);
  else apply();
})();
