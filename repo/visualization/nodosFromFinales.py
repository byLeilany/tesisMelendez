import numpy as np
import pandas as pd
from datetime import datetime, timedelta


from pathlib import Path
current_dir = Path(__file__).parent
file_path = current_dir.parent /"bases"/"para tesis LCC_v3.xlsx"

from aux_functions import df_cursadas_por_alumno, df_finales_por_alumno, dic_materias, get_camada

# df_totales = pd.read_excel(file_path)

"""
df_planes_por_alumno = pd.read_excel(file_path, sheet_name="planes por alumno")
df_cursadas_por_alumno = pd.read_excel(file_path, sheet_name="cursadas por alumno (2)")
df_lista_de_materias = pd.read_excel(file_path, sheet_name="lista de materias")
df_finales_por_alumno = pd.read_excel(file_path, sheet_name="finales por alumno (2)") #sheet_name="finales por alumno")

dic_materias = df_lista_de_materias[df_lista_de_materias['codigo_materia'].str.contains('COMP93')].sort_values(by="codigo_materia")[:17].drop_duplicates().reset_index().drop(columns=('index'))

### agrego materias de PLAN23
dic_materias23 = df_lista_de_materias[df_lista_de_materias['codigo_materia'].str.contains('COMP23')].sort_values(by="codigo_materia")[:12].drop_duplicates().reset_index().drop(columns=('index'))
dic_materias23 = pd.concat([dic_materias23, df_lista_de_materias[df_lista_de_materias['codigo_materia'] == 'LCDA210006']], axis=0) ##faltaba ALC
dic_materias23.index = [i+len(dic_materias) for i in range(len(dic_materias23))]
dic_materias = pd.concat([dic_materias, dic_materias23])



materiasCatalogo = pd.merge(dic_materias, df_lista_de_materias, on='codigo_materia', how='left')
# materiasCatalogo['codigo'] = ['alg','algo1','algo2','algo3','analisis', 'bd', 'inge1','inge2', 'LyC','metNum','orga1','orga2','plp','proba','SO','redes', 'tleng']
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
"""


# def strMateriasAprobadas(l): #l <- nodosCaminos.iloc[i]['vector']
#     boolean_mask = [bool(valor) for valor in l]

#     output = f""
#     for i in range(len(materiasCatalogo[boolean_mask])): #  materiasCatalogo[boolean_mask]['codigo'].tolist():
#         output+= str(materiasCatalogo[boolean_mask].iloc[i].name+1) +'. '+ materiasCatalogo[boolean_mask].iloc[i]['codigo'] +'\n'
#     return output[:len(output)-1]




def generate_FINALS_nodes_and_edges(yearList, planYear):
    #__________________________
    #DONE 17/06 camadaYEAR parametrizado
    """
    personasXFirstYearFalcultad = df_cursadas_por_alumno[ df_cursadas_por_alumno['persona'].isin(df_planes_por_alumno['persona']) ].groupby('persona')['anio_academico'].min().reset_index()
    camadaYEAR = personasXFirstYearFalcultad[(personasXFirstYearFalcultad['anio_academico'].isin(yearList))]

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


    #__________________________
    #todos los finales de los estudiantes de la 
    # - finales aprobados,
    # - camada de year, 
    # - y es de las materias obligatorias

    finales_camadaYEAR = df_finales_por_alumno[(df_finales_por_alumno['resultado'] == 'A') & 
                                            (df_finales_por_alumno['persona'].isin(camadaYEAR['persona'].to_list())) & 
                                            (df_finales_por_alumno['codigo_materia'].isin(dic_materias['codigo_materia'].tolist()) )]

    #__________________________

    #agrego vector con todos ceros y sort
    finales_camadaYEAR.insert(len(finales_camadaYEAR.columns), 'vector', [[0]*len(dic_materias) for i in range(len(finales_camadaYEAR)) ]  )
    finales_camadaYEAR = finales_camadaYEAR.sort_values(['persona', 'fecha_cierre_acta' ] ) # hago sort por persona, luego year, luego periodo
    
    
    #    ################### recorrer a los finales en ese orden
    #     Genero los vectores (aprovechando que esta ordenado por ['persona', 'anio_academico', 'periodo']) nos permite recorrer las filas en ese orden:
    #  - si es persona que ya hemos visto: actualizo vector con el de la fila anterior (si es persona nueva, dejo vector de ceros)
    #  - y si resultado fue Aprobado, actualizo pos correspondiente al dic de materias


    for filaNro in range(1, len(finales_camadaYEAR)):
        oldFila = finales_camadaYEAR.iloc[filaNro-1]
        fila = finales_camadaYEAR.iloc[filaNro]

        if int(oldFila.persona) == int(fila.persona):
            finales_camadaYEAR.at[int(fila.name), 'vector']  = oldFila.vector

        if fila.resultado == 'A':
            newVect = finales_camadaYEAR.loc[int(fila.name), 'vector'].copy()
            k = int(dic_materias[dic_materias['codigo_materia'] == fila.codigo_materia ]['codigo_materia'].index[0])
            newVect[k] = 1
            finales_camadaYEAR.at[int(fila.name), 'vector'] = newVect


    #__________________________
    finales_camadaYEAR['vectStr'] = finales_camadaYEAR['vector'].apply(str) # agrego copia de fila 'vector' pero como string


    #__________________________
    finales_camadaYEAR[['vectStr', 'vector']].copy().drop_duplicates('vectStr').reset_index().drop(columns=('index')) 

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

    #asocia nodo <-> numero
    dic_node = finales_camadaYEAR[['vectStr', 'vector']].copy().drop_duplicates('vectStr').reset_index().drop(columns=('index')) # index es el nombre del nodo que usaré para nodos de grafic
    
    if len(dic_node[dic_node['vectStr'] == vectorCeroStandar]) == 0: #agrego vector nulo en caso de que no exista
        nodo_cero = pd.DataFrame({'vectStr': [vectorCeroStandar], 'vector': [[0]*len(dic_materias)]})
        dic_node = pd.concat([nodo_cero, dic_node], ignore_index=False)
        dic_node.index = dic_node.index + 1

    for p in finales_camadaYEAR['persona'].drop_duplicates().tolist():
        personaCursadas = finales_camadaYEAR[finales_camadaYEAR['persona'] == p]

        vectA = vectorCeroStandar

        oldFila = personaCursadas.iloc[0]
        oldDate = oldFila.fecha_cierre_acta

        
        for i in range(0,len(personaCursadas)): 
            fila = personaCursadas.iloc[i]
            laDate = fila.fecha_cierre_acta

            if oldDate!= laDate: 
                originPoint = int(dic_node[dic_node['vectStr'] == vectA].iloc[0].name) 
                endPoint = int(dic_node[dic_node['vectStr'] == oldFila.vectStr ].iloc[0].name)

                edges.append((originPoint, endPoint))
                persona.append(int(fila.persona))
                esLoop.append(originPoint==endPoint)

                vectA = oldFila.vectStr


            oldFila = fila
            oldDate = laDate


        if vectA!=oldFila.vectStr: # and isAproved=='A':
            originPoint = int(dic_node[dic_node['vectStr'] == vectA].iloc[0].name) 
            endPoint = int(dic_node[dic_node['vectStr'] == oldFila.vectStr ].iloc[0].name)
        
            edges.append((originPoint, endPoint))
            persona.append(int(fila.persona))
            esLoop.append(originPoint==endPoint)
        
            


    #####################
    #####################
    ### DF final para poder hacer el grafico: agrego cantidad de apariciones para grosor de edges

    allEdges = pd.DataFrame({'edges' : edges, 'persona': persona, 'esLoop': esLoop})

    #Loops 
    losLoops = allEdges[allEdges['esLoop']].drop_duplicates().copy()
    losEdges = allEdges[~(allEdges['esLoop'])]

    allAllEdges = pd.concat([losEdges,losLoops])


    df_edges = pd.DataFrame({'edge': allAllEdges['edges'].drop_duplicates()  })
    df_edges.insert(1, 'appears', [ len(allAllEdges[allAllEdges['edges'] == df_edges['edge'].iloc[i]]) for i in range(len(df_edges)) ] ) 
    df_edges.insert(2, 'idList', [allAllEdges[allAllEdges['edges'] == df_edges['edge'].iloc[i] ]['persona'].to_list() for i in range(len(df_edges)) ])
    
    return df_edges, dic_node
    