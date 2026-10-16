// Campos secretos (contraseña de sudo, valores de variables, tokens) sin que el navegador ofrezca
// "¿Guardar contraseña?": un <input type="password"> lo dispara siempre (y toma el campo de al lado
// como "usuario"). Se usa texto enmascarado con CSS (.secret-field) donde el navegador lo soporta;
// si no, se queda en password (enmascarar pesa más que el aviso).
export const SECRET_TYPE: "text" | "password" =
  typeof CSS !== "undefined" && CSS.supports?.("-webkit-text-security", "disc") ? "text" : "password";

// Lo que los gestores de contraseñas (el del navegador, 1Password, LastPass, Bitwarden) respetan.
export const noSave = {
  autocomplete: "off",
  "data-1p-ignore": "",
  "data-lpignore": "true",
  "data-bwignore": "",
  "data-form-type": "other",
} as const;
