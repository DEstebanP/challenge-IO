# Solución al Reto Estudiantil ASOCIO 2025: Asignación Óptima de Puestos de Trabajo

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Repositorio oficial de la solución propuesta para el **Student Challenge '25** de la Asociación Colombiana de Investigación Operativa (ASOCIO).

---

## 📜 Tabla de Contenido

1.  [Descripción del Problema](#-descripción-del-problema)
2.  [Características Principales](#-características-principales-de-la-solución)
3.  [Estructura del Proyecto](#-estructura-del-proyecto)
4.  [Prerrequisitos e Instalación](#️-prerrequisitos-e-instalación)
    * [Instalación del Solver CBC](#2-instalación-del-solver-cbc)
    * [Instalación del Proyecto](#3-guía-de-instalación-del-proyecto)
5.  [Cómo Ejecutar](#-cómo-ejecutar)
    * [Uso de Otras Instancias](#uso-de-otras-instancias)
6.  [Contribuciones](#-contribuciones)
7.  [Licencia](#-licencia)
8.  [Créditos y Contacto](#-créditos-y-contacto)

---

## 📝 Descripción del Problema

Este proyecto aborda el desafío de asignar puestos de trabajo en un entorno laboral híbrido para la Dirección de Planeación y Desarrollo Institucional de una universidad. El objetivo es desarrollar una herramienta de apoyo a la toma de decisiones que sustituya el ineficiente proceso manual y optimice la asignación de espacios. Para ello, la solución busca un equilibrio entre objetivos complejos y a menudo contrapuestos: debe respetar las **preferencias** de día de los empleados, fomentar la **consistencia** en el uso de puestos y asegurar la **cohesión** de los equipos, un objetivo que se logra al evitar el **aislamiento** de cualquier individuo, fomentando así el bienestar y la colaboración.



## ✨ Características Principales de la Solución

La herramienta desarrollada aborda este desafío mediante una estrategia híbrida y adaptativa que no solo resuelve el problema, sino que **aprende de sus resultados** para mejorar progresivamente. Sus características clave son:

1. **Modelo Híbrido:**  
   La solución descompone el complejo desafío en etapas más manejables combinado la **optimización matemática (Pyomo)** con **heurísticas estratégicas**. Primero, realiza análisis preliminares de riesgo y asigna escritorios \"ancla\" de referencia. Luego, una planificación semanal decide a alto nivel qué empleados asisten cada día, para después resolver la asignación diaria detallada de escritorios.

2. **Ciclo de Retroalimentación y Aprendizaje:**  
   Esta es la característica más potente de la solución. El sistema opera en un ciclo iterativo de **proponer, probar y corregir**:
   
   - *Propone:* La Etapa 2 genera un horario semanal.  
   - *Prueba:* La Etapa 3 simula la asignación diaria y evalúa su calidad, midiendo principalmente el *costo de aislamiento*.  
   - *Aprende:* Si la calidad es deficiente, la Etapa 4 identifica el **núcleo del conflicto** (el grupo de empleados que causa el problema) y genera una nueva restricción o *corte*. Este corte prohíbe esa combinación problemática en la siguiente iteración, forzando al modelo a encontrar una alternativa mejor.

3. **Preparación:**  
   Antes de la optimización, el sistema realiza un **Análisis de Riesgo** para identificar a los empleados \"difíciles\" (con alta probabilidad de quedar aislados) y sus escritorios recomendados. Esta información se utiliza para asignar recursos clave desde el inicio.

4. **Heurística de Escritorios Ancla:**  
   Se asignan los escritorios de forma estratégica, dando prioridad a los casos más complejos y guiando la optimización hacia soluciones más coherentes desde el inicio.

5. **Priorización de la Cohesión:**  
   El modelo está diseñado para priorizar la **cohesión de equipos** y minimizar el aislamiento por encima de otros objetivos secundarios. Esto se logra mediante una función objetivo ponderada en la Etapa 3 que penaliza fuertemente los casos de aislamiento, asegurando que el modelo haga concesiones en otros frentes (como las preferencias de día o la consistencia con el ancla) para mantener a los equipos juntos.

6. **Eficiencia Computacional:**  
   La solución está diseñada para ser **práctica y escalable**. La etapa más intensiva computacionalmente, la asignación diaria (Etapa 3), se ejecuta en **paralelo**, utilizando múltiples núcleos del procesador para resolver todos los días de la semana simultáneamente. Esto reduce significativamente el tiempo total de ejecución y garantiza su aplicabilidad en un entorno real.


---

## 📂 Estructura del Proyecto

```
challenge-IO/
├── data/
│   ├── instance1.json
│   └── ... (demás instancias)
├── src/
│   ├── main.py             # Script principal para ejecutar el programa
│   ├── analysis/
│   │   └── analyzer.py     # Módulo para generar el informe final
│   ├── data/
│   │   └── load_data.py    # Carga y preprocesamiento de datos
│   └── optimizer/
│       ├── heuristics/     # Módulos con las heurísticas
│       └── model/          # Módulos con los modelos de Pyomo
├── .gitignore              # Archivo para ignorar ficheros
├── requirements.txt        # Archivo con las dependencias de Python para pip
└── README.md
```

---

## 🛠️ Prerrequisitos e Instalación

Sigue estos pasos para configurar y ejecutar el proyecto en tu máquina local.

### 1. Prerrequisitos

* **Python:** Desarrollado y probado con la versión 3.12.
* **Git:** Para clonar el repositorio.
* **Solver CBC:** Pyomo necesita un solver externo para funcionar. CBC debe estar instalado y accesible desde la línea de comandos.

### 2. Instalación del Solver CBC

Si no tienes CBC instalado, sigue las instrucciones para tu sistema operativo:

* **En Debian/Ubuntu (y subsistemas Linux en Windows como WSL):**
    ```bash
    sudo apt-get update
    sudo apt-get install coinor-cbc
    ```

* **En macOS (usando Homebrew):**
    ```bash
    brew install cbc
    ```

* **En Windows:**
    1.  Descarga la versión más reciente para tu arquitectura (ej. `Cbc-2.10.10-win64-msvc17-md.zip`) desde la [página oficial de descargas de CBC](https://github.com/coin-or/Cbc/releases).
    2.  Descomprime el archivo en una ubicación permanente, por ejemplo, `C:\Program Files\CBC`.
    3.  Añade la carpeta `bin` de esa ubicación (ej. `C:\Program Files\CBC\bin`) a la variable de entorno **PATH** de tu sistema para que la terminal pueda encontrar el archivo `cbc.exe`.

### 3. Guía de Instalación del Proyecto

Con los prerrequisitos listos, sigue estos pasos en tu terminal:

a. **Clona el repositorio:**
```bash
git clone [https://github.com/DEstebanP/challenge-IO.git](https://github.com/DEstebanP/challenge-IO.git)
cd challenge-IO
```

b. **Crea un entorno virtual:**
```bash
python -m venv venv
```

c. **Activa el entorno virtual:**
* **Windows (CMD/PowerShell):**
    ```bash
    .\venv\Scripts\activate
    ```
* **macOS / Linux:**
    ```bash
    source venv/bin/activate
    ```

d. **Instala las dependencias de Python:**
Este comando leerá el archivo `requirements.txt` e instalará todas las librerías necesarias (Pyomo, Pandas, Tabulate).
```bash
pip install -r requirements.txt
```

¡Listo! El entorno está preparado.

---

## 🚀 Cómo Ejecutar

El script principal es `main.py` y se encuentra en la carpeta `src/`. Se ejecuta de la siguiente manera:

```bash
python src/main.py --file [NOMBRE_DEL_ARCHIVO_JSON]
```

#### Ejemplo:

Para resolver la instancia `instance7.json` ubicada en la carpeta `data/`:

```bash
python src/main.py --file instance7.json
```

El programa procesará la instancia y, al finalizar, imprimirá en la consola un informe estructurado con el resumen ejecutivo, las decisiones operacionales y los análisis de calidad de la solución encontrada.

### Uso de Otras Instancias

Si deseas probar el modelo con nuevas instancias, simplemente coloca los archivos `.json` correspondientes dentro de la carpeta `data/` en la raíz del proyecto. Asegúrate de que los archivos JSON mantengan la misma estructura que las instancias de ejemplo proporcionadas.

---

## 🤝 Contribuciones

Las contribuciones, sugerencias y mejoras son siempre bienvenidas. Si tienes una idea para mejorar el proyecto, siéntete libre de:

1.  Crear un "Fork" del repositorio.
2.  Crear una nueva rama para tu mejora (`git checkout -b feature/AmazingFeature`).
3.  Hacer "Commit" de tus cambios (`git commit -m 'Add some AmazingFeature'`).
4.  Hacer "Push" a la rama (`git push origin feature/AmazingFeature`).
5.  Abrir un "Pull Request".

También puedes simplemente abrir un "Issue" con la etiqueta "suggestion" para discutir cualquier idea que tengas.

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Ver el archivo `LICENSE` para más información.

---

## 👥 Créditos y Contacto

Este proyecto fue desarrollado por:

* **Daniel Esteban Pachon**
    * GitHub: [DEstebanP](https://github.com/DEstebanP)
    * Email: [pachondanielesteban@gmail.com](mailto:pachondanielesteban@gmail.com)

* **Karen Pachon**
    * GitHub: [KarenDaP](https://github.com/KarenDaP)
    * Email: [pachonkaren12@gmail.com](mailto:pachonkaren12@gmail.com)