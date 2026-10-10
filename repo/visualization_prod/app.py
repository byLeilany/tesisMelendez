from pathlib import Path

import dash
from flask_caching import Cache

from core.data_loader import cargar_base_siu
from core.utils import get_carreras_planes_disponibles, _compute_max_steps

BASE_DIR = Path(__file__).parent
DEFAULT_SOURCE_PATH = BASE_DIR.parent /"bases" / "para tesis LCC_v3.xlsx" #"para tesis LCC (DATOS).xlsx" # para tesis LCC (LMAT).xlsx

PLANS_DIR = BASE_DIR / "plan"


app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Grafo de Trayectorias Académicas - FCEyN UBA"
server = app.server

cache = Cache(server, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
})

# Carga única de los datos al iniciar el server 
ACADEMIC_DATASET = cargar_base_siu(DEFAULT_SOURCE_PATH)

# Carga de carrerasEnBaseDisponibles al iniciar el server. Para los dropdowns dependientes carrera -> plan.
CARRERAS_PLANES_DISPONIBLES = get_carreras_planes_disponibles(ACADEMIC_DATASET.planes_por_alumno)

# Busca max global para max de RangeSlider
MAX_STEP_CURSADAS = _compute_max_steps(ACADEMIC_DATASET.cursadas_por_alumno, ["anio_academico", "periodo"])
MAX_STEP_FINALES  = _compute_max_steps(ACADEMIC_DATASET.finales_por_alumno, ["fecha_cierre_acta"])