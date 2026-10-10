import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from aux_functions import df_cursadas_por_alumno, dic_materias, get_camada


from flask import Flask, current_app
# current_app.logger.debug(len(camadaYEAR))



"""
from pathlib import Path
current_dir = Path(__file__).parent
file_path = current_dir.parent /"bases"/"para tesis LCC_v3.xlsx"

# file_path = "../bases/para tesis LCC_v3.xlsx"

df_planes_por_alumno = pd.read_excel(file_path, sheet_name="planes por alumno")
df_planes_por_alumno['anio_inscripcion'] = df_planes_por_alumno['fecha_inscripcion'].dt.year

df_cursadas_por_alumno = pd.read_excel(file_path, sheet_name="cursadas por alumno (2)") #pd.read_excel(file_path, sheet_name="cursadas por alumno")
df_lista_de_materias = pd.read_excel(file_path, sheet_name="lista de materias")


dic_materias = df_lista_de_materias[df_lista_de_materias['codigo_materia'].str.contains('COMP93')].sort_values(by="codigo_materia")[:17].drop_duplicates().reset_index().drop(columns=('index')) 
### agrego materias de PLAN23
dic_materias23 = df_lista_de_materias[df_lista_de_materias['codigo_materia'].str.contains('COMP23')].sort_values(by="codigo_materia")[:12].drop_duplicates().reset_index().drop(columns=('index'))
dic_materias23 = pd.concat([dic_materias23, df_lista_de_materias[df_lista_de_materias['codigo_materia'] == 'LCDA210006']], axis=0) ##faltaba ALC


dic_materias23.index = [i+len(dic_materias) for i in range(len(dic_materias23))]
dic_materias = pd.concat([dic_materias, dic_materias23])



materiasCatalogo = pd.merge(dic_materias, df_lista_de_materias, on='codigo_materia', how='left')
materiasCatalogo['codigo'] = ['alg','algo1','algo2','algo3','analisis', 'bd', 'inge1','inge2', 'LyC','metNum','orga1','orga2','plp','proba','SO','redes', 'tleng',
                              'algo2','bd','analisis','arqOrg','complej','proba', 'inge1','algo1','lengF','seminario','sistDig','TDA', 'ALC'] # new



nodosDelPlan93 = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
                [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], #alg y analisis
                [1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0], #alg, algo1. analisis. proba'
                [1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0], #alg. algo1. algo2. analisis. orga1. proba'
                [1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0], #alg. algo1. algo2. analisis. metNum. orga1. orga2. proba'
                [1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0], #alg. algo1. algo2. algo3. analisis. metNum. orga1. orga2. proba. SO'
                [1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0], #alg. algo1. algo2. algo3. analisis. inge1. LyC. metNum. orga1. orga2. proba. SO. redes
                [1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1], #alg. algo1. algo2. algo3. analisis. bd. inge1. LyC. metNum. orga1. orga2. plp. proba. SO. redes. tleng'
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  #alg. algo1. algo2. algo3. analisis. bd. inge1. inge2. LyC. metNum. orga1. orga2. plp. proba. SO. redes. tleng'
                ]
nodosDelPlan93 = [l+([0]*len(dic_materias23)) for l in nodosDelPlan93]



nodosDelPlan23 = [[0]*len(dic_materias) for _ in range(8)]
nodosDelPlan23[1][0]=1;nodosDelPlan23[1][24]=1 #1er cuatri
nodosDelPlan23[2]=nodosDelPlan23[1].copy(); nodosDelPlan23[2][19]=1;nodosDelPlan23[2][17]=1 #2do cuatri
nodosDelPlan23[3]=nodosDelPlan23[2].copy(); nodosDelPlan23[3][28]=1;nodosDelPlan23[3][27]=1;nodosDelPlan23[3][12]=1 #3er cuatri
nodosDelPlan23[4]=nodosDelPlan23[3].copy(); nodosDelPlan23[4][25]=1;nodosDelPlan23[4][20]=1;nodosDelPlan23[4][23]=1 #4to cuatri
nodosDelPlan23[5]=nodosDelPlan23[4].copy(); nodosDelPlan23[5][29]=1;nodosDelPlan23[5][21]=1;nodosDelPlan23[5][14]=1 #5to cuatri
nodosDelPlan23[6]=nodosDelPlan23[5].copy(); nodosDelPlan23[6][22]=1;nodosDelPlan23[6][18]=1 #6to cuatri
nodosDelPlan23[7]=nodosDelPlan23[6].copy(); nodosDelPlan23[7][15]=1;nodosDelPlan23[7][26]=1 #8vo cuatri



rangeYearsDropdown = list(df_cursadas_por_alumno['anio_academico'].unique())
#default_max_range_slider = 10



def strMateriasAprobadas(l, nameColumn): #l <- nodosCaminos.iloc[i]['vector'], nameColumn opciones: 'codigo','nombre_materia_x'
    boolean_mask = [bool(valor) for valor in l]
    
    output = f""
    for i in range(len(materiasCatalogo[boolean_mask])): #  materiasCatalogo[boolean_mask]['codigo'].tolist():
        output+= str(materiasCatalogo[boolean_mask].iloc[i].name+1) +'. '+ materiasCatalogo[boolean_mask].iloc[i][nameColumn] +'\n'
    return output[:len(output)-1]
"""


# def buscarNodosDesconectados(df_edges, dic_node, nodosDesconect):
#     df_arrowIn = pd.DataFrame({
#         'nodoID': dic_node.index.to_list(),
#         'flechaIn': [False for _ in range(len(dic_node))]
#         })

#     for row in df_edges.itertuples():
#         beginning = row.edge[0]
#         end = row.edge[1]
#         if beginning != end and beginning not in nodosDesconect: 
#             df_arrowIn.loc[end,'flechaIn'] = True

#     return df_arrowIn




# ########### refactor de comment anterior 22/5/2026
def buscarNodosDesconectados(df_edges, dic_node, nodosDesconect):
    indices = set(dic_node.index.to_list())
    indices.remove(0)
    tienenFlechaIn = set()

    if len(df_edges)>0:
        tienenFlechaIn = set(df_edges[(df_edges['edge'].str[1] != df_edges['edge'].str[0]) & 
                                    ~(df_edges['edge'].str[0].isin(nodosDesconect)) ]['edge'].str[1].to_list())

    return list(indices-tienenFlechaIn)


def generate_TP_nodes_and_edges(yearList, planYear, cantCuatrisPassed): #, edgeMinWeight

    ###################old, solo 1 año selected. new: aceptaYearList
    # cursaronYEAR = df_cursadas_por_alumno[(df_cursadas_por_alumno['anio_academico'] == year) 
    #                                  & (df_cursadas_por_alumno['periodo'].isin(['1er Cuatrimestre', '1er Bimestre'])) 
    #                                  & (df_cursadas_por_alumno['codigo_materia'].isin(['COMP930001', 'COMP930007']))
    #                                  & (df_cursadas_por_alumno['persona'].isin(df_planes_por_alumno['persona']))  ][['persona']].drop_duplicates('persona').copy() #personaID que cursaron en YEAR

    # preYEAR = df_cursadas_por_alumno[df_cursadas_por_alumno['anio_academico'] < year][['persona']].drop_duplicates('persona') #personasID con inscripcion  pre-YEAR
    # camadaYEAR = cursaronYEAR.drop( cursaronYEAR[cursaronYEAR['persona'].isin( list(preYEAR.transpose().iloc[0].values) )].index ) #camada2022 = cursaron2022 SIN los que se han inscripto pre-YEAR
    
    

    # personasXFirstYearFalcultad = df_cursadas_por_alumno[ df_cursadas_por_alumno['persona'].isin(df_planes_por_alumno['persona']) ].groupby('persona')['anio_academico'].min().reset_index()
    #camadaYEAR = personasXFirstYearFalcultad[(personasXFirstYearFalcultad['anio_academico'].isin(yearList))]
    """
    personasXFirstYearFalcultad = df_planes_por_alumno[(df_planes_por_alumno['codigo_carrera'] =='LCCOMP')].groupby('persona')['anio_inscripcion'].min().reset_index().drop_duplicates()
    camadaYEAR = personasXFirstYearFalcultad[(personasXFirstYearFalcultad['anio_inscripcion'].isin(yearList))]
    
    ## elijo año plan
    if type(planYear) is int: 
        camadaYEAR =camadaYEAR[camadaYEAR['persona'].isin(df_planes_por_alumno[(df_planes_por_alumno['codigo_carrera'] =='LCCOMP') & (df_planes_por_alumno['plan'] ==planYear)]['persona'].to_list())]

    
    #### Filtro extra: en CAMADA de ese year, quiero SOLO las personas que se hayan inscripto en su primera materia a alguna de las 4 de primer año
    mustBe1stMaterias = ["COMP930001", "COMP930007", "COMP930003", "COMP930016"]+["COMP230003", "COMP230001", "COMP230008"]

    primera_materia = df_cursadas_por_alumno[df_cursadas_por_alumno['persona'].isin(camadaYEAR['persona'].to_list()) ].sort_values(['persona', 'anio_academico', 'periodo' ] ).groupby('persona')['codigo_materia'].first()
    camadaYEAR = primera_materia[primera_materia.isin(mustBe1stMaterias)].reset_index()
    """
    camadaYEAR = get_camada(yearList, planYear)


    ###################
    cursadas_camadaYEAR = df_cursadas_por_alumno[df_cursadas_por_alumno['persona'].isin(list(camadaYEAR.transpose().iloc[0].values)) & 
                                           (df_cursadas_por_alumno['codigo_materia'].isin(dic_materias['codigo_materia'].tolist())) & 
                                           (df_cursadas_por_alumno['resultado'] != 'U')]
    
    cursadas_camadaYEAR.insert(len(cursadas_camadaYEAR.columns), 'vector', [[0]*len(dic_materias) for i in range(len(cursadas_camadaYEAR)) ]  )
    # hago sort 
    cursadas_camadaYEAR = cursadas_camadaYEAR.sort_values(['persona', 'anio_academico', 'periodo' ] ) 


    ###################
    ###################
    #####Agrego variable de input porque quiero saber cómo la gente avanza en x #cuatrimestres . cantCuatrisPassed = [initNroCuatri, finNroCuatri]

    # tomo periodos por alumnos
    periodos_por_alumno = (
        cursadas_camadaYEAR[['persona', 'anio_academico', 'periodo']]
        .drop_duplicates()
        #.sort_values(['persona', 'anio_academico', 'periodo'])
    )
    periodos_por_alumno['cuatri_nro'] = periodos_por_alumno.groupby('persona').cumcount() + 1
    
    cursadas_camadaYEAR = cursadas_camadaYEAR.merge(
        periodos_por_alumno, 
        on=['persona', 'anio_academico', 'periodo'], 
        how='left'
    )

    ###################
    #     Genero los vectores (aprovechando que esta ordenado por ['persona', 'anio_academico', 'periodo']) nos permite recorrer las filas en ese orden:
    #  - si es persona que ya hemos visto: actualizo vector con el de la fila anterior (si es persona nueva, dejo vector de ceros)
    #  - y si resultado fue Aprobado, actualizo pos correspondiente al dic de materias

    for filaNro in range(1, len(cursadas_camadaYEAR)):
        oldFila = cursadas_camadaYEAR.iloc[filaNro-1]
        fila = cursadas_camadaYEAR.iloc[filaNro]

        if int(oldFila.persona) == int(fila.persona):
            cursadas_camadaYEAR.at[int(fila.name), 'vector']  = oldFila.vector

        if fila.resultado == 'A':
            newVect = cursadas_camadaYEAR.loc[int(fila.name), 'vector'].copy()
            k = int(dic_materias[dic_materias['codigo_materia'] == fila.codigo_materia ]['codigo_materia'].index[0])
            newVect[k] = 1
            cursadas_camadaYEAR.at[int(fila.name), 'vector'] = newVect


    cursadas_camadaYEAR['vectStr'] = cursadas_camadaYEAR['vector'].apply(str) 

    #####################
    #####################
    #####################
    # 13/06: Ahora sí filtrar por rango de cuatrimestres para los EDGES 
    if cantCuatrisPassed is not None:
        #default_max_range_slider =  periodos_por_alumno['cuatri_nro'].max() ## Aun no se si colocar esto en limite de slider 

        cursadas_camadaYEAR = cursadas_camadaYEAR[
            (cursadas_camadaYEAR['cuatri_nro'] <= cantCuatrisPassed[1])
        ]


    #####################
    #####################
    #####################
    # 
    #  IDEA para generar edges
    # for persona_unique_ID, agregar los edges d esa persona. Considerando ++ el de vectZeros y el vect final 

    vectorCeroStandar = str([0]*len(dic_materias))
    edges = []
    persona = []
    esLoop = []

    #para poder filtrar cantidadCuatrisPassed luego
    cuatri_nro_list = []

    #asocia nodo <-> numero
    dic_node = cursadas_camadaYEAR[['vectStr', 'vector']].copy().drop_duplicates('vectStr').reset_index().drop(columns=('index')) # index es el nombre del nodo que usaré para nodos de grafic
    # if(len(dic_node[dic_node['vectStr'] == vectorCeroStandar]) == 0):
    #     dic_node.loc[-1] = [vectorCeroStandar, [0]*len(dic_materias) ]
    #     dic_node.index = dic_node.index + 1
    if len(dic_node[dic_node['vectStr'] == vectorCeroStandar]) == 0: #agrego vector nulo en caso de que no exista
        nodo_cero = pd.DataFrame({'vectStr': [vectorCeroStandar], 'vector': [[0]*len(dic_materias)]})
        dic_node = pd.concat([nodo_cero, dic_node], ignore_index=False)
        dic_node.index = dic_node.index + 1

    for p in cursadas_camadaYEAR['persona'].drop_duplicates().tolist():
        personaCursadas = cursadas_camadaYEAR[cursadas_camadaYEAR['persona'] == p]

        vectA = vectorCeroStandar

        oldFila = personaCursadas.iloc[0]
        oldPeriodo = oldFila.periodo
        oldYear = oldFila.anio_academico

        
        for i in range(0,len(personaCursadas)): 
            fila = personaCursadas.iloc[i]
            periodo = fila.periodo
            year = fila.anio_academico

            if not (oldPeriodo==periodo and oldYear==year): 
                originPoint = int(dic_node[dic_node['vectStr'] == vectA].iloc[0].name) 
                endPoint = int(dic_node[dic_node['vectStr'] == oldFila.vectStr ].iloc[0].name)

                edges.append((originPoint, endPoint))
                persona.append(int(fila.persona))
                esLoop.append(originPoint==endPoint)
                cuatri_nro_list.append(oldFila.cuatri_nro)

                vectA = oldFila.vectStr


            oldFila = fila
            oldPeriodo = periodo
            oldYear = year


        #if vectA!=oldFila.vectStr: :
        originPoint = int(dic_node[dic_node['vectStr'] == vectA].iloc[0].name) 
        endPoint = int(dic_node[dic_node['vectStr'] == oldFila.vectStr ].iloc[0].name)

        # print((originPoint, endPoint))
        edges.append((originPoint, endPoint))
        persona.append(int(fila.persona))
        esLoop.append(originPoint==endPoint)
        cuatri_nro_list.append(fila.cuatri_nro)
        
            
    # edges
    


    #####################
    #####################
    ### DF final para poder hacer el grafico: agrego cantidad de apariciones para grosor de edges

    if len(edges) == 0:
        # vectorCeroStandar = str([0]*len(dic_materias))
        dic_node_empty = pd.DataFrame({'vectStr': [vectorCeroStandar], 'vector': [[0]*len(dic_materias)]})
        df_edges_empty = pd.DataFrame({'edge': [], 'appears': [], 'idList': []})
        return df_edges_empty, dic_node_empty

   

    allEdges = pd.DataFrame({'edges' : edges, 'persona': persona, 'esLoop': esLoop, 'cuatri_nro': cuatri_nro_list})

    #Loops 
    losLoops = allEdges[allEdges['esLoop']].drop_duplicates().copy()
    losEdges = allEdges[~(allEdges['esLoop'])]

    allAllEdges = pd.concat([losEdges,losLoops])
    
    df_edges = pd.DataFrame({'edge': allAllEdges['edges'].drop_duplicates()  })
    df_edges.insert(1, 'appears', [ len(
                                    allAllEdges[(allAllEdges['edges'] == df_edges['edge'].iloc[i]) &
                        
                                                (allAllEdges['cuatri_nro'] >= cantCuatrisPassed[0]) &
                                                (allAllEdges['cuatri_nro'] <= cantCuatrisPassed[1])
                    
                                                ]) 
                                
                                   for i in range(len(df_edges)) ] ) 
    df_edges.insert(2, 'idList', [allAllEdges[(allAllEdges['edges'] == df_edges['edge'].iloc[i]) &
                        
                                            (allAllEdges['cuatri_nro'] >= cantCuatrisPassed[0]) &
                                            (allAllEdges['cuatri_nro'] <= cantCuatrisPassed[1])
                                              
                                              ]['persona'].to_list()
                                  for i in range(len(df_edges)) ])


    edges_en_rango = set(
                    allAllEdges[
                        (allAllEdges['cuatri_nro'] >= cantCuatrisPassed[0]) &
                        (allAllEdges['cuatri_nro'] <= cantCuatrisPassed[1])
                    ]['edges'].tolist()
                )

    #####################
    #####################
    #####################

    if cantCuatrisPassed is not None:
        
        mask_fuera = ~df_edges['edge'].isin(edges_en_rango)
        df_edges.loc[mask_fuera, 'appears'] = 0
        for idx in df_edges[mask_fuera].index:
            df_edges.at[idx, 'idList'] = []

    return df_edges, dic_node




def cut_edges_at(df_edges, dic_node, edgeMinWeight):

    #####################
    # Mati sugerencia: limitar a nodos con aristas de >= 3 personas
    df_edges = df_edges[df_edges['appears'] >= edgeMinWeight ]



    ####################
    #### Buscar y eliminar nodos a los que no les llega edge
    
    idNodosDesconectados = buscarNodosDesconectados(df_edges, dic_node, [])
    oldLenNodosDesconectados =  -1


    while len(idNodosDesconectados) != oldLenNodosDesconectados:
        df_flechaIn_Again = buscarNodosDesconectados(df_edges, dic_node, idNodosDesconectados)

        oldLenNodosDesconectados = len(idNodosDesconectados)

        idNodosDesconectados = df_flechaIn_Again


    # idNodosDesconectados = []

    ####################
    #### hago lista de nodos
    tpl = set()
    for tuple in df_edges['edge'].tolist():
        tpl.add(tuple[0])
        tpl.add(tuple[1])
    #tpl son los index de los nodos que SI les llega o sale una edge de ellos                 # tpl = tpl - nodeExclude
    tpl = list(tpl)
    tpl = [x for x in tpl if x not in idNodosDesconectados]
    
    ###################
    ### filtro que no haya edges de nodos desconectados
    if len(df_edges) > 0:
        df_edges = df_edges[~df_edges['edge'].str[0].isin(idNodosDesconectados)]
        df_edges = df_edges[~df_edges['edge'].str[1].isin(idNodosDesconectados)]

    return tpl, df_edges #, dic_node

    # return df_edges, dic_node
    