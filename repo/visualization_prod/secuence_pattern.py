# DEPRECATED!! SE MOVIÓ A sequence_mining.py y a run_sequence_mining.py
"""
Descubrimiento de patrones secuenciales (PrefixSpan) sobre trayectorias académicas.

Reemplaza la versión vieja hardcodeada por año único y catálogo fijo de 17 materias
de COMP93. Reutiliza las funciones vigentes del proyecto:

- data_loader.cargar_base_siu / load_plan_from_directory / build_unified_catalog /
  build_dic_materia_idx: para catálogo dinámico de materias (en vez del slice manual
  df_lista_de_materias[...].str.contains('COMP93')[:17] de la versión vieja).
- utils.get_camada: para filtrar la camada de estudiantes (parametrizada por year_list,
  igual que en callbacks.py), en vez del filtrado manual ad-hoc por año único que hacía
  el script viejo (cursaronYEAR / preYEAR / camadaYEAR).
- utils.vectorEstado_to_vectStr: para la representación hasheable del vector de estado,
  igual que graph_engine.generate_nodes_and_edges, en vez de "".join(map(str, x)).

Cada estudiante se traduce a una secuencia de snapshots de estado acumulado (mismo
criterio de cummax por persona que graph_engine.py), y esa secuencia de strings se
pasa a PrefixSpan para minar subsecuencias frecuentes.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from prefixspan import PrefixSpan

from core.data_loader import (
    build_dic_materia_idx,
    build_unified_catalog,
    load_plan_from_directory,
)
from core.utils import get_camada, vectorEstado_to_vectStr

APPROVED_RESULT = "A"
EXCLUDED_RESULTS = {"U"}


# --------------------------------------------------------------------------- #
# Construcción de secuencias de estado por persona (mismo criterio que graph_engine)
# --------------------------------------------------------------------------- #
def build_sequence_database(
    cursadas_por_alumno: pd.DataFrame,
    camada: pd.DataFrame,
    dic_materia_idx: dict[str, int],
    date_columns: list[str] = ["anio_academico", "periodo"],
    result_column: str = "resultado",
    persona_column: str = "persona",
    materia_column: str = "codigo_materia",
) -> list[list[str]]:
    """Genera, para cada persona de la camada, la secuencia ordenada de vectStr
    (estado acumulado de materias aprobadas) por step_nro. Es el mismo cálculo
    de estado acumulado que graph_engine.generate_nodes_and_edges (cummax
    agrupado por persona), pero devuelto como lista de secuencias en vez de
    grafo de nodos/aristas, que es el formato que espera PrefixSpan.

    generate_nodes_and_edges >>> para obtener stateMatrix
    """
    m = len(dic_materia_idx)

    df = cursadas_por_alumno[cursadas_por_alumno[persona_column].isin(camada[persona_column])].copy()
    df = df[df[materia_column].isin(dic_materia_idx.keys())]
    df = df[~df[result_column].isin(EXCLUDED_RESULTS)]

    if df.empty:
        return []

    df["materia_pos"] = df[materia_column].map(dic_materia_idx)
    df["is_approved"] = df[result_column] == APPROVED_RESULT

    step_order = (
        df[[persona_column] + date_columns]
        .drop_duplicates()
        .sort_values([persona_column] + date_columns)
    )
    step_order["step_nro"] = step_order.groupby(persona_column).cumcount() + 1
    df = df.merge(step_order[[persona_column, "step_nro"] + date_columns], on=[persona_column] + date_columns)

    wide = (
        df[df["is_approved"]]
        .pivot_table(
            index=[persona_column, "step_nro"],
            columns="materia_pos",
            values="is_approved",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=range(m), fill_value=0)
        .astype(np.int8)
    )
    wide.index.set_names([persona_column, "step_nro"], inplace=True)

    full_index = pd.MultiIndex.from_frame(
        step_order[[persona_column, "step_nro"]].drop_duplicates(),
        names=[persona_column, "step_nro"],
    )
    wide_full = wide.reindex(full_index, fill_value=0).astype(np.int8)
    wide_full = wide_full.sort_index(level=[persona_column, "step_nro"])

    state_matrix = wide_full.groupby(level=persona_column).cummax()
    state_matrix["vectStr"] = [vectorEstado_to_vectStr(row) for row in state_matrix.to_numpy(dtype=np.int8)]
    state_matrix = state_matrix.reset_index() # ACA EMPIEZA EDIT.sort_values([persona_column, "step_nro"])

    zero_vectStr = vectorEstado_to_vectStr(np.zeros(m, dtype=np.int8))
    unique_vectStr = state_matrix["vectStr"].drop_duplicates().tolist()

    if zero_vectStr in unique_vectStr:
        unique_vectStr.remove(zero_vectStr)            # se elimina el zero_vectStr en caso de que este en pos distinta al inicio
    unique_vectStr = [zero_vectStr] + unique_vectStr      # y lo forzamos SIEMPRE a la posición 0

    #vectStr_to_id: se crea un diccionario vectStr -> nodo_id
    vectStr_to_id = {key: idx for idx, key in enumerate(unique_vectStr)}
    # ---- 6. Aristas: transición estado_(t-1) -> estado_t, PASO A PASO -------
    # (incluye pasos sin avance donde source == target que genera un self-loop)
    state_matrix["node_id"] = state_matrix["vectStr"].map(vectStr_to_id)         # col con nodo_id para su vectStr correspondiente
    state_matrix = state_matrix.sort_values([persona_column, "step_nro"])
    # ACA TERMINA EDIT

    sequence_database = (
        state_matrix.groupby(persona_column)["vectStr"]
        .apply(list)
        .tolist()
    )
    return sequence_database


# --------------------------------------------------------------------------- #
# Traducción de vector binario a nombres legibles de materias
# --------------------------------------------------------------------------- #
def materias_aprobadas_from_vectstr(vect_str: str, catalog: pd.DataFrame, name_column: str = "nomenclatura") -> str:
    """Traduce un vectStr (hex) de vuelta a un listado legible de materias
    aprobadas, usando el catálogo dinámico. Reemplaza el strMateriasAprobadas
    hardcodeado del script viejo (que dependía de una columna 'codigo' manual)."""
    vector = np.frombuffer(bytes.fromhex(vect_str), dtype=np.int8)
    boolean_mask = vector.astype(bool)
    nombres = catalog.loc[boolean_mask, name_column].tolist()
    return "{" + ", ".join(nombres) + "}"


def parse_snapshot(pattern: list[str], catalog: pd.DataFrame, name_column: str = "nomenclatura") -> list[str]:
    """Convierte una secuencia de vectStr (un patrón hallado por PrefixSpan) en
    su representación legible de materias, paso a paso."""
    return [materias_aprobadas_from_vectstr(snp, catalog, name_column) for snp in pattern]


# --------------------------------------------------------------------------- #
# Minado de patrones y armado del DataFrame de resultados
# --------------------------------------------------------------------------- #
def mine_sequence_patterns(
    sequence_database: list[list[str]],
    catalog: pd.DataFrame,
    porcentaje_apariciones: float = 0.2,
    top_k: int = -1,
    name_column: str = "nomenclatura",
) -> pd.DataFrame:
    """Corre PrefixSpan sobre sequence_database y arma el DataFrame de patrones
    frecuentes, ordenado por [Lenght, Support] descendente, con columna extra
    PatternMaterias (traducción legible de cada patrón).

    porcentaje_apariciones: fracción mínima de trayectorias en las que debe
    aparecer un patrón para considerarse frecuente (soporte mínimo = 
    porcentaje_apariciones * cantidad_total_de_trayectorias).
    top_k: cantidad de patrones (ordenados por longitud desc.) a incluir en el
    DataFrame final -- reemplaza el [:20] hardcodeado del script viejo.
    """
    trayectorias_posibles = len(sequence_database)
    if trayectorias_posibles == 0:
        return pd.DataFrame(columns=["Lenght", "Support", "Pattern", "PatternMaterias"])

    # arraysTotales = 0
    # for i in sequence_database:
    #     arraysTotales +=len(i)
    # print("long sequence_database: " + str(len(sequence_database)))
    # print(str(sequence_database[0]))
    # print(type(sequence_database[0][0]))
    # print("long arraysTotales: " + str(arraysTotales))

    ps = PrefixSpan(sequence_database)
    min_support = trayectorias_posibles * porcentaje_apariciones
    patterns = ps.frequent(min_support)
    print("min_support: " + str(min_support))

    longest_first = sorted(patterns, key=lambda x: len(x[1]), reverse=True)[:top_k]

    df_patterns = pd.DataFrame({
        "Lenght": [len(item[1]) for item in longest_first],
        "Support": [item[0] for item in longest_first],
        "Pattern": [item[1] for item in longest_first],
    })
    df_patterns = df_patterns.sort_values(["Lenght", "Support"], ascending=False).reset_index(drop=True)
    df_patterns["PatternMaterias"] = df_patterns["Pattern"].apply(
        lambda pattern: parse_snapshot(pattern, catalog, name_column)
    )
    return df_patterns#[df_patterns["Lenght"]>1]


# --------------------------------------------------------------------------- #
# Plot: longitud vs. soporte, resaltando el patrón top (primero tras el sort)
# --------------------------------------------------------------------------- #
def plot_length_vs_support(df_patterns: pd.DataFrame, output_path: Path | None = None) -> plt.Figure:
    """Scatter Lenght vs. Support. El patrón que queda primero tras
    sort_values(['Lenght','Support'], ascending=False) -- es decir, el más largo
    y, entre los más largos, el de mayor soporte -- se resalta con un círculo."""
    fig, ax = plt.subplots(figsize=(7, 5))

    ax.scatter(df_patterns["Lenght"], df_patterns["Support"], s=40, color="#009DAC", zorder=2)

    if not df_patterns.empty:
        top = df_patterns.iloc[0]
        ax.scatter(
            [top["Lenght"]], [top["Support"]],
            s=260, facecolors="none", edgecolors="#B20D30", linewidths=2.2, zorder=3,
            label=f"Mejor patrón (Lenght={top['Lenght']}, Support={round(top['Support'],0)})",
        )
        ax.legend(loc="best", fontsize=9)

    ax.set_xlabel("Sequence Pattern Length")
    ax.set_ylabel("Support (Frecuencia del patrón)")
    ax.set_title("Patrones secuenciales: Longitud vs. Frecuencia")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150)
    return fig


# --------------------------------------------------------------------------- #
# Orquestación end-to-end (equivalente al bloque __main__ del script viejo)
# --------------------------------------------------------------------------- #
def run_sequence_pattern_mining(
    cursadas_por_alumno: pd.DataFrame,
    planes_por_alumno: pd.DataFrame,
    plans_dir: Path,
    plan_id: str,
    year_list: list[int],
    codigo_carrera: str = "LCCOMP",
    plan_filter: str | int | None = None,
    porcentaje_apariciones: float = 0.2,
    top_k: int = -1,
    name_column: str = "nomenclatura",
    output_plot_path: Path | None = None,
) -> tuple[pd.DataFrame, plt.Figure]:
    """Pipeline completo: arma camada -> catálogo -> secuencias -> PrefixSpan -> plot.
    Parametrizado por year_list (antes año único hardcodeado) y por
    porcentaje_apariciones/top_k (antes valores fijos en el script)."""
    catalog = build_unified_catalog({plan_id: load_plan_from_directory(plans_dir, plan_id)})
    dic_materia_idx = build_dic_materia_idx(catalog)

    camada = get_camada(
        planes_por_alumno,
        cursadas_por_alumno,
        year_list=year_list,
        plan=plan_filter,
        codigo_carrera=codigo_carrera,
    )

    sequence_database = build_sequence_database(cursadas_por_alumno, camada, dic_materia_idx)
    
    df_patterns = mine_sequence_patterns(
        sequence_database, catalog,
        porcentaje_apariciones=porcentaje_apariciones,
        top_k=top_k,
        name_column=name_column,
    )

    fig = plot_length_vs_support(df_patterns, output_path=output_plot_path)
    return df_patterns, fig



from core.data_loader import cargar_base_siu

BASE_DIR = Path(__file__).parent
SOURCE_PATH = BASE_DIR.parent / "bases" / "para tesis LCC_v3.xlsx"
PLANS_DIR = BASE_DIR / "plan"
PLAN_ID = "LCCOMP_1993"

output_fig = "C:/Users/Leila/Documents/uba/tesis/git/tesis/assets_latex/"

dataset = cargar_base_siu(SOURCE_PATH)

df_patterns, fig = run_sequence_pattern_mining(
    cursadas_por_alumno=dataset.cursadas_por_alumno,
    planes_por_alumno=dataset.planes_por_alumno,
    plans_dir=PLANS_DIR,
    plan_id=PLAN_ID,
    year_list=range(2010,2026), #[2019], #          # parametrizable: lista de años, no año único
    porcentaje_apariciones=0.05,
    # top_k=30,
    output_plot_path=Path(output_fig)/"patrones_secuenciales.png",
)

df_patterns.to_csv(Path(output_fig)/"patrones_secuenciales.csv", index=False)
print(df_patterns)