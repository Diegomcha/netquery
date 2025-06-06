# Cambios
En teoría los cambios no deberían de afectar a ningún otro usuario, deberían de ser locales al usuario `go9689`.

## Detalles

### Conexión a Ubuntu a través de VSCode
A grandes rasgos conlleva la instalación automática a nivel de usuario de un servicio `vscode-server` con una serie de extensiones que facilitan el desarrollo Python.
Dicho servicio está alojado en la carpeta home del usuario en un directorio `.vscode-server` que contiene tanto los binarios como las configuraciones y las distintas extensiones.

### Creación de un directorio para el proyecto
Creación del directorio `app` en el home del usuario.

### Creación de un entorno virtual (.venv)
Dicho entorno esta en el directorio `app/.venv`. De esta forma los paquetes se instalan de forma local al proyecto.

### Instalación de paquetes
Estos paquetes se han instalado en el entorno virtual local.
- `netmiko` y deps.
- `typer` y deps (si existen).