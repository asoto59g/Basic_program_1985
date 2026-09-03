# Destokenizador GW-BASIC / IBM BASICA

Convierte un `.BAS` guardado en formato tokenizado (primer byte `0xFF`) a texto UTF-8.

```bash
python tools/detokenize_gwbasic.py original/NIVEL2.BAS original/NIVEL2.txt
```

Si el archivo empieza por texto (`10 CLS`…) ya es ASCII: ábralo directo. Si empieza por `FE`, está protegido (`SAVE ,P`).
