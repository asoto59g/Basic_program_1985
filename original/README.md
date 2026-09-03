# Fuentes originales (BASICA / GW-BASIC)

| Archivo | Fecha | Qué es |
|---|---|---|
| `NIVEL2.BAS` | 21 sep 1990 | Tokenizado (binario, primer byte `FF`). Versión de campo. |
| `NIVEL.BAS` | 17 ene 1991 | Misma aplicación, 4 líneas distintas (impresora y menú). |
| `NIVEL2.txt` | rescatado 2026 | Listado ASCII de `NIVEL2.BAS`. |
| `NIVEL.txt` | rescatado 2026 | Listado ASCII de `NIVEL.BAS`. |

No se incluye `BASICA.EXE` ni `BASIC.COM`: son binarios de Microsoft (1984–1985) y no se pueden redistribuir.

Para volver a pasar un `.BAS` tokenizado a texto:

```bash
python tools/detokenize_gwbasic.py original/NIVEL2.BAS original/NIVEL2.txt
```
