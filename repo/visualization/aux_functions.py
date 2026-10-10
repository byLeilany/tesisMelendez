import numpy as np
import pandas as pd

from datetime import datetime, timedelta


from pathlib import Path
current_dir = Path(__file__).parent
file_path = current_dir.parent /"bases"/"para tesis LCC_v3.xlsx"


df_planes_por_alumno = pd.read_excel(file_path, sheet_name="planes por alumno")
df_planes_por_alumno['anio_inscripcion'] = df_planes_por_alumno['fecha_inscripcion'].dt.year



df_cursadas_por_alumno = pd.read_excel(file_path, sheet_name="cursadas por alumno (2)") #pd.read_excel(file_path, sheet_name="cursadas por alumno")
df_finales_por_alumno = pd.read_excel(file_path, sheet_name="finales por alumno (2)") #sheet_name="finales por alumno")
df_lista_de_materias = pd.read_excel(file_path, sheet_name="lista de materias")


### Diccionario de materias (indice representa el la posicion en el vector)
dic_materias = df_lista_de_materias[df_lista_de_materias['codigo_materia'].str.contains('COMP93')].sort_values(by="codigo_materia")[:17].drop_duplicates().reset_index().drop(columns=('index')) 
### agrego materias de PLAN23
dic_materias23 = df_lista_de_materias[df_lista_de_materias['codigo_materia'].str.contains('COMP23')].sort_values(by="codigo_materia")[:12].drop_duplicates().reset_index().drop(columns=('index'))
dic_materias23 = pd.concat([dic_materias23, df_lista_de_materias[df_lista_de_materias['codigo_materia'] == 'LCDA210006']], axis=0) ##faltaba ALC
dic_materias23.index = [i+len(dic_materias) for i in range(len(dic_materias23))]
dic_materias = pd.concat([dic_materias, dic_materias23])

## VV es para el orden de los nombres en los nodos. 
ordenMaterias93 = [1, 3, 5, 9, 0, 13, 11, 16, 12, 7, 4, 6, 14, 2, 8, 10, 15, 19, 29, 18, 23, 26, 28, 24, 17, 22, 30, 21, 20, 25]
dic_materias['ordenPlan93'] = ordenMaterias93
dic_materias = dic_materias.sort_values(by="ordenPlan93").reset_index()[['codigo_materia', 'nombre_materia']]



df_mapping_materia_codigo = pd.DataFrame({
    'codigo_materia': [
        'COMP930001', 'COMP930003', 'COMP930004', 'COMP930005', 'COMP930007',
        'COMP930008', 'COMP930009', 'COMP930010', 'COMP930011', 'COMP930012',
        'COMP930013', 'COMP930014', 'COMP930015', 'COMP930016', 'COMP930017',
        'COMP930018', 'COMP930019', 'COMP230001', 'COMP230002', 'COMP230003',
        'COMP230004', 'COMP230005', 'COMP230006', 'COMP230007', 'COMP230008',
        'COMP230009', 'COMP230013', 'COMP230014', 'COMP230015', 'LCDA210006'
    ],
    'codigo': [
        'alg', 'algo1', 'algo2', 'algo3', 'analisis', 'bd', 'inge1', 'inge2',
        'LyC', 'metNum', 'orga1', 'orga2', 'plp', 'proba', 'SO', 'redes', 'tleng',
        'algo2', 'bd', 'analisis', 'arqOrg', 'complej', 'proba', 'inge1',
        'algo1', 'lengF', 'seminario', 'sistDig', 'TDA', 'ALC'
    ]
})
df_mapping_materia_codigo
materiasCatalogo = pd.merge(dic_materias, df_lista_de_materias, on='codigo_materia', how='left')
materiasCatalogo = pd.merge(materiasCatalogo, df_mapping_materia_codigo, on='codigo_materia', how='left')
# materiasCatalogo['codigo'] = ['alg','algo1','algo2','algo3','analisis', 'bd', 'inge1','inge2', 'LyC','metNum','orga1','orga2','plp','proba','SO','redes', 'tleng',
#                               'algo2','bd','analisis','arqOrg','complej','proba', 'inge1','algo1','lengF','seminario','sistDig','TDA', 'ALC'] # new



### Planes de estudio 93 y 23
# nodosDelPlan93 = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
#                 [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], #alg y analisis
#                 [1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0], #alg, algo1. analisis. proba'
#                 [1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0], #alg. algo1. algo2. analisis. orga1. proba'
#                 [1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0], #alg. algo1. algo2. analisis. metNum. orga1. orga2. proba'
#                 [1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0], #alg. algo1. algo2. algo3. analisis. metNum. orga1. orga2. proba. SO'
#                 [1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0], #alg. algo1. algo2. algo3. analisis. inge1. LyC. metNum. orga1. orga2. proba. SO. redes
#                 [1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1], #alg. algo1. algo2. algo3. analisis. bd. inge1. LyC. metNum. orga1. orga2. plp. proba. SO. redes. tleng'
#                 [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  #alg. algo1. algo2. algo3. analisis. bd. inge1. inge2. LyC. metNum. orga1. orga2. plp. proba. SO. redes. tleng'
#                 ]
nodosDelPlan93 = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # ninguna
    [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # analisis, alg
    [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # analisis, alg, proba, algo1
    [1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # analisis, alg, proba, algo1, orga1, algo2
    [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # analisis, alg, proba, algo1, orga1, algo2, orga2, metNum
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],  # + SO, algo3
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],  # + redes, inge1, LyC
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],  # + bd, plp, tleng
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # + inge2
]
nodosDelPlan93 = [l+([0]*len(dic_materias23)) for l in nodosDelPlan93]



# nodosDelPlan23 = [[0]*len(dic_materias) for _ in range(8)]
# nodosDelPlan23[1][0]=1;nodosDelPlan23[1][24]=1 #1er cuatri
# nodosDelPlan23[2]=nodosDelPlan23[1].copy(); nodosDelPlan23[2][19]=1;nodosDelPlan23[2][17]=1 #2do cuatri
# nodosDelPlan23[3]=nodosDelPlan23[2].copy(); nodosDelPlan23[3][28]=1;nodosDelPlan23[3][27]=1;nodosDelPlan23[3][12]=1 #3er cuatri
# nodosDelPlan23[4]=nodosDelPlan23[3].copy(); nodosDelPlan23[4][25]=1;nodosDelPlan23[4][20]=1;nodosDelPlan23[4][23]=1 #4to cuatri
# nodosDelPlan23[5]=nodosDelPlan23[4].copy(); nodosDelPlan23[5][29]=1;nodosDelPlan23[5][21]=1;nodosDelPlan23[5][14]=1 #5to cuatri
# nodosDelPlan23[6]=nodosDelPlan23[5].copy(); nodosDelPlan23[6][22]=1;nodosDelPlan23[6][18]=1 #6to cuatri
# nodosDelPlan23[7]=nodosDelPlan23[6].copy(); nodosDelPlan23[7][15]=1;nodosDelPlan23[7][26]=1 #8vo cuatri
nodosDelPlan23 = [[0]*30 for _ in range(8)]
nodosDelPlan23[1][1]=1;nodosDelPlan23[1][17]=1 #1er cuatri
nodosDelPlan23[2]=nodosDelPlan23[1].copy(); nodosDelPlan23[2][18]=1;nodosDelPlan23[2][19]=1 #2do cuatri
nodosDelPlan23[3]=nodosDelPlan23[2].copy(); nodosDelPlan23[3][20]=1;nodosDelPlan23[3][21]=1;nodosDelPlan23[3][14]=1 #3er cuatri
nodosDelPlan23[4]=nodosDelPlan23[3].copy(); nodosDelPlan23[4][22]=1;nodosDelPlan23[4][23]=1;nodosDelPlan23[4][24]=1 #4to cuatri
nodosDelPlan23[5]=nodosDelPlan23[4].copy(); nodosDelPlan23[5][25]=1;nodosDelPlan23[5][26]=1;nodosDelPlan23[5][8]=1 #5to cuatri
nodosDelPlan23[6]=nodosDelPlan23[5].copy(); nodosDelPlan23[6][27]=1;nodosDelPlan23[6][28]=1 #6to cuatri
nodosDelPlan23[7]=nodosDelPlan23[6].copy(); nodosDelPlan23[7][29]=1 #;nodosDelPlan23[7][26]=1 #8vo cuatri






rangeYearsDropdown = list(df_cursadas_por_alumno['anio_academico'].unique())



def strMateriasAprobadas(l, nameColumn): 
    """
    l <- nodosCaminos.iloc[i]['vector'], 
    nameColumn opciones: 'codigo','nombre_materia_x'
    """
    boolean_mask = [bool(valor) for valor in l]
    
    output = f""
    for i in range(len(materiasCatalogo[boolean_mask])): #  materiasCatalogo[boolean_mask]['codigo'].tolist():
        output+= str(materiasCatalogo[boolean_mask].iloc[i].name+1) +'. '+ materiasCatalogo[boolean_mask].iloc[i][nameColumn] +'\n'
    return output[:len(output)-1]




def get_camada(yearList, planYear):
    personasXFirstYearFalcultad = df_planes_por_alumno[(df_planes_por_alumno['codigo_carrera'] =='LCCOMP')].groupby('persona')['anio_inscripcion'].min().reset_index().drop_duplicates()
    camadaYEAR = personasXFirstYearFalcultad[(personasXFirstYearFalcultad['anio_inscripcion'].isin(yearList))]

    ## elijo año plan
    if type(planYear) is int: 
        camadaYEAR =camadaYEAR[camadaYEAR['persona'].isin(df_planes_por_alumno[(df_planes_por_alumno['codigo_carrera'] =='LCCOMP') & (df_planes_por_alumno['plan'] ==planYear)]['persona'].to_list())]


    #### Filtro extra: en CAMADA de ese year, quiero SOLO las personas que se hayan inscripto en su primera materia a alguna de las 4 de primer año
    # mustBe1stMaterias = ["COMP930001", "COMP930007", "COMP930003", "COMP930016"]+["COMP230003", "COMP230001", "COMP230008"]

    # primera_materia = df_cursadas_por_alumno[df_cursadas_por_alumno['persona'].isin(camadaYEAR['persona'].to_list()) ].sort_values(['persona', 'anio_academico', 'periodo' ] ).groupby('persona')['codigo_materia'].first()
    # camadaYEAR = primera_materia[primera_materia.isin(mustBe1stMaterias)].reset_index()
    
    return camadaYEAR