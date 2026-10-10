from graphviz import Digraph
import numpy as np
import pandas as pd

dot = Digraph()

dot.node('A', '[0,0,0,0,0,0,0,0,0,0]')
dot.node('c', '[1,1,1,0,0,0,0,0,0,0]')

dot.node('d', '[1,1,1,0,0,0,0,0,0,0]')
dot.edge('A','c', penwidth='10.0')
dot.edge('A','d', penwidth='1.0',color="#9ACEEB")


dot.render('graphic2', format='png', cleanup=True)


# file_path = "para tesis LCC.xlsx"
# df_totales = pd.read_excel(file_path)
# df_planes_por_alumno = pd.read_excel(file_path, sheet_name="planes por alumno")
# df_cursadas_por_alumno = pd.read_excel(file_path, sheet_name="cursadas por alumno")
# df_lista_de_materias = pd.read_excel(file_path, sheet_name="lista de materias")
# df_finales_por_alumno = pd.read_excel(file_path, sheet_name="finales por alumno")
# df_estados_de_actas = pd.read_excel(file_path, sheet_name="estados de actas")
# df_resultados_posibles = pd.read_excel(file_path, sheet_name="resultados posibles")






# print(df_resultados_posibles)
