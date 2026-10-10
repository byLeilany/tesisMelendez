######### DEPRECATED ?

# run_sequence_mining_standalone.py
"""
Script standalone (fuera de la app Dash) para correr sequence mining sobre
la camada de una carrera+plan seleccionado.
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

import sys
sys.path.append(r"repo") 

from visualization_prod.core.data_loader import cargar_base_siu, load_plan_from_directory, build_unified_catalog,build_dic_materia_idx, get_first_year_materias
from visualization_prod.core.utils import get_camada
from sequence_mining import build_student_sequences, mine_frequent_patterns, pattern_to_readable

# --------------------------------------------------------------------------- #
# 1. Paths
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).parent.parent
PLANS_DIR = BASE_DIR / "visualization_prod" / "plan"

##### PARA COMPU
SOURCE_PATH = BASE_DIR / "bases" / "para tesis LCC_v3.xlsx"
CODIGO_CARRERA = "LCCOMP"
PLAN_VALUE = "1993"
PLAN_ID = f"{CODIGO_CARRERA}_{PLAN_VALUE}"   # debe coincidir con LCCOMP_1993.csv en PLANS_DIR

# # ##### PARA MATE
# SOURCE_PATH = BASE_DIR / "bases" / "para tesis LCC (LCMAT).xlsx"
# CODIGO_CARRERA = "LCMAT"
# PLAN_VALUE = "1982"
# PLAN_ID = f"{CODIGO_CARRERA}_{PLAN_VALUE}"   # debe coincidir con LCMAT_1982.csv en PLANS_DIR


# --------------------------------------------------------------------------- #
# extra:  Plot: longitud vs. soporte, resaltando el patrón top (primero tras el sort)
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
            label=f"Mejor patrón (Longitud={top['Lenght']}, Soporte={round(top['Support'],0)})",
        )
        ax.legend(loc="best", fontsize=9)

    ax.set_xlabel("Longitud del Patrón Secuencial")
    ax.set_ylabel("Soporte (Frecuencia del patrón)")
    ax.set_title(f'Patrones secuenciales de {CODIGO_CARRERA}: Longitud vs. Soporte')
    ax.grid(alpha=0.3)

    fig.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150)
    return fig



# --------------------------------------------------------------------------- #
# 2. Carga de datos (misma lógica que app.py)
# --------------------------------------------------------------------------- #
ACADEMIC_DATASET = cargar_base_siu(SOURCE_PATH)

YEAR_LIST = sorted(ACADEMIC_DATASET.planes_por_alumno[ACADEMIC_DATASET.planes_por_alumno['anio_inscripcion']>=2010]['anio_inscripcion'].unique())  # camada a analizar - ajustar según necesidad
# print(YEAR_LIST)

parsed_plan = load_plan_from_directory(PLANS_DIR, PLAN_ID)
catalog = build_unified_catalog({PLAN_ID: parsed_plan})
dic_materia_idx = build_dic_materia_idx(catalog)

# --------------------------------------------------------------------------- #
# 3. Camada (misma función que usa callbacks._compute_graph)
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
# 4. Secuencias + PrefixSpan
# --------------------------------------------------------------------------- #
sequence_database, persona_order = build_student_sequences(
    events=ACADEMIC_DATASET.cursadas_por_alumno,
    camada=camada,
    dic_materia_idx= dic_materia_idx,
    date_columns=["anio_academico", "periodo"],   # cursadas (ver nota de unidad de paso en sequence_mining.py)
    # min_sequence_length=2,
)
    
print(f"Cantidad de estudiantes en camada con secuencia válida: {len(sequence_database)}\n")


cant_estudiantes_por_year = ACADEMIC_DATASET.planes_por_alumno[
    ACADEMIC_DATASET.planes_por_alumno["anio_inscripcion"].isin(YEAR_LIST)
    ].groupby("anio_inscripcion").agg(cant_estudiantes=("persona", "nunique"))
avg_cant_estudiantes_por_year = round(cant_estudiantes_por_year['cant_estudiantes'].mean(),0)
print(f"Promedio de cantidad de estudiantes por año: {avg_cant_estudiantes_por_year}")

top_k= None 
patterns = mine_frequent_patterns(sequence_database, min_support=100, top_k=top_k)

print(f"Cantidad de patterns: {len(patterns)}")



# --------------------------------------------------------------------------- #
# extra: Para hacer grafico para Latex
# --------------------------------------------------------------------------- #
longest_first = sorted(patterns, key=lambda x: len(x[1]), reverse=True)[:top_k]


df_patterns = pd.DataFrame({
    "Lenght": [len(item[1]) for item in longest_first],
    "Support": [item[0] for item in longest_first],
    "Pattern": [item[1] for item in longest_first],
})
df_patterns = df_patterns.sort_values(["Lenght", "Support"], ascending=False).reset_index(drop=True)
# df_patterns = df_patterns[df_patterns["Lenght"]>1]
df_patterns["PatternMaterias"] = df_patterns["Pattern"].apply(
                                    lambda pattern: pattern_to_readable(pattern, catalog, "nomenclatura") #parse_snapshot
                                )


output_fig = BASE_DIR.parent / "assets_latex"
output_plot_path = Path(output_fig)/f'patrones_secuenciales_{CODIGO_CARRERA}_{PLAN_VALUE}.png'

fig = plot_length_vs_support(df_patterns, output_path=output_plot_path)

df_patterns.to_csv(Path(output_fig)/f'patrones_secuenciales_{CODIGO_CARRERA}_{PLAN_VALUE}.csv', index=False)


# --------------------------------------------------------------------------- #
# 5. Output
# --------------------------------------------------------------------------- #
# print(f"Cantidad de estudiantes en camada con secuencia válida: {len(sequence_database)}\n")

# for support, pattern in patterns:
#     print(f"Soporte: {support} | Patrón (códigos): {pattern}")
#     print(f"Soporte: {support} | Patrón (legible): {pattern_to_readable(pattern, catalog, 'nomenclatura')}")
#     print()