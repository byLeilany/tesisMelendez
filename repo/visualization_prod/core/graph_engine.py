# core/graph_engine.py
"""
-Algoritmo genérico y vectorizado de construcción del grafo de trayectorias.
-Reemplaza nodosFromTP.py + nodosFromFINALES.py
-(pasos sin aprobación nueva -> source== target), con peso = cantidad de PERSONAS ÚNICAS (nunique), no de ocurrencias.
-Registra recursadas
-expone max_appears del subgrafo renderizado para normalización dinámica de aristas (Crítica #6).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.utils import vectorEstado_to_vectStr

#para debuggear
from flask import Flask, current_app



APPROVED_RESULT = "A"
EXCLUDED_RESULTS = {"U"}


@dataclass
class TrajectoryGraph:
    nodes: pd.DataFrame   # index = node_id; columnas: vectStr, vector (np.ndarray)
    edges: pd.DataFrame   # columnas: source, target, appears, id_list
    max_appears: int = 0
    edges_by_step: pd.DataFrame | None = None   # (source, target, step_nro) por transición individual
    # loop_materia_info: pd.DataFrame | None = None #"source", "target", "codigo_materia","lista_estudiantes","sum_intentos


##
def generate_nodes_and_edges(
    events: pd.DataFrame,
    camada: pd.DataFrame,
    dic_materia_idx: dict[str, int],
    date_columns: list[str],
    result_column: str = "resultado",
    persona_column: str = "persona",
    materia_column: str = "codigo_materia",
) -> TrajectoryGraph:
    """
    Función GENÉRICA: sirve tanto para cursadas como para finales.

    Genera self-loops: en el cuatrimestre en el que el estudiante no logró ninguna aprobación nueva (recursada sin éxito)
    cuyo peso `appears` es la cantidad de PERSONAS ÚNICAS con al menos un cuatrimestre estancado en ese estado (no la cantidad de intentos).
    """
    m = len(dic_materia_idx)

    #filtro cursadas/finales por:
    df = events[events[persona_column].isin(camada[persona_column])].copy() # que sea de personas dentro de la camada
    df = df[df[materia_column].isin(dic_materia_idx.keys())]                # codigo_materia filtro materias que esten en el plan
    df = df[~df[result_column].isin(EXCLUDED_RESULTS)]                      # no es resultado "U" ausente

    if df.empty:
        zero_vec = np.zeros(m, dtype=np.int8)
        nodes = pd.DataFrame({"vectStr": [vectorEstado_to_vectStr(zero_vec)], "vector": [zero_vec]})
        edges = pd.DataFrame(columns=["source", "target", "appears", "id_list", "is_loop", "reprobadas_info"]) #avg_intentos_previos
        edges_by_step = pd.DataFrame(columns=["source", "target", "step_nro"])
        # loop_info = pd.DataFrame(columns=["source", "target", "codigo_materia","lista_estudiantes","sum_intentos"])
        return TrajectoryGraph(nodes=nodes, edges=edges, max_appears=0, edges_by_step=edges_by_step)#, loop_materia_info=loop_info)


    df["materia_pos"] = df[materia_column].map(dic_materia_idx)     # crea col con idx de esa materia
    df["is_approved"] = df[result_column] == APPROVED_RESULT        # crea colBool aprobada?
    # current_app.logger.debug(df)                

    # ---- 1. Ordinal de paso por persona (incluye pasos SIN aprobación) ------
    step_order = (                        #dfChico que representa en orden todos los step_nro distintos que aparecen en df. Ordenado por [persona, date_columns]
        df[[persona_column] + date_columns]
        .drop_duplicates()
        .sort_values([persona_column] + date_columns)
    )
    step_order["step_nro"] = step_order.groupby(persona_column).cumcount() + 1          #en step_nro esta enumerando los [date_columns] agrupado por persona. (es decir, su1erCuatri, su2doCuatri,... ó su1erFechaFinal, su2daFechaFinal, ...)
    # current_app.logger.debug(step_order) 
    df = df.merge(step_order[([persona_column,"step_nro"]+date_columns)], on=([persona_column]+date_columns)) #agrega ese step_nro al df
    df = df.sort_values([persona_column, materia_column] + date_columns)

    #ARCHIVED idea ---- 2. Recursadas mean: intentos fallidos acumulados por (persona, materia) - 
    # df["intentos_previos_fallidos"] = (         #col intentos_previos_fallidos enumera para esa (persona,materia) la cantidad veces antes reprobo esa misma materia
    #     (~df["is_approved"]).groupby([df[persona_column], df[materia_column]]).cumsum()
    # ) 
    # intentos_al_aprobar = df.loc[
    #     df["is_approved"], [persona_column, "step_nro", "intentos_previos_fallidos"]     #al momento que se logra aprobar esa materia, se guardar es por paso step_nro la #intentos_fallidos
    # ]                                                                                    #se utilizara como medida de “cuánto le costó, en promedio, aprobar lo que aprobó en ese tram
    # current_app.logger.debug(intentos_al_aprobar)  


    ## TODO WIP:
    # ---- 2b. Capturar raw data recursadas
    # recursadas = df[df["is_approved"]].copy()
    # recursadas_por_paso = (
    #     recursadas.groupby([persona_column, "step_nro", materia_column])
    #     .agg(
    #         lista_estudiantes=(persona_column, "nunique"),
    #         sum_intentos=("intentos_previos_fallidos", "max"),
    #     )
    #     .reset_index()
    #     .rename(columns={materia_column: "codigo_materia"})
    # )
    # current_app.logger.debug(recursadas_por_paso[(recursadas_por_paso["codigo_materia"]=="COMP930016") & (recursadas_por_paso["persona"]==23683) ])

    # ---- 3. Matriz wide SOLO con aprobaciones 
    #matriz pivot con filas persona,step_nro y cols posMateria donde hay 1 en todas las materias que aprobó en ese step (indice con solo persona,stepNroAprobado)
    wide = (        
        df[df["is_approved"]]
        .pivot_table(
            index=[persona_column, "step_nro"], #una fila es por cada (persona,step_nro)
            columns="materia_pos",
            values="is_approved",
            aggfunc="max",
            fill_value=0,
        )
        .reindex(columns=range(m), fill_value=0)
        .astype(np.int8)
    )
    wide.index.set_names([persona_column, "step_nro"], inplace=True)
    # current_app.logger.debug(wide)
    #621     1          0   0   0   0   0   0   0   0   1   0   0   0   0   0   0   0   0
    #        2          0   1   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0

    # ---- 3b. Full wide matriz con TODOS los pasos (lo que genera los loops). 
    # Si habia persona,step_nro con "R", aca queda con vector 0 en esta matriz
    full_index = pd.MultiIndex.from_frame(                                #crea indice con todos persona,step_nro disponibles (el indice son 2 valores)
        step_order[[persona_column, "step_nro"]].drop_duplicates(),
        names=[persona_column, "step_nro"],
    )
    wide_full = wide.reindex(full_index, fill_value=0).astype(np.int8)    #amplia a wide para que haya una fila con cada step posible
    # current_app.logger.debug(wide_full)

    # ---- 4. Estado acumulado: OR lógico vectorizado (cummax) por persona ----
    wide_full = wide_full.sort_index(level=[persona_column, "step_nro"])    ## se confirma que esté ordenado segun (persona,step_nro) antes de hacer OR

    state_matrix = wide_full.groupby(level=persona_column).cummax()         ## para que fila a fila (una fila es por cada (persona,step_nro)) se haga un OR logico acumulativo (cunmax). Por lo que en cada fila queda el vector_Estado que representa sus materias aprobadas hasta ese paso
    state_matrix["vectStr"] = [vectorEstado_to_vectStr(row) for row in state_matrix.to_numpy(dtype=np.int8)] #to_numpy da una matriz 2D (una fila es por cada (persona,step_nro)), donde cada row es un vector_estado
    state_matrix = state_matrix.reset_index()
    
    """
    # antes de reset_index() — índice MultiIndex:
                    0   1   vectStr
    persona step_nro
    1001    1           1   0   "..."
    1001    2           1   1   "..."
    
    # después de reset_index() — columnas normales:
       persona  step_nro  0   1   vectStr
    0  1001     1         1   0   "..."
    1  1001     2         1   1   "..."
    """
    
    # ---- 5. Nodos únicos: hash de vector -> node_id -------------------------
    zero_vectStr = vectorEstado_to_vectStr(np.zeros(m, dtype=np.int8))
    unique_vectStr = state_matrix["vectStr"].drop_duplicates().tolist()

    if zero_vectStr in unique_vectStr:
        unique_vectStr.remove(zero_vectStr)            # se elimina el zero_vectStr en caso de que este en pos distinta al inicio
    unique_vectStr = [zero_vectStr] + unique_vectStr      # y lo forzamos SIEMPRE a la posición 0

    #vectStr_to_id: se crea un diccionario vectStr -> nodo_id
    vectStr_to_id = {key: idx for idx, key in enumerate(unique_vectStr)} #le coloca a cada vectStr un nro de Nodo (el idx)
    # current_app.logger.debug(vectStr_to_id)

    vector_cols = list(range(m))
    #vectStr_to_vector: se crea diccionario vectStr -> vector
    vectStr_to_vector = {zero_vectStr: np.zeros(m, dtype=np.int8)}
    for key, vec in zip(state_matrix["vectStr"], state_matrix[vector_cols].to_numpy(dtype=np.int8)):
        vectStr_to_vector.setdefault(key, vec)

    nodes = (
        pd.DataFrame({"vectStr": list(vectStr_to_id.keys()), 
                      "vector": [vectStr_to_vector[k] for k in vectStr_to_id.keys()]},
                    index=list(vectStr_to_id.values())).sort_index()
    )


    # ---- 6. Aristas: transición estado_(t-1) -> estado_t, PASO A PASO -------
    # (incluye pasos sin avance donde source == target que genera un self-loop)
    state_matrix["node_id"] = state_matrix["vectStr"].map(vectStr_to_id)         # col con nodo_id para su vectStr correspondiente
    state_matrix = state_matrix.sort_values([persona_column, "step_nro"])

    zero_id = vectStr_to_id[zero_vectStr]
    # quiero que en cada fila tenga nodo_id_Origen y nodo_id(destino).
    # col donde agrupado por persona hago shift de la col node_id hacia abajo, (en el step_nro 1 de cada persona, como no tiene "paso anterior" 
    # se rellena con el node_id 0 que representa al vectorZero (es decir todos arrancan desde vectStr 0...0))
    state_matrix["prev_node_id"] = (        
        state_matrix.groupby(persona_column)["node_id"].shift(1).fillna(zero_id).astype(int)
    )

    #ARCHIVED idea: guardo info de intentosPreviosPromedio antes de por fin aprobar la materia
    # intentos_por_paso = (
    #     intentos_al_aprobar.groupby([persona_column, "step_nro"])["intentos_previos_fallidos"]
    #     .mean()
    #     .rename("intentos_previos_promedio")
    #     .reset_index()
    # )
    # current_app.logger.debug(intentos_por_paso[intentos_por_paso["intentos_previos_promedio"]!=0])
    # current_app.logger.debug(intentos_al_aprobar[intentos_al_aprobar[persona_column]==25246])
    # current_app.logger.debug(state_matrix[state_matrix[persona_column]==25246])

    #ARCHIVED idea 
    # Imprimir intent intentos_por_paso para haber si hay algo != 0.0 y check si tiene sentido con valores en state_matrix
    # state_matrix = state_matrix.merge(intentos_por_paso, on=[persona_column, "step_nro"], how="left")
    #state_matrix["intentos_previos_promedio"] = state_matrix["intentos_previos_promedio"].fillna(0.0)
    

    edges_raw = state_matrix[[persona_column, "step_nro", "prev_node_id", "node_id"
                              #, "intentos_previos_promedio"
                              ]].rename( 
        columns={"prev_node_id": "source", "node_id": "target"}
    )

    # ---- 6b. Reprobadas info per edge_by_step -------
    # Creo edges_by_step donde a edges_raw agrego una columna materia_column que si HAY info significa que la materia fue Reprobada EnEseStep y causa que no pudieron salir de ese estado
    # por si en edges_raw (persona,step_nro) reprobo N materias, por el merge se crean tantas filas para (persona,step_nro) como reprobadas tenga en ese step_nro
    edges_by_step = edges_raw.merge(
                            df[~df["is_approved"]][[persona_column, "step_nro", materia_column]],
                            on=[persona_column, "step_nro"],
                            how="left"
                        )
    
    # current_app.logger.debug(edges_by_step[(edges_by_step[persona_column].isin([25953, 37669, 37676, 23821, 25170])) &
    #                                        (edges_by_step["step_nro"]<=2) ])

    reprobadas_per_edge_info = edges_by_step.groupby(["source", "target", "codigo_materia"]     #por esa arista y por materia quiero ver #intentos y #personasUnicasQueLaReprobaronEnEseEstado
                    ).agg(
                        lista_estudiantes=(persona_column, lambda s: sorted(set(s.astype(int).tolist()))),
                        sum_intentos=(persona_column, "count")
                    ).reset_index()
    

    # en df_reprobada_info: me quedo unicamente con 3 columnas ["source", "target", "reprobadas_info"]
    df_reprobada_info = (reprobadas_per_edge_info.groupby(["source", "target"])
                     # Filtramos solo las columnas que importan para el "mini df"
                     .apply(lambda x: x[["codigo_materia", "lista_estudiantes", "sum_intentos"]].to_dict('records'), include_groups=False)
                     .reset_index(name='reprobadas_info'))
    #archived
    # reprobadas_with_steps = df[~df["is_approved"]].merge( edges_raw, on=[persona_column, "step_nro"], how="inner") 
    # reprobadas_per_edge_info["reprobadas_info"] = reprobadas_per_edge_info["codigo_materia"].astype(str) + ": " + reprobadas_per_edge_info[["lista_estudiantes","sum_intentos"]].astype(str).agg(", ".join, axis=1)
    # df_reprobada_info = (reprobadas_per_edge_info.groupby(["source", "target"])['reprobadas_info']
    #                                                         .apply(f'\n '.join)
    #                                                         .reset_index())
    # current_app.logger.debug(df_reprobada_info)

    # ---- 7. Agregación: appears = PERSONAS ÚNICAS por arista -----------------
    # nunique descarta duplicados tanto para loops 
    

    edges = (
        edges_raw.groupby(["source", "target"])
        .agg(
            appears=(persona_column, "nunique"), # para (source == target), entonces loops me queden con #personasQueNoAvanzaron de estado
            id_list=(persona_column, lambda s: sorted(set(s.astype(int).tolist())))
            # ARCHIVED idea
            # avg_intentos_previos=("intentos_previos_promedio", "mean"),
        )
        .reset_index()
    )
    # current_app.logger.debug(edges)
    edges["is_loop"] = edges["source"] == edges["target"]
    edges = edges.merge(df_reprobada_info, on=["source","target"], how="left")
    # edges["reprobadas_info"] = edges["reprobadas_info"].fillna({})

    max_appears = int(edges["appears"].max()) if not edges.empty else 0
    return TrajectoryGraph(
        nodes=nodes,
        edges=edges,
        max_appears=max_appears,
        edges_by_step=edges_by_step #edges_raw[["source", "target", "step_nro",persona_column]]
    )



##
def filter_by_step_range(graph: TrajectoryGraph, min_step: int, max_step: int, persona_column: str = "persona",) -> TrajectoryGraph:
    """Recalcula appears SOLO con las transiciones dentro de [min_step, max_step], 
    pero preserva el universo de aristas de graph.edges (left-merge) que se alcanzaron hasta max_step: 
    una arista sin ocurrencias en el rango queda con appears=0 en vez de desaparecer, 
    para poder visualizar evolución temporal manteniendo la topología completa del grafo."""

    valid_pairs = (
        graph.edges_by_step.loc[
            graph.edges_by_step["step_nro"] <= max_step,
            ["source", "target"],
        ]
        .drop_duplicates()
    )
    edges = graph.edges.merge(valid_pairs, on=["source", "target"], how="inner").reset_index(drop=True)
    # current_app.logger.debug(edges.columns)

    in_range = graph.edges_by_step[graph.edges_by_step["step_nro"].between(min_step, max_step)]
    # current_app.logger.debug(in_range[(in_range["source"]==0)&(in_range["target"]==0)])

    if in_range.empty:
        recomputed = edges[["source", "target"]].copy()
        recomputed["appears"] = 0
        recomputed["id_list"] = [[] for _ in range(len(recomputed))]
        recomputed["reprobadas_info"] = [{} for _ in range(len(recomputed))]
        df_reprobada_info = pd.DataFrame(columns=["source", "target"])
        # recomputed["reprobadas_info"] = pd.DataFrame(columns=["codigo_materia", "lista_estudiantes", "sum_intentos"]).to_dict('records')
        # recomputed["avg_intentos_previos"] = 0.0
    else: 
        # current_app.logger.debug(f"min={min_step} max={max_step}")
        # current_app.logger.debug(in_range["step_nro"].unique())
        recomputed = (
            in_range.groupby(["source", "target"])
            .agg(appears=(persona_column, "nunique"),
                 id_list=(persona_column, lambda s: sorted(set(s.astype(int).tolist())))
            ) 
            .reset_index()
        )
        reprobadas_recomputed = (
            in_range.dropna(subset=["codigo_materia"])
            .groupby(["source", "target", "codigo_materia"])
            .agg(
                lista_estudiantes=(persona_column, lambda s: sorted(set(s.astype(int).tolist()))),
                sum_intentos=(persona_column, "count")
            )
            .reset_index()
        )
        df_reprobada_info = (reprobadas_recomputed.groupby(["source","target"])
        .apply(lambda x: x[["codigo_materia","lista_estudiantes","sum_intentos"]].to_dict('records'), include_groups=False)
        .reset_index(name='reprobadas_info'))

    
    
    ##dropeo las dos columnas que recalcule para agregarlas con el merge 
    # a recomputed que tiene ["appears","id_list"] recalculadas
    edges = edges.drop(columns=["appears","id_list","reprobadas_info"]).merge( 
        recomputed, on=["source", "target"], how="left"
    )
    # y merge a df_reprobada_info que tiene ["reprobadas_info"] recalculada
    edges = edges.merge(df_reprobada_info, on=["source","target"], how="left")
    # edges["reprobadas_info"] = edges["reprobadas_info"].apply(lambda x: x if isinstance(x, dict) else {})
    edges["id_list"] = edges["id_list"].apply(lambda x: x if isinstance(x, list) else [])
    edges["appears"] = edges["appears"].fillna(0).astype(int)
    # edges["reprobadas_info"] =  edges["reprobadas_info"].fillna({}) 
    # edges["avg_intentos_previos"] = edges.get("avg_intentos_previos", 0.0)

    max_appears = int(edges["appears"].max()) if not edges.empty else 0
    return TrajectoryGraph(nodes=graph.nodes, edges=edges, max_appears=max_appears, edges_by_step=graph.edges_by_step)

##
def prune_graph(graph: TrajectoryGraph, min_edge_weight: int) -> TrajectoryGraph: 
    """cut_edges_at, es decir poda por umbral mínimo de estudiantes por arista + eliminación iterativa
    de nodos sin arista entrante (excepto la raíz, node_id == 0)."""
    edges = graph.edges[graph.edges["appears"] >= min_edge_weight].copy()
    all_ids = set(graph.nodes.index)

    def _disconnected(edges_df: pd.DataFrame, exclude: set[int]) -> set[int]:               ##busca nodos desconectados
        reachable = set(edges_df.loc[edges_df["source"] != edges_df["target"], "target"])   #nodos_id con flecha de entrada
        return all_ids - reachable - {0} - exclude                                          #a todos los nodos le quito los alcanzable y los que ya marque como desconectado, en caso de que haya cadena que empezaba en weight (a)-abajoMin->(b)-overMin->(c) y tengo que eliminar la cadena extra desconectada dando vueltas

    disconnected: set[int] = set() #empiezo con ningun nodo para desconectar
    prev_len = -1
    while len(disconnected) != prev_len:    #mientras siga finding (disconnected keeps crecer) nodos sin flechaEntrada
        prev_len = len(disconnected)
        edges = edges[~edges["source"].isin(disconnected) & ~edges["target"].isin(disconnected)] #quito los edges si van a un nodoDesconectado
        disconnected |= _disconnected(edges, disconnected)              #agrega al set disconnected todos los elementos nuevos que devuelve _disconnected, sin duplicar

    remaining_ids = sorted(all_ids - disconnected)  # me quedo con los idx de los nodosConectados
    nodes = graph.nodes.loc[remaining_ids]
    max_appears = int(edges["appears"].max()) if not edges.empty else 0
    # current_app.logger.debug(edges.columns)
    return TrajectoryGraph(nodes=nodes, edges=edges.reset_index(drop=True), max_appears=max_appears,edges_by_step=graph.edges_by_step,)

##
def normalized_edge_width(appears: int, max_appears: int, min_width: float = 1.0, max_width: float = 30.0) -> float:
    """Normalización dinámica de edgeWidth 
    Usa el máximo#Apariciones del grafo"""
    if max_appears <= 0:
        return min_width
    return max(min_width, round((appears / max_appears) * max_width, 2))


# def filter_by_step_range(graph: TrajectoryGraph, min_step: int, max_step: int) -> TrajectoryGraph:
#     """Busca aristas validas 
#     Filtra aristas cuya transición ocurrió fuera de [min_step, max_step] para AL MENOS una persona. Usa merge en vez de .apply(axis=1): además de
#     ser vectorizado (más rápido), evita un bug de pandas donde .apply(axis=1)
#     sobre un DataFrame vacío devuelve el propio DataFrame en vez de una
#     Series booleana, corrompiendo las columnas del resultado.


#     Me quedo con las edgesIN que son aristas que cumplan que su step_nro este dentro de cuatriRange.
#     TODO: quiero que edges = edgesIN + edgeHistoricosPeroCon#AppearsEn0. 
#     Es decir que para los graph.edges_by_step["step_nro"].between(1, min_step) siga existiendo la arista pero con appears=0 y id_list=[]
#     TODO: check if puedo tomar "foto" por ejm al cuatriRange [2,2]? 
#     """
#     valid_pairs = (
#         graph.edges_by_step.loc[
#             graph.edges_by_step["step_nro"].between(min_step, max_step),
#             ["source", "target"],
#         ]
#         .drop_duplicates()
#     )

#     if valid_pairs.empty or graph.edges.empty:
#         empty_edges = graph.edges.iloc[0:0].copy()  # conserva columnas, unicamente deja fila de vectorNulo
#         return TrajectoryGraph(
#             nodes=graph.nodes, 
#             edges=empty_edges, 
#             max_appears=0, 
#             edges_by_step=graph.edges_by_step
#         )

#     edges = graph.edges.merge(valid_pairs, on=["source", "target"], how="inner").reset_index(drop=True)
#     max_appears = int(edges["appears"].max()) if not edges.empty else 0
#     return TrajectoryGraph(nodes=graph.nodes, edges=edges, max_appears=max_appears, edges_by_step=graph.edges_by_step, loop_materia_info=graph.loop_materia_info)
