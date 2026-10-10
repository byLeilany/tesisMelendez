# core/spmf_adapter.py
"""
Adaptador para migrar la minería de patrones secuenciales de la librería
`prefixspan` (PyPI, itemsets tratados como símbolos atómicos, ver discusión
Director/Gemini sobre soporte no-monótono entre itemsets hermanos) a SPMF
(Fournier-Viger et al.), que sí implementa subset-matching real de itemsets
para el algoritmo PrefixSpan clásico (Pei et al., 2001).

DECISIÓN DE DISEÑO: se mantiene la MISMA firma de entrada/salida que
`sequence_mining.mine_frequent_patterns`, para que `run_sequence_mining.py`
y los callbacks de la app Dash requieran el mínimo cambio posible. Lo que
cambia es exclusivamente el motor de minería (Java/SPMF en vez de Python puro).

REQUISITOS:
- Java instalado y accesible en PATH (`java -version`).
- `pip install spmf` (wrapper Python, ver https://pypi.org/project/spmf/).
- `spmf.jar` descargado de http://www.philippe-fournier-viger.com/spmf/index.php?link=download.php
  y ubicado según SPMF_JAR_DIR (ver más abajo) o pasado explícitamente.

NOTA IMPORTANTE (léase antes de correr en la base real):
Este adaptador fue construido inspeccionando el código fuente de la librería
`spmf` 1.4 de PyPI y el formato de salida documentado de SPMF, pero no pudo
ser ejecutado end-to-end contra el JAR real en el entorno de desarrollo usado
para escribirlo (la descarga del .jar estaba bloqueada por política de red).
Antes de confiar en los resultados para la tesis, correr `self_test()` al
final de este archivo contra tu propio spmf.jar y verificar que el ejemplo
mínimo (con soporte esperado conocido a mano) devuelve lo esperado.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

try:
    from spmf import Spmf
except ImportError as exc:
    raise ImportError(
        "Falta instalar el wrapper de SPMF: pip install spmf"
    ) from exc


# Ajustar a la carpeta donde se descargó spmf.jar (ver docstring del módulo).
# Por defecto se busca en el mismo directorio que este archivo.
path_spmf_jar = "repo/sequence_mining/spmf.jar"
SPMF_JAR_DIR = Path(path_spmf_jar).parent

# Algoritmos de SPMF que soportan itemsets (subset-matching real) por paso.
# "PrefixSpan" es el equivalente directo al que ya usabas conceptualmente.
# "CM-SPADE" es una alternativa más rápida en datasets grandes, mismo resultado.
SUPPORTED_ALGORITHMS = {"PrefixSpan", "CM-SPADE", "SPADE"}

########## Patch sobre funcion de spmf que por no cerrar el archivo, tira error en windows 
def _write_temp_input_file_windows_safe(self, input_text, file_ending):
    import os
    import tempfile
 
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.write(bytes(input_text, "UTF-8"))
    name = tf.name
    tf.close()  # <- fix: cerrar el handle ANTES de renombrar
    os.rename(name, name + file_ending)
    return name + file_ending
Spmf.write_temp_input_file = _write_temp_input_file_windows_safe


def _reraise_with_java_stderr(
    original_exc: Exception,
    spmf_jar_dir: Path | str,
    algorithm: str,
    input_path: str,
    output_path: str,
    min_support_arg: str,
) -> None:
    """El wrapper `spmf` (PyPI) llama subprocess.check_output(), que solo
    captura stdout — cuando Java lanza una excepción (formato de argumento
    inválido, jar corrupto, algoritmo mal escrito, etc.) el mensaje real
    queda en stderr y se pierde, y lo único que ve el caller es un
    CalledProcessError genérico con 'exit status 1'. Esta función repite
    la MISMA llamada capturando stderr explícitamente, para poder mostrar
    el mensaje real de la JVM antes de relanzar el error original."""
    import subprocess

    cmd = [
        "java", "-jar", str(Path(spmf_jar_dir) / "spmf.jar"),
        "run", algorithm, input_path, output_path, min_support_arg,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print("=== Comando ejecutado ===")
    print(" ".join(cmd))
    print("=== STDOUT ===")
    print(proc.stdout)
    print("=== STDERR (motivo real del fallo, si lo hay) ===")
    print(proc.stderr)
    raise RuntimeError(
        f"SPMF/Java falló (returncode={proc.returncode}). Ver STDERR arriba para "
        f"el mensaje real de la excepción Java. Causas típicas: (a) min_support "
        f"fuera de rango o mal formateado, (b) spmf.jar no está en {spmf_jar_dir}, "
        f"(c) nombre de algoritmo no reconocido por esta versión del jar."
    ) from original_exc


@dataclass
class SpmfMiningResult:
    """Mismo espíritu que SequenceMiningResult en sequence_mining.py, pero
    los patrones ya vienen traducidos a codigo_materia (str), no a IDs (int)."""
    patterns: list[tuple[int, list[tuple[str, ...]]]]  # (soporte, patron) — mismo shape que ps.frequent()
    raw_output_path: str  # para debug / trazabilidad, no se borra el archivo temporal


# --------------------------------------------------------------------------- #
# 1. sequence_database (con codigo_materia string) -> IDs numéricos para SPMF
# --------------------------------------------------------------------------- #

def _build_item_id_maps(
    sequence_database: list[list[tuple[str, ...]]],
) -> tuple[dict[str, int], dict[int, str]]:
    """Construye el vocabulario de símbolos (incluye variantes '!materia' como
    símbolos DISTINTOS de 'materia', igual que en sequence_mining.py) y les
    asigna un ID entero >= 1 (SPMF reserva 0 en algunas variantes; se evita
    para no pisar convenciones internas del formato)."""
    vocabulario = sorted({item for seq in sequence_database for itemset in seq for item in itemset})
    item_to_id = {item: idx + 1 for idx, item in enumerate(vocabulario)}
    id_to_item = {idx: item for item, idx in item_to_id.items()}
    return item_to_id, id_to_item


def _sequences_to_spmf_input(
    sequence_database: list[list[tuple[str, ...]]],
    item_to_id: dict[str, int],
) -> list[list[list[int]]]:
    """Traduce sequence_database (list[persona][step] = tuple[str]) al shape
    que espera `Spmf(input_direct=...)`: list[seq][itemset][item], todo int.
    (el wrapper Python ya se encarga de intercalar -1 / -2, ver Spmf.handle_input).

    IMPORTANTE: la documentación oficial de SPMF exige explícitamente que los
    items DENTRO de un mismo itemset estén en orden total (lexicográfico/numérico)
    — ver https://www.philippe-fournier-viger.com/spmf/PrefixSpan.php, sección
    "What is the input?": "it is assumed that items in an itemset are sorted
    in lexicographical order". El wrapper de PyPI NO normaliza esto por vos
    (ver _build_item_id_maps / Spmf.handle_input): si el mismo itemset semántico
    llega con los items en distinto orden entre dos secuencias (ej. ('!alg',
    '!analisis') en una fila y ('!analisis', '!alg') en otra), SPMF los trata
    como DOS itemsets distintos y NO fusiona su soporte — bug detectado
    empíricamente: ver discusión en el chat de la tesis, caso con juguete de
    7 secuencias donde split '!alg,!analisis' con soporte 3+2 en vez de 5.

    build_student_sequences() en sequence_mining.py ya construye cada itemset
    con tuple(sorted(set(...))) sobre STRINGS de codigo_materia, así que en el
    pipeline real esto normalmente ya viene ordenado — pero el orden alfabético
    de STRINGS no es necesariamente el mismo que el orden NUMÉRICO de los IDs
    asignados acá (ej. si "!COMP930010" < "!COMP930099" alfabéticamente pero
    sus IDs quedan invertidos por construcción del vocabulario). Por eso se
    reordena explícitamente por ID acá, como garantía adicional e independiente
    de cómo venga ordenado sequence_database."""
    return [
        [sorted(item_to_id[item] for item in itemset) for itemset in secuencia]
        for secuencia in sequence_database
    ]


# --------------------------------------------------------------------------- #
# 2. Ejecución de SPMF
# --------------------------------------------------------------------------- #

def mine_frequent_patterns_spmf(
    sequence_database: list[list[tuple[str, ...]]],
    min_support: float,
    is_absolute_count: bool = True,
    algorithm: str = "PrefixSpan",
    spmf_jar_dir: Path | str = SPMF_JAR_DIR,
    top_k: int | None = None,
) -> list[tuple[int, list[tuple[str, ...]]]]:
    """
    Reemplazo directo de sequence_mining.mine_frequent_patterns(), pero
    delegando la minería a SPMF (subset-matching real de itemsets).

    IMPORTANTE sobre min_support: SPMF (línea de comandos, familia PrefixSpan)
    exige el soporte como PORCENTAJE en formato STRING con el signo '%' pegado
    (ej. "25%"), tal como documenta
    https://www.philippe-fournier-viger.com/spmf/PrefixSpan.php — el comando
    de referencia oficial es literalmente `... output.txt 50%`. El wrapper de
    PyPI (`spmf`) hace simplemente str(a) para cada argumento (ver
    spmf/__init__.py línea 49) y NO agrega el '%' por vos, y tampoco captura
    stderr — por eso un argumento mal formado producía antes un
    'CalledProcessError: exit status 1' sin mensaje útil.

    is_absolute_count (bool):
        - True  (default): `min_support` es un ENTERO absoluto de secuencias,
          igual al criterio que ya usabas en run_sequence_mining.py
          (avg_cant_estudiantes_por_year). Se convierte a ratio dividiendo
          por len(sequence_database) ANTES de mandarlo a Java.
        - False: `min_support` ya es un ratio en [0, 1] (o un porcentaje en
          [0, 100] si querés pasarlo directo — se detecta por el rango).
        No se infiere automáticamente a partir del valor numérico (una
        heurística tipo "si es > 1 asumo entero absoluto" es ambigua: un
        min_support=1 absoluto y un min_support=1.0 como ratio 100% son
        indistinguibles sin que el caller lo aclare explícitamente).

    Returns:
        Lista de (soporte, patron) con el MISMO shape que devolvía
        prefixspan.frequent(): patron es list[tuple[str,...]], soporte es int
        (cantidad absoluta de secuencias, no ratio) — para no romper
        pattern_to_readable() ni el resto del pipeline downstream.
    """
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Algoritmo '{algorithm}' no valida subset-matching de itemsets "
            f"garantizado; usar uno de {SUPPORTED_ALGORITHMS}."
        )

    if not sequence_database:
        return []

    item_to_id, id_to_item = _build_item_id_maps(sequence_database)
    spmf_sequences = _sequences_to_spmf_input(sequence_database, item_to_id)

    n_secuencias = len(sequence_database)

    if is_absolute_count:
        min_support_ratio = min_support / n_secuencias
    elif min_support > 1:
        # ya viene como porcentaje 0-100 en vez de ratio 0-1
        min_support_ratio = min_support / 100
    else:
        min_support_ratio = min_support



    # min_support_ratio=0
    print(n_secuencias)
    print(min_support_ratio)

    print(f"{n_secuencias*min_support_ratio} avo de secuencias")
    min_support_arg = f"{min_support_ratio * 100:.10f}".rstrip("0").rstrip(".") + "%"

    print(f"support es de: {min_support_arg}")

    spmf = Spmf(
        algorithm_name=algorithm,
        input_direct=spmf_sequences,
        input_type="normal",
        output_filename=str(Path(spmf_jar_dir) / "spmf-output.txt"),
        arguments=[min_support_arg],
        spmf_bin_location_dir=str(spmf_jar_dir),
    )
    try:
        spmf.run()
    except Exception as exc:
        _reraise_with_java_stderr(exc, spmf_jar_dir, algorithm, spmf.input_, spmf.output_, min_support_arg)

    raw_patterns = spmf.parse_output()  # list[list[str]], cada elemento: itemsets separados, último trozo "#SUP: N"

    patterns: list[tuple[int, list[tuple[str, ...]]]] = []
    for pattern_sup in raw_patterns:
        if not pattern_sup:
            continue
        *itemset_chunks, sup_chunk = pattern_sup
        sup_chunk = sup_chunk.strip()
        if not sup_chunk.startswith("#SUP"):
            raise ValueError(
                f"Formato de salida SPMF inesperado, no encontré '#SUP' al final: {pattern_sup!r}"
            )
        soporte = int(sup_chunk.split()[1])

        patron_legible: list[tuple[str, ...]] = []
        for chunk in itemset_chunks:
            ids_del_itemset = [int(tok) for tok in chunk.split() if tok.strip()]
            items_del_itemset = tuple(id_to_item[i] for i in ids_del_itemset)
            if items_del_itemset:
                patron_legible.append(items_del_itemset)

        patterns.append((soporte, patron_legible))

    patterns.sort(key=lambda x: x[0], reverse=True)
    if top_k is not None:
        patterns = patterns[:top_k]

    return patterns


# --------------------------------------------------------------------------- #
# 3. Self-test: correr esto primero, con datos de juguete, ANTES de la base real
# --------------------------------------------------------------------------- #

def self_test(spmf_jar_dir: Path | str = SPMF_JAR_DIR,
              juguete:list[list[set]] =[]) -> None:
    """
    Reproduce el caso del chat con el Director: 3 personas reprueban Álgebra
    y Análisis JUNTOS en un mismo paso, 1 persona reprueba Análisis SOLA.
    Con subset-matching real, el soporte de '{!analisis}' aislado debe ser
    4 (no 1), porque las 3 primeras personas también "contienen" !analisis
    dentro de su itemset conjunto. Si esto no se cumple, hay un problema de
    configuración de SPMF (versión del jar, algoritmo elegido, o argumento
    de min_support mal interpretado) y NO hay que confiar en los resultados
    contra la base real todavía.
    """
    juguete = [
        [("!alg", "!analisis")],
        [("!alg", "!analisis")],
        [("!alg", "!analisis")],
        [("!analisis",)],
    ]

    # min_support=1
    min_support=50
    resultado = mine_frequent_patterns_spmf(
        juguete, 
        min_support=min_support, 
        is_absolute_count=False, 
        spmf_jar_dir=spmf_jar_dir
    )
    print("Patrones encontrados (self_test):")
    for sup, patt in resultado:
        print(f"  soporte={sup}  patron={patt}")

    soporte_analisis_solo = next((sup for sup, patt in resultado if patt == [("!analisis",)]), None)
    print()
    if soporte_analisis_solo == 4:
        print("OK: subset-matching funcionando como se espera (soporte de {!analisis} = 4).")
    else:
        print(
            f"ALERTA: soporte obtenido para {{!analisis}} fue {soporte_analisis_solo}, "
            "se esperaba 4. Revisar versión de spmf.jar, algoritmo elegido, y si "
            "min_support se está interpretando como ratio correctamente."
        )


if __name__ == "__main__":
    self_test()
