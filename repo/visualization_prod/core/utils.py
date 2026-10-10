# core/utils.py
"""
Funciones auxiliares puras
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#para debuggear
from flask import Flask, current_app


##
def get_camada(
    planes_por_alumno: pd.DataFrame,
    cursadas_por_alumno: pd.DataFrame,
    year_list: list[int],
    plan: str | int | None = None,
    codigo_carrera: str = "LCCOMP",
    must_be_1st_materias: list[str] | None = None,
) -> pd.DataFrame:
    """ camada de estudiantes por yearlist dado
        para estudiantes con yearInscripcion en esa carrera en ese yearList y (opcional) a plan selected
        (opcional) primera materia efectivamente cursada fue del primer año de ese plan"""
    
    # planes_carrera se queda SOLO a inscripciones a codigo_carrera selected
    planes_carrera = planes_por_alumno[planes_por_alumno["codigo_carrera"] == codigo_carrera]
    
    # planes_carrera se queda SOLO a inscripciones a plan selected
    if plan is not None:
        planes_carrera = planes_carrera[planes_carrera["plan"].astype(str).str.strip() == str(plan).strip()]

    primer_anio = (
        planes_carrera.groupby("persona")["anio_inscripcion"]
        .min()
        .reset_index()
        .drop_duplicates()
    )

    camada = primer_anio[primer_anio["anio_inscripcion"].isin(year_list)]       # año de inscripcion a carreraSelected está en yearList
    
    if not must_be_1st_materias:
        return camada[["persona"]]

    personas_candidatas = camada["persona"].unique()
    #obtengo primera cursada de personas_candidatas
    primera_materia = ( 
        cursadas_por_alumno[cursadas_por_alumno["persona"].isin(personas_candidatas)]
        .sort_values(["persona", "anio_academico", "periodo"])
        .groupby("persona")["codigo_materia"]
        .first()
    )

    #me quedo solo con personas que su primera cursada sea alguna de las validasMustBe1st
    camada_validada = primera_materia[primera_materia.isin(must_be_1st_materias)].reset_index()
    return camada_validada[["persona"]]

##
def get_carreras_planes_disponibles(planes_por_alumno: pd.DataFrame) -> pd.DataFrame:
    """Combinaciones (codigo_carrera, plan) que EFECTIVAMENTE existen en el
    registro de inscripciones. 'plan' se normaliza a str, por si la fuente trae tipos mixtos (int/str). 
    Fuente de los dropwdowns"""
    df = planes_por_alumno[["codigo_carrera", "plan"]].dropna().copy()
    df["plan"] = df["plan"].astype(str).str.strip()
    return (
        df.drop_duplicates()
        .sort_values(["codigo_carrera", "plan"])
        .reset_index(drop=True)
    )

##
def get_planes_por_carrera(carreras_planes: pd.DataFrame, codigo_carrera: str) -> list:
    """Planes válidos para una carrera dada."""
    planes = carreras_planes.loc[carreras_planes["codigo_carrera"] == codigo_carrera, "plan"]
    return sorted(planes.astype(str).unique().tolist())

##
def vectorEstado_to_vectStr(vector) -> str:
    """Representación en vectStr y hasheable de un vectorEstado """ #dict O(1)
    return np.asarray(vector, dtype=np.int8).tobytes().hex()

##
def materias_aprobadas_str(vector, catalog: pd.DataFrame, name_column: str = "nomenclatura") -> str:
    """Traduce un vector binario a un listado legible, usando el catálogo de materias(con su cuatri sugerido) dinámico.
        orden label coincide con plan csv y nro corresponde a su posicion en el vectorEstado"""
    boolean_mask = np.asarray(vector, dtype=bool)
    
    aprobadas = catalog.loc[boolean_mask, name_column]
    return "\n".join(f"{i + 1}. {nombre}" for i, nombre in aprobadas.items()) 

##
def _compute_max_steps(events, date_columns, persona_column="persona"):
    """Cota superior real de 'pasos' para el rango del slider (cuatrimestres para cursadas, instancias de examen para finales) 
    observada en todo el dataset histórico, sin filtrar por camada/ plan"""
    step_key = events[date_columns].astype(str).agg("|".join, axis=1)
    counts = events.assign(step_key=step_key).groupby(persona_column)["step_key"].nunique()
    return int(counts.max()) if not counts.empty else 20