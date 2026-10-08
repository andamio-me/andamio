# 0013. Secretos cifrados en el repo con sops + age

- **Estado:** Aceptada
- **Fecha:** 2026-10-07

## Decisión
- **sops + age.** Una llave age; la privada vive solo en el WSL del operador
  (`~/.config/sops/age/keys.txt`) y en el gestor de contraseñas. El servidor
  nunca la tiene: Ansible descifra en el WSL y escribe los archivos ya en claro.
- **Qué va cifrado en el repo:**
  - `<stack>/secrets.sops.env`: el `.env` de cada stack y app (formato dotenv:
    los nombres de las variables quedan visibles, los valores no).
  - `host/sops/*.sops`: `/etc/restic/env`, `/etc/restic/password` y
    `/etc/homelab/telegram.env` (binario: se reproducen byte a byte).
- **`TAG` no se cifra**: lo cambia `deploy-app.sh` en cada deploy; Ansible
  conserva el valor que haya en el servidor.
- **Ansible nunca imprime secretos**: tareas con `no_log` y `diff: false`.
- **Editar un secreto:** `sops stacks/data/secrets.sops.env`, commit y
  `ansible-playbook site.yml -K --tags homelab`. Si cambia en el servidor:
  `ansible-playbook tools/cifrar-secretos-host.yml -K`.

## Consecuencias
- El gestor de contraseñas solo necesita la llave age y la contraseña de sudo.
- Perder la llave age = perder el acceso a todos los secretos del repo (el
  backup de restic sigue sirviendo, pero sus credenciales también están cifradas).
- Siguen fuera del repo (en restic): llaves de host SSH, WireGuard, deploy key
  del repo y login de GHCR.
- Rotar la llave age: `sops updatekeys` en cada archivo tras cambiar `.sops.yaml`.
