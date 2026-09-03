"""Nivelacion por cuadricula — corte y relleno (puerto de NIVEL2.BAS, 1990)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from nivelacion import (
    Lote,
    OpcionesDiseno,
    calcular,
    cargar_lote_basica,
    cargar_lote_json,
    guardar_lote_basica,
    guardar_lote_json,
    listar_lotes,
    matriz_a_dataframe,
    reporte_texto,
)

CARPETA = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Nivelación corte-relleno",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .block-container {padding-top: 1.4rem; max-width: 1400px;}
    h1 {font-weight: 650; letter-spacing: -0.03em;}
    div[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
    .stDataFrame {font-variant-numeric: tabular-nums;}
</style>
""",
    unsafe_allow_html=True,
)


def _init_state() -> None:
    if "lote" not in st.session_state:
        st.session_state.lote = None
    if "resultado" not in st.session_state:
        st.session_state.resultado = None
    if "editor_id" not in st.session_state:
        st.session_state.editor_id = 0


def _activar_lote(lote: Lote) -> None:
    """Deja el lote en sesion y fuerza hileras/columnas/nombre del archivo cargado."""
    st.session_state.lote = lote
    st.session_state.resultado = None
    st.session_state.editor_id = int(st.session_state.get("editor_id", 0)) + 1
    st.session_state.n_nombre = lote.nombre
    st.session_state.n_localizacion = lote.localizacion
    st.session_state.n_fecha = lote.fecha
    st.session_state.n_persona = lote.persona
    st.session_state.n_hileras = int(lote.hileras)
    st.session_state.n_columnas = int(lote.columnas)
    st.session_state.n_distancia = float(lote.distancia)
    st.session_state.skip_editor_once = True


def _ensure_widget_keys(lote: Lote) -> None:
    faltantes = {
        "n_nombre": lote.nombre,
        "n_localizacion": lote.localizacion,
        "n_fecha": lote.fecha,
        "n_persona": lote.persona,
        "n_hileras": int(lote.hileras),
        "n_columnas": int(lote.columnas),
        "n_distancia": float(lote.distancia),
    }
    for key, val in faltantes.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _lote_desde_editor(lote: Lote, tabla: pd.DataFrame) -> Lote:
    """Convierte la tabla del editor a elevaciones. Celdas vacías -> 0."""
    df = tabla.copy()
    cols = [c for c in df.columns if str(c).upper().startswith("C")]
    if not cols:
        cols = list(df.columns)
    nums = df[cols].apply(pd.to_numeric, errors="coerce")
    arr = nums.to_numpy(dtype=float)
    if arr.size == 0:
        return lote
    vals = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    grid = np.zeros((lote.hileras, lote.columnas), dtype=float)
    if vals.ndim == 2:
        r = min(lote.hileras, vals.shape[0])
        c = min(lote.columnas, vals.shape[1])
        grid[:r, :c] = vals[:r, :c]
    if np.any(lote.sta > 0.001) and not np.any(grid > 0.001):
        return lote
    lote.sta = grid
    return lote


def _nuevo_lote() -> Lote:
    return Lote(
        nombre="NUEVO",
        hileras=3,
        columnas=3,
        distancia=25.0,
        fecha=date.today().strftime("%d/%m/%y"),
        persona="",
        localizacion="",
        sta=np.zeros((3, 3)),
    )


def _cargar(path: Path) -> Lote:
    if path.suffix.lower() == ".json":
        return cargar_lote_json(path)
    return cargar_lote_basica(path)


def _estilo_cr(df: pd.DataFrame):
    def color(val):
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ""
        if abs(v) < 0.001:
            return "color: #8aa090"
        if v > 0:
            return "background-color: rgba(46, 140, 110, 0.35); color: #d8ffe8"
        return "background-color: rgba(160, 70, 55, 0.40); color: #ffe0d4"

    return df.style.format("{:+.2f}").map(color)


def _chart_cr(cr: np.ndarray):
    import altair as alt

    filas = []
    a, b = cr.shape
    for i in range(a):
        for j in range(b):
            filas.append(
                {
                    "x": j + 1,
                    "y": i + 1,
                    "Hilera": f"H{i + 1}",
                    "Columna": f"C{j + 1}",
                    "CR": round(float(cr[i, j]), 3),
                }
            )
    df = pd.DataFrame(filas)
    return (
        alt.Chart(df)
        .mark_rect(stroke="#141c18", strokeWidth=1)
        .encode(
            x=alt.X("x:O", title="Oeste  →  Este"),
            y=alt.Y("y:O", title="Norte  ↑", sort="descending"),
            color=alt.Color(
                "CR:Q",
                title="Corte (−) / Relleno (+)",
                scale=alt.Scale(scheme="redblue", domainMid=0),
            ),
            tooltip=["Hilera", "Columna", "CR"],
        )
        .properties(height=max(280, 28 * a))
    )


def main() -> None:
    _init_state()

    st.title("Nivelación por cuadrícula")
    st.caption(
        "Compensación de corte y relleno — mismo método que NIVEL2.BAS (BASICA, 1990). "
        "Hilera 1 = norte · Columna 1 = oeste · Elevación 0 = estación vacía."
    )

    with st.sidebar:
        st.header("Lote")
        lotes = listar_lotes(CARPETA)
        etiquetas = ["— lote nuevo —"] + [
            str(p.relative_to(CARPETA)) if p.is_relative_to(CARPETA) else str(p) for p in lotes
        ]
        eleccion = st.selectbox("Abrir", etiquetas, index=0)

        c1, c2 = st.columns(2)
        with c1:
            abrir = st.button("Cargar", width="stretch")
        with c2:
            crear = st.button("Nuevo", width="stretch")

        if crear:
            _activar_lote(_nuevo_lote())
            st.rerun()

        if abrir and eleccion != etiquetas[0]:
            path = lotes[etiquetas.index(eleccion) - 1]
            try:
                _activar_lote(_cargar(path))
                st.success(f"Cargado {path.name}")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        st.divider()
        st.markdown("**Subcuadrícula** (opción 3 del original)")
        h1 = st.number_input("1ª hilera", min_value=1, max_value=200, value=1, key="ext_h1")
        h2 = st.number_input("Última hilera", min_value=1, max_value=200, value=1, key="ext_h2")
        c1n = st.number_input("1ª columna", min_value=1, max_value=200, value=1, key="ext_c1")
        c2n = st.number_input("Última columna", min_value=1, max_value=200, value=1, key="ext_c2")
        nombre_hijo = st.text_input("Nombre del lote nuevo", "LOTE2")
        if st.button("Extraer de lote abierto", width="stretch"):
            if st.session_state.lote is None:
                st.warning("Abra un lote primero")
            else:
                try:
                    _activar_lote(
                        st.session_state.lote.extraer(
                            int(h1), int(h2), int(c1n), int(c2n), nombre_hijo.strip() or "LOTE2"
                        )
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    lote: Lote | None = st.session_state.lote
    if lote is None:
        st.info("Cargue un lote NIVEL2 (PRUEBA, RH12, o los de TOPO92) o cree uno nuevo.")
        st.markdown(
            """
Los archivos originales viven junto a esta aplicación:

- `PRUEBA` / `RH12` / `FSFS` — cuadrículas 3×3 de prueba
- `TOPO92\\` — lotes de campo NIVEL2 (Bocana, Las Piedras, etc.)

`TOPO91` usa otro formato y no aparece en la lista.

Al calcular se obtienen centroide, pendientes naturales O–E y N–S, plano de diseño,
cortes/rellenos, metros cúbicos y m³/ha. Opcionalmente se itera el centroide hasta
la relación corte/relleno pedida, igual que `CORTERELLENO$` en el BASICA.
"""
        )
        return

    _ensure_widget_keys(lote)

    meta1, meta2, meta3, meta4 = st.columns(4)
    lote.nombre = meta1.text_input("Nombre del lote", key="n_nombre")
    lote.localizacion = meta2.text_input("Localización", key="n_localizacion")
    lote.fecha = meta3.text_input("Fecha de campo", key="n_fecha")
    lote.persona = meta4.text_input("Levantó", key="n_persona")

    dim1, dim2, dim3, dim4 = st.columns(4)
    hileras = int(dim1.number_input("Hileras (N→S)", min_value=1, max_value=80, step=1, key="n_hileras"))
    columnas = int(dim2.number_input("Columnas (O→E)", min_value=1, max_value=80, step=1, key="n_columnas"))
    lote.distancia = float(
        dim3.number_input("Distancia entre estaciones (m)", min_value=1.0, max_value=1000.0, step=1.0, key="n_distancia")
    )
    dim4.metric("Estaciones", f"{lote.hileras} × {lote.columnas}")
    if (hileras != lote.hileras or columnas != lote.columnas) and st.button("Aplicar tamaño de cuadrícula"):
        grid = np.zeros((hileras, columnas))
        r = min(hileras, lote.sta.shape[0])
        c = min(columnas, lote.sta.shape[1])
        grid[:r, :c] = lote.sta[:r, :c]
        lote.sta = grid
        lote.hileras = hileras
        lote.columnas = columnas
        st.session_state.editor_id += 1
        st.session_state.skip_editor_once = True
        st.rerun()

    tabs = st.tabs(["Elevaciones de terreno", "Diseño y cálculo", "Resultados", "Listado"])

    with tabs[0]:
        st.caption("Edite la cuadrícula. Cero o vacío = estación no levantada.")
        tabla = st.data_editor(
            matriz_a_dataframe(lote.sta, vaciar_ceros=True),
            num_rows="fixed",
            width="stretch",
            key=f"grid_{st.session_state.editor_id}",
            column_config={
                col: st.column_config.NumberColumn(col, format="%.2f", step=0.01)
                for col in [f"C{i+1}" for i in range(lote.columnas)]
            },
        )
        if st.session_state.pop("skip_editor_once", False):
            st.session_state.lote = lote
        else:
            lote = _lote_desde_editor(lote, tabla)
            st.session_state.lote = lote

    with tabs[1]:
        st.subheader("Pendientes y centroide")
        usar_nat = st.checkbox("Usar pendientes y centroide naturales (recomendado)", value=True)
        p1, p2, p3 = st.columns(3)
        oe_pct = p1.number_input("Pendiente Oeste–Este (%)", -50.0, 50.0, 0.0, 0.01, disabled=usar_nat)
        ns_pct = p2.number_input("Pendiente Norte–Sur (%)", -50.0, 50.0, 0.0, 0.01, disabled=usar_nat)
        cen = p3.number_input("Elevación del centroide (m)", 0.0, 9999.0, 0.0, 0.01, disabled=usar_nat)

        st.subheader("Relación corte / relleno")
        ajustar = st.checkbox("Compensar el plano hasta una relación deseada", value=False)
        rel = st.number_input("Relación corte/relleno deseada", 0.1, 20.0, 1.0, 0.05, disabled=not ajustar)

        if st.button("Calcular compensación", type="primary"):
            opciones = OpcionesDiseno()
            if not usar_nat:
                opciones.pendiente_oe_pct = float(oe_pct)
                opciones.pendiente_ns_pct = float(ns_pct)
                if cen > 0:
                    opciones.centroide = float(cen)
            if ajustar:
                opciones.relacion_corte_relleno = float(rel)
            try:
                st.session_state.resultado = calcular(lote, opciones)
                st.success("Cálculo terminado")
            except Exception as exc:
                st.session_state.resultado = None
                st.error(str(exc))

        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            if st.button("Guardar JSON"):
                ruta = guardar_lote_json(lote, CARPETA / f"{lote.nombre}.json")
                st.success(f"Guardado {ruta.name}")
        with g2:
            if st.button("Guardar formato 1990 (DAT + binario)"):
                b, d = guardar_lote_basica(lote, CARPETA)
                st.success(f"Guardados {b.name} y {d.name}")

    res = st.session_state.resultado
    with tabs[2]:
        if res is None:
            st.info("Calcule el diseño en la pestaña anterior.")
        else:
            m = st.columns(6)
            m[0].metric("Centroide", f"{res.centroide:.2f} m")
            m[1].metric("Estación (H,C)", f"{res.sy} , {res.sx}")
            m[2].metric("Corte", f"{abs(res.corte):.2f} m")
            m[3].metric("Relleno", f"{abs(res.relleno):.2f} m")
            m[4].metric("Relación C/R", f"{res.relacion:.2f}")
            m[5].metric("Corte", f"{res.tcorte:,.1f} m³")

            m2 = st.columns(4)
            m2[0].metric("Pendiente O–E", f"{res.oe:+.3f} m/est", f"S = {res.s_oe(lote.distancia):.4f}")
            m2[1].metric("Pendiente N–S", f"{res.ns:+.3f} m/est", f"S = {res.s_ns(lote.distancia):.4f}")
            m2[2].metric("Área", f"{res.area_ha:.2f} ha")
            m2[3].metric("Intensidad", f"{res.mch:,.1f} m³/ha")

            st.caption(
                f"Centroide natural {res.centroide_natural:.2f} m · "
                f"OE natural {res.oe_natural:+.4f} · NS natural {res.ns_natural:+.4f} · "
                f"líneas de referencia V={res.lineay:.2f} H={res.lineax:.2f} · "
                f"cota estación ({res.sy},{res.sx}) = {res.centro2:.2f} m"
                + (f" · {res.iteraciones} iteraciones de compensación" if res.iteraciones else "")
            )

            c_izq, c_der = st.columns((1.1, 1))
            with c_izq:
                st.markdown("**Cortes (−) y rellenos (+)**")
                st.dataframe(_estilo_cr(matriz_a_dataframe(res.cr)), width="stretch")
            with c_der:
                st.altair_chart(_chart_cr(res.cr), width="stretch")

            st.markdown("**Elevaciones de diseño**")
            st.dataframe(
                matriz_a_dataframe(res.sta1).style.format("{:.2f}"),
                width="stretch",
            )

    with tabs[3]:
        if res is None:
            st.info("Calcule el diseño para generar el listado.")
        else:
            texto = reporte_texto(lote, res)
            st.download_button(
                "Descargar listado .txt",
                texto.encode("utf-8"),
                file_name=f"{lote.nombre}_listado.txt",
                mime="text/plain",
            )
            st.code(texto, language=None)


if __name__ == "__main__":
    main()
