# # layout.py

"""
Componentes visuales de Dash.
"""

from dash import dcc, html
import dash_daq as daq
import dash_cytoscape as cyto

#para debuggear
from flask import Flask, current_app


AZUL = "#009DAC"
ROJO = "#B20D30"

CYTOSCAPE_STYLESHEET = [
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "90px",
            "background-color": "#ffffff",
            "border-color": "data(color)",
            "border-width": 2.5,
            "border-radius": "10px",
            "shape": "roundrectangle",
            "width": 100, #"data(width)", #
            "height": "data(height)",
        },
    },
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "label": "data(label_frequencyBased)",
            "width": "data(weight_frequencyBased)",
            "target-arrow-shape": "triangle",
            "font-size": "15px",
            "text-rotation": "autorotate",
            "text-margin-y": "data(calculated_margin)",
            "line-color": "data(color)",
            "target-arrow-color": "data(color)",
            "loop-sweep": "-45deg",
            "control-point-step-size": 90,
        },
    },
    { ### asi se puede ver mejor con cuatriRangeSlider
        'selector': '[label_frequencyBased <= 0]',
        'style': {
            'line-color': "#DADADA",
            'target-arrow-color': "#DADADA"
        }
    },
    {
        "selector": "node:selected",
        "style": {
            "background-color": "#9E2A2B",
            "border-color": ROJO,
            "border-width": 4,
            "color": "#ffffff",
            "z-index": 9999,
        },
    },
    {
        "selector": "edge:selected",
        "style": {
            "line-color": ROJO,
            "target-arrow-color": ROJO,
            "width": "data(weight_frequencyBased)",
            "z-index": 9999,
        },
    }
]


def build_data_identity_panel() -> html.Div:
    """Sección debajo del título con dropdowns dependientes carrera -> plan.
    El plan de estudios se resuelve server-side buscando plan/{codigo_carrera}_{plan}.csv según la selección de estos dropdowns."""
    return html.Div(
        style={
            "display": "flex", "gap": "20px", "alignItems": "flex-start",
            "padding": "10px 15px", "backgroundColor": "#ffffff",
            "border": "1px solid #e0e0e0", "borderRadius": "8px",
            "boxShadow": "2px 2px 10px rgba(0,0,0,0.05)", "marginBottom": "20px",
            "background-color":"#009EACC5"
        },
        children=[
            html.Div(
                style={"flex": "1","display": "flex", "gap": "10px",
                       "maxWidth":"22.5%", "marginTop":"5px" },
                children=[
                    html.H4("Carrera:", 
                            style={"color": "#2c3e50", 
                                   "margin": "8px 0 6px 0",
                                   "color":"#ffffff"}),
                    dcc.Dropdown(
                        id="dropdown-carrera",
                        placeholder="Seleccionar carrera...",
                        clearable=True, searchable=False,
                        options=[],
                        style={"flexGrow": 1, "width": "50%",'zIndex': 1001 }
                    ),
                ],
            ),
            html.Div(
                style={"display": "flex", "gap": "10px", "flex": "1",
                       "maxWidth":"22.5%", "marginTop":"5px"},
                children=[
                    html.H4("Plan:", 
                            style={"color": "#2c3e50", 
                                   "margin": "8px 0 6px 0",
                                   "color":"#ffffff"}),
                    dcc.Dropdown(
                        id="dropdown-plan",
                        placeholder="Seleccionar plan...",
                        clearable=True, searchable=False,
                        options=[],
                        disabled=True,
                        style={"flexGrow": 1, "width": "50%",'zIndex': 1001 }
                    ),
                ],
            ),
            html.Div(
                style={"flex": "2","gap": "20px", "maxWidth":"45%"}, #
                children=[
                    dcc.Checklist(
                        id="filters-by-plan-checkbox",
                        options=[
                        {
                            "label": "Filtrar sólo a inscriptos en plan seleccionado (sino, son todos los de la carrera)",
                            "value": "filter_by_plan",
                        },
                        {
                            "label": "Filtrar que primera materia inscripta corresponde a las del primer año del plan seleccionado",
                            "value": "filter_1st_year",
                        }],
                        value=["filter_by_plan","filter_1st_year"],  #filtrado por default
                        inline=True,
                        style={"color": "#2c3e50", "fontSize": "13px"},#, "maxWidth":"420px"},
                        labelStyle={"align-items": "center","display":"flex", 'display': 'inline-block',"color":"#ffffff"}#, "maxWidth":"15%"}
                    ),
                    dcc.Interval(id="plan-feedback-timer", interval=10000, n_intervals=0, disabled=True)
                ]
            ),
            html.Div(id="plan-load-feedback", 
                     style={"flex": "3","fontSize": "12px", "color":"#ffffff", #, "backgroun-color": "#C7284A"
                            "font-style":"italic", 
                            "font-weight": "bold",
                            "marginTop":"2px",
                            "maxWidth":"10%","text-align":"right",
                            "whiteSpace": "normal",   # habilita wrap (por defecto en un Div ya es normal, pero si el padre tiene nowrap o flex sin basis, puede no wrappear)
                            "wordBreak": "break-word",  # corta palabras largas si hace falta
                            "maxWidth": "300px"}),
        ],
    )


def build_control_panel(range_years_dropdown: list[int]) -> html.Div:
    """Panel de control lateral: solo filtros de VISUALIZACIÓN del grafo.
    Identidad de datos (carrera/plan/CSV) vive ahora en build_data_identity_panel()."""
    return html.Div(
        style={
            "padding": "20px", "backgroundColor": "#ffffff", "border": "1px solid #e0e0e0",
            "borderRadius": "8px", "boxShadow": "2px 2px 10px rgba(0,0,0,0.05)", "marginBottom": "20px",
        },
        children=[
            html.H2("⚙️ Panel de Control", style={"color": "#2c3e50","marginTop": "5px"}),
            html.Div([
                html.H4("Año de camada:", style={"color": "#2c3e50", "marginTop": "8px"}),
                dcc.Dropdown(
                    id="dropdown-update-graph", placeholder="Seleccionar un año...",
                    clearable=True, searchable=False, persistence=True, multi=True,
                    options=[{"label": str(y), "value": y} for y in range_years_dropdown],
                    style={"flexGrow": 1, "width": "50%"},
                    # value=[2017]
                ),
                ],
                style={"display": "flex", "gap": "10px"},
            ),

            # html.Div(
            #     [
            #         dcc.Checklist(
            #             id="filter-first-year-checkbox",
            #             options=[{
            #                 "label": "Filtrar estudiantes que su primera materia cursada "
            #                          "corresponde a las del primer año del plan seleccionado",
            #                 "value": "filter_on",
            #             }],
            #             value=["filter_on"],
            #             style={"color": "#2c3e50", "fontSize": "13px"},
            #         ),
            #     ],
            #     style={"marginTop": "10px", "marginBottom": "10px"}
            # ),

            html.Div(
                [
                    daq.BooleanSwitch(id="graph-switch", on=False, color=AZUL, disabled=True),
                    html.H4(id="switch-label", style={"margin": "0", "marginTop": "10px", "color": "#2c3e50"}),
                ],
                style={"display": "flex", "gap": "10px", "marginBottom": "20px"},
            ),

            html.H4("Mínimo de estudiantes únicos por arista:", style={"color": "#2c3e50"}),
            dcc.Slider(id="minEdgeWeight-update", persistence=True, min=0, max=15, value=3),

            html.H4(id="cuatri-range-label", children="Rango de cuatrimestres:", style={"color": "#2c3e50"}),
            dcc.RangeSlider(id="cuatris-range-slider-update", persistence=False, min=1, max=20, value=[1, 20]),
        ],
    )


def build_info_panels() -> list[html.Div]:
    return [
        html.Div(
            id="edge-info-div",
            children=[
                html.H3("ℹ️ Información de aristas:", 
                    style={"color": "#2c3e50", "marginTop":"10px"}),
                html.Pre(id="selected-edges-info-output", 
                        style= {'text-wrap': 'wrap',
                                'maxHeight': '82px',
                                'overflowY': 'scroll',    
                                'overflowX': 'hidden',
                                'whiteSpace': 'pre-wrap',
                                'wordBreak': 'break-word',
                                'display': 'block'
                                } ),
                html.Table([
                    # Encabezados fijos [a, b, c]
                    html.Thead(
                        html.Tr([html.Th("Materia Reprobada"), 
                                 html.Th("Estudiantes Únicos"), 
                                 html.Th("Intentos Reprobados")
                                 ],
                                style={
                                "fontFamily": "monospace", 
                                "fontSize": "18px" # Ajusta este valor (ej. 13px o 14px) para igualar el tamaño exacto de tu Pre
                                })
                    ),
                    # Cuerpo vacío que recibirá las filas dinámicas
                    html.Tbody(id="filas-dinamicas")
                    ],
                    id="reprobados-info-table",
                    style={"display": "none"}
                )
            ]
            # ,style= {'height': '100px',        # altura FIJA (no maxHeight)
            #         'overflowY': 'scroll',      # scroll solo si excede
            #         'overflowX': 'hidden',
            #         'display': 'block',
            #         'padding': '10px',
            #         'text-wrap': 'wrap',
            #         'whiteSpace': 'pre-wrap',
            #         'wordBreak': 'break-word',
            #         }
        ),
        html.Div(
            id="node-info-div",
            children=[
                html.H3("ℹ️ Información de nodos:", 
                    style={"color": "#2c3e50", "marginTop":"10px"}),
                html.Pre(id="selected-nodes-info-output",
                         style= {'text-wrap': 'wrap',
                                    'maxHeight': '200px',
                                    'overflowY': 'auto',    
                                    'overflowX': 'hidden',
                                    'whiteSpace': 'pre-wrap',
                                    'wordBreak': 'break-word',
                                    'display': 'block'
                                    }),
            ],
        ),
    ]


def build_graph_panel() -> html.Div:
    return html.Div(
        style={"flex": "3", "border": "1px solid #e0e0e0", "borderRadius": "8px", "backgroundColor": "#f9f9f9"},
        children=[
            ## GRAPH
            dcc.Loading(
                id="loading-1", type="circle", delay_hide=180, color=AZUL,
                children=cyto.Cytoscape(
                    id="cytoscape-graph",
                    elements=[],
                    style={"width": "100%", "height": "850px"},
                    layout={"name": "breadthfirst", "directed": True, "roots": '[id = "0"]', "spacingFactor": 0.85},
                    stylesheet=CYTOSCAPE_STYLESHEET,
                ),
            ),
            ## LEGEND
            html.Div(
                style={'position': 'absolute',
                        'top': '20px',      # Floats 20px from the bottom
                        'left': '20px',        # Floats 20px from the left
                        'backgroundColor': 'rgba(255, 255, 255, 0.9)', # Slightly transparent white
                        'padding': '15px',
                        'border': '1px solid #d1d5db',
                        'borderRadius': '8px',
                        'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
                        'zIndex': 1000         # Ensures it sits ON TOP of the Cytoscape canvas
                    },
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "marginBottom": "8px"},
                        children=[
                            html.Div(style={"width": "16px", "height": "16px", "backgroundColor": "#fff",
                                             "border": "1px solid #000", "marginRight": "10px", "border-radius": "20%"}),
                            html.Span("Materias Aprobadas", style={"fontSize": "14px", "color": "#4b5563"}),
                        ],
                    ),
                    html.Div(
                        id="legend-panel",
                        style={"display": "none", "alignItems": "center"}, # Punto d.1): arranca oculta, se muestra solo con plan seleccionado
                        children=[
                            html.Div(id="icon-legend", style={"width": "20px", "height": "7px", "backgroundColor": AZUL, "marginRight": "6px"}),
                            html.Span(id="plan-legend-label", style={"fontSize": "14px", "color": "#4b5563"}),
                        ],
                    )
                ],
            ),
        ],
    )


def build_layout(range_years_dropdown: list[int] | None = None) -> html.Div:
    range_years_dropdown = range_years_dropdown or []
    return html.Div(
        style={"fontFamily": "Arial, sans-serif", "padding": "5px"},
        children=[
            # html.H1("Grafo de Trayectorias Académicas - FCEyN UBA",
            #         style={"textAlign": "center", "color": "#2c3e50", "padding": "0px"}),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr auto 1fr",
                    "alignItems": "center",
                    "padding": "0px",
                    "gap": "15px",
                },
                children=[
                    html.Img(
                        src="/assets/Logo_exactas.svg",
                        style={"height": "40px", "width": "auto", "justifySelf": "start", "marginLeft": "10px"},
                    ),
                    html.H1(
                        "Grafo de Trayectorias Académicas - FCEyN UBA",
                        style={"textAlign": "center", "color": "#2c3e50"},
                    ),
                    html.Div(),  # columna vacía para balancear el logo y mantener el título centrado
                ],
            ),
            

            dcc.Store(id="raw-plans-store"),    #diccionario csvName -> planEnVectoresEstado
            dcc.Store(id="plan-catalog-store"),
            dcc.Store(id="plan-ref-store"),
            dcc.Store(id="max-cuatri-by-carrera-store"),

            #### DIV Selector de Carrera, Plan, filtrar_by_plan
            build_data_identity_panel(),

            html.Div(
                style={"display": "flex", "flexDirection": "row", "gap": "20px",
                       "height": "855px", "marginTop": "20px", "position": "relative",
                       'overflowY': 'auto','overflowX': 'hidden'},
                children=[
                    #### Grafo con su leyenda
                    build_graph_panel(),

                    #### Panel de control y extraInfoDisplay
                    html.Div(
                        style={"flex": "1"},
                        children=[build_control_panel(range_years_dropdown)]+build_info_panels() #, *build_info_panels()]
                    ),
                ],
            ),
        ],
    )