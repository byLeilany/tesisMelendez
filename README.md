## Run herramienta de visualizacion:

- Correr **/repo/visualization_prod/index.py**
- Abrir en navegador la ruta local que te indica en la terminal

## Carpetas Relevantes
**repo/visualization_prod**: Contiene los archivos necesarios para crear y visualizar la herramienta

**repo/bases**: Contiene las bases **.xlsx** utilizadas (lic. en ciencias de computación y en datos)


## Cómo cambiar la **<u>base</u>** que utiliza la herramienta?: 
Hay que ir a **repo/visualization_prod/app.py** y cambiar en `DEFAULT_SOURCE_PATH` el nombre del **.xlsx** deseado

## Cómo editar el **<u>plan</u>** que utiliza la herramienta?: 
Los **.csv** que representan los planes de estudio están **repo/visualization_prod/plan**. Tienen que tener el formato de nombre `CARRERA`_`PLAN`.csv con `CARRERA` y `PLAN` valores que figuren en las columnas "codigo_carrera" y "plan" respectivamente en la hoja "planes por alumno" del **.xlsx** de la base utilizada


## Cómo conseguir "codigo_carrera" para crear un nuevo csv **plan**?:
En archivo **materias_para_catalog.ipynb** es posible cambiar la base **.xlsx** y te permite explorar la hoja de "lista de materias" filtrada por el la particula con la que comienzan las materias de esa carrera. Ejm: todas las materias de la Lic.Cs.Computación empiezan con `COMP93` o `COMP23` dependiendo del plan 93 o 23 respectivamente.