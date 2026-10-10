from app import app, ACADEMIC_DATASET #, server
from layout import build_layout
import callbacks 

#mayor al 2013 que fue cuando se digitalizo y se paso al SIU Guarani
years_range = sorted(ACADEMIC_DATASET.planes_por_alumno[ACADEMIC_DATASET.planes_por_alumno['anio_inscripcion']>=2010]['anio_inscripcion'].unique())
app.layout = build_layout(years_range)

if __name__ == "__main__":
    app.run(debug=True)
