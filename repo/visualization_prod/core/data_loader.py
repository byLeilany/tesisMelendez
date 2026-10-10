# core/data_loader.py
"""
-Carga e inyección de datos.
-Todas las funciones reciben o devuelven DataFrames explícitos.
-Catálogo de materias dinámico.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

import pandas as pd

#para debuggear
from flask import Flask, current_app

PERIODO_TO_CUATRI = {
    "1er Bimestre": "1er Cuatrimestre",     ##mappea Cursada de Verano a 1erCuatrimestre  (tienen su periodo en 1erBimestre)
    "2do Bimestre": "1er Cuatrimestre",
    "1er Cuatrimestre": "1er Cuatrimestre",
    "3er Bimestre": "2do Cuatrimestre",
    "4to Bimestre": "2do Cuatrimestre",
    "2do Cuatrimestre": "2do Cuatrimestre",
}

############### para añadir 4 csvs
CSV_FILES = {
    "planes": "datos_inscripcion_carrera.csv",
    "cursadas": "datos_actas_tps.csv",
    "finales": "datos_actas_examenes.csv",
    "materias": "datos_materias.csv",
}
def _read_csv(path, **kw):
    # sep=None: detecta ',' o ';' solo. utf-8-sig: tolera el BOM que agrega Excel
    return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", **kw)

REQUIRED_COLUMNS = {
    "planes": {"persona", "codigo_carrera", "plan", "fecha_inscripcion"},
    "cursadas": {"persona", "codigo_materia", "anio_academico", "periodo", "resultado"},
    "finales": {"persona", "codigo_materia", "resultado", "fecha_llamado_mesa", "fecha_cierre_acta"},
    "materias": {"codigo_materia", "nombre_materia"}
}

def _check_columns(df, nombre):
    faltan = REQUIRED_COLUMNS[nombre] - set(df.columns)
    if faltan:
        raise ValueError(f"'{CSV_FILES[nombre]}': faltan columnas {faltan}. "
                         f"Columnas leídas: {list(df.columns)}")
############### para añadir 4 csvs


@dataclass
class AcademicDataset:
    planes_por_alumno: pd.DataFrame
    cursadas_por_alumno: pd.DataFrame
    finales_por_alumno: pd.DataFrame
    lista_de_materias: pd.DataFrame

##
# def cargar_base_siu(source: Union[str, Path]) -> AcademicDataset:
#     """Única función que toca el xlsx para los datos históricos.
#     Se invoca explícitamente desde app.py"""
#     xls = pd.ExcelFile(source)

#     planes = pd.read_excel(xls, sheet_name="planes por alumno")
#     planes["anio_inscripcion"] = pd.to_datetime(planes["fecha_inscripcion"]).dt.year
#     planes["plan"] = planes["plan"].astype(str).str.strip()

#     cursadas = pd.read_excel(xls, sheet_name="cursadas por alumno (2)")
#     cursadas["periodo"] = cursadas["periodo"].map(PERIODO_TO_CUATRI).fillna(cursadas["periodo"])

#     finales = pd.read_excel(xls, sheet_name="finales por alumno (2)")
#     materias = pd.read_excel(xls, sheet_name="lista de materias")

#     return AcademicDataset(
#         planes_por_alumno=planes,
#         cursadas_por_alumno=cursadas,
#         finales_por_alumno=finales,
#         lista_de_materias=materias,
#     )

def cargar_base_siu(source: Union[str, Path]) -> AcademicDataset:
    source = Path(source)
    if source.suffix == ".xlsx":  # modo legacy: no rompe scripts ni notebook viejos
        xls = pd.ExcelFile(source)
        planes = pd.read_excel(xls, sheet_name="planes por alumno")
        cursadas = pd.read_excel(xls, sheet_name="cursadas por alumno (2)")
        finales = pd.read_excel(xls, sheet_name="finales por alumno (2)")
        materias = pd.read_excel(xls, sheet_name="lista de materias")
    else:
        planes = _read_csv(source / CSV_FILES["planes"], parse_dates=["fecha_inscripcion"])
        cursadas = _read_csv(source / CSV_FILES["cursadas"])
        finales = _read_csv(source / CSV_FILES["finales"],
                            parse_dates=["fecha_llamado_mesa", "fecha_cierre_acta"])
        materias = _read_csv(source / CSV_FILES["materias"])
        _check_columns(planes, "planes")
        _check_columns(cursadas, "cursadas")
        _check_columns(finales, "finales")
        _check_columns(materias, "materias")

    # post-proceso común (idéntico al actual)
    planes["anio_inscripcion"] = pd.to_datetime(planes["fecha_inscripcion"]).dt.year
    planes["plan"] = planes["plan"].astype(str).str.strip()
    cursadas["periodo"] = cursadas["periodo"].map(PERIODO_TO_CUATRI).fillna(cursadas["periodo"])
    return AcademicDataset(planes, cursadas, finales, materias)


# --------------------------------------------------------------------------- #
# Plan de estudios dinámico
# --------------------------------------------------------------------------- #
REQUIRED_PLAN_COLUMNS = {"codigo_materia", "nombre_oficial", "nomenclatura", "cuatrimestre_sugerido"}


class InvalidPlanFormatError(ValueError):
    pass

##
def load_study_plan(source: Path, plan_id: str) -> pd.DataFrame: # Union[str, Path, pd.DataFrame]
    """Carga un plan de estudios desde CSV en /source
    Columnas requeridas: codigo_materia, nombre_oficial, nomenclatura,cuatrimestre_sugerido."""
    df = pd.read_csv(source) #source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(source)

    missing = REQUIRED_PLAN_COLUMNS - set(df.columns)
    if missing:
        raise InvalidPlanFormatError(f"Plan '{plan_id}': faltan columnas {missing}")

    df = df.drop_duplicates(subset="codigo_materia").reset_index(drop=True)
    df["plan_id"] = plan_id
    df["cuatrimestre_sugerido"] = df["cuatrimestre_sugerido"].astype(int)
    return df[["plan_id", "codigo_materia", "nombre_oficial", "nomenclatura", "cuatrimestre_sugerido"]]

##
def load_plan_from_directory(plans_dir: Path, plan_id: str # Union[str, Path]
                        #codigo_carrera: str, plan: str
                        ) -> pd.DataFrame:
    """Busca y manda a load el CSV de un plan con el plan_id.csv dentro de `plans_dir`.
    El servidor resuelve el archivo a partir de la selección de los dropdowns carrera/plan
    """
    # plans_dir = Path(plans_dir)
    # plan_id = f"{codigo_carrera}_{plan}"
    csv_path = plans_dir / f"{plan_id}.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"No se encontró '{csv_path.name}' en {plans_dir}."
            f"Verificá que el archivo exista de la forma CARRERA_PLAN.csv."
        )

    return load_study_plan(csv_path, plan_id=plan_id)

## pero ver screenshots en ipad (respecto al TODO de orden names label nodos)
def build_unified_catalog(plans: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Unifica N planes (filas de los csv) en un único catálogo. 
    Causa que las posiciones de ls materias en el vector de estado corresponda a codigo_materia."""
    if not plans:
        raise ValueError("Se requiere al menos un plan de estudios.")

    # df con todas las filas de los CSV (idependiente del plan), para asi sacar la lista de materias UNICAS (con su nombre_oficial y corto) 
    # que componen a todos los planes
    all_plans = pd.concat(list(plans.values()), ignore_index=True)
    # catalogInit con los (codigo_materia,longName,shortName) unicos, sorted by codigo_materia
    catalog = ( 
        all_plans[["codigo_materia", "nombre_oficial", "nomenclatura"]]
        .drop_duplicates(subset="codigo_materia")       
        .sort_values("codigo_materia")        #TODO: mantener hace que el orden de las posiciones de vectorEstado corresponda a codigo_materia. updatE: pincho la idea de sacar sort, pero capaz hay forma d hacer sort en materiasAprobadasStr
        .reset_index(drop=True)
    )

    # por cada plan,
    for plan_id, plan_df in plans.items():
        mapping = plan_df.set_index("codigo_materia")["cuatrimestre_sugerido"]               #hago mapeo == df unica col cuatriSugerido para ese plan con codigo_materia como index 
        catalog[f"cuatri_sugerido__{plan_id}"] = catalog["codigo_materia"].map(mapping)     # agrego columna a catalog de cuatriSugeridoEsePlan con map que toma columna cod_materia y reemplaza con cuatriSugeridoDeMap sino esta esa materia, deja en NaN
        # map es la forma vectorizada (O(n), evita loops/merges manuales) de alinear valores por clave sin depender del orden de filas entre catalog y plan_df.

    return catalog

##
def build_dic_materia_idx(catalog: pd.DataFrame) -> dict[str, int]:
    """return diccionario (codigo_materia -> posición en vector_Estado) . Lookup O(1)"""
    return {codigo: idx for idx, codigo in enumerate(catalog["codigo_materia"])}

##
def build_reference_plan(catalog: pd.DataFrame, plan_id: str) -> list[list[int]]:
    """Trayectoria curricular ideal (una por cuatrimestre sugerido) derivada del
    catálogo dinámico. En lista de vectoresEstado (lista binaria)
    Reemplaza `nodosDelPlan93` / `nodosDelPlan23` hardcodeados."""
    cuatris_ese_plan = f"cuatri_sugerido__{plan_id}"
    if cuatris_ese_plan not in catalog.columns:
        raise KeyError(f"El catálogo no contiene información del plan '{plan_id}'.")

    m = len(catalog)    #long vectoresEstado sera #materias en catalog aka #materiasUniqueEnTodosLosPlanesCargados
    max_cuatri = int(catalog[cuatris_ese_plan].dropna().max())
    #todos empiezan en el cuatri sin ninguna materia aprobada
    trayectoria = [[0] * m]

    acumulado = [0] * m         #por cuatrimestre, el plan me indica que debo tener ciertas materias aprobadas, y asi ir avanzando
    for cuatri in range(1, max_cuatri + 1):
        for pos in catalog.index[catalog[cuatris_ese_plan] == cuatri].tolist():     #indice aka catalog[codigo_materia] indica orden de los vectoresEstado
            acumulado[pos] = 1
        trayectoria.append(acumulado.copy())

    return trayectoria
##
def get_first_year_materias(catalog: pd.DataFrame, plan_id: str, max_cuatri: int = 2) -> list[str]:
    """Encuentra en el catalogo los codigo_materia que pertenecen hasta el 2do cuatri del plan sugerido"""
    cuatris_ese_plan = f"cuatri_sugerido__{plan_id}"
    if cuatris_ese_plan not in catalog.columns:
        raise KeyError(f"El catálogo no contiene información del plan '{plan_id}'.")
    return catalog.loc[catalog[cuatris_ese_plan] <= max_cuatri, "codigo_materia"].drop_duplicates().tolist()


# def migrate_legacy_plan_matrix(
#     materia_codes: list[str],
#     nombres_largos: list[str],
#     nombres_cortos: list[str],
#     legacy_cumulative_matrix: list[list[int]],
# ) -> pd.DataFrame:
#     """Utilidad de migración: convierte una matriz acumulativa hardcodeada del
#     estilo `nodosDelPlan93` al nuevo formato tabular (codigo_materia, ..., 
#     cuatrimestre_sugerido), para no perder el trabajo de modelado curricular ya hecho."""
#     m = len(materia_codes)
#     cuatri_sugerido = [None] * m
#     for cuatri_idx, row in enumerate(legacy_cumulative_matrix):
#         for pos in range(m):
#             if row[pos] == 1 and cuatri_sugerido[pos] is None:
#                 cuatri_sugerido[pos] = cuatri_idx
#     return pd.DataFrame(
#         {
#             "codigo_materia": materia_codes,
#             "nombre_oficial": nombres_largos,
#             "nomenclatura": nombres_cortos,
#             "cuatrimestre_sugerido": cuatri_sugerido,
#         }
#     )
