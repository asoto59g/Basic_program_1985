# Guía para rescatar sistemas BASICA / GW-BASIC (incluidos “ERP” de empresa)

Esta nota complementa el [README](../README.md). Sirve cuando el programa no es
un solo `.BAS` de 250 líneas, sino un directorio de decenas o cientos de
módulos que en los 80 y 90 llevaban inventario, facturación, nómina o
contabilidad en un PC XT/AT.

## 1. Inventariar antes de tocar nada

Haga una copia bit a bit del disco o carpeta. Luego liste:

- `*.BAS` — código (tokenizado `FF…` o ASCII).
- `*.EXE` / `*.COM` — intérprete (`GWBASIC.EXE`, `BASICA.EXE`) o runtime
  compilado (`BASCOM`, QuickBASIC `/O`). Un `.EXE` de 60–80 KB de 1985 suele
  ser el intérprete, no el programa de negocio.
- Archivos **sin extensión** junto a un `.DAT` — típico acceso aleatorio
  (`OPEN … AS #1 LEN=n`).
- `*.DAT`, `*.IDX`, `*.KEY`, `*.RND` — datos.
- `*.BAT` — cómo se lanzaba (`BASICA NIVEL2`, `GWBASIC MENU`).
- `CHAIN`, `RUN "…"`, `COMMON` en el código — mapa de módulos.

Anote fechas de archivo: el `.BAS` más reciente suele ser la versión en
producción.

## 2. Reconocer el dialecto

| Señal | Dialectos |
|---|---|
| Primer byte `FF`, tokens `OPTION`, `FIELD`, `MKS$` | IBM BASICA / GW-BASIC |
| Primeros bytes `FC` / `FB` o texto `DECLARE` | QuickBASIC / PDS 7 |
| `TYPE … END TYPE`, `SELECT CASE` | QuickBASIC o posterior |
| `DEF SEG`, `PEEK`/`POKE`, `BLOAD` | Dependencia de memoria real |
| `EXEC`, `SHELL`, `CALL INTERRUPT` | Enlaces a DOS / hardware |

Un “ERP” de 1988 casi siempre es **varios `.BAS` que se CHAIN-ean** más
archivos de datos de longitud fija. No es un solo listado.

## 3. Destokenizar todos los módulos

```text
for each *.BAS:
    if byte0 == 0xFF → destokenizar
    if byte0 == 0xFE → protegido (SAVE ,P): hay que quitar protección
    if texto ASCII  → ya es listado
```

Programas protegidos (`SAVE "X",P`): el truco clásico es cargar un stub
`CHR$(255)` y volver a `LOAD` (documentado en foros de GW-BASIC). Hágalo
solo sobre **copias** y solo si usted es dueño del código.

Después de destokenizar, busque en todos los listados:

```text
CHAIN
RUN "
OPEN
KILL
NAME
COMMON SHARED
```

Eso dibuja el grafo: menú → facturas → existencias → listados.

## 4. Entender los datos, no solo el código

En BASICA el “esquema” no está en SQL: está en `FIELD`, `LEN=` y `WRITE #`.

**Acceso aleatorio (un registro = una estación, un cliente, una factura):**

```basic
OPEN LOTE$ AS 1 LEN=4
FIELD 1, 4 AS ESTACION$
RSET ESTACION$ = MKS$(VALOR)
PUT 1, NUMERO%
… GET 1, NUMERO% : VALOR = CVS(ESTACION$)
```

`MKS$`/`CVS` son **Microsoft Binary Format** (4 bytes), no IEEE. Un puerto
moderno debe decodificar MBF o los números salen basura.

**Secuencial `WRITE`/`INPUT`:**

```basic
WRITE #2, MADRE$, HILERA%, COLUMNA%, DISTANCIA%, LOCALIZACION$
```

Es CSV con comillas, a menudo terminado en `Ctrl+Z` (`1A`).

En un ERP grande verá decenas de `LEN=32`, `LEN=128` con varios `FIELD`
(nombre, saldo, fecha). Documente cada layout **antes** de migrar.

## 5. Estrategia de puerto (sistemas grandes)

No traduzca línea a línea 20.000 `GOTO`.

1. **Congelar datos de prueba** (un cliente, una factura, un lote) y anotar
   la salida del programa original (pantalla o listado LPRINT).
2. **Extraer el motor**: fórmulas, validaciones, totales. En NIVEL2 eran
   centroide, pendientes y corte/relleno. En un ERP serán existencias,
   impuestos, asientos.
3. **Reproducir un caso** hasta el último céntimo / último decimal.
4. **UI nueva** (web, Streamlit, escritorio). El `LOCATE`/`PRINT` de 80×25
   no merece un emulador si el negocio ya está verificado.
5. Recién entonces migre archivos a SQLite/CSV, **dejando un lector del
   formato viejo** para no perder el archivo histórico.

## 6. Lo que suele romper un puerto

- `OPTION BASE 1` frente a arrays 0-based.
- `CINT` (redondeo al par) vs `INT` (hacia −∞).
- `IF A=2 OR 3` (siempre verdadero): hay que decidir si se corrige.
- `=` para asignación y comparación.
- `A$="S"` vs `"s"`: sin `UCASE$` el menú falla.
- Páginas de código: `cp437` o `cp850`, no UTF-8.
- Fechas `DD/MM/YY` con año 70–99.
- División `/` siempre real; `\` es entera.
- Variables no declaradas = 0 o `""` (no hay Null).

## 7. Cuando el “programa” es un .EXE compilado

Si no hay `.BAS` y solo un `.EXE` de QuickBASIC/BASCOM, el rescate es
ingeniería inversa (strings, DOSBox + debugger) o reescritura a partir de
manuales y datos. Este repositorio cubre el caso **afortunado**: el `.BAS`
tokenizado sigue en el disco.

## 8. Ética y legalidad

- El código de la empresa o del autor original sigue siendo suyo.
- No suba `GWBASIC.EXE` / `BASICA.EXE` a GitHub (copyright Microsoft).
- No publique datos personales de clientes, nóminas o fincas reales sin
  permiso. En este repo solo hay lotes de ejemplo y levantamientos de
  trabajo propios del autor.
