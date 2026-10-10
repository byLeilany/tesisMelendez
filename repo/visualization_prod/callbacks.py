"""
Lógica de interactividad de la app
"""

import base64
import io

import pandas as pd
import numpy as np
from dash import Input, Output, State, html, no_update


from app import app, cache, ACADEMIC_DATASET, PLANS_DIR, CARRERAS_PLANES_DISPONIBLES,  MAX_STEP_CURSADAS, MAX_STEP_FINALES
from core.data_loader import (
    InvalidPlanFormatError,
    get_first_year_materias,
    build_dic_materia_idx,
    load_plan_from_directory,
    build_unified_catalog,
    build_reference_plan,
)
from core.graph_engine import generate_nodes_and_edges, filter_by_step_range, prune_graph, normalized_edge_width
from core.utils import get_camada, materias_aprobadas_str ,get_planes_por_carrera, _compute_max_steps


from flask import Flask, current_app


AZUL = "#009DAC"


HIDDEN = {"display": "none"}
VISIBLE_LEGEND = {"display": "flex"}

# # --------------------------------------------------------------------------- #
# # Carga del CSV de materias del plan
# # --------------------------------------------------------------------------- #
"""TODO: Consistencia entre /plan y planes_por_alumno no se valida automáticamente. El dropdown de plan se puebla desde CARRERAS_PLANES_DISPONIBLES 
(datos reales de inscripción), pero nada garantiza que exista el CSV correspondiente en /plan — si falta, el usuario recién se entera 
al seleccionar, con el mensaje de FileNotFoundError. Se podría filtrar el dropdown de plan para que solo muestre las combinaciones que 
también tienen CSV en disco (agregando una función list_available_plan_files(plans_dir) que intersecte con CARRERAS_PLANES_DISPONIBLES 
al arrancar el server). 

reply a TODO: esta bien que se pueble con todos los planes posibles dentro de planes_por_alumno, si falta o si se cambia la base, el usuario puede 
agregar CSV faltante.

idea para overleaf: si un usuario quiere probar un nuevo plan para los de compu de 2023, puede reemplazar archivo nuevo y 
contrastar con trayectorias reales de cursadas
"""
@app.callback(
    Output("raw-plans-store", "data"),
    Output("plan-catalog-store", "data"),
    Output("plan-ref-store", "data"),
    Output("plan-load-feedback", "children"),
    Output("plan-feedback-timer", "disabled"),
    Output("plan-feedback-timer", "n_intervals"),
    Input("dropdown-carrera", "value"),             # codigo_carrera
    Input("dropdown-plan", "value"),                # plan_value
    State("raw-plans-store", "data"),               # raw_plans         # {plan_id: list[dict]} tq list[dict] son recordsDelCSV
    State("plan-ref-store", "data")                 # trajectory_plan_ref_vect     # {plan_id: list[list[int]]} con los vectoresEstado
)
##
def load_plan_from_disk(codigo_carrera, plan_value, raw_plans, trajectory_plan_ref_vect): 

    #Caso A: no hay carrera ni plan seleccionado en dropdowns
    if not codigo_carrera or plan_value is None:
        return no_update, no_update, no_update,"", True, 0

    raw_plans = raw_plans or {}
    trajectory_plan_ref_vect = trajectory_plan_ref_vect or {}

    plan_id = f"{codigo_carrera}_{plan_value}" ## formato de nombre CARRERA_PLAN.csv en /plan

    # Caso B: en esta sesión ya cargué ese planCSV a store raw_planes
    if plan_id in raw_plans:
        all_plans = {pid: pd.DataFrame(recs) for pid, recs in raw_plans.items()}
        catalog = build_unified_catalog(all_plans)     
        
        #actualizo en caso de que se haya actualizado allplans y sea necesario calcular de nuevo plans caminos para length catalogo nuevo
        # current_app.logger.debu(raw_plans.keys())
        for plan_id in raw_plans.keys():
            trajectory_plan_ref_vect[plan_id] = build_reference_plan(catalog, plan_id=plan_id) 

        return no_update, catalog.to_dict("records"), trajectory_plan_ref_vect, f"🗃️ Plan '{plan_id}' ya cargado.", False, 0 

    # Caso C: hay que cargar el plan_id.csv
    try:
        # cargo csv a raw_plans[plan_id]
        parsed_plan = load_plan_from_directory(PLANS_DIR, plan_id) #codigo_carrera, plan_value
        raw_plans[plan_id] = parsed_plan.to_dict("records")

        # hago de forma local all_plans={plan_id: pd.DataFrame} con la info de raw_planes
        all_plans = {pid: pd.DataFrame(recs) for pid, recs in raw_plans.items()}
        catalog = build_unified_catalog(all_plans)                                  #se re-construye catalogo con (oldInfo+nueva de plan selected)
        # current_app.logger.debug(catalog)
        trajectory_plan_ref_vect[plan_id] = build_reference_plan(catalog, plan_id=plan_id)     #agrega instancia de ese plan_id como listaVectoresEstadoDeEsePlan en el dict TODO: de trajectories*Ref 

        return (
            raw_plans, catalog.to_dict("records"), trajectory_plan_ref_vect,   #updates para Stores
            f"✅ Plan '{plan_id}' cargado desde /plan.", False, 0      #update para timer
        )
    except FileNotFoundError as exc:
        return no_update, no_update, no_update, f"❌ {str(exc)}", False, 0 
    except InvalidPlanFormatError as exc:
        return no_update, no_update, no_update, f"⚠️ Formato de CSV inválido en '{plan_id}': {exc}", False, 0
    except Exception as exc:  # noqa: BLE001
        return no_update, no_update, no_update, f"❌ Error al cargar el plan '{plan_id}': {exc}", False, 0 
    
@app.callback(
    Output("plan-load-feedback", "children", allow_duplicate=True),
    Output("plan-feedback-timer", "disabled", allow_duplicate=True),
    Input("plan-feedback-timer", "n_intervals"),
    prevent_initial_call=True,
)
##
def clear_plan_feedback(n_intervals):
    if n_intervals and n_intervals >= 1:
        return "", True  # limpia el texto y apaga el timer (no sigue corriendo de fondo)
    return no_update, no_update


# --------------------------------------------------------------------------- #
# Dropdowns dependientes carrera -> plan
# # --------------------------------------------------------------------------- #
@app.callback(
    Output("dropdown-carrera", "options"),
    Input("dropdown-carrera", "id"),  # dispara una sola vez al montar la página
)
## setea values de dropdown carrera
def init_carrera_dropdown(_):
    carreras = sorted(CARRERAS_PLANES_DISPONIBLES["codigo_carrera"].unique().tolist())
    return [{"label": c, "value": c} for c in carreras]

@app.callback(
    Output("dropdown-plan", "options"),
    Output("dropdown-plan", "value"),
    Output("dropdown-plan", "disabled"),
    Input("dropdown-carrera", "value")
)
## setea values de dropdown plan segun carrera picked
def update_plan_dropdown(codigo_carrera):
    if not codigo_carrera:
        return [], None, True

    planes_validos = get_planes_por_carrera(CARRERAS_PLANES_DISPONIBLES, codigo_carrera)
    options = [{"label": str(p), "value": p} for p in planes_validos]
    autoselect = planes_validos[0] if len(planes_validos) == 1 else None
    return options, autoselect, False


@app.callback(
    Output("cuatris-range-slider-update", "min"),
    Output("cuatris-range-slider-update", "max"),
    Output("cuatris-range-slider-update", "value"),
    Output("cuatris-range-slider-update", "marks"),
    Output("cuatri-range-label", "children"),
    Input("graph-switch", "on"),
)
##
def recalibrate_step_range(cuatri_on):
    """Recalibra min/max/value/label del slider según el modo activo:
    cuatrimestres reales para cursadas, instancias de examen para finales
    (son escalas distintas, ver discusión previa sobre step_nro)."""
    if cuatri_on:
        max_step = MAX_STEP_FINALES
        label = "Rango de cantidad instancias de finales:"
    else:
        max_step = MAX_STEP_CURSADAS
        label = "Rango de cuatrimestres:"

    marks = {1: "1", max_step: str(max_step)}
    return 1, max_step, [1, max_step], marks, label





# # --------------------------------------------------------------------------- #
# # Actualizacion elementos del grafo 
# # --------------------------------------------------------------------------- #

##
@cache.memoize()
def _compute_graph(year_list_key, codigo_carrera, 
                   plan_value, filter_by_plan,
                   must_be_1st_materias_key, min_edge_weight, cuatri_range_key,
                   mode, catalog_records):

    plan_para_camada = plan_value if filter_by_plan else None

    catalog = pd.DataFrame(catalog_records)          #csv rows
    dic_materia_idx = build_dic_materia_idx(catalog) #{'COMP930001': 0, 'COMP930003': 1, 'COMP930004': 2, 'COMP930005': 3, 'COMP930007': 4, 'COMP930008': 5, ...}
    # current_app.logger.debug(dic_materia_idx);


    must_be_1st = must_be_1st_materias_key if must_be_1st_materias_key else None


    camada = get_camada(
        ACADEMIC_DATASET.planes_por_alumno,
        ACADEMIC_DATASET.cursadas_por_alumno,
        year_list=list(year_list_key),
        plan=plan_para_camada,
        codigo_carrera=codigo_carrera or "LCCOMP",
        must_be_1st_materias=must_be_1st,
    )
    
    if mode == "finales":
        graph = generate_nodes_and_edges(
            events=ACADEMIC_DATASET.finales_por_alumno,
            camada=camada,
            dic_materia_idx=dic_materia_idx,
            date_columns=["fecha_llamado_mesa"],
        )
    else:
        graph = generate_nodes_and_edges(
            events=ACADEMIC_DATASET.cursadas_por_alumno,
            camada=camada,
            dic_materia_idx=dic_materia_idx,
            date_columns=["anio_academico", "periodo"],
        )

    # me quedo con cuatris en ese cuatriRange. Es decir desde el cuatri NroX hasta el paso del cuatri NroY
    graph = filter_by_step_range(graph, cuatri_range_key[0], cuatri_range_key[1])
    
    # filtro edgeWeight con cota minima y elimino nodos/aristas desconectados del grafo
    graph = prune_graph(graph, min_edge_weight=min_edge_weight)

    nodes_with_id = graph.nodes.reset_index().rename(columns={"index": "node_id"})
    return nodes_with_id.to_dict("records"), graph.edges.to_dict("records"), graph.max_appears

##
def _build_cyto_elements(nodes_records, edges_records, max_appears, catalog_records, reference_plan):
    catalog = pd.DataFrame(catalog_records)             #csv
    reference_vectors = reference_plan or []

    nodes_by_id = {rec["node_id"]: rec for rec in nodes_records}
    cyto_nodes = []
    for node_id, rec in nodes_by_id.items():
        vector = rec["vector"]
        cyto_nodes.append({
            "data": {
                "id": str(node_id),
                "label": f"{node_id}\n" + materias_aprobadas_str(vector, catalog, "nomenclatura"),
                "vector": vector,
                "height": int(np.sum(vector)) * 15 + 60,
                "color": AZUL if list(vector) in reference_vectors else "#000000",
            }
        })
    # current_app.logger.debug(reference_vectors);
    # current_app.logger.debug(rec["vector"])
    cyto_edges = []
    for row in edges_records:
        source, target = row["source"], row["target"]
        appears = row["appears"]
        width = normalized_edge_width(appears, max_appears)  # Crítica #6: dinámico
        cyto_edges.append({
            "data": {
                "source": str(source),
                "target": str(target),
                "label_frequencyBased": appears,
                "weight_frequencyBased": width,
                "calculated_margin": f"{-20 - int((width / 3) / 2)}px",
                # ARCHIVED IDEA
                # "avg_intentos_previos": round(row.get("avg_intentos_previos", 0.0), 2),
                "idList": row["id_list"],
                "color": AZUL if (
                    list(nodes_by_id[source]["vector"]) in reference_vectors and 
                    list(nodes_by_id[target]["vector"]) in reference_vectors and
                    list(nodes_by_id[source]["vector"])!=list(nodes_by_id[target]["vector"]) # Dani: AZUL si NO son loop
                ) else "#5c5c5c",
                "reprobadas_info":row.get("reprobadas_info")
            }
        })

    return cyto_nodes + cyto_edges


@app.callback(
    Output("cytoscape-graph", "elements"),
    Output("legend-panel", "style"),
    Output("plan-legend-label", "children"),
    Output("graph-switch", "disabled"),
    Output("switch-label", "children"),
    Input("dropdown-update-graph", "value"),            # year_list
    Input("minEdgeWeight-update", "value"),             # min_edge_weight
    Input("graph-switch", "on"),                        # cuatri_on
    Input("dropdown-carrera", "value"),                 # codigo_carrera
    Input("dropdown-plan", "value"),                    # plan_value
    Input("filters-by-plan-checkbox", "value"),         # filters_by_plan_values
    Input("cuatris-range-slider-update", "value"),      # cuatri_range
    Input("plan-catalog-store", "data"),                # catalog_records, 
    Input("plan-ref-store", "data"),                    # trajectory_plan_ref_vect
)
##
def update_graph(year_list, min_edge_weight, cuatri_on,codigo_carrera, 
                 plan_value, filter_by_plan_values, 
                 cuatri_range, catalog_records, trajectory_plan_ref_vect):

    # current_app.logger.debug(cuatri_range)
    #si checkbox ON de filtrar camada con primera materia inscripta a alguna de las materias de "primer año del plan"
    # solo aplicable si hay plan seleccionado (si no, no hay cuatrimestre_sugerido) ##### TODO home: disable y en gris este checkbox, capaz deberia estar en barrita DIV de arriba con dropdowns carrera plan 
    plan_id = f"{codigo_carrera}_{plan_value}" if (codigo_carrera and plan_value is not None) else None

    if not year_list or not catalog_records:
        return [], HIDDEN, "",True,"Tipo de Grafo"

    must_be_1st = None
    if "filter_1st_year" in (filter_by_plan_values or []) and plan_id:
        try:
            must_be_1st = get_first_year_materias(pd.DataFrame(catalog_records), plan_id=plan_id, max_cuatri=2)
        except KeyError as exec:
            return [], HIDDEN, "",True,"Tipo de Grafo"


    filter_by_plan = "filter_by_plan" in (filter_by_plan_values or [])       # si checkbox ON de filtrar camada por plan seleccionado
    graphMode = "finales" if cuatri_on else "cursadas"                       # toggle tipo de grafo 
    nodes_records, edges_records, max_appears = _compute_graph(tuple(sorted(year_list)),
                                                               codigo_carrera, 
                                                               plan_value, filter_by_plan,
                                                               must_be_1st if must_be_1st else None,
                                                               min_edge_weight, tuple(cuatri_range), graphMode, 
                                                               catalog_records)     #csv con plan 
    
    # Highlight planSugerido si esta seleccionado carrera + plan
    trajectory_plan_ref_vect = trajectory_plan_ref_vect or {}                 
    reference_plan = trajectory_plan_ref_vect.get(plan_id) if plan_id else None        #busco si plan_id selected está en variable con todos planReferenced como vectoresEstado

    #outputs
    elements = _build_cyto_elements(nodes_records, edges_records, max_appears, catalog_records, reference_plan)
    legend_style = VISIBLE_LEGEND if reference_plan else HIDDEN  
    plan_label = f"Plan '{plan_id}' sugerido" if reference_plan else ""
    label_text = "Grafo de Finales" if cuatri_on else "Grafo de Cursadas"

    return elements, legend_style, plan_label, False, label_text

# # --------------------------------------------------------------------------- #
# # MOSTRAR INFO: nodo y arista seleccionados
# # --------------------------------------------------------------------------- #
# ==========================================
# Seleccionar Edge
@app.callback(
    Output("edge-info-div", "style"),
    Output("selected-edges-info-output", "children"),
    Output("filas-dinamicas", "children"),
    Output("reprobados-info-table", "style"),
    Input("cytoscape-graph", "selectedEdgeData"),       #list
    State("plan-catalog-store", "data")                 #catalog_records
)
##
def display_selected_edges(selected_edges, catalog_records):
    base_style = {"padding": "20px", 
                  "border": "1px solid #e0e0e0", 
                  "borderRadius": "8px", 
                  "marginBottom": "20px"}

    #No hay edge/s seleccionado/s
    if not selected_edges:
        base_style["backgroundColor"] = "#ffffff"
        return base_style, "Seleccione arista/s para saber más.", [], HIDDEN #TODO home html.I("(se puede seleccionar más de una manteniendo Ctrl)")

    ids,df_reprobadas =  [], pd.DataFrame(columns=["codigo_materia", "lista_estudiantes", "sum_intentos"])
    # current_app.logger.debug(selected_edges)
    for edge in selected_edges:
        ids += edge.get("idList")
        ## TODO future: la info para el histograma de materias que intento cursar los recursantes if isLoop es true
        
        reprobadas_ese_edge = pd.DataFrame(edge.get("reprobadas_info"))
        df_reprobadas = pd.concat([df_reprobadas,reprobadas_ese_edge])


    # current_app.logger.debug(df_reprobadas)
    df_reprobadas = df_reprobadas.groupby("codigo_materia").agg(
        cant_uniq_estudiantes_total =("lista_estudiantes", lambda s: len(set(x for lista in s for x in lista))), #sorted
        sum_intentos_total = ("sum_intentos", "sum")
    ).reset_index()
    # current_app.logger.debug(df_reprobadas)
    uniq_ids = set(ids)


    
    ### TODO: ugly necesita refactor
    catalog = pd.DataFrame(catalog_records)[["codigo_materia","nombre_oficial"]]
    df_reprobadas = df_reprobadas.merge(catalog, on=["codigo_materia"], how="left") ##agrego nombre_oficial


    filas_output = [
        html.Tr([
            html.Td(row["nombre_oficial"]), 
            html.Td(row["cant_uniq_estudiantes_total"], style={"text-align":"center"}), 
            html.Td(row["sum_intentos_total"], style={"text-align":"center"})
            ],
            style={
            "fontFamily": "monospace", 
            "fontSize": "14px" # Ajusta este valor (ej. 13px o 14px) para igualar el tamaño exacto de tu Pre
            }   
        ) 
        for _, row in df_reprobadas.iterrows()
    ]

    VISIBLE_TABLE = {} if len(df_reprobadas)>0 else HIDDEN
    
    # txt_df_reprobadas = ""
    # if len(df_reprobadas)>0:
    #     txt_df_reprobadas="Materia Reprobada, Estudiantes Unicos, Cantidad Intentos\n"
    #     df_reprobadas["reprobadas_info"] = df_reprobadas["nombre_oficial"].astype(str)  + ":    " + df_reprobadas[["cant_uniq_estudiantes_total","sum_intentos_total"]].astype(str).agg(",    ".join, axis=1)
    #     txt_df_reprobadas += f'\n'.join(df_reprobadas['reprobadas_info']) + "\n\n"
    

    txt = (
        f"Cantidad de IDs Únicos: {len(uniq_ids)}\n\n"
        # f"{txt_df_reprobadas}"
        f"IDs Estudiantes: {uniq_ids}"
    )

    base_style["backgroundColor"] = "#D7F4F5"
    return base_style, txt, filas_output, VISIBLE_TABLE


# ==========================================
# Seleccionar Nodo
@app.callback(
    Output("node-info-div", "style"),
    Output("selected-nodes-info-output", "children"),
    Input("cytoscape-graph", "tapNodeData"),
    Input("cytoscape-graph", "selectedNodeData"),
    State("plan-catalog-store", "data")
)
##
def display_selected_nodes(tapped_node, any_selected, catalog_records):
    base_style = {"padding": "20px", 
                  "border": "1px solid #e0e0e0", 
                  "borderRadius": "8px"}

    if not any_selected or not catalog_records:
        base_style["backgroundColor"] = "#ffffff"
        return base_style, "Seleccione un nodo para saber más."

    catalog = pd.DataFrame(catalog_records)
    txt = f"Nodo ID: {tapped_node['id']}\n\nMaterias:\n{materias_aprobadas_str(tapped_node['vector'], catalog, 'nombre_oficial')}"
    base_style["backgroundColor"]="#D7F4F5"
    return base_style, txt
