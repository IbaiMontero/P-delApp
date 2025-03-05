# 🏆 PadelApp

**PadelApp** es una aplicación diseñada para la gestión de estadísticas de pádel, utilizando el sistema de **TrueSkill** para evaluar el rendimiento de los jugadores a lo largo del tiempo. Permite registrar partidos, analizar rankings y visualizar estadísticas de manera interactiva.

## 📋 **Características Principales**
- Registro de jugadores y partidos.
- Cálculo de ranking utilizando el algoritmo **TrueSkill**.
- Visualización de estadísticas individuales y de temporada.
- Interfaz gráfica interactiva con **Tkinter**.
- Gráficos y análisis detallado de rendimiento.

---

## 🛠 **Instalación**
### 1️⃣ **Clonar el repositorio**
```sh
git clone https://github.com/IbaiMontero/PadelApp.git
cd PadelApp
```

### 2️⃣ **Instalar las dependencias**
Asegúrate de tener Python 3 instalado y luego ejecuta:
```sh
pip install -r requirements.txt
```

### 3️⃣ **Ejecutar la aplicación**
Ejecuta el siguiente comando para iniciar la interfaz gráfica:
```sh
python PadelApp/main.py
```

Si prefieres ejecutarlo desde Jupyter Notebook, abre Jupyter y carga los archivos en `notebooks/`.

---

## 📊 **Cómo utilizar PadelApp**
### 🏁 **1. Registro de Jugadores**
- Puedes agregar jugadores manualmente en la interfaz.
- Los jugadores se guardan en `data/jugadores.json`.

### 🎾 **2. Registrar un Partido**
- Selecciona los jugadores de cada equipo.
- Introduce los sets jugados y el ganador.
- La aplicación actualizará automáticamente el ranking **TrueSkill**.

### 📈 **3. Consultar Estadísticas**
- Puedes ver los rankings por temporada.
- Gráficos de evolución de jugadores.
- Estadísticas individuales y generales.

---

## 🔍 **Estructura del Proyecto**
```
PadelApp/
│── data/               # Datos en formato JSON y CSV
│── notebooks/          # Notebooks de análisis
│── src/                # Código fuente en Python
│── tests/              # Pruebas unitarias
│── main.py             # Archivo principal de ejecución
│── requirements.txt    # Dependencias del proyecto
│── README.md           # Descripción del proyecto
│── .gitignore          # Archivos ignorados por Git
```

---

## 📌 **Notas Importantes**
- La aplicación utiliza **Tkinter** para la interfaz gráfica.
- El sistema de rankings está basado en **TrueSkill**.
- Para futuras actualizaciones, puedes hacer `git pull` para obtener los últimos cambios.

Si tienes dudas o sugerencias, ¡no dudes en contribuir! 🚀

