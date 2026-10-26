## Ejecución de la herramienta de visualización

1. Ejecutar el archivo **`repo/visualization_prod/index.py`**
2. Acceder desde un navegador web a la dirección local indicada en la terminal

## Estructura del repositorio

| Directorio | Descripción |
|---|---|
| `repo/visualization_prod/` | Módulos principales de la herramienta de visualización |
| `repo/bases/` | Bases de datos en formato `.xlsx` o `.csv` |

## Configuración

### Cambiar la base de datos utilizada

La herramienta acepta dos formatos de entrada, configurables en `repo/visualization_prod/app.py`:

- **Archivo `.xlsx` (modo legacy):** modificar la variable `DEFAULT_SOURCE_PATH` con la ruta al archivo deseado.
- **Carpeta con archivos `.csv`:** modificar `DEFAULT_SOURCE_PATH` con la ruta a un directorio que contenga los siguientes cuatro archivos, con exactamente esos nombres:

| Nombre de archivo | Columnas requeridas |
|---|---|
| `datos_inscripcion_carrera.csv` | `persona`, `codigo_carrera`, `plan`, `fecha_inscripcion` |
| `datos_actas_tps.csv` | `persona`, `codigo_materia`, `anio_academico`, `periodo`, `resultado` |
| `datos_actas_examenes.csv` | `persona`, `codigo_materia`, `resultado`, `fecha_llamado_mesa`, `fecha_cierre_acta` |
| `datos_materias.csv` | `codigo_materia`, `nombre_materia` |

Los archivos deben estar codificados en UTF-8 y utilizar `,` o `;` como separador.


### Agregar o modificar un plan de estudios
Los planes de estudio se representan mediante archivos `.csv` ubicados en **`repo/visualization_prod/plan/`**. El nombre de cada archivo debe respetar la convención `CARRERA_PLAN.csv`, donde `CARRERA` y `PLAN` corresponden a los valores presentes en las columnas `codigo_carrera` y `plan` de la hoja *"planes por alumno"* del archivo `.xlsx` de la base utilizada.

### Obtener el código de carrera para un nuevo plan
El notebook **`materias_para_catalog.ipynb`** permite explorar la hoja *"lista de materias"* del archivo `.xlsx` seleccionado, filtrada por el prefijo identificatorio de cada carrera. Por ejemplo, las materias de la Licenciatura en Ciencias de la Computación utilizan los prefijos `COMP93` (Plan 93) y `COMP23` (Plan 2023).

### Reproducir los histogramas de distribución temporal por materia

Los histogramas de distribución del primer intento de cursada por cuatrimestre (utilizados en el análisis de sincronía y retraso estructural) se generan mediante el notebook **`repo/histograma_NroCuatri_CantPersona.ipynb`**.

**Requisitos previos:** tener configurada la base de datos (ver sección *Cambiar la base de datos utilizada*) y al menos un archivo de plan de estudios en `repo/visualization_prod/plan/`.

**Parámetros configurables al inicio del notebook:**

| Variable | Descripción |
|---|---|
| `SOURCE_PATH` | Ruta al archivo `.xlsx` o carpeta con CSVs de la base SIU-Guaraní |
| `PLANS_DIR` | Ruta a la carpeta con los archivos `.csv` de planes de estudio |
| `PLAN_ID` | Identificador del plan a analizar, con formato `CARRERA_PLAN` (ej. `LCCOMP_93`) |
| `MATERIAS` | Lista de códigos de materia a graficar |
| `YEAR_LIST` | Lista de años de inscripción que definen la camada a analizar |

Al ejecutar todas las celdas se genera un gráfico por materia con la distribución empírica del `step_nro` del primer intento de cursada, la mediana empírica, el cuatrimestre sugerido por el plan y el valor $\Delta$ resultante.
