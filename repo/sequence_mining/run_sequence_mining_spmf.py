# run_sequence_mining_spmf.py
"""
Variante de run_sequence_mining.py que usa SPMF (subset-matching real de
itemsets) en vez de la libreria `prefixspan` de PyPI (itemsets tratados
como simbolos atomicos, ver discusion Director/Gemini).

DIFERENCIA CON EL ORIGINAL: la construccion de sequence_database (via
build_student_sequences) es EXACTAMENTE la misma — no cambia la logica de
agrupacion por (persona, step_nro). Lo unico que cambia es el motor de
mineria: mine_frequent_patterns_spmf en vez de mine_frequent_patterns.

Antes de correr esto contra la base real:
1. pip install spmf
2. Descargar spmf.jar de
   http://www.philippe-fournier-viger.com/spmf/index.php?link=download.php
3. Poner spmf.jar en la misma carpeta que spmf_adapter.py (o pasar
   spmf_jar_dir explicito en las llamadas de abajo).
4. Correr `python spmf_adapter.py` (self_test) y confirmar que imprime "OK".
"""

import numpy as np

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

import sys
sys.path.append(r"repo") 

from visualization_prod.core.data_loader import cargar_base_siu, load_plan_from_directory, build_unified_catalog,build_dic_materia_idx, get_first_year_materias
from visualization_prod.core.utils import get_camada
from sequence_mining import build_student_sequences, pattern_to_readable

from spmf_adapter import mine_frequent_patterns_spmf, SPMF_JAR_DIR

# --------------------------------------------------------------------------- #
# 1. Paths
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).parent.parent
PLANS_DIR = BASE_DIR / "visualization_prod" / "plan"

###### PARA COMPU
# SOURCE_PATH = BASE_DIR / "bases" / "para tesis LCC_v3.xlsx"
# CODIGO_CARRERA = "LCCOMP"
# PLAN_VALUE = "1993"
# PLAN_ID = f"{CODIGO_CARRERA}_{PLAN_VALUE}"
# print("ANALISIS PARA COMPU")

##### PARA MATE
SOURCE_PATH = BASE_DIR / "bases" / "para tesis LCC (LCMAT).xlsx"
CODIGO_CARRERA = "LCMAT"
PLAN_VALUE = "1982"
PLAN_ID = f"{CODIGO_CARRERA}_{PLAN_VALUE}"
print("ANALISIS PARA MATE")


# --------------------------------------------------------------------------- #
# extra: Plot: longitud vs. soporte (idéntico al original)
# --------------------------------------------------------------------------- #
def plot_length_vs_support(df_patterns: pd.DataFrame, output_path: Path | None = None) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7, 5))

    #Jitter
    rng = np.random.default_rng(seed=42)
    jitter_x = rng.uniform(-0.15, 0.15, size=len(df_patterns)) 

    ax.scatter(df_patterns["Lenght"] + jitter_x, #Jitter
               df_patterns["Support"], 
               s=10, #Jitter
               color="#009DAC", zorder=2)

    if not df_patterns.empty:
        top = df_patterns.iloc[0]
        top_jitter = jitter_x[0] #Jitter
        ax.scatter(
            [top["Lenght"] + top_jitter], #Jitter #[top["Lenght"]], 
            [top["Support"]],
            s=260, facecolors="none", edgecolors="#B20D30", linewidths=2.2, zorder=3,
            label=f"Mejor patrón (Longitud={top['Lenght']}, Soporte={round(top['Support'],0)})",
        )
        # ax.legend(loc="best", fontsize=9)

    ax.set_xticks(sorted(df_patterns["Lenght"].unique())) #Jitter
    ax.set_xlabel("Longitud del Patrón Secuencial")
    ax.set_ylabel("Soporte (Frecuencia del patrón)")
    # ax.set_title(f'Patrones secuenciales de {CODIGO_CARRERA}: Longitud vs. Soporte')
    ax.grid(alpha=0.3)

    fig.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150)
    return fig


# --------------------------------------------------------------------------- #
# 2. Carga de datos (misma logica que app.py)
# --------------------------------------------------------------------------- #
ACADEMIC_DATASET = cargar_base_siu(SOURCE_PATH)

YEAR_LIST = sorted(ACADEMIC_DATASET.planes_por_alumno[
    (ACADEMIC_DATASET.planes_por_alumno['anio_inscripcion'] >= 2010) 
    & (ACADEMIC_DATASET.planes_por_alumno['anio_inscripcion'] <= 2019)
    ]['anio_inscripcion'].unique())  # camada a analizar - ajustar según necesidad
# print(YEAR_LIST)

parsed_plan = load_plan_from_directory(PLANS_DIR, PLAN_ID)
catalog = build_unified_catalog({PLAN_ID: parsed_plan})
dic_materia_idx = build_dic_materia_idx(catalog)

# --------------------------------------------------------------------------- #
# 3. Camada (misma funcion que usa callbacks._compute_graph)
# --------------------------------------------------------------------------- #
must_be_1st = get_first_year_materias(pd.DataFrame(catalog), plan_id=PLAN_ID, max_cuatri=2)
# print(must_be_1st)

camada = get_camada(
    ACADEMIC_DATASET.planes_por_alumno,
    ACADEMIC_DATASET.cursadas_por_alumno,
    year_list=YEAR_LIST,
    # plan=PLAN_VALUE,
    codigo_carrera=CODIGO_CARRERA,
    must_be_1st_materias=must_be_1st,
)

print(f'Cantidad de estudiades en ese rango de años: {len(camada)}')

# --------------------------------------------------------------------------- #
# 4. Secuencias (SIN CAMBIOS respecto al pipeline con prefixspan) + SPMF
# --------------------------------------------------------------------------- #
sequence_database, persona_order = build_student_sequences(
    events=ACADEMIC_DATASET.cursadas_por_alumno,
    camada=camada,
    dic_materia_idx=dic_materia_idx,
    date_columns=["anio_academico", "periodo"],
)

print(f"Cantidad de estudiantes en camada con secuencia válida: {len(sequence_database)}\n")

cant_estudiantes_por_year = ACADEMIC_DATASET.planes_por_alumno[
    ACADEMIC_DATASET.planes_por_alumno["anio_inscripcion"].isin(YEAR_LIST)
].groupby("anio_inscripcion").agg(cant_estudiantes=("persona", "nunique"))
avg_cant_estudiantes_por_year = round(cant_estudiantes_por_year['cant_estudiantes'].mean(), 0)
print(f"Promedio de cantidad de estudiantes por año: {avg_cant_estudiantes_por_year}")

top_k = None

min_support=15
patterns = mine_frequent_patterns_spmf(
    sequence_database,
    min_support= min_support, #avg_cant_estudiantes_por_year,
    is_absolute_count=False, #True,       # avg_cant_estudiantes_por_year es conteo absoluto, no ratio
    algorithm="PrefixSpan",       # subset-matching real de itemsets, ver spmf_adapter.py
    spmf_jar_dir=SPMF_JAR_DIR,
    # top_k=top_k,
)

print(f"Cantidad de patterns: {len(patterns)}")

# --------------------------------------------------------------------------- #
# extra: Para hacer grafico para Latex (idéntico al original)
# --------------------------------------------------------------------------- #
longest_first = sorted(patterns, key=lambda x: len(x[1]), reverse=True)[:top_k]

df_patterns = pd.DataFrame({
    "Lenght": [len(item[1]) for item in longest_first],
    "Support": [item[0] for item in longest_first],
    "Pattern": [item[1] for item in longest_first],
})
df_patterns = df_patterns.sort_values(["Lenght", "Support"], ascending=False).reset_index(drop=True)
df_patterns["PatternMaterias"] = df_patterns["Pattern"].apply(
                                    lambda pattern: pattern_to_readable(pattern, catalog, "nomenclatura")
                                )

output_fig = BASE_DIR.parent / "assets_latex"
output_plot_path = Path(output_fig) / f'patrones_secuenciales_{CODIGO_CARRERA}_{PLAN_VALUE}_spmf.png'

fig = plot_length_vs_support(df_patterns, output_path=output_plot_path)

df_patterns.to_csv(Path(output_fig) / f'patrones_secuenciales_{CODIGO_CARRERA}_{PLAN_VALUE}_spmf.csv', index=False)




# ___________________________________________
def caption_stats(csv_path: str | Path) -> dict:
    """
    Calcula las estadísticas necesarias para las captions de las tablas LaTeX
    de patrones secuenciales.

    Parámetros
    ----------
    csv_path : str | Path
        Ruta al CSV de output generado por run_sequence_mining_spmf.py.
        Se espera que tenga las columnas: Lenght, Support, Pattern, PatternMaterias.

    Retorna
    -------
    dict con las claves:
        - total_csv          : total de filas en el CSV
        - total_positivos    : patrones sin negación (sin '!' en PatternMaterias)
        - total_sin_cooc     : patrones positivos donde todos los itemsets tienen tamaño 1
        - total_con_cooc     : patrones positivos con al menos un itemset de tamaño > 1
    """
    import ast

    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    def _has_cooccurrence(pattern_str: str) -> bool:
        try:
            parsed = ast.literal_eval(pattern_str)
            return any(len(itemset) > 1 for itemset in parsed)
        except Exception:
            return False

    df["has_cooc"] = df["Pattern"].apply(_has_cooccurrence)

    df_pos         = df[~df["PatternMaterias"].str.contains("!", na=False)]
    total_pos      = len(df_pos)
    total_con_cooc = int(df_pos["has_cooc"].sum())
    total_sin_cooc = len(df) - total_con_cooc

    stats = {
        "total_csv":       len(df),
        "total_positivos": total_pos,
        "total_sin_cooc":  total_sin_cooc,
        "total_con_cooc":  total_con_cooc,
    }

    print("=" * 52)
    print(f"  Estadísticas de patrones: {Path(csv_path).name}")
    print("=" * 52)
    print(f"  Total filas en CSV          : {stats['total_csv']}")
    print(f"  Patrones positivos          : {stats['total_positivos']}")
    print(f"  └─ Sin co-ocurrencia        : {stats['total_sin_cooc']}")
    print(f"  └─ Con co-ocurrencia        : {stats['total_con_cooc']}")
    print("=" * 52)
    print(f"  Caption tabla A → 'De un total de {stats['total_sin_cooc']} patrones sin")
    print(f"                     co-ocurrencia detectados'")
    print(f"  Caption tabla B → 'De un total de {stats['total_positivos']} patrones")
    print(f"                     positivos, {stats['total_con_cooc']} presentan al menos")
    print(f"                     una co-ocurrencia de este tipo.'")
    print("=" * 52)

    return stats

caption_stats(Path(output_fig) / f'patrones_secuenciales_{CODIGO_CARRERA}_{PLAN_VALUE}_spmf.csv')