######### DEPRECATED ?

# core/sequence_mining.py
"""
Minería de patrones secuenciales sobre trayectorias académicas.

Complementa a graph_engine.py: en vez de construir el vector de estado
ACUMULADO por paso (usado para el grafo de transiciones), construye por
estudiante una secuencia de ITEMSETS = materias efectivamente aprobadas
EN ESE PASO (delta entre estado acumulado en t y en t-1), que es la
representación correcta para alimentar PrefixSpan.

DECISIÓN GUARDADA PARA LA TESIS (no mezclar sin documentar):
- date_columns=["anio_academico", "periodo"]  -> unidad de paso CURSADAS
- date_columns=["fecha_llamado_mesa"]         -> unidad de paso FINALES
  Cada llamado a build_student_sequences() opera sobre UNA sola fuente
  (cursadas O finales) con su propia escala de step_nro. No se combinan
  en una misma secuencia sin una escala temporal común (fecha real).

DECISIÓN GUARDADA PARA LA TESIS (aclarar en el texto):
- El patrón que devuelve PrefixSpan sobre estas secuencias mide ORDEN DE
  APROBACIÓN (en qué paso una materia pasó a estar aprobada por primera
  vez), NO orden de intento/recursada. Un estudiante que recursó una
  materia 3 veces antes de aprobarla aparece en la secuencia únicamente
  en el paso donde la aprobó; los intentos fallidos previos no generan
  itemset (se filtran como pasos vacíos, ver _EXCLUDED_RESULTS).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from prefixspan import PrefixSpan


APPROVED_RESULT = "A"
EXCLUDED_RESULTS = {"U"}


@dataclass
class SequenceMiningResult:
    sequence_database: list[list[list[str]]]   # una lista de itemsets (listas de codigo_materia) por estudiante
    persona_order: list[int]                   # persona_column correspondiente a cada secuencia, mismo orden que sequence_database
    patterns: list[tuple[int, list[list[str]]]] # (soporte, patron) tal como los devuelve PrefixSpan.frequent(...)


# --------------------------------------------------------------------------- #
# 1. Construcción de secuencias de itemsets (delta por paso)
# --------------------------------------------------------------------------- #

## Agregar en core/graph_engine.py (o en un nuevo core/sequence_mining.py, ver nota al final del archivo)
def build_student_sequences(
    events: pd.DataFrame,
    camada: pd.DataFrame,
    date_columns: list[str],
    dic_materia_idx: dict[str, int],
    result_column: str = "resultado",
    persona_column: str = "persona",
    materia_column: str = "codigo_materia",
    min_sequence_length: int = 1,
) -> tuple[list[list[list[str]]], list[int]]:
    """
    Construye, por estudiante de `camada`, la secuencia ordenada de itemsets de
    materias efectivamente APROBADAS en cada paso (delta), lista para PrefixSpan.

    A diferencia de generate_nodes_and_edges() (graph_engine.py), acá NO se
    calcula el vector de estado acumulado ni su hash: el itemset de un paso es
    directamente la lista de codigo_materia con resultado == "A" agrupada por
    (persona, step_nro). Los pasos sin ninguna aprobación (recursada pura)
    no producen itemset y se omiten de la secuencia.

    date_columns:
        - ["anio_academico", "periodo"]  para cursadas
        - ["fecha_llamado_mesa"]         para finales
      (ver nota de módulo: no mezclar ambas fuentes en una misma llamada)

    min_sequence_length:
        descarta secuencias con menos de N itemsets no vacíos. Sirve para
        mitigar el sesgo de censura por deserción (Crítica #3 del Director:
        estudiantes con 1 sola aprobación registrada inflan el soporte de
        patrones cortos sin ser representativos de una trayectoria completa).

    Returns:
        (sequence_database, persona_order) donde sequence_database[i] es la
        secuencia de itemsets de persona_order[i]. Mismo orden en ambas listas
        (necesario para poder trazar de vuelta qué estudiante aportó cada
        patrón, útil para el panel lateral).
    """
    df = events[events[persona_column].isin(camada[persona_column])].copy()
    df = df[df[materia_column].isin(dic_materia_idx.keys())]
    df = df[~df[result_column].isin(EXCLUDED_RESULTS)]

    if df.empty:
        return [], []

    # ---- 1. step_nro por persona (mismo criterio que graph_engine.generate_nodes_and_edges) ----
    step_order = (
        df[[persona_column] + date_columns]
        .drop_duplicates()
        .sort_values([persona_column] + date_columns)
    )
    step_order["step_nro"] = step_order.groupby(persona_column).cumcount() + 1
    df = df.merge(step_order[[persona_column, "step_nro"] + date_columns], on=[persona_column] + date_columns)

    # print(df[df[persona_column]==4085])

    # OLD ---- 2. Itemset por (persona, step_nro): SOLO materias con resultado == "A" en ese paso ----
    # aprobadas = df[df[result_column] == APPROVED_RESULT]
    # if aprobadas.empty:
    #     return [], []

    # ---- 2. Itemset por (persona, step_nro): agrego en materia_column distintivo "!" si resultado==R ----

    aprobadas = df
    aprobadas[materia_column] = [ ("!" if row.resultado =="R" else "") + row.codigo_materia  for row in aprobadas.itertuples()]



    # print(aprobadas[aprobadas[persona_column]==4085])

    itemsets_por_paso = (
        aprobadas.groupby([persona_column, "step_nro"])[materia_column]
        .apply(lambda s: tuple(sorted(set(s.tolist()))))  #.apply(lambda s: sorted(set(s.tolist())))   # sorted: orden determinístico dentro del itemset
        .reset_index(name="itemset")
        .sort_values([persona_column, "step_nro"])
    )

    # ---- 3. Agrupar en secuencia por persona (lista de itemsets, en orden de step_nro) ----
    secuencias = itemsets_por_paso.groupby(persona_column)["itemset"].apply(list)
    # print(secuencias[:10])

    if min_sequence_length > 1:
        secuencias = secuencias[secuencias.apply(len) >= min_sequence_length]

    persona_order = secuencias.index.tolist()
    sequence_database = secuencias.tolist()
    return sequence_database, persona_order


# --------------------------------------------------------------------------- #
# 2. Minería de patrones frecuentes
# --------------------------------------------------------------------------- #

## Agregar en core/graph_engine.py (o en un nuevo core/sequence_mining.py, ver nota al final del archivo)
def mine_frequent_patterns(
    sequence_database: list[list[tuple[str, ...]]],
    min_support: float = 2, #min_support_ratio
    top_k: int | None = None,
) -> list[tuple[int, list[list[str]]]]:
    """
    Corre PrefixSpan sobre sequence_database (lista de secuencias de itemsets)
    y devuelve los patrones con soporte >= min_support_ratio * len(sequence_database).a.

    top_k: si se especifica, devuelve solo los top_k patrones por soporte
    descendente 
    """

    if not sequence_database:
        return []

    ps = PrefixSpan(sequence_database)
    # min_support = max(1, int(len(sequence_database) * min_support_ratio))
    # print("min_support:  "+str(min_support))
    patterns = ps.frequent(min_support)

    patterns = sorted(patterns, key=lambda x: x[0], reverse=True)  # por soporte desc
    if top_k is not None:
        patterns = patterns[:top_k]

    return patterns




# --------------------------------------------------------------------------- #
# 3. Traducción legible + trazabilidad de estudiantes por patróns
# --------------------------------------------------------------------------- #

## Agregar en core/utils.py
def pattern_to_readable(pattern: list[list[str]], catalog: pd.DataFrame, name_column: str = "nomenclatura") -> str:
    """
    Traduce un patrón (lista de itemsets de codigo_materia) a texto legible,
    usando el catálogo dinámico ya existente (mismo catalog que usa
    materias_aprobadas_str en utils.py). Cada itemset se separa por " -> ",
    y las materias dentro de un mismo itemset (co-ocurrentes en un mismo paso)
    se separan por ", ".

    Ejemplo de salida: "{Algebra} -> {AlgoI, Fisica}"
    """
    codigo_to_nombre = catalog.set_index("codigo_materia")[name_column].to_dict()

    partes = []
    for itemset in pattern:
        nombres = [ ("!" if "!" in cod else "") +(codigo_to_nombre.get(cod.replace("!",""), cod)) for cod in itemset]
        partes.append("{" + ", ".join(nombres) + "}")
    return " -> ".join(partes)


## Agregar en core/sequence_mining.py (o graph_engine.py)
# def students_matching_pattern(
#     pattern: list[list[str]],
#     sequence_database: list[list[list[str]]],
#     persona_order: list[int],
# ) -> list[int]:
#     """
#     Devuelve la lista de personas (subset de persona_order) cuya secuencia
#     contiene `pattern` como subsecuencia (orden preservado, no necesariamente
#     contigua) — es decir, los estudiantes que "votaron" el soporte de ese
#     patrón. Útil para el panel lateral: al seleccionar un patrón, poder
#     mostrar cuántos y cuáles estudiantes lo cumplen (mismo espíritu que
#     "IDs Estudiantes" ya usado en display_selected_edges de callbacks.py).

#     Implementación: matching de subsecuencia por itemsets (greedy, O(len(seq)))
#     término a término: cada itemset del patrón debe estar CONTENIDO
#     (as subset) en algún itemset de la secuencia del estudiante, respetando
#     el orden.
#     """
#     matching_personas = []

#     for persona, secuencia in zip(persona_order, sequence_database):
#         pattern_idx = 0
#         for itemset_estudiante in secuencia:
#             if pattern_idx >= len(pattern):
#                 break
#             itemset_patron = set(pattern[pattern_idx])
#             if itemset_patron.issubset(set(itemset_estudiante)):
#                 pattern_idx += 1
#         if pattern_idx == len(pattern):
#             matching_personas.append(int(persona))

#     return matching_personas

