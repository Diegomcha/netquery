# Comandos Útiles de Cisco IOS

| Comando                              | Descripción                                                              |
| ------------------------------------ | ------------------------------------------------------------------------ |
| `show run`                           | Muestra la configuración en ejecución (running configuration)            |
| `/texto`                             | Muestra a partir de la primera coincidencia (útil para saltar el banner) |
| `+texto`                             | Muestra solo las coincidencias                                           |
| `show term length 0`                 | Desactiva el paginado (`--More--`)                                       |
| `show run linenum`                   | Muestra el número de línea de cada parámetro (no relevante)              |
| `show run \| i texto\|text2\|texto3` | Búsqueda de múltiples coincidencias                                      |
| `show run \| section bgp`            | Muestra la sección de configuración de BGP                               |
| `more flash:/text`                   | Lee el contenido de un archivo en la memoria flash                       |
| `show run \| i ^texto`               | Muestra líneas que comienzan con "texto"                                 |
| `show run \| i texto$`               | Muestra líneas que terminan con "texto"                                  |
| `show run \| i \.`                   | Muestra líneas que contienen un punto (útil para buscar IPs)             |
| `show run all`                       | Muestra la configuración incluyendo valores por defecto (poco útil)      |
