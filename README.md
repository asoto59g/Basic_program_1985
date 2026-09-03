# Rescate de NIVEL2.BAS (BASICA, 1990) → Python

[![Licencia MIT](https://img.shields.io/badge/Licencia-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39+-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://basicprogram1985-qdzcuwr6wwgke5w6rnqopx.streamlit.app/)
[![BASICA 1990](https://img.shields.io/badge/BASICA-1990-1B4D3E.svg)](original/NIVEL2.txt)
[![Último commit](https://img.shields.io/github/last-commit/asoto59g/Basic_program_1985)](https://github.com/asoto59g/Basic_program_1985)



#**App en línea:** [https://basicprogram1985-qdzcuwr6wwgke5w6rnqopx.streamlit.app/](https://basicprogram1985-qdzcuwr6wwgke5w6rnqopx.streamlit.app/)

Este proyecto documenta, con un caso real, cómo **recuperar el código fuente** de un programa IBM BASICA / GW-BASIC de finales de los 80 y **volver a usarlo** en una máquina actual. El ejemplar es `NIVEL2.BAS` (1990): compensación de **corte y relleno** en una nivelación topográfica por cuadrícula.

Sirve como guía para otros discos de esa época: menús, facturación, inventario o sistemas que en la práctica eran el ERP de una empresa. Ver [docs/RESCATE-SISTEMAS-BASIC.md](docs/RESCATE-SISTEMAS-BASIC.md).

---

## Qué hay en este disco

A finales de los 80 el flujo de trabajo era:

1. Arrancar DOS.
2. Ejecutar el intérprete `BASICA.EXE` (IBM, 1985) o `GWBASIC.EXE`.
3. `LOAD "NIVEL2"` y `RUN`.

En el folder original aparecían, entre otros:

| Pieza | Rol |
|---|---|
| `BASICA.EXE` / `BASIC.COM` | Intérprete Microsoft. **No se publica** (copyright). |
| `NIVEL2.BAS` / `NIVEL.BAS` | Programa **tokenizado** (no es texto). |
| `LOTE` + `LOTE.DAT` | Elevaciones (binario MBF, 4 bytes) y metadatos ASCII. |
| `TOPO92\` | Lotes de campo NIVEL2 (Bocana, Las Piedras, etc.). |
| `TOPO91\` | Otro programa; el formato no es NIVEL2. |

`PRUEBA.DAT` (Las Piedras, 3×3, 1995) es el lote de comprobación: el puerto Python reproduce centroide, pendientes y volúmenes del `.DAT` guardado por BASICA.

---

## El problema: el `.BAS` no se puede abrir en el Bloc de notas

BASICA, por defecto, hace `SAVE "NIVEL2"` en **formato tokenizado**:

- Primer byte: `FF`.
- Cada línea: puntero, número de línea, palabras clave como un byte (`CLS` = `C0`, `PRINT` = `91`, `OPTION` = `B8`…) y un `00` al final.

Un editor moderno muestra basura. No está cifrado: está **comprimido con la tabla de tokens** de GW-BASIC/BASICA.

### Cómo se rescató NIVEL2

1. Confirmar el encabezado (`FF 4F 0A 0A 00…` → línea 10).
2. Destokenizar con la tabla de IBM BASICA (no la de BASIC-80 de CP/M: los códigos no coinciden).
3. Grabar un listado UTF-8 equivalente a `SAVE "NIVEL2.TXT",A`.

```bash
python tools/detokenize_gwbasic.py original/NIVEL2.BAS original/NIVEL2.txt
```

Fuentes:

- Tokenizados: [`original/NIVEL2.BAS`](original/NIVEL2.BAS), [`original/NIVEL.BAS`](original/NIVEL.BAS)
- Listados: [`original/NIVEL2.txt`](original/NIVEL2.txt), [`original/NIVEL.txt`](original/NIVEL.txt)

`NIVEL.BAS` (ene 1991) solo cambia 4 líneas respecto a `NIVEL2.BAS` (sep 1990): listado de cotejo a impresora y, al terminar, volver al menú en lugar de `SYSTEM`.

### Si el programa está protegido (`SAVE ,P`)

`LIST` responde `Illegal function call`. Hay un procedimiento clásico (cargar un stub `CHR$(255)`) descrito en la literatura de GW-BASIC. Úselo solo sobre una **copia** y solo si es dueño del código. NIVEL2 no estaba protegido.

---

## Qué hace el programa (negocio)

Nivelación por **cuadrícula de estaciones**:

1. Lote nuevo, lote viejo, extraer un subrectángulo, o salir.
2. Pide nombre, **hileras**, **columnas**, distancia entre estaciones, localización, fecha y quién levantó.
3. Elevación de cada estación (0 = no levantada). Hilera 1 = norte, columna 1 = oeste.
4. Calcula centroide, pendientes naturales O–E y N–S, plano de diseño, matriz corte/relleno. Opcionalmente itera el centroide hasta una **relación corte/relleno**.
5. Reporta m³, hectáreas y m³/ha (el área usa `filas × distancia`, como el original, no `filas−1`).

Datos:

- Archivo sin extensión, registros de 4 bytes: `MKS$` / `CVS` (Microsoft Binary Format, no IEEE).
- `NOMBRE.DAT`: `WRITE` de BASICA (CSV con comillas, a menudo termina en `Ctrl+Z`).

---

## Ejecutar la aplicación Python

Requisitos: Python 3.10 o superior.

```bash
cd Basic_program_1985          # o la carpeta del clon
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
python -m streamlit run app.py
```

El navegador abre [http://localhost:8501](http://localhost:8501).

### Desplegar (no usar Vercel)

Vercel espera un `app.py` tipo Flask/FastAPI con `app`, `application` o `handler`. Esta aplicación es **Streamlit**: un servidor con WebSockets que tiene que seguir vivo. En Vercel no puede correr; el error `does not export a top-level "app"` es exactamente eso.

**Opción recomendada — Streamlit Community Cloud (gratis):**

La app publicada está en:

[https://basicprogram1985-qdzcuwr6wwgke5w6rnqopx.streamlit.app/](https://basicprogram1985-qdzcuwr6wwgke5w6rnqopx.streamlit.app/)

Para volver a desplegar: [share.streamlit.io](https://share.streamlit.io) → repositorio `asoto59g/Basic_program_1985`, rama `main`, archivo `app.py`.

**Opción Docker** (Render, Railway, Fly.io, un VPS):

```bash
docker build -t nivel2 .
docker run -p 8501:8501 nivel2
```

Uso:

1. **Abrir** un lote (`PRUEBA.DAT`, `RH12.DAT`, o `TOPO92\LOT184.DAT`) y **Cargar**.
2. Revisar la cuadrícula (vacío o 0 = estación libre).
3. **Diseño y cálculo** → **Calcular compensación**.
4. **Resultados** y **Listado** (descarga el reporte que antes iba a la impresora).

También se puede crear un lote nuevo, recortar una subcuadrícula (opción 3 del BASICA) y guardar JSON o el par `LOTE` + `LOTE.DAT` de 1990.

Sin interfaz, el motor es importable:

```python
from pathlib import Path
from nivelacion import cargar_lote_basica, calcular

lote = cargar_lote_basica(Path("PRUEBA.DAT"))
res = calcular(lote)
print(res.centroide_natural, res.oe_natural, res.ns_natural, res.tcorte)
```

Comprobación contra el `.DAT` que escribió BASICA en 1995:

| Magnitud | BASICA (`PRUEBA.DAT`) | Python |
|---|---|---|
| Centroide natural | 12.16 m | 12.16 |
| Pendiente O–E | −0.07667 m/estación | igual |
| Plano horizontal 12.14 | corte 0.44, relleno 0.30, 275 m³ | igual |
| `TOPO92\LOT184` Bocana 12×23 | centroide 9.63, 13.625 ha | igual |

---

## Cómo se portó el código (resumen)

No se emuló DOS. Se **tradujo el algoritmo** y se cambió la UI.

1. Destokenizar y leer el listado con números de línea (`GOSUB 1720`, `GOTO 1040`).
2. Reproducir `CINT`, `OPTION BASE 1`, umbrales `0.005` / `0.001`, y el MBF.
3. Contrastar con lotes reales, no con un ejemplo inventado.
4. Streamlit para menú, tabla y mapa corte/relleno.

Detalle para programas mucho más grandes: [docs/RESCATE-SISTEMAS-BASIC.md](docs/RESCATE-SISTEMAS-BASIC.md).

---

## Estructura del repositorio

```text
app.py                      # Interfaz Streamlit
nivelacion.py               # Motor (MBF, centroide, corte/relleno)
requirements.txt
tools/detokenize_gwbasic.py # .BAS tokenizado → texto
original/                   # NIVEL2 / NIVEL tokenizados y listados
docs/RESCATE-SISTEMAS-BASIC.md
TOPO92/                     # Lotes NIVEL2 de campo
PRUEBA  PRUEBA.DAT          # Lote de prueba 3×3
```

No se incluyen `BASICA.EXE` ni la carpeta `TOPO91` (otro formato). El `.gitignore` ya los deja fuera.

---

## Publicar en GitHub

Destino: [https://github.com/asoto59g/Basic_program_1985](https://github.com/asoto59g/Basic_program_1985)

Con GitHub Desktop (o el panel Source Control de Cursor):

1. Publique esta carpeta `TOPOGRAF` como repositorio local si aún no lo es.
2. El primer commit puede usar este mensaje:

```text
Documentar el rescate de NIVEL2.BAS (1990) y el puerto a Python.

Incluye el destokenizador GW-BASIC, el motor de corte/relleno, la app
Streamlit, lotes de ejemplo y una guía para recuperar sistemas BASICA
de esa época.
```

3. Remote: `https://github.com/asoto59g/Basic_program_1985.git` (rama `main`).
4. Push. Si el repo en GitHub está vacío, ese push queda como contenido inicial; no hace falta pull request.

---

## Licencia

El puerto Python y las herramientas de rescate se publican bajo [MIT](LICENSE). `NIVEL2.BAS` se conserva como documento histórico del autor. Los lotes de `TOPO92` son levantamientos de trabajo de la misma época; no los use como datos de terceros sin contexto.
