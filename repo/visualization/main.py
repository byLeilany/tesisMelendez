from aux_functions import strMateriasAprobadas, nodosDelPlan93, nodosDelPlan23, rangeYearsDropdown #, default_max_range_slider
from nodosFromTP import generate_TP_nodes_and_edges, cut_edges_at

from nodosFromFinales import generate_FINALS_nodes_and_edges

import numpy as np
import math
import pandas as pd


import dash
from dash import html, dcc, Input, Output
import dash_daq as daq
import dash_cytoscape as cyto

#para debuggear
from flask import Flask, current_app

azul = "#009DAC"
red = "#B20D30"

def actualizar_elementsTP_graph(yearInput, minIDsInput, yearPlan, cantCuatrisRange): #cantCuatrisFrom,
    
    if yearPlan==2023:
        nodosPlan = nodosDelPlan23
    elif yearPlan==1993: 
        nodosPlan = nodosDelPlan93
    else:
        nodosPlan = []


    df_edges_uncut, dic_node = generate_TP_nodes_and_edges(yearInput, yearPlan, cantCuatrisRange) #, minIDsInput
    tpl, df_edges = cut_edges_at(df_edges_uncut, dic_node, minIDsInput)

    cyto_nodes = [{"data": {"id": str(i), 
                            "label": str(i) +'\n' + strMateriasAprobadas(dic_node.loc[i]['vector'], 'codigo'), 
                            "vector": dic_node.loc[i]['vector'],
                            "cant_students_llegaron": len(set(df_edges[(df_edges['edge'].str[1]==i) ].sum()['idList'] or [])),  #sin el "or[]" explota cuando lo otro es 0
                            "height": sum(dic_node.loc[i]['vector'])*15+60, #quantityMaterias height basado en #materias
                            "color": azul if(dic_node.loc[i]['vector'] in nodosPlan) else "#000000" }}
                    
                for i in tpl]
    
    # Translating to Cytoscape format:
    cyto_edges = [
        {"data": {"source": str(row.edge[0]), 
                "target": str(row.edge[1]), 
                'label_frequencyBased':len(set(row.idList)), #row.appears,  row.appears, 
                'weight_frequencyBased':  max(1, round((row.appears / 200) * 30)), #int(row.appears/3) if row.appears >=3 else 1, 
                'calculated_margin': str(-15 - (int((row.appears/3)/2)))+"px",
                'color': azul if((dic_node.loc[row.edge[0]]['vector'] in nodosPlan) and 
                                        (dic_node.loc[row.edge[1]]['vector'] in nodosPlan) and 
                                        abs(nodosPlan.index(dic_node.loc[row.edge[0]]['vector']) - nodosPlan.index(dic_node.loc[row.edge[1]]['vector'])) == 1)  else "#5c5c5c",
                "idList": row.idList}} 
        for row in df_edges.itertuples() #if row.edge[0] not in idNodosDesconectados
    ]

    elements = cyto_nodes + cyto_edges

    # for row in df_edges.itertuples():
    #     current_app.logger.debug(str(row.edge) + ", edgeWeight: "+ str(len(set(row.idList))) + ", from: " +str(row.edge[0]) + strMateriasAprobadas(dic_node.loc[row.edge[0]]['vector'], 'codigo')
    #                                                 + ", to: " +str(row.edge[1]) + strMateriasAprobadas(dic_node.loc[row.edge[1]]['vector'], 'codigo') ) 
    return elements


def actualizar_elementsFINALS_graph(yearInput, minIDsInput, yearPlan):
    
    if yearPlan==2023:
        nodosPlan = nodosDelPlan23
    elif yearPlan==1993: 
        nodosPlan = nodosDelPlan93
    else:
        nodosPlan = []

    df_edges_uncut, dic_node = generate_FINALS_nodes_and_edges(yearInput, yearPlan) #, minIDsInput
    tpl, df_edges = cut_edges_at(df_edges_uncut, dic_node, minIDsInput)

    cyto_nodes = [{"data": {"id": str(i), 
                            "label": str(i) +'\n' + strMateriasAprobadas(dic_node.loc[i]['vector'], 'codigo'), #stsMA(dic_node.loc[i]['vector']), 
                            "vector": dic_node.loc[i]['vector'],
                            "cant_students_llegaron": len(set(df_edges[(df_edges['edge'].str[1]==i) ].sum()['idList'] or [])),  #sin el "or[]" explota cuando lo otro es 0
                            "height": sum(dic_node.loc[i]['vector'])*15+60, #quantityMaterias height basado en #materias
                            "color": azul if(dic_node.loc[i]['vector'] in nodosPlan) else "#000000" }}
                    
                for i in tpl]
    
    # Translating to Cytoscape format:
    cyto_edges = [
        {"data": {"source": str(row.edge[0]), 
                "target": str(row.edge[1]), 
                'label_frequencyBased': row.appears, 
                'weight_frequencyBased': max(1, round((row.appears / 200) * 30)), 
                'calculated_margin': str(-15 - (int((row.appears/3)/2)))+"px",
                'color': azul if((dic_node.loc[row.edge[0]]['vector'] in nodosPlan) and 
                                        (dic_node.loc[row.edge[1]]['vector'] in nodosPlan) and 
                                        abs(nodosPlan.index(dic_node.loc[row.edge[0]]['vector']) - nodosPlan.index(dic_node.loc[row.edge[1]]['vector'])) == 1)  else "#5c5c5c",
                "idList": row.idList}} 
        for row in df_edges.itertuples() #if row.edge[0] not in idNodosDesconectados
    ]

    elements = cyto_nodes + cyto_edges
    return elements





app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# # 1. Graph empieza vacio
elements = {} 

# 2. Define the layout
app.layout = html.Div(
    style={'fontFamily': 'Arial, sans-serif', 'padding': '10px'}, 
    children=[
    html.H1(
            "Grafo de Trayectorias Históricas Cs. Computación FCEyN-UBA", 
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '20px'}
        ),

    html.Div(
            style={
                'display': 'flex',          # This is the magic word for side-by-side!
                'flexDirection': 'row',     # Aligns children horizontally
                'gap': '20px',              # Adds space between the graph and the sidebar
                'height': '850px',           # Set a fixed height for the whole interactive area
                'marginTop': '20px',
                
                'position': 'relative', 
                'overflow': 'hidden'
            },
            children=[
            ### left
            html.Div(
                style={
                    'flex': '3',        # Grows to take up 3 parts of the available space
                    'border': '1px solid #e0e0e0',
                    'borderRadius': '8px',
                    'backgroundColor': '#f9f9f9'
                },
                children=[
                dcc.Loading(
                    id="loading-1",
                    type="circle", # Options: "graph", "cube", "circle", "dot", or "default"
                    delay_hide=180,
                    color="#009DAC",
                    children= 
                    cyto.Cytoscape(
                        id='cytoscape-graph',
                        elements=elements,
                        style={'width': '100%', 'height': '1000px'},
                        
                        
                        # 'breadthfirst' with directed=True mimics Graphviz's top-down look
                        layout={
                            'name': 'breadthfirst',
                            'directed': True,
                            'roots': '[id = "0"]',
                            'spacingFactor': 0.85,
                            'boxSelectionEnabled': False       
                        },
                        
                        # 3. Add basic styling to mimic your PDF
                        stylesheet=[
                            {
                                'selector': 'node',
                                'style': {
                                    'label': 'data(label)',
                                    'text-valign': 'top',
                                    'text-valign': 'center',
                                    'text-halign': 'center',
                                    'text-wrap': 'wrap',
                                    'text-max-width': '80px',

                                    'background-color': '#ffffff',
                                    'border-color': 'data(color)',
                                    'border-width': 2.5,
                                    'border-radius': '10px',
                                    'shape': 'roundrectangle',
                                    'width': 90,
                                    'height': 'data(height)',
                                }
                            },
                            {
                                'selector': 'edge',
                                'style': {
                                    'curve-style': 'bezier',
                                    'label': 'data(label_frequencyBased)',
                                    'width': 'data(weight_frequencyBased)',
                                    'target-arrow-shape': 'triangle',
                                    
                                    'font-size': '15px',
                                    'text-rotation': 'autorotate',  # Makes the text angle match the line!
                                    'text-margin-y': 'data(calculated_margin)',

                                    'line-color': 'data(color)',
                                    'target-arrow-color': 'data(color)',
                                    
                                    # 'loop-direction': '-45deg',
                                    'loop-sweep': '-45deg',
                                    'control-point-step-size': 90
                                }
                            },

                            # ==========================================
                            # 2. SELECTED STYLES
                            # ==========================================
                            
                            # Selected Node Style
                            {
                            'selector': 'node:selected',
                            'style': {
                                'background-color': '#9E2A2B', # Bright blue background
                                'border-color':  red,     # Dark blue border
                                'border-width': 4,             # Thicker border
                                'color': '#ffffff',
                                
                                # Elevate the selected node above others
                                'z-index': 9999
                                
                                # # Optional: Add a slight shadow/glow effect (supported in newer Cytoscape.js)
                                # 'underlay-color': '#93C5FD',
                                # 'underlay-padding': 5,
                                # 'underlay-opacity': 0.5
                            }
                            },
                            
                            # Selected Edge Style
                            {
                                'selector': 'edge:selected',
                                'style': {
                                    'line-color': red,       # Bright red line
                                    'target-arrow-color': red, # Match arrow color to line
                                    'width': 'data(weight_frequencyBased)',
                                    
                                    # Elevate the selected edge above other edges
                                    'z-index': 9999
                                }
                            }
                        ]
                    )
                
                ),

                html.Div(
                            style={
                                'position': 'absolute',
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
                                # Legend Item 1: Standard Node
                                html.Div(
                                    style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'}, 
                                    children=[
                                        # The "Color Swatch" (Circle)
                                        html.Div(style={
                                            'width': '16px', 'height': '16px', #, 'borderRadius': '50%' 
                                            'backgroundColor': '#ffffff', 'border': '1px solid #000000', 'marginRight': '10px', 'border-radius':'20%'
                                        }),
                                        html.Span("Materias Aprobadas", style={'fontSize': '14px', 'color': '#4b5563'})
                                    ]
                                ),

                                # Legend Item 2: Plan 93' sugerido
                                html.Div(
                                    style={'display': 'flex', 'alignItems': 'center'}, 
                                    children=[
                                        # The "Color Swatch" (Line)
                                        html.Div(id="icon-legend", style={
                                            'width': '20px', 'height': '7px', 'backgroundColor': azul, 'marginRight': '6px'
                                        }),
                                        html.Span(#"Plan 93' sugerido",
                                                  id="plan-legend-label", style={'fontSize': '14px', 'color': '#4b5563'})
                                    ]
                                )
                            ]
                        )

            ]),
            
            ### right
            html.Div(
                    style={
                        'flex': '1'        # Grows to take up 1 part of the available space
                        # 'padding': '20px',
                        # 'backgroundColor': '#ffffff',
                        # 'border': '1px solid #e0e0e0',
                        # 'borderRadius': '8px',
                        # 'boxShadow': '2px 2px 10px rgba(0,0,0,0.05)' # Gives it a nice pop
                    },
                    children=[
                        

                        # Panel de Control
                        html.Div(
                            style={
                                # 'flex': '1',
                                'padding': '20px',
                                'backgroundColor': '#ffffff',
                                'border': '1px solid #e0e0e0',
                                'borderRadius': '8px',
                                'boxShadow': '2px 2px 10px rgba(0,0,0,0.05)', # Gives it a nice pop
                                'marginBottom': '20px'
                            },
                            children=[
                            html.H2("⚙️ Panel de Control",
                                    style={'color': '#2c3e50', 'marginTop':'10px'}),
                            html.Div([
                                html.H4("Sólo estudiantes del:",
                                    style={'color': '#2c3e50', 'marginRight':'15px', 'marginTop':'20px'}),
                                dcc.Dropdown(
                                    id="dropdown-planYear-graph",
                                    placeholder = 'Seleccionar plan...',
                                    searchable = False,
                                    clearable = True,
                                    multi=False,
                                    options=[
                                        {"label": "" if year is None else "Plan '"+str(year)[2:] , "value": year}
                                        for year in [1993, 2023]
                                    ],
                                )                                           
                                ], 
                                style={'display': 'flex', 'align-items': 'center'}
                            ),
                            html.Div([
                                html.H4("Año de camada:",
                                    style={'color': '#2c3e50', 'marginRight':'15px', 'marginTop':'20px'}),
                                dcc.Dropdown(
                                    id="dropdown-update-graph",
                                    placeholder="Seleccionar un año ...",
                                    clearable=True,
                                    searchable = False,
                                    persistence=True,
                                    multi=True,
                                    options=[
                                        {"label": str(year), "value": year}
                                        for year in rangeYearsDropdown
                                    ],
                                )                                           
                                ], 
                                style={'display': 'flex',  'align-items': 'center'}
                            ),

                            

                            html.Div(
                                [
                                    daq.BooleanSwitch(
                                        id="graph-switch",
                                        on=False,
                                        color= azul,
                                        style={'marginRight':'5px'}
                                    ),

                                    html.H4(
                                        # "Grafico de Cuatrimestre",
                                        id="switch-label",
                                        style={
                                            "margin": "0", 
                                            'marginTop':'15px',
                                            'color': '#2c3e50'
                                        }
                                    )
                                ],
                                style={
                                    "display": "flex",
                                    "gap": "10px",
                                    "marginBottom": "20px"
                                }
                            ),
                            
                            html.H4("Rango con cantidad de cuatrimestres seleccionados:",
                                    style={'color': '#2c3e50', 'marginTop':'10px'}),
                            dcc.RangeSlider(
                                id="cuatris-range-slider-update", 
                                persistence=True,
                                min=1, 
                                max=20, #default_max_range_slider,  
                                value=[1,20]
                            )
                            
                            ,
                            
                            html.H4("Mínimo de estudiantes únicos por arista:",
                                    style={'color': '#2c3e50', 'marginTop':'10px'}),
                            dcc.Slider(
                                id="minEdgeWeight-update", 
                                persistence=True,
                                min=0, 
                                max=15, 
                                value=3
                                
                            )
                            ]
                        ),
                        # Info Aristas/Edges
                        html.Div(
                        id='edge-info-div',
                        # style={
                        #         'maxHeight': '100px',      # alto máximo, ajustalo a tu gusto
                        #         'overflowY': 'auto'
                        #         # # 'flex': '1',
                        #         # 'padding': '20px',
                        #         # # 'backgroundColor': '#ffffff',
                        #         # 'border': '1px solid #e0e0e0',
                        #         # 'borderRadius': '8px',
                        #         # 'boxShadow': '2px 2px 10px rgba(0,0,0,0.05)', # Gives it a nice pop
                        #         # 'marginTop': '20px'
                        #     },
                        children=[
                            html.H3("ℹ️ Información de aristas:",
                                style={'color': '#2c3e50','marginTop':'10px'}),
                            html.Pre(id='selected-edges-info-output',
                            style= {'text-wrap': 'wrap',
                                    'maxHeight': '82px',
                                    'overflowY': 'scroll',    
                                    'overflowX': 'hidden',
                                    'whiteSpace': 'pre-wrap',
                                    'wordBreak': 'break-word',
                                    'display': 'block'
                                    } )
                        ]),
                        # Info Nodos
                        html.Div(
                        id='node-info-div',
                        children=[
                            html.H3("ℹ️ Información de nodos:",
                                style={'color': '#2c3e50','marginTop':'10px'}),
                            html.Pre(id='selected-nodes-info-output',
                            style= {'text-wrap': 'wrap',
                                    'maxHeight': '82px',
                                    'overflowY': 'scroll',    
                                    'overflowX': 'hidden',
                                    'whiteSpace': 'pre-wrap',
                                    'wordBreak': 'break-word',
                                    'display': 'block'
                                    } )
                        ])
                         
                    ])

                
                
                
        ])
    
])



# ==========================================
# Seleccionar edge
# ==========================================
@app.callback(
    Output('edge-info-div', 'style'),
    Output('selected-edges-info-output', 'children'),
    Input('cytoscape-graph', 'selectedEdgeData') # List of selected edge data
)

def display_selected_edges(selected_edges):
    color_output = {'padding': '20px',
                    'border': '1px solid #e0e0e0',
                    'borderRadius': '8px',
                    'boxShadow': '2px 2px 10px rgba(0,0,0,0.05)', # Gives it a nice pop
                    'marginBottom': '20px'
                    }

    if not selected_edges:
        color_output['backgroundColor'] = '#ffffff'

        txt_output = f"Seleccione arista/s para saber más.\n",html.I("(se puede seleccionar más de una manteniendo Ctrl)")
        return color_output, txt_output

    color_output['backgroundColor'] = "#D7F4F5"


    edge_ids = []

    for edge in selected_edges:
        edge_ids += edge.get('idList')

    uniqIDs = set(edge_ids)

    txt_output = "Cantidad de IDs Únicos: "+ str(len(uniqIDs))+ f"\n\n"+ f"IDs Estudiantes de Arista/s Seleccionadas: " + str(uniqIDs)

    return color_output, txt_output


# ==========================================
# Seleccionar Nodo
# ==========================================
@app.callback(
    Output('node-info-div', 'style'),
    Output('selected-nodes-info-output', 'children'),
    Input('cytoscape-graph', 'tapNodeData'),
    Input('cytoscape-graph', 'selectedNodeData') # List of tapped and selected node data
)

def display_selected_nodes(tappedNode, anyNodeSelected):
    color_output = {'padding': '20px',
                    'border': '1px solid #e0e0e0',
                    'borderRadius': '8px',
                    'boxShadow': '2px 2px 10px rgba(0,0,0,0.05)' # Gives it a nice pop
                    }

    if not anyNodeSelected:
        color_output['backgroundColor'] = '#ffffff'

        txt_output = f"Seleccione un nodo para saber más."
        return color_output, txt_output


    color_output['backgroundColor'] = "#D7F4F5"
    txt_output = f"Al nodo de ID: {tappedNode['id']} llegaron {tappedNode['cant_students_llegaron']} estudiantes. \n\nNombre Materias:\n{strMateriasAprobadas(tappedNode['vector'], 'nombre_materia_x')}" #{', '.join(map(str, nodes_info ))}"

    return color_output, txt_output


    


# ==========================================
# Actualizar Graph por dropdown, slicer and switch
# ==========================================
@app.callback(
    Output("cytoscape-graph", "elements"),
    Output("switch-label", "children"),
    Output("plan-legend-label", "children"),
    Output("icon-legend", "style"),
    Input("dropdown-update-graph", "value"),
    Input("minEdgeWeight-update", "value"),
    Input('graph-switch', 'on'),
    Input("dropdown-planYear-graph", "value"),
    Input("cuatris-range-slider-update", "value")
)
def update_graph(yearList, frecuencyIDs, cuatri_On, yearPlan, cantCuatrisRange):
    labelText = ""
    style = {'width': '20px', 'height': '7px', 'backgroundColor': azul, 'marginRight': '6px'}

    if yearPlan==2023:
        # nodosPlan = nodosDelPlan23
        legendLabel = "Plan 2023' sugerido"
    elif yearPlan==1993: 
        # nodosPlan = nodosDelPlan93
        legendLabel = "Plan 1993' sugerido"
    else:
        # nodosPlan = []
        legendLabel = ""
        style = {}

    if yearList: # NOT None AND has a length > 0
        
        if cuatri_On == False:
            elements = actualizar_elementsTP_graph(yearList, frecuencyIDs, yearPlan, cantCuatrisRange)
            labelText = "Grafico Cursadas"
        elif cuatri_On == True:
            elements = actualizar_elementsFINALS_graph(yearList, frecuencyIDs, yearPlan)
            labelText = "Grafico Finales"
    else:
        elements = {}
    
    return  elements , labelText, legendLabel, style


  


if __name__ == '__main__':
    app.run(debug=True)


