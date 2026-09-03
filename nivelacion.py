"""Motor de compensacion corte/relleno — puerto de NIVEL2.BAS (BASICA, 1990).

La numeracion de la cuadricula es la del original:
  hilera 1 = norte, ultima hilera = sur
  columna 1 = oeste, ultima columna = este
Estaciones con elevacion < 0.005 se tratan como vacias al promediar;
< 0.001 se tratan como vacias al armar el plano de diseno.
"""

from __future__ import annotations

import csv
import io
import json
import math
import struct
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

VACIO_PROMEDIO = 0.005
VACIO_DISENO = 0.001
PASO_CENTROIDE = 0.001
MAX_ITER_RELACION = 200_000


def cint(x: float) -> int:
    """CINT de GW-BASIC: redondeo al entero mas cercano, .5 al par."""
    return int(round(float(x)))


def redondear2(x: float) -> float:
    return cint(x * 100.0) / 100.0


def mbf_a_float(b: bytes) -> float:
    """CVS: simple precision Microsoft Binary Format (4 bytes) -> float."""
    if len(b) < 4 or b[3] == 0:
        return 0.0
    signo = b[2] & 0x80
    exp_ieee = b[3] - 2
    if exp_ieee <= 0:
        return 0.0
    if exp_ieee >= 255:
        exp_ieee = 254
    ieee = bytearray(4)
    ieee[3] = signo | (exp_ieee >> 1)
    ieee[2] = ((exp_ieee << 7) & 0x80) | (b[2] & 0x7F)
    ieee[1] = b[1]
    ieee[0] = b[0]
    return float(struct.unpack("<f", bytes(ieee))[0])


def float_a_mbf(x: float) -> bytes:
    """MKS$: float -> 4 bytes Microsoft Binary Format."""
    if x == 0.0 or not math.isfinite(x):
        return bytes(4)
    b0, b1, b2, b3 = struct.pack("<f", float(x))
    signo = b3 & 0x80
    exp_ieee = ((b3 & 0x7F) << 1) | (b2 >> 7)
    exp_mbf = exp_ieee + 2
    if exp_mbf <= 0:
        return bytes(4)
    if exp_mbf > 255:
        exp_mbf = 255
    return bytes([b0, b1, (b2 & 0x7F) | signo, exp_mbf & 0xFF])


def _es_vacio(valor: float, umbral: float) -> bool:
    return (not math.isfinite(valor)) or valor < umbral


def _promedio_fila(sta: np.ndarray, fila: int, umbral: float = VACIO_PROMEDIO) -> float:
    vals = [float(v) for v in sta[fila] if not _es_vacio(float(v), umbral)]
    if not vals:
        return float("nan")
    return sum(vals) / len(vals)


def _promedio_columna(sta: np.ndarray, col: int, umbral: float = VACIO_PROMEDIO) -> float:
    vals = [float(v) for v in sta[:, col] if not _es_vacio(float(v), umbral)]
    if not vals:
        return float("nan")
    return sum(vals) / len(vals)


def _pendiente_indices(valores: list[float]) -> float:
    """Regresion lineal identica a lineas 840-890 de NIVEL2.BAS.

    indices 1-based.  pendiente = metros de elevacion por estacion.
    """
    n = len(valores)
    if n < 2:
        return 0.0
    z = x = v = nn = 0.0
    for i, val in enumerate(valores, start=1):
        if not math.isfinite(val):
            continue
        z += i * val
        x += i
        v += val
        nn += i * i
    denom = nn - (x * x) / n
    if abs(denom) < 1e-15:
        return 0.0
    return (z - (x * v) / n) / denom


def _float_campo(valor, default: float = 0.0) -> float:
    texto = str(valor).strip() if valor is not None else ""
    if not texto:
        return default
    try:
        return float(texto)
    except ValueError:
        return default


def _leer_lineas_basic(path: Path) -> list[list[str]]:
    raw = path.read_bytes().replace(b"\x1a", b"")
    text = raw.decode("cp437", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    filas = []
    for linea in text.split("\n"):
        linea = linea.strip()
        if not linea:
            continue
        filas.append(next(csv.reader([linea])))
    return filas


@dataclass
class Lote:
    nombre: str
    madre: str = ""
    hileras: int = 3
    columnas: int = 3
    distancia: float = 25.0
    localizacion: str = ""
    fecha: str = ""
    persona: str = ""
    sta: np.ndarray = field(default_factory=lambda: np.zeros((3, 3)))

    def __post_init__(self) -> None:
        self.sta = np.asarray(self.sta, dtype=float)
        if self.sta.shape != (self.hileras, self.columnas):
            grid = np.zeros((self.hileras, self.columnas), dtype=float)
            r = min(self.hileras, self.sta.shape[0])
            c = min(self.columnas, self.sta.shape[1])
            grid[:r, :c] = self.sta[:r, :c]
            self.sta = grid

    def extraer(self, h1: int, h2: int, c1: int, c2: int, nuevo_nombre: str) -> "Lote":
        """Submatriz 1-based inclusive, como la opcion 3 del original."""
        h1 = max(1, h1)
        c1 = max(1, c1)
        h2 = min(self.hileras, h2)
        c2 = min(self.columnas, c2)
        if h2 < h1 or c2 < c1:
            raise ValueError("Rango de hileras/columnas invalido")
        recorte = self.sta[h1 - 1 : h2, c1 - 1 : c2].copy()
        return Lote(
            nombre=nuevo_nombre,
            madre=self.nombre,
            hileras=recorte.shape[0],
            columnas=recorte.shape[1],
            distancia=self.distancia,
            localizacion=self.localizacion,
            fecha=self.fecha,
            persona=self.persona,
            sta=recorte,
        )


@dataclass
class Resultado:
    hil: list[float]
    col: list[float]
    centroide_natural: float
    centroide: float
    oe_natural: float
    ns_natural: float
    oe: float
    ns: float
    oens: float
    lineay: float
    lineax: float
    sy: int
    sx: int
    centro2: float
    sta1: np.ndarray
    cr: np.ndarray
    relleno: float
    corte: float
    tcorte: float
    area_ha: float
    mch: float
    relacion: float
    iteraciones: int = 0

    def s_oe(self, distancia: float) -> float:
        return self.oe / distancia if distancia else 0.0

    def s_ns(self, distancia: float) -> float:
        return self.ns / distancia if distancia else 0.0


@dataclass
class OpcionesDiseno:
    pendiente_oe_pct: Optional[float] = None
    pendiente_ns_pct: Optional[float] = None
    centroide: Optional[float] = None
    relacion_corte_relleno: Optional[float] = None


def localizar_centroide(sta: np.ndarray) -> tuple[float, float, int, int]:
    """Lineas 1720-1890: centroide geometrico de estaciones ocupadas."""
    a, b = sta.shape
    p = np.zeros(a, dtype=float)
    h = np.zeros(a, dtype=float)
    ll = 1
    for row in range(a, 0, -1):
        l = 0
        for col in range(b):
            if not _es_vacio(float(sta[row - 1, col]), VACIO_DISENO):
                l += 1
        p[row - 1] = ll * l
        h[row - 1] = l
        ll += 1
    th = float(h.sum())
    lineay = float(p.sum() / th) if th else (a + 1) / 2.0

    ph = np.zeros(b, dtype=float)
    hh = np.zeros(b, dtype=float)
    for col in range(1, b + 1):
        l = 0
        for row in range(a):
            if not _es_vacio(float(sta[row, col - 1]), VACIO_DISENO):
                l += 1
        ph[col - 1] = col * l
        hh[col - 1] = l
    thh = float(hh.sum())
    lineax = float(ph.sum() / thh) if thh else (b + 1) / 2.0

    sy = cint(lineay)
    sx = cint(lineax)
    sy = min(max(sy, 1), a)
    sx = min(max(sx, 1), b)
    return lineay, lineax, sy, sx


def _plano_diseno(sta: np.ndarray, centro2: float, sy: int, sx: int, ns: float, oe: float) -> np.ndarray:
    """Lineas 1030-1124: plano a partir de la estacion mas cercana al centroide."""
    a, b = sta.shape
    i_ent = ((a - 1) - (a - sy)) * -1  # 1 - sy
    i1_ent = ((b - 1) - (b - sx)) * -1  # 1 - sx
    i = redondear2(i_ent * ns)
    i1 = redondear2(i1_ent * oe)
    paso_ns = (i / i_ent) if i_ent != 0 else ns
    paso_oe = (i1 / i1_ent) if i1_ent != 0 else oe

    sta1 = np.zeros((a, b), dtype=float)
    sta1[0, 0] = centro2 + (i + i1)
    for row in range(a):
        if row != 0:
            sta1[row, 0] = sta1[row - 1, 0] + paso_ns
        for col in range(1, b):
            sta1[row, col] = sta1[row, col - 1] + paso_oe
    for row in range(a):
        for col in range(b):
            if _es_vacio(float(sta[row, col]), VACIO_DISENO):
                sta1[row, col] = 0.0
    return sta1


def _sumas_corte_relleno(cr: np.ndarray) -> tuple[float, float]:
    relleno = 0.0
    corte = 0.0
    for val in cr.ravel():
        if val > 0:
            relleno += float(val)
        else:
            corte += float(val)
    return relleno, corte


def calcular(lote: Lote, opciones: Optional[OpcionesDiseno] = None) -> Resultado:
    opciones = opciones or OpcionesDiseno()
    sta = np.asarray(lote.sta, dtype=float)
    a, b = sta.shape
    if a < 1 or b < 1:
        raise ValueError("La cuadricula esta vacia")
    dist = float(lote.distancia)
    if dist <= 0:
        raise ValueError("La distancia entre estaciones debe ser positiva")

    hil = [_promedio_fila(sta, row) for row in range(a)]
    col = [_promedio_columna(sta, c) for c in range(b)]

    hil_ok = [x for x in hil if math.isfinite(x)]
    if not hil_ok:
        raise ValueError("No hay estaciones con elevacion valida")
    # El original divide por A% (todas las hileras). Si alguna esta vacia usamos las validas.
    centroide_natural = redondear2(sum(hil_ok) / (a if len(hil_ok) == a else len(hil_ok)))

    oe_natural = _pendiente_indices(col)
    ns_natural = _pendiente_indices(hil)

    oe = oe_natural
    ns = ns_natural
    if opciones.pendiente_oe_pct is not None:
        oe = (opciones.pendiente_oe_pct / 100.0) * dist
    if opciones.pendiente_ns_pct is not None:
        ns = (opciones.pendiente_ns_pct / 100.0) * dist

    centroide = float(opciones.centroide) if opciones.centroide is not None else centroide_natural

    lineay, lineax, sy, sx = localizar_centroide(sta)
    slopy = sy - lineay
    slopx = sx - lineax
    elev1 = slopy * ns
    elev2 = slopx * oe
    centro2 = centroide + (elev1 + elev2)

    ajustar = opciones.relacion_corte_relleno is not None
    cr1 = float(opciones.relacion_corte_relleno or 0.0)
    paso1 = 0.0
    paso2 = 0.0
    iteraciones = 0

    while True:
        sta1 = _plano_diseno(sta, centro2, sy, sx, ns, oe)
        cr = sta1 - sta
        relleno, corte = _sumas_corte_relleno(cr)
        if not ajustar:
            break
        if abs(relleno) < 1e-12:
            relacion_act = math.inf if abs(corte) > 1e-12 else 0.0
        else:
            relacion_act = abs(corte) / abs(relleno)
        if math.isfinite(relacion_act) and abs(relacion_act - cr1) < 1e-9:
            break
        iteraciones += 1
        if iteraciones > MAX_ITER_RELACION:
            break
        if relacion_act < cr1:
            paso1 = relacion_act if math.isfinite(relacion_act) else 0.0
            if paso1 > 0 and paso2 > 0:
                if abs(paso1 - cr1) > abs(paso2 - cr1):
                    centro2 -= PASO_CENTROIDE
                ajustar = False
                corte = 0.0
                relleno = 0.0
                centroide = centro2 - (elev1 + elev2)
                continue
            centro2 -= PASO_CENTROIDE
        else:
            paso2 = relacion_act if math.isfinite(relacion_act) else 0.0
            if paso1 > 0 and paso2 > 0:
                if abs(paso1 - cr1) > abs(paso2 - cr1):
                    centro2 -= PASO_CENTROIDE
                ajustar = False
                corte = 0.0
                relleno = 0.0
                centroide = centro2 - (elev1 + elev2)
                continue
            centro2 += PASO_CENTROIDE

    oens = (oe + ns) / math.sqrt(dist * dist + dist * dist)
    tcorte = abs(corte) * (dist * dist)

    esquinas = (
        not _es_vacio(float(sta[0, 0]), VACIO_DISENO)
        and not _es_vacio(float(sta[0, b - 1]), VACIO_DISENO)
        and not _es_vacio(float(sta[a - 1, 0]), VACIO_DISENO)
        and not _es_vacio(float(sta[a - 1, b - 1]), VACIO_DISENO)
    )
    if esquinas:
        area_ha = ((a * dist) * (b * dist)) / 10000.0
    else:
        ocupadas = int(np.sum(sta > VACIO_DISENO))
        area_ha = ((dist * dist) * ocupadas) / 10000.0
    mch = tcorte / area_ha if area_ha else 0.0
    relacion = abs(corte) / abs(relleno) if abs(relleno) > 1e-15 else 0.0

    return Resultado(
        hil=hil,
        col=col,
        centroide_natural=centroide_natural,
        centroide=centroide,
        oe_natural=oe_natural,
        ns_natural=ns_natural,
        oe=oe,
        ns=ns,
        oens=oens,
        lineay=lineay,
        lineax=lineax,
        sy=sy,
        sx=sx,
        centro2=centro2,
        sta1=sta1,
        cr=cr,
        relleno=relleno,
        corte=corte,
        tcorte=tcorte,
        area_ha=area_ha,
        mch=mch,
        relacion=relacion,
        iteraciones=iteraciones,
    )


def _parse_meta_nivel2(ruta_dat: Path) -> tuple[str, int, int, float, str, str, str] | None:
    """Lee la primera linea WRITE de NIVEL2. None si el .DAT es de otro programa."""
    try:
        filas = _leer_lineas_basic(ruta_dat)
    except Exception:
        return None
    if not filas:
        return None
    meta = list(filas[0])
    while len(meta) < 7:
        meta.append("")
    hileras = _float_campo(meta[1], 0)
    columnas = _float_campo(meta[2], 0)
    distancia = _float_campo(meta[3], 0)
    if hileras < 1 or columnas < 1 or hileras > 80 or columnas > 80:
        return None
    if distancia <= 0:
        return None
    if abs(hileras - int(hileras)) > 1e-6 or abs(columnas - int(columnas)) > 1e-6:
        return None
    return (
        str(meta[0]),
        int(hileras),
        int(columnas),
        float(distancia),
        str(meta[4]),
        str(meta[5]),
        str(meta[6]),
    )


def es_lote_nivel2(ruta_dat: Path) -> bool:
    """True si hay metadatos NIVEL2 y el binario de estaciones tiene el tamano esperado."""
    ruta_dat = Path(ruta_dat)
    if ruta_dat.suffix.lower() == ".json":
        return ruta_dat.is_file()
    meta = _parse_meta_nivel2(ruta_dat)
    if meta is None:
        return False
    _madre, hileras, columnas, _dist, _loc, _fecha, _persona = meta
    binario = ruta_dat.with_name(ruta_dat.stem)
    if not binario.is_file():
        return False
    return binario.stat().st_size >= hileras * columnas * 4


def cargar_lote_basica(ruta_dat: Path) -> Lote:
    """Lee LOTE.DAT (WRITE de BASICA) + archivo binario LOTE (MKS$/CVS)."""
    ruta_dat = Path(ruta_dat)
    meta = _parse_meta_nivel2(ruta_dat)
    if meta is None:
        raise ValueError(
            f"{ruta_dat.name} no es un .DAT de NIVEL2 (metadatos de lote). "
            "Los de TOPO91 suelen ser de otro programa."
        )
    madre, hileras, columnas, distancia, localizacion, fecha, persona = meta
    binario = ruta_dat.with_name(ruta_dat.stem)
    if not binario.is_file():
        raise FileNotFoundError(f"No esta el archivo de estaciones: {binario}")
    data = binario.read_bytes()
    n = hileras * columnas
    if len(data) < n * 4:
        raise ValueError(f"{binario.name} tiene {len(data)} bytes, se esperaban {n * 4}")
    sta = np.zeros((hileras, columnas), dtype=float)
    i = 0
    for row in range(hileras):
        for col in range(columnas):
            sta[row, col] = mbf_a_float(data[i * 4 : i * 4 + 4])
            i += 1
    return Lote(
        nombre=binario.name,
        madre=madre,
        hileras=hileras,
        columnas=columnas,
        distancia=distancia,
        localizacion=localizacion,
        fecha=fecha,
        persona=persona,
        sta=sta,
    )


def guardar_lote_basica(lote: Lote, carpeta: Path) -> tuple[Path, Path]:
    """Escribe el par LOTE + LOTE.DAT compatible con el programa de 1990."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_bin = carpeta / lote.nombre
    ruta_dat = carpeta / f"{lote.nombre}.DAT"
    buf = bytearray()
    for row in range(lote.hileras):
        for col in range(lote.columnas):
            buf.extend(float_a_mbf(float(lote.sta[row, col])))
    ruta_bin.write_bytes(bytes(buf))
    madre = lote.madre.replace('"', "'")
    loc = lote.localizacion.replace('"', "'")
    fecha = lote.fecha.replace('"', "'")
    persona = lote.persona.replace('"', "'")
    linea = (
        f'"{madre}",{lote.hileras},{lote.columnas},{_fmt_basic_num(lote.distancia)},'
        f'"{loc}","{fecha}","{persona}"\r\n'
    )
    ruta_dat.write_bytes(linea.encode("cp437", errors="replace") + b"\x1a")
    return ruta_bin, ruta_dat


def anexar_resultado_dat(lote: Lote, res: Resultado, carpeta: Path) -> Path:
    """Segunda linea del .DAT, como WRITE #2 ... APPEND del original."""
    ruta_dat = Path(carpeta) / f"{lote.nombre}.DAT"
    vals = [
        res.centroide,
        res.centroide_natural,
        res.oe,
        res.ns,
        res.oe_natural,
        res.ns_natural,
        res.oens,
        res.relleno,
        res.corte,
        res.tcorte,
        res.area_ha,
        res.mch,
        res.sy,
        res.sx,
        res.lineay,
        res.lineax,
        res.centro2,
    ]
    linea = ",".join(_fmt_basic_num(v) for v in vals) + "\r\n"
    raw = ruta_dat.read_bytes().replace(b"\x1a", b"") if ruta_dat.exists() else b""
    ruta_dat.write_bytes(raw + linea.encode("ascii") + b"\x1a")
    return ruta_dat


def _fmt_basic_num(v: float) -> str:
    if isinstance(v, (int, np.integer)) or (isinstance(v, float) and float(v).is_integer()):
        iv = int(v)
        if abs(float(v) - iv) < 1e-9:
            return str(iv)
    x = float(v)
    if abs(x) >= 0.1 or x == 0:
        s = f"{x:.7G}"
        if s.startswith("0."):
            s = s[1:]
        elif s.startswith("-0."):
            s = "-" + s[2:]
        return s
    return f"{x:.6E}".replace("E+0", "E+").replace("E-0", "E-")


def guardar_lote_json(lote: Lote, ruta: Path) -> Path:
    ruta = Path(ruta)
    payload = asdict(lote)
    payload["sta"] = lote.sta.tolist()
    ruta.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return ruta


def cargar_lote_json(ruta: Path) -> Lote:
    data = json.loads(Path(ruta).read_text(encoding="utf-8"))
    data["sta"] = np.array(data["sta"], dtype=float)
    return Lote(**data)


def listar_lotes(carpeta: Path) -> list[Path]:
    carpeta = Path(carpeta)
    encontrados = []
    for dat in sorted(carpeta.rglob("*.DAT")):
        if es_lote_nivel2(dat):
            encontrados.append(dat)
    for js in sorted(carpeta.glob("*.json")):
        encontrados.append(js)
    return encontrados


def reporte_texto(lote: Lote, res: Resultado) -> str:
    """Listado equivalente al LPRINT de las lineas 2130-2450."""
    dist = float(lote.distancia)
    out = io.StringIO()
    p = out.write
    p("\n\n")
    p(f"   Nombre del lote = {lote.nombre:<40} FECHA {lote.fecha}\n")
    p(f"   Preparado por : {lote.persona}\n")
    if lote.localizacion:
        p(f"   Localizacion : {lote.localizacion}\n")
    if lote.madre:
        p(f"   Lote madre : {lote.madre}\n")
    p(f"   La elevacion del centroide= {res.centroide_natural:7.2f}\n")
    p(
        f"   Pendiente natural OESTE-ESTE = {res.oe_natural:+6.3f} ENTRE ESTACIONES"
        f"  S ={res.oe_natural / dist:8.4f}\n"
    )
    p(
        f"   Pendiente natural NORTE-SUR = {res.ns_natural:+6.3f} ENTRE ESTACIONES"
        f"  S ={res.ns_natural / dist:8.4f}\n"
    )
    p("\n   El centroide se encuentra localizado en :\n")
    p(f"   Linea de referencia vertical = {res.lineay:6.2f}\n")
    p(f"   Linea de referencia horizontal = {res.lineax:6.2f}\n")
    p(f"   Estacion mas cercana = {res.sy} , {res.sx}\n")
    p(
        f"   La elevacion de la estacion ({res.sy},{res.sx}) "
        f"utilizando el presente centroide es de = {res.centro2:.2f}\n"
    )
    p("\n" + " " * 40 + "ELEVACIONES ORIGINALES\n")
    p(_matriz_texto(lote.sta, "{:7.2f}"))
    p("\n" + " " * 46 + "DISENO FINAL\n")
    p(f"   Nuevo centroide= {res.centroide:7.2f}\n")
    p(f"   Pendiente OESTE-ESTE = {res.oe:+6.3f} ENTRE ESTACIONES  S ={res.oe / dist:8.4f}\n")
    p(f"   Pendiente NORTE-SUR = {res.ns:+6.3f} ENTRE ESTACIONES  S ={res.ns / dist:8.4f}\n")
    p(f"   Pendiente compuesta = {res.oens:8.4f}\n")
    p(f"   Total de relleno = {abs(res.relleno):8.2f}\n")
    p(f"   Total de corte = {abs(res.corte):8.2f}\n")
    p(f"   Relacion corte relleno = {res.relacion:6.2f}\n")
    p(f"   Total de corte en metros cubicos = {res.tcorte:11.2f}\n")
    p(f"   Area total en hectareas = {res.area_ha:8.2f}\n")
    p(f"   Metros cubicos por hectarea = {res.mch:10.2f}\n")
    p(f"   Elevacion de la estacion ({res.sy},{res.sx}) = {res.centro2:6.2f}\n")
    p("\n" + " " * 36 + "ELEVACIONES FINALES DE DISENO\n")
    p(_matriz_texto(res.sta1, "{:7.2f}"))
    p("\n" + " " * 34 + "CORTES Y RELLENOS DEL DISENO FINAL\n")
    p(_matriz_texto(res.cr, "{:7.2f}"))
    return out.getvalue()


def _matriz_texto(mat: np.ndarray, fmt: str) -> str:
    lineas = []
    for row in mat:
        lineas.append("".join(fmt.format(float(v)) for v in row))
    return "\n".join(lineas) + "\n"


def matriz_a_dataframe(mat: np.ndarray, vaciar_ceros: bool = False):
    import pandas as pd

    a, b = mat.shape
    data = {}
    for col in range(b):
        col_vals = []
        for row in range(a):
            v = float(mat[row, col])
            if vaciar_ceros and _es_vacio(v, VACIO_DISENO):
                col_vals.append(None)
            else:
                col_vals.append(v)
        data[f"C{col + 1}"] = col_vals
    return pd.DataFrame(data, index=[f"H{i + 1}" for i in range(a)])
