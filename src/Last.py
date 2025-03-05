#!/usr/bin/env python
# coding: utf-8

import itertools
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import csv
import json
from tkcalendar import DateEntry
import sys, os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime
from collections import defaultdict

# ---------------------------------
# 1. TrueSkill
# ---------------------------------
import trueskill

# Ajustes de TrueSkill para más volatilidad y subidas/bajadas más notorias
env = trueskill.TrueSkill(
    mu=25.0,
    sigma=12.0,      # Mayor sigma inicial => más cambios al principio
    beta=6.0,        # Factor de habilidad => subidas/bajadas más marcadas
    tau=0.3,         # Mantiene volatilidad con el tiempo
    draw_probability=0.0
)

# ---------------------------------
# 2. Funciones de utilidad
# ---------------------------------
def resource_path(relative_path):
    # Devuelve la carpeta donde se está ejecutando el .exe,
    # en lugar de usar _MEIPASS.
    return os.path.join(os.path.dirname(sys.executable), relative_path)

def obtener_season(fecha_str):
    """
    Determina la 'Season' según la fecha.
    Ajusta la lógica según tu calendario real de temporadas.
    """
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
    except Exception:
        return "Unknown"
    limite = datetime(2025, 1, 1)
    if fecha < limite:
        return "Season 0"
    else:
        year_diff = fecha.year - 2025
        sem = 0 if fecha.month <= 6 else 1
        season_num = 1 + (2 * year_diff) + sem
        return f"Season {season_num}"

# Menos conservador que mu - 3*sigma: permite subir/bajar más rápido
def rating_value(rating_obj):
    return rating_obj.mu - 2 * rating_obj.sigma

# ---------------------------------
# 3. Variables globales
# ---------------------------------
jugadores = []
resultados = []
parejas = []
equipos_str = []
equipo_str_a_pareja = {}

ranking_trueskill_por_season = {}  # {season: {jugador: Rating}}
ts_changes_por_partido = {}        # {idx_partido: {jugador: cambio_en_rating}}
champion_by_season = {}            # {season: nombre_jugador_campeon}

# Contadores de puestos
trofeos_Liga_jugador = defaultdict(int)  # 1º puestos
segundos_Liga_jugador = defaultdict(int) # 2º puestos
terceros_Liga_jugador = defaultdict(int) # 3º puestos

# Lista de ganadores de torneos (tupla de (fecha, ganador1, ganador2))
torneo_winners = []
# Contador de torneos ganados por cada jugador
torneos_jugador = defaultdict(int)

# ---------------------------------
# 4. Lectura/Escritura de Jugadores
# ---------------------------------
def leer_jugadores():
    global jugadores
    archivo_jugadores = resource_path("jugadores.json")
    if os.path.exists(archivo_jugadores):
        try:
            with open(archivo_jugadores, "r", encoding="utf-8") as f:
                jugadores = json.load(f)
        except Exception as e:
            print("Error al leer jugadores:", e)
            jugadores = []
    else:
        jugadores = ["Ibai", "Xabi", "Ian", "Aitor", "Cifu", "David",
                     "Igarki", "Aimar", "Erli", "Maria", "Dani", "AnderM",
                     "Abad", "Sanchez"]
    jugadores.sort()

def guardar_jugadores():
    archivo_jugadores = resource_path("jugadores.json")
    with open(archivo_jugadores, "w", encoding="utf-8") as f:
        json.dump(jugadores, f, ensure_ascii=False, indent=4)

# ---------------------------------
# 5. Lectura/Escritura de Resultados
# ---------------------------------
def leer_resultados():
    global resultados
    resultados.clear()
    archivo_resultados = resource_path("resultados.csv")
    if os.path.exists(archivo_resultados):
        with open(archivo_resultados, mode='r', newline='', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    eq1j1 = row.get("equipo1_jugador1", "").strip()
                    eq1j2 = row.get("equipo1_jugador2", "").strip()
                    eq2j1 = row.get("equipo2_jugador1", "").strip()
                    eq2j2 = row.get("equipo2_jugador2", "").strip()
                    g1s1 = row.get("ganador_primer_set_jugador1", "").strip()
                    g1s2 = row.get("ganador_primer_set_jugador2", "").strip()
                    gpart1 = row.get("ganador_partido_jugador1", "").strip()
                    gpart2 = row.get("ganador_partido_jugador2", "").strip()
                    puntuaciones = row.get("puntuaciones", "").split(';') if row.get("puntuaciones") else []
                    fecha_str = row.get("fecha", "").strip()
                    season = row.get("season") or obtener_season(fecha_str)
                    resultado = {
                        "partido": ((eq1j1, eq1j2), (eq2j1, eq2j2)),
                        "ganador_primer_set": (g1s1, g1s2),
                        "ganador_partido": (gpart1, gpart2),
                        "mvp": row.get("mvp", "").strip(),
                        "puntuaciones": puntuaciones,
                        "tie_breaks": int(row["tie_breaks"]) if row.get("tie_breaks") else 0,
                        "lugar": row.get("lugar", "").strip(),
                        "fecha": fecha_str,
                        "season": season
                    }
                    resultados.append(resultado)
                except Exception as e:
                    print(f"Error procesando fila: {row}, Error: {e}")

def guardar_resultado_csv(resultado):
    archivo_resultados = resource_path("resultados.csv")
    file_exists = os.path.exists(archivo_resultados)
    fieldnames = [
        "equipo1_jugador1", "equipo1_jugador2",
        "equipo2_jugador1", "equipo2_jugador2",
        "ganador_primer_set_jugador1", "ganador_primer_set_jugador2",
        "ganador_partido_jugador1", "ganador_partido_jugador2",
        "mvp", "puntuaciones", "tie_breaks", "lugar", "fecha", "season"
    ]
    with open(archivo_resultados, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "equipo1_jugador1": resultado["partido"][0][0],
            "equipo1_jugador2": resultado["partido"][0][1],
            "equipo2_jugador1": resultado["partido"][1][0],
            "equipo2_jugador2": resultado["partido"][1][1],
            "ganador_primer_set_jugador1": resultado["ganador_primer_set"][0],
            "ganador_primer_set_jugador2": resultado["ganador_primer_set"][1],
            "ganador_partido_jugador1": resultado["ganador_partido"][0],
            "ganador_partido_jugador2": resultado["ganador_partido"][1],
            "mvp": resultado["mvp"],
            "puntuaciones": ';'.join(resultado["puntuaciones"]),
            "tie_breaks": resultado["tie_breaks"],
            "lugar": resultado["lugar"],
            "fecha": resultado["fecha"],
            "season": resultado["season"]
        })

# ---------------------------------
# 6. TrueSkill: Cálculos
# ---------------------------------
def actualizar_trueskill_sin_guardar(ratings_local, partido):
    equipo1, equipo2 = partido["partido"]
    ganador = partido["ganador_partido"]

    old_values = {}
    for j in (equipo1 + equipo2):
        old_values[j] = rating_value(ratings_local[j])

    team1 = [ratings_local[equipo1[0]], ratings_local[equipo1[1]]]
    team2 = [ratings_local[equipo2[0]], ratings_local[equipo2[1]]]

    # Determinamos ranks según quién ganó
    if set(ganador) == set(equipo1):
        new_team1, new_team2 = env.rate([team1, team2], ranks=[0, 1])
    else:
        new_team1, new_team2 = env.rate([team1, team2], ranks=[1, 0])

    ratings_local[equipo1[0]], ratings_local[equipo1[1]] = new_team1
    ratings_local[equipo2[0]], ratings_local[equipo2[1]] = new_team2

    changes = {}
    for j in (equipo1 + equipo2):
        new_val = rating_value(ratings_local[j])
        changes[j] = round(new_val - old_values[j], 2)
    return changes

def recalcular_trueskill_por_season():
    ranking_trueskill_por_season.clear()
    ts_changes_por_partido.clear()
    champion_by_season.clear()
    trofeos_Liga_jugador.clear()
    segundos_Liga_jugador.clear()
    terceros_Liga_jugador.clear()

    seasons_dict = defaultdict(list)
    for idx, partido in enumerate(resultados):
        season = partido["season"]
        seasons_dict[season].append((idx, partido))

    def season_sort_key(s):
        if s == "Season 0":
            return 0
        try:
            return int(s.split()[1])
        except:
            return 9999

    sorted_seasons = sorted(seasons_dict.keys(), key=season_sort_key)
    for season in sorted_seasons:
        # Creamos un rating inicial para cada jugador
        ratings_local = {j: env.create_rating() for j in jugadores}
        lista_partidos = seasons_dict[season]
        # Ordenamos por fecha para que se actualice en orden cronológico
        lista_partidos.sort(key=lambda x: x[1]["fecha"])
        for (idx, p) in lista_partidos:
            cambios = actualizar_trueskill_sin_guardar(ratings_local, p)
            ts_changes_por_partido[idx] = cambios
        final_dict = {j: ratings_local[j] for j in jugadores}
        ranking_trueskill_por_season[season] = final_dict

        # Determinamos campeón, 2º y 3º
        ranking_ordenado = sorted(final_dict.items(),
                                  key=lambda x: rating_value(x[1]),
                                  reverse=True)
        for i, (jug, _) in enumerate(ranking_ordenado):
            if i == 0:
                champion_by_season[season] = jug
                trofeos_Liga_jugador[jug] += 1
            elif i == 1:
                segundos_Liga_jugador[jug] += 1
            elif i == 2:
                terceros_Liga_jugador[jug] += 1
            else:
                break

# ---------------------------------
# 7. Animales / Badges / Títulos y Banner
# ---------------------------------
def asignar_animal_por_ts(ts_val):
    """
    Ejemplo de 'apodos' según TS. Ajusta a tu gusto.
    """
    if ts_val < -1:
        return "Hormiga"
    elif ts_val < -0.5:
        return "Escapatrajo"
    elif ts_val == 0:
        return "Mono"
    elif ts_val < 2:
        return "Besugo"
    elif ts_val < 5:
        return "Borrego"
    elif ts_val < 10:
        return "Merluza"
    elif ts_val < 15:
        return "Gato"
    elif ts_val < 20:
        return "Mapache"
    elif ts_val < 25:
        return "Cobra"
    elif ts_val < 30:
        return "Zorro"
    elif ts_val < 35:
        return "Tigre"
    elif ts_val < 40:
        return "Great White Shark"
    elif ts_val < 45:
        return "Rinoceronte"
    elif ts_val < 50:
        return "León"
    elif ts_val < 55:
        return "Elefante"
    else:
        return "Dragón"

def get_banner_for_player(player):
    # Títulos de liga
    wins = trofeos_Liga_jugador[player]
    # Títulos de torneos
    wins_torneos = torneos_jugador[player]
    total_wins = wins + wins_torneos
    
    if total_wins == 0:
        podios = segundos_Liga_jugador[player] + terceros_Liga_jugador[player]
        return f"Sin títulos, pero con {podios} podios"  
    elif total_wins == 1:
        return "¡Campeón Novel!"
    elif total_wins == 2:
        return "Multi-campeón"
    elif total_wins == 3:
        return "Triplete"
    elif total_wins == 4:
        return "Alumno de Faker"
    elif total_wins == 5:
        return "Manita"
    else:
        return "¡Leyenda del juego!"


# ---------------------------------
# 8. Mostrar Ranking (Seasons)
# ---------------------------------
def mostrar_ranking_elo():
    recalcular_trueskill_por_season()
    ranking_window = tk.Toplevel()
    ranking_window.title("Ranking TrueSkill (por Seasons)")
    ranking_window.geometry("1000x650")

    style = ttk.Style(ranking_window)
    style.theme_use('clam')
    style.configure('Treeview', 
                    background='white', 
                    foreground='black',
                    rowheight=25, 
                    fieldbackground='white')
    style.configure('Treeview.Heading', 
                    background='#1976D2', 
                    foreground='white',
                    font=('Helvetica', 10))

    notebook = ttk.Notebook(ranking_window)
    notebook.pack(expand=True, fill="both")

    current_season = obtener_season(datetime.today().strftime('%Y-%m-%d'))

    def season_sort_key(s):
        if s == "Season 0":
            return 0
        try:
            return int(s.split()[1])
        except:
            return 9999

    sorted_seasons = sorted(ranking_trueskill_por_season.keys(), key=season_sort_key)

    for season in sorted_seasons:
        frame = tk.Frame(notebook)
        notebook.add(frame, text=season)

        ranking_local = ranking_trueskill_por_season[season]
        ranking_ordenado = sorted(
            ranking_local.items(),
            key=lambda x: rating_value(x[1]),
            reverse=True
        )

        tree = ttk.Treeview(
            frame,
            columns=("Pos", "Jugador", "TS_Rating", "Sigma", "Animal"),
            show='headings'
        )
        tree.heading("Pos", text="Posición")
        tree.heading("Jugador", text="Jugador")
        tree.heading("TS_Rating", text="TS Rating")
        tree.heading("Sigma", text="σ")
        tree.heading("Animal", text="Animal")

        tree.column("Pos", anchor="center", width=70, stretch=True)
        tree.column("Jugador", anchor="center", width=120, stretch=True)
        tree.column("TS_Rating", anchor="center", width=80, stretch=True)
        tree.column("Sigma", anchor="center", width=80, stretch=True)
        tree.column("Animal", anchor="center", width=120, stretch=True)

        # Etiquetas para 1º, 2º, 3º
        tree.tag_configure("first", background="#FFD700", font=('Helvetica', 10))   # Oro
        tree.tag_configure("second", background="#C0C0C0", font=('Helvetica', 10))  # Plata
        tree.tag_configure("third", background="#CD7F32", font=('Helvetica', 10))   # Bronce

        scrollbar_y = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.pack(side='right', fill='y')
        tree.pack(expand=True, fill='both')

        pos = 1
        for (jug, r_obj) in ranking_ordenado:
            ts_val = rating_value(r_obj)
            sigma_val = r_obj.sigma
            animal = asignar_animal_por_ts(ts_val)

            # 1º con copa, 2º y 3º con el número
            if pos == 1:
                pos_display = "🏆"
            else:
                pos_display = str(pos)

            values = (pos_display, jug, f"{ts_val:.2f}", f"{sigma_val:.2f}", animal)

            if season == current_season:
                if pos == 1:
                    tree.insert("", tk.END, values=values, tags=("first",))
                elif pos == 2:
                    tree.insert("", tk.END, values=values, tags=("second",))
                elif pos == 3:
                    tree.insert("", tk.END, values=values, tags=("third",))
                else:
                    tree.insert("", tk.END, values=values)
            else:
                tree.insert("", tk.END, values=values)

            pos += 1

# ---------------------------------
# NUEVO: Añadir ganadores de torneo
# ---------------------------------
def añadir_ganadores_torneo():
    win = tk.Toplevel()
    win.title("Añadir ganadores del torneo")
    tk.Label(win, text="Ganador 1:").grid(row=0, column=0, padx=5, pady=5)
    ganador1_var = tk.StringVar()
    cb1 = ttk.Combobox(win, textvariable=ganador1_var, values=jugadores, state='readonly')
    cb1.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(win, text="Ganador 2:").grid(row=1, column=0, padx=5, pady=5)
    ganador2_var = tk.StringVar()
    cb2 = ttk.Combobox(win, textvariable=ganador2_var, values=jugadores, state='readonly')
    cb2.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(win, text="Fecha del Torneo (YYYY-mm-dd):").grid(row=2, column=0, padx=5, pady=5)
    fecha_torneo_var = DateEntry(win, width=12, background='darkblue', foreground='white',
                                 borderwidth=2, date_pattern='y-mm-dd')
    fecha_torneo_var.grid(row=2, column=1, padx=5, pady=5)

    def guardar_ganadores():
        g1 = ganador1_var.get()
        g2 = ganador2_var.get()
        if not g1 or not g2:
            messagebox.showerror("Error", "Selecciona ambos ganadores.")
            return
        fecha_torneo = fecha_torneo_var.get_date().strftime('%Y-%m-%d')
        torneo_winners.append((fecha_torneo, g1, g2))
        torneos_jugador[g1] += 1
        torneos_jugador[g2] += 1
        messagebox.showinfo("OK", "Ganadores del torneo añadidos.")
        win.destroy()

    tk.Button(win, text="Guardar", command=guardar_ganadores).grid(row=3, column=0, columnspan=2, pady=10)

# ---------------------------------
# NUEVO: Mostrar campeones y ganadores de torneos
# ---------------------------------
torneos_jugador = defaultdict(int)

def contar_torneos():
    torneos_jugador.clear()
    for (fecha, g1, g2) in torneo_winners:
        torneos_jugador[g1] += 1
        torneos_jugador[g2] += 1
def mostrar_campeones():
    recalcular_trueskill_por_season()
    contar_torneos()  # Para actualizar el conteo

    # Recontar torneos_jugador si quieres que sume a la "copa total" de cada jugador
    # (opcional: ver punto 5)
    
    win = tk.Toplevel()
    win.title("Campeones")
    win.geometry("700x500")
    notebook = ttk.Notebook(win)
    notebook.pack(expand=True, fill="both")

    # Pestaña 1: Campeones de cada Season
    frame1 = tk.Frame(notebook)
    notebook.add(frame1, text="Season Champions")

    tree1 = ttk.Treeview(frame1, columns=("Season", "Campeón", "RatingFinal", "Vict%"), show='headings')
    tree1.heading("Season", text="Season")
    tree1.heading("Campeón", text="Campeón")
    tree1.heading("RatingFinal", text="Rating Final")
    tree1.heading("Vict%", text="%Victorias")
    tree1.column("Season", anchor="center", width=80)
    tree1.column("Campeón", anchor="center", width=120)
    tree1.column("RatingFinal", anchor="center", width=100)
    tree1.column("Vict%", anchor="center", width=80)

    def season_sort_key(s):
        if s == "Season 0":
            return 0
        try:
            return int(s.split()[1])
        except:
            return 9999

    sorted_seasons = sorted(champion_by_season.keys(), key=season_sort_key)
    for season in sorted_seasons:
        champ = champion_by_season[season]
        rating_dict = ranking_trueskill_por_season[season]
        champ_rating_obj = rating_dict.get(champ, None)
        champ_rating_val = rating_value(champ_rating_obj) if champ_rating_obj else 0.0
        # % de victorias
        matches = [r for r in resultados if r["season"] == season and (champ in r["partido"][0] or champ in r["partido"][1])]
        wins = [r for r in matches if champ in r["ganador_partido"]]
        vict_exact = (len(wins) / len(matches) * 100) if matches else 0.0
        tree1.insert("", tk.END, values=(season, champ, f"{champ_rating_val:.2f}", f"{vict_exact:.1f}%"))

    tree1.pack(expand=True, fill="both")

    # Pestaña 2: Ganadores de Torneos
    frame2 = tk.Frame(notebook)
    notebook.add(frame2, text="Torneo Ganadores")

    tree2 = ttk.Treeview(frame2, columns=("Torneo", "Ganador 1", "Ganador 2"), show='headings')
    tree2.heading("Torneo", text="Torneo")
    tree2.heading("Ganador 1", text="Ganador 1")
    tree2.heading("Ganador 2", text="Ganador 2")
    tree2.column("Torneo", anchor="center", width=150)
    tree2.column("Ganador 1", anchor="center", width=150)
    tree2.column("Ganador 2", anchor="center", width=150)
    tree2.pack(expand=True, fill="both")

    for idx, (fecha, g1, g2) in enumerate(torneo_winners, start=1):
        tree2.insert("", tk.END, values=(f"Torneo {idx} - {fecha}", g1, g2))

    # Botón para añadir ganadores del torneo
    btn = tk.Button(frame2, text="Añadir ganadores del torneo",
                    command=lambda: [añadir_ganadores_torneo(), win.destroy()])
    btn.pack(pady=10)

# ---------------------------------
# 10. Mostrar Partidos (Seasons) con filtro de fechas
# ---------------------------------
def mostrar_partidos():
    recalcular_trueskill_por_season()
    partidos_window = tk.Toplevel()
    partidos_window.title("Lista de Partidos")
    partidos_window.geometry("1200x700")

    style = ttk.Style(partidos_window)
    style.theme_use('clam')
    style.configure('Treeview', background='#E3F2FD', foreground='black',
                    rowheight=25, fieldbackground='#E3F2FD')
    style.configure('Treeview.Heading', background='#1976D2',
                    foreground='white', font=('Helvetica', 10))

    filtro_frame = tk.Frame(partidos_window)
    filtro_frame.pack(pady=5)

    tk.Label(filtro_frame, text="Filtrar por Jugador:", font=('Helvetica', 12)).grid(row=0, column=0, padx=5)
    jugador_filtro_var = tk.StringVar(value="Todos")
    lista_jugadores_filtro = ["Todos"] + jugadores
    jugador_filtro_combobox = ttk.Combobox(filtro_frame, textvariable=jugador_filtro_var,
                                           values=lista_jugadores_filtro, state='readonly')
    jugador_filtro_combobox.grid(row=0, column=1, padx=5)

    # Filtro de fecha desde
    tk.Label(filtro_frame, text="Fecha Desde:", font=('Helvetica', 12)).grid(row=0, column=2, padx=5)
    fecha_desde_var = DateEntry(filtro_frame, width=12, background='darkblue', foreground='white',
                                borderwidth=2, date_pattern='y-mm-dd')
    fecha_desde_var.grid(row=0, column=3, padx=5)
    
    # Establecer "Fecha Desde" al primer día de la temporada actual
    today = datetime.today()
    current_season = obtener_season(today.strftime('%Y-%m-%d'))
    if current_season != "Season 0":
        if today.month <= 6:
            season_start = datetime(today.year, 1, 1)
        else:
            season_start = datetime(today.year, 7, 1)
        fecha_desde_var.set_date(season_start)


    # Filtro de fecha hasta
    tk.Label(filtro_frame, text="Fecha Hasta:", font=('Helvetica', 12)).grid(row=0, column=4, padx=5)
    fecha_hasta_var = DateEntry(filtro_frame, width=12, background='darkblue', foreground='white',
                                borderwidth=2, date_pattern='y-mm-dd')
    fecha_hasta_var.grid(row=0, column=5, padx=5)

    filtrar_button = ttk.Button(filtro_frame, text="Filtrar", command=lambda: actualizar_partidos())
    filtrar_button.grid(row=0, column=6, padx=10)

    # Podemos poner "fecha hasta" = hoy
    fecha_hasta_var.set_date(datetime.today().date())

    notebook = ttk.Notebook(partidos_window)
    notebook.pack(expand=True, fill='both')

    seasons_dict = defaultdict(list)
    for idx, r in enumerate(resultados):
        season = r["season"]
        seasons_dict[season].append((idx, r))

    def season_sort_key(s):
        if s == "Season 0":
            return 0
        else:
            try:
                return int(s.split()[1])
            except:
                return 9999

    sorted_seasons = sorted(seasons_dict.keys(), key=season_sort_key)
    treeviews = {}

    columnas = ["Fecha", "Equipo 1", "Equipo 2", "Puntuaciones",
                "Ganador", "MVP", "Tie-breaks", "Lugar", "Δ Rating"]

    for season in sorted_seasons:
        frame = tk.Frame(notebook)
        notebook.add(frame, text=season)

        tree = ttk.Treeview(frame, columns=columnas, show='headings')
        for col in columnas:
            tree.heading(col, text=col)
            tree.column(col, anchor='center', width=120, stretch=True)

        tree.pack(expand=True, fill='both')

        scrollbar_y = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        scrollbar_y.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar_y.set)

        treeviews[season] = tree

    def actualizar_partidos():
        filtro_jugador = jugador_filtro_var.get()
        fecha_desde = fecha_desde_var.get_date()
        fecha_hasta = fecha_hasta_var.get_date()

        for season in sorted_seasons:
            tree = treeviews[season]
            tree.delete(*tree.get_children())

            lista_partidos = seasons_dict[season]
            lista_partidos.sort(key=lambda x: x[1]["fecha"])

            for (idx, r) in lista_partidos:
                match_date = datetime.strptime(r["fecha"], '%Y-%m-%d').date()
                # Filtro por rango de fecha
                if not (fecha_desde <= match_date <= fecha_hasta):
                    continue

                eq1_str = " & ".join(r["partido"][0])
                eq2_str = " & ".join(r["partido"][1])
                puntuaciones = "; ".join(r["puntuaciones"]) if r["puntuaciones"] else "N/A"
                ganador = " & ".join(r["ganador_partido"])
                mvp = r["mvp"]
                tie_breaks = r["tie_breaks"]
                lugar = r["lugar"]

                # Filtro por jugador
                jug_partido = list(r["partido"][0]) + list(r["partido"][1])
                if filtro_jugador != "Todos" and filtro_jugador not in jug_partido:
                    continue

                # Calculamos Δ Rating solo si estamos filtrando un jugador concreto
                delta_rating = ""
                if filtro_jugador != "Todos":
                    cambios = ts_changes_por_partido.get(idx, {})
                    if filtro_jugador in cambios:
                        diff = cambios[filtro_jugador]
                        delta_rating = f"+{diff}" if diff >= 0 else str(diff)

                tree.insert("", tk.END, values=(
                    r["fecha"],
                    eq1_str,
                    eq2_str,
                    puntuaciones,
                    ganador,
                    mvp,
                    tie_breaks,
                    lugar,
                    delta_rating
                ))

    jugador_filtro_combobox.bind("<<ComboboxSelected>>", lambda e: actualizar_partidos())
    actualizar_partidos()

    ttk.Button(partidos_window, text="Cerrar", command=partidos_window.destroy).pack(pady=5)

# ---------------------------------
# 11. Estadísticas Generales y Gráficos
# ---------------------------------
def calcular_estadisticas(resultados_filtrar):
    lugares = ["Ibaiondo", "Bakh", "Otro"]
    estadisticas = {}
    for j in jugadores:
        estadisticas[j] = {
            "partidos_jugados": 0,
            "victorias": 0,
            "mvp": 0,
            "sets_jugados": 0,
            "sets_ganados": 0,
            "tie_breaks": 0,
            "primer_set_ganado": 0,
            "games_ganados": 0,
            "games_perdidos": 0,
            "victorias_por_lugar": {l: 0 for l in lugares}
        }
    for r in resultados_filtrar:
        eq1, eq2 = r["partido"]
        ganador = r["ganador_partido"]
        mvp = r["mvp"]
        lugar = r["lugar"]
        sets_jugados = len(r["puntuaciones"])
        for jug in eq1 + eq2:
            if jug not in estadisticas:
                estadisticas[jug] = {
                    "partidos_jugados": 0,
                    "victorias": 0,
                    "mvp": 0,
                    "sets_jugados": 0,
                    "sets_ganados": 0,
                    "tie_breaks": 0,
                    "primer_set_ganado": 0,
                    "games_ganados": 0,
                    "games_perdidos": 0,
                    "victorias_por_lugar": {l: 0 for l in lugares}
                }
        for jug in eq1 + eq2:
            estadisticas[jug]["partidos_jugados"] += 1
            estadisticas[jug]["sets_jugados"] += sets_jugados
        for jug in ganador:
            estadisticas[jug]["victorias"] += 1
            if lugar in estadisticas[jug]["victorias_por_lugar"]:
                estadisticas[jug]["victorias_por_lugar"][lugar] += 1
        for jug in r["ganador_primer_set"]:
            estadisticas[jug]["primer_set_ganado"] += 1
        for set_result in r["puntuaciones"]:
            if '(' in set_result:
                score_part, _ = set_result.split('(')
                s1, s2 = map(int, score_part.split('-'))
                tie_breaks_in_set = 1
            else:
                s1, s2 = map(int, set_result.split('-'))
                tie_breaks_in_set = 0
            for jug in eq1 + eq2:
                estadisticas[jug]["tie_breaks"] += tie_breaks_in_set
            if s1 > s2:
                for jug in eq1:
                    estadisticas[jug]["sets_ganados"] += 1
            else:
                for jug in eq2:
                    estadisticas[jug]["sets_ganados"] += 1
            for jug in eq1:
                estadisticas[jug]["games_ganados"] += s1
                estadisticas[jug]["games_perdidos"] += s2
            for jug in eq2:
                estadisticas[jug]["games_ganados"] += s2
                estadisticas[jug]["games_perdidos"] += s1
        if mvp in estadisticas:
            estadisticas[mvp]["mvp"] += 1
    for jug, st in estadisticas.items():
        pj = st["partidos_jugados"]
        if pj > 0:
            st["porcentaje_victorias"] = st["victorias"] / pj * 100
            st["porcentaje_primer_set"] = st["primer_set_ganado"] / pj * 100
        else:
            st["porcentaje_victorias"] = 0
            st["porcentaje_primer_set"] = 0
        st["diferencia_games"] = st["games_ganados"] - st["games_perdidos"]
    return estadisticas

torneo_winners = []  # Lista de tuplas (fecha, ganador1, ganador2)

def leer_torneos():
    """
    Lee los ganadores de torneos desde torneos.csv y los carga en torneo_winners.
    Cada fila contendrá fecha, ganador1 y ganador2.
    """
    global torneo_winners
    archivo_torneos = resource_path("torneos.csv")
    torneo_winners.clear()
    if os.path.exists(archivo_torneos):
        with open(archivo_torneos, mode='r', newline='', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                fecha = row["fecha"].strip()
                g1 = row["ganador1"].strip()
                g2 = row["ganador2"].strip()
                torneo_winners.append((fecha, g1, g2))

def guardar_torneo_csv(fecha, g1, g2):
    """
    Añade una nueva entrada de torneo (fecha, ganador1, ganador2) en torneos.csv.
    """
    archivo_torneos = resource_path("torneos.csv")
    file_exists = os.path.exists(archivo_torneos)
    fieldnames = ["fecha", "ganador1", "ganador2"]

    with open(archivo_torneos, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()  # Escribe la cabecera si el archivo no existía
        writer.writerow({"fecha": fecha, "ganador1": g1, "ganador2": g2})

def añadir_ganadores_torneo():
    win = tk.Toplevel()
    win.title("Añadir ganadores del torneo")

    # Fecha
    tk.Label(win, text="Fecha del Torneo (YYYY-mm-dd):").grid(row=0, column=0, padx=5, pady=5)
    fecha_var = DateEntry(win, width=12, background='darkblue', foreground='white',
                          borderwidth=2, date_pattern='y-mm-dd')
    fecha_var.grid(row=0, column=1, padx=5, pady=5)

    # Ganador 1
    tk.Label(win, text="Ganador 1:").grid(row=1, column=0, padx=5, pady=5)
    ganador1_var = tk.StringVar()
    cb1 = ttk.Combobox(win, textvariable=ganador1_var, values=jugadores, state='readonly')
    cb1.grid(row=1, column=1, padx=5, pady=5)

    # Ganador 2
    tk.Label(win, text="Ganador 2:").grid(row=2, column=0, padx=5, pady=5)
    ganador2_var = tk.StringVar()
    cb2 = ttk.Combobox(win, textvariable=ganador2_var, values=jugadores, state='readonly')
    cb2.grid(row=2, column=1, padx=5, pady=5)

    def guardar_ganadores():
        g1 = ganador1_var.get()
        g2 = ganador2_var.get()
        if not g1 or not g2:
            messagebox.showerror("Error", "Selecciona ambos ganadores.")
            return
        
        fecha_str = fecha_var.get_date().strftime('%Y-%m-%d')
        # Añadimos en la lista en memoria
        torneo_winners.append((fecha_str, g1, g2))
        # Guardamos en CSV
        guardar_torneo_csv(fecha_str, g1, g2)

        messagebox.showinfo("OK", "Ganadores del torneo añadidos.")
        win.destroy()

    tk.Button(win, text="Guardar", command=guardar_ganadores).grid(row=3, column=0, columnspan=2, pady=10)

def mostrar_estadisticas():
    stats_window = tk.Toplevel()
    stats_window.title("Estadísticas de Jugadores")
    stats_window.geometry("1000x600")

    filtro_frame = ttk.Frame(stats_window)
    filtro_frame.pack(pady=5)

    tk.Label(filtro_frame, text="Selecciona Season:", font=('Helvetica', 10)).grid(row=0, column=0, padx=5)
    recalcular_trueskill_por_season()

    def season_sort_key(s):
        if s == "Season 0":
            return 0
        try:
            return int(s.split()[1])
        except:
            return 9999

    all_seasons = sorted(ranking_trueskill_por_season.keys(), key=season_sort_key)
    seasons_combo = ["Todas"] + all_seasons
    season_var = tk.StringVar(value="Todas")
    combo_season = ttk.Combobox(filtro_frame, textvariable=season_var, values=seasons_combo, state='readonly')
    combo_season.grid(row=0, column=1, padx=5)

    columnas = ("Jugador", "PJ", "Vict", "%Vict", "SetsJug", "SetsGan",
                "GamesGan", "GamesPer", "DifGames", "MVP", "TieBreaks", "%PrimerSet", "Títulos")

    tree = ttk.Treeview(stats_window, columns=columnas, show='headings')
    for col in columnas:
        tree.heading(col, text=col)
        tree.column(col, anchor='center', width=80)
    tree.pack(side='left', fill='both', expand=True)

    scrollbar_y = ttk.Scrollbar(stats_window, orient='vertical', command=tree.yview)
    scrollbar_y.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scrollbar_y.set)

    def cargar_estadisticas():
        tree.delete(*tree.get_children())
        sel_season = season_var.get()
        if sel_season == "Todas":
            resultados_filtrar = resultados
        else:
            resultados_filtrar = [r for r in resultados if r["season"] == sel_season]
        stats = calcular_estadisticas(resultados_filtrar)
        for jug, st in stats.items():
            pj = st["partidos_jugados"]
            vict = st["victorias"]
            porc_vict = f"{st['porcentaje_victorias']:.1f}%"
            sets_jug = st["sets_jugados"]
            sets_gan = st["sets_ganados"]
            games_gan = st["games_ganados"]
            games_per = st["games_perdidos"]
            dif_games = st["diferencia_games"]
            mvp = st["mvp"]
            tie_b = st["tie_breaks"]
            porc_pset = f"{st['porcentaje_primer_set']:.1f}%"
            titulos = trofeos_Liga_jugador[jug]
            tree.insert("", tk.END, values=(
                jug, pj, vict, porc_vict, sets_jug, sets_gan,
                games_gan, games_per, dif_games, mvp, tie_b, porc_pset,
                titulos
            ))

    combo_season.bind("<<ComboboxSelected>>", lambda e: cargar_estadisticas())
    cargar_estadisticas()

def mostrar_grafico_jugadores():
    recalcular_trueskill_por_season()
    if not ranking_trueskill_por_season:
        messagebox.showinfo("Info", "No hay datos de TrueSkill para mostrar.")
        return

    def season_sort_key(s):
        if s == "Season 0":
            return 0
        try:
            return int(s.split()[1])
        except:
            return 9999

    sorted_seasons = sorted(ranking_trueskill_por_season.keys(), key=season_sort_key)
    last_season = sorted_seasons[-1]
    ranking = ranking_trueskill_por_season[last_season]

    fig, ax = plt.subplots(figsize=(8, 6))
    jugadores_ = list(ranking.keys())
    rating_values = [rating_value(ranking[j]) for j in jugadores_]
    ax.bar(jugadores_, rating_values, color='steelblue')
    ax.set_title(f"Ranking TrueSkill - {last_season}")
    ax.set_xlabel("Jugador")
    ax.set_ylabel("TS Rating (mu - 2.5*sigma)")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()

    win = tk.Toplevel()
    win.title("Gráfico de Jugadores (TrueSkill)")
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def mostrar_grafico_acumulado():
    if not resultados:
        messagebox.showinfo("Info", "No hay resultados para mostrar.")
        return
    sorted_resultados = sorted(resultados, key=lambda r: r["fecha"])
    if not sorted_resultados:
        messagebox.showinfo("Info", "No hay resultados para mostrar.")
        return

    ratings_local = {j: env.create_rating() for j in jugadores}
    history = {j: [] for j in jugadores}

    first_date = datetime.strptime(sorted_resultados[0]["fecha"], '%Y-%m-%d')
    for j in jugadores:
        history[j].append((first_date, rating_value(ratings_local[j])))

    for r in sorted_resultados:
        match_date = datetime.strptime(r["fecha"], '%Y-%m-%d')
        actualizar_trueskill_sin_guardar(ratings_local, r)
        for j in jugadores:
            history[j].append((match_date, rating_value(ratings_local[j])))

    fig, ax = plt.subplots(figsize=(10, 6))
    for j in jugadores:
        dates = [p[0] for p in history[j]]
        vals = [p[1] for p in history[j]]
        ax.plot(dates, vals, label=j)
    ax.set_title("Evolución Acumulada del TrueSkill Rating")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("TS Rating (mu - 2.5*sigma)")
    ax.legend(loc='best', fontsize='small')
    fig.autofmt_xdate()
    fig.tight_layout()

    win = tk.Toplevel()
    win.title("Gráfico Acumulado (TrueSkill)")
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def mostrar_heatmap_partidos_vs_ratio():
    from itertools import combinations
    if not resultados:
        messagebox.showinfo("Info", "No hay resultados para calcular el heatmap.")
        return

    pair_matches = {}
    pair_wins = {}
    for pair in combinations(jugadores, 2):
        p = tuple(sorted(pair))
        pair_matches[p] = 0
        pair_wins[p] = 0

    for r in resultados:
        eq1, eq2 = r["partido"]
        ganador = r["ganador_partido"]
        if set(ganador) == set(eq1):
            perdedor = eq2
        else:
            perdedor = eq1
        w = tuple(sorted(ganador))
        l = tuple(sorted(perdedor))
        pair_matches[w] += 1
        pair_wins[w] += 1
        pair_matches[l] += 1

    n = len(jugadores)
    idx_map = {jug: i for i, jug in enumerate(jugadores)}
    T = np.zeros((n, n), dtype=int)
    R = np.zeros((n, n), dtype=float)

    for (p1, p2), total in pair_matches.items():
        i = idx_map[p1]
        j = idx_map[p2]
        wins = pair_wins[(p1, p2)]
        ratio = wins / total if total > 0 else 0
        T[i, j] = total
        T[j, i] = total
        R[i, j] = ratio
        R[j, i] = ratio

    fig, ax = plt.subplots(figsize=(8, 6))
    cax = ax.imshow(R, vmin=0, vmax=1, cmap="Greens", alpha=0.8)
    ax.set_title("Heatmap: Partidos Totales (texto) vs. % Victorias (color)")
    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(jugadores, rotation=45, ha="right")
    ax.set_yticklabels(jugadores)

    for i in range(n):
        for j in range(n):
            if i != j:
                text = str(T[i, j])
                ax.text(j, i, text, ha="center", va="center", color="black", fontsize=9)

    cb = fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Ratio de Victorias", rotation=90)
    fig.tight_layout()

    win = tk.Toplevel()
    win.title("Heatmap Partidos vs. Ratio")
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def mostrar_scatter_elo_vs_metricas():
    recalcular_trueskill_por_season()
    if not ranking_trueskill_por_season:
        messagebox.showinfo("Info", "No hay datos de TrueSkill para mostrar.")
        return

    def season_sort_key(s):
        if s == "Season 0":
            return 0
        try:
            return int(s.split()[1])
        except:
            return 9999

    sorted_seasons = sorted(ranking_trueskill_por_season.keys(), key=season_sort_key)
    last_season = sorted_seasons[-1]
    ranking = ranking_trueskill_por_season[last_season]
    stats = calcular_estadisticas(resultados)

    ts_list = []
    win_perc_list = []
    game_diff_list = []
    names = []

    for jug in jugadores:
        ts_val = rating_value(ranking[jug])
        win_perc = stats[jug]["porcentaje_victorias"]
        game_diff = stats[jug]["diferencia_games"]
        ts_list.append(ts_val)
        win_perc_list.append(win_perc)
        game_diff_list.append(game_diff)
        names.append(jug)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    ax1.scatter(ts_list, win_perc_list, color="darkgreen", s=100)
    for i, name in enumerate(names):
        ax1.annotate(name, (ts_list[i], win_perc_list[i]),
                     textcoords="offset points", xytext=(5,5), fontsize=9)
    ax1.set_xlabel("TS Rating")
    ax1.set_ylabel("% Victorias")
    ax1.set_title("TrueSkill vs. % Victorias")

    ax2.scatter(ts_list, game_diff_list, color="darkblue", s=100)
    for i, name in enumerate(names):
        ax2.annotate(name, (ts_list[i], game_diff_list[i]),
                     textcoords="offset points", xytext=(5,5), fontsize=9)
    ax2.set_xlabel("TS Rating")
    ax2.set_ylabel("Diferencia de Games")
    ax2.set_title("TrueSkill vs. Diferencia de Games")

    fig.tight_layout()
    win = tk.Toplevel()
    win.title("Scatter Plot: TrueSkill vs. Métricas")
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def mostrar_scatter_elo_vs_partidos():
    recalcular_trueskill_por_season()
    if not ranking_trueskill_por_season:
        messagebox.showinfo("Info", "No hay datos de TrueSkill para mostrar.")
        return

    def season_sort_key(s):
        if s == "Season 0":
            return 0
        try:
            return int(s.split()[1])
        except:
            return 9999

    sorted_seasons = sorted(ranking_trueskill_por_season.keys(), key=season_sort_key)
    last_season = sorted_seasons[-1]
    ranking = ranking_trueskill_por_season[last_season]
    stats = calcular_estadisticas(resultados)

    x_partidos = []
    y_ts = []
    labels = []

    for jug in jugadores:
        partidos_jugados = stats[jug]["partidos_jugados"]
        ts_val = rating_value(ranking[jug])
        x_partidos.append(partidos_jugados)
        y_ts.append(ts_val)
        labels.append(jug)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(x_partidos, y_ts, color="dodgerblue", s=100)
    for i, name in enumerate(labels):
        ax.annotate(name, (x_partidos[i], y_ts[i]),
                    textcoords="offset points", xytext=(5,5), fontsize=9)
    ax.set_xlabel("Partidos Totales")
    ax.set_ylabel("TS Rating (Última Season)")
    ax.set_title("TrueSkill vs. Partidos Totales")
    fig.tight_layout()

    win = tk.Toplevel()
    win.title("Scatter: TrueSkill vs. Partidos Totales")
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

def estadisticas_jugador_detalladas(player):
    ally_data = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0})
    enemy_data = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0})

    for match in resultados:
        eq1, eq2 = match["partido"]
        winner = match["ganador_partido"]
        if player in eq1:
            ally = eq1[1] if eq1[0] == player else eq1[0]
            opp1, opp2 = eq2
            if set(eq1) == set(winner):
                ally_data[ally]["wins"] += 1
                ally_data[ally]["games"] += 1
                enemy_data[opp1]["losses"] += 1
                enemy_data[opp1]["games"] += 1
                enemy_data[opp2]["losses"] += 1
                enemy_data[opp2]["games"] += 1
            else:
                ally_data[ally]["losses"] += 1
                ally_data[ally]["games"] += 1
                enemy_data[opp1]["wins"] += 1
                enemy_data[opp1]["games"] += 1
                enemy_data[opp2]["wins"] += 1
                enemy_data[opp2]["games"] += 1
        elif player in eq2:
            ally = eq2[1] if eq2[0] == player else eq2[0]
            opp1, opp2 = eq1
            if set(eq2) == set(winner):
                ally_data[ally]["wins"] += 1
                ally_data[ally]["games"] += 1
                enemy_data[opp1]["losses"] += 1
                enemy_data[opp1]["games"] += 1
                enemy_data[opp2]["losses"] += 1
                enemy_data[opp2]["games"] += 1
            else:
                ally_data[ally]["losses"] += 1
                ally_data[ally]["games"] += 1
                enemy_data[opp1]["wins"] += 1
                enemy_data[opp1]["games"] += 1
                enemy_data[opp2]["wins"] += 1
                enemy_data[opp2]["games"] += 1

    def ally_ratio(a):
        return a["wins"] / a["games"] if a["games"] > 0 else 0

    # Fiel compañero
    if ally_data:
        ally_list = [(a, d) for a, d in ally_data.items() if d["games"] > 0]
        if ally_list:
            fiel_companero = max(ally_list, key=lambda x: x[1]["games"])
            fiel_companero_name = fiel_companero[0]
            fiel_companero_games = fiel_companero[1]["games"]
        else:
            fiel_companero_name, fiel_companero_games = "N/A", 0
    else:
        fiel_companero_name, fiel_companero_games = "N/A", 0

    # Mejor/Peor aliado
    if ally_data:
        valid_allies = [(ally, info) for ally, info in ally_data.items() if info["games"] > 0]
        if valid_allies:
            best_ally = max(valid_allies, key=lambda item: ally_ratio(item[1]))
            worst_ally = min(valid_allies, key=lambda item: ally_ratio(item[1]))
            mejor_aliado_name = best_ally[0]
            mejor_aliado_ratio = ally_ratio(best_ally[1])
            peor_aliado_name = worst_ally[0]
            peor_aliado_ratio = ally_ratio(worst_ally[1])
        else:
            mejor_aliado_name, mejor_aliado_ratio = "N/A", 0
            peor_aliado_name, peor_aliado_ratio = "N/A", 0
    else:
        mejor_aliado_name, mejor_aliado_ratio = "N/A", 0
        peor_aliado_name, peor_aliado_ratio = "N/A", 0

    # Mayor enemigo, enemigo más débil, archirrival
    enemy_list = [(e, d) for e, d in enemy_data.items() if d["games"] > 0]
    if enemy_list:
        biggest_enemy = max(enemy_list, key=lambda x: x[1]["wins"])
        mayor_enemigo_name = biggest_enemy[0]
        mayor_enemigo_wins = biggest_enemy[1]["wins"]

        weakest_enemy = max(enemy_list, key=lambda x: x[1]["losses"])
        enemigo_mas_debil_name = weakest_enemy[0]
        enemigo_mas_debil_losses = weakest_enemy[1]["losses"]

        archirrival = max(enemy_list, key=lambda x: x[1]["games"])
        archirrival_name = archirrival[0]
        archirrival_games = archirrival[1]["games"]
    else:
        mayor_enemigo_name, mayor_enemigo_wins = "N/A", 0
        enemigo_mas_debil_name, enemigo_mas_debil_losses = "N/A", 0
        archirrival_name, archirrival_games = "N/A", 0

    return {
        "fiel_companero": (fiel_companero_name, fiel_companero_games),
        "mejor_aliado": (mejor_aliado_name, mejor_aliado_ratio),
        "peor_aliado": (peor_aliado_name, peor_aliado_ratio),
        "mayor_enemigo": (mayor_enemigo_name, mayor_enemigo_wins),
        "enemigo_mas_debil": (enemigo_mas_debil_name, enemigo_mas_debil_losses),
        "archirrival": (archirrival_name, archirrival_games),
    }

def mostrar_estadisticas_jugador_avanzadas():
    window = tk.Toplevel()
    window.title("Datos Curiosos por Jugador")
    window.geometry("500x400")

    tk.Label(window, text="Selecciona Jugador:").pack(pady=5)
    player_var = tk.StringVar(value="")
    cb_jugadores = ttk.Combobox(window, textvariable=player_var,
                                values=jugadores, state='readonly')
    cb_jugadores.pack(pady=5)

    stats_text = tk.Text(window, width=60, height=15)
    stats_text.pack(pady=10)

    def on_player_selected(event):
        player = player_var.get()
        if not player:
            return
        info = estadisticas_jugador_detalladas(player)
        fiel_companero_name, fiel_companero_games = info["fiel_companero"]
        mejor_aliado_name, mejor_aliado_ratio = info["mejor_aliado"]
        peor_aliado_name, peor_aliado_ratio = info["peor_aliado"]
        mayor_enemigo_name, mayor_enemigo_wins = info["mayor_enemigo"]
        enemigo_mas_debil_name, enemigo_mas_debil_losses = info["enemigo_mas_debil"]
        archirrival_name, archirrival_games = info["archirrival"]

        mejor_aliado_percent = f"{mejor_aliado_ratio*100:.1f}%" if mejor_aliado_ratio else "0%"
        peor_aliado_percent = f"{peor_aliado_ratio*100:.1f}%" if peor_aliado_ratio else "0%"
        banner = get_banner_for_player(player)

        torneos = torneos_jugador[player]
        total_titulos = trofeos_Liga_jugador[player] + torneos

        texto_final = (
            f"Estadísticas de {player}:\n\n"
            f"  • Fiel compañero: {fiel_companero_name} (juntos {fiel_companero_games} partidos)\n"
            f"  • Mejor aliado: {mejor_aliado_name} (ratio: {mejor_aliado_percent})\n"
            f"  • Peor aliado: {peor_aliado_name} (ratio: {peor_aliado_percent})\n\n"
            f"  • Mayor enemigo: {mayor_enemigo_name} (te ha ganado {mayor_enemigo_wins} veces)\n"
            f"  • Enemigo más débil: {enemigo_mas_debil_name} (le has ganado {enemigo_mas_debil_losses} veces)\n"
            f"  • Archirrival: {archirrival_name} (os habéis enfrentado {archirrival_games} veces)\n\n"
            f"  • Copas de Torneos: {torneos}\n"
            f"  • Total de Títulos (Season + Torneos): {total_titulos}\n\n"
            f"Banner:\n  {banner}\n"
        )
        stats_text.delete("1.0", tk.END)
        stats_text.insert(tk.END, texto_final)

    cb_jugadores.bind("<<ComboboxSelected>>", on_player_selected)

# ---------------------------------
# 12. Interfaz Principal
# ---------------------------------
def actualizar_datos_equipos():
    global parejas, equipos_str, equipo_str_a_pareja
    parejas = list(itertools.combinations(jugadores, 2))
    equipos_str = ["{} & {}".format(j1, j2) for (j1, j2) in parejas]
    equipo_str_a_pareja = dict(zip(equipos_str, parejas))

def crear_interfaz():
    root = tk.Tk()
    root.title("Registrar Resultado de Partido (TrueSkill)")
    root.geometry("900x700")

    style = ttk.Style(root)
    style.theme_use('clam')
    primary_color = '#1E88E5'
    background_color = '#E3F2FD'
    root.configure(bg=background_color)
    style.configure('TButton', font=('Segoe UI', 10), padding=5)
    style.configure('TLabel', font=('Segoe UI', 10))
    style.configure('TCombobox', font=('Segoe UI', 10))

    menu_bar = tk.Menu(root)
    navegacion_menu = tk.Menu(menu_bar, tearoff=0)
    navegacion_menu.add_command(label="Gráfico Jugadores", command=mostrar_grafico_jugadores)
    navegacion_menu.add_command(label="Gráfico Acumulado", command=mostrar_grafico_acumulado)
    navegacion_menu.add_command(label="Heatmap Partidos vs. Ratio", command=mostrar_heatmap_partidos_vs_ratio)
    navegacion_menu.add_command(label="Scatter: TrueSkill vs. Partidos", command=mostrar_scatter_elo_vs_partidos)
    navegacion_menu.add_command(label="Scatter: TrueSkill vs Métricas", command=mostrar_scatter_elo_vs_metricas)
    navegacion_menu.add_command(label="Estadísticas", command=mostrar_estadisticas)
    navegacion_menu.add_command(label="Datos Curiosos", command=mostrar_estadisticas_jugador_avanzadas)
    navegacion_menu.add_command(label="Campeones", command=mostrar_campeones)
    menu_bar.add_cascade(label="Navegación", menu=navegacion_menu)
    root.config(menu=menu_bar)

    tk.Label(root, text="Fecha del Partido (YYYY-mm-dd):", bg=background_color).grid(row=0, column=0, sticky='e')
    fecha_var = DateEntry(root, width=12, background='darkblue', foreground='white',
                          borderwidth=2, date_pattern='y-mm-dd')
    fecha_var.grid(row=0, column=1, pady=5, padx=5)

    tk.Label(root, text="Equipo 1 - Jugador 1:", bg=background_color).grid(row=1, column=0, sticky='e')
    equipo1_j1_var = tk.StringVar()
    equipo1_j1_cb = ttk.Combobox(root, textvariable=equipo1_j1_var, values=jugadores, state='readonly')
    equipo1_j1_cb.grid(row=1, column=1, pady=5, padx=5)

    tk.Label(root, text="Equipo 1 - Jugador 2:", bg=background_color).grid(row=2, column=0, sticky='e')
    equipo1_j2_var = tk.StringVar()
    equipo1_j2_cb = ttk.Combobox(root, textvariable=equipo1_j2_var, values=jugadores, state='readonly')
    equipo1_j2_cb.grid(row=2, column=1, pady=5, padx=5)

    tk.Label(root, text="Equipo 2 - Jugador 1:", bg=background_color).grid(row=3, column=0, sticky='e')
    equipo2_j1_var = tk.StringVar()
    equipo2_j1_cb = ttk.Combobox(root, textvariable=equipo2_j1_var, values=jugadores, state='readonly')
    equipo2_j1_cb.grid(row=3, column=1, pady=5, padx=5)
    tk.Label(root, text="Equipo 2 - Jugador 2:", bg=background_color).grid(row=4, column=0, sticky='e')
    equipo2_j2_var = tk.StringVar()
    equipo2_j2_cb = ttk.Combobox(root, textvariable=equipo2_j2_var, values=jugadores, state='readonly')
    equipo2_j2_cb.grid(row=4, column=1, pady=5, padx=5)
    tk.Label(root, text="Ganador 1er Set:", bg=background_color).grid(row=5, column=0, sticky='e')
    ganador_primer_set_var = tk.StringVar()
    ganador_primer_set_cb = ttk.Combobox(root, textvariable=ganador_primer_set_var,
                                         values=["Equipo 1", "Equipo 2"], state='readonly')
    ganador_primer_set_cb.grid(row=5, column=1, pady=5, padx=5)
    tk.Label(root, text="Ganador Partido:", bg=background_color).grid(row=6, column=0, sticky='e')
    ganador_partido_var = tk.StringVar()
    ganador_partido_cb = ttk.Combobox(root, textvariable=ganador_partido_var,
                                      values=["Equipo 1", "Equipo 2"], state='readonly')
    ganador_partido_cb.grid(row=6, column=1, pady=5, padx=5)
    tk.Label(root, text="MVP:", bg=background_color).grid(row=7, column=0, sticky='e')
    mvp_jugador = ttk.Combobox(root, values=jugadores, state='readonly')
    mvp_jugador.grid(row=7, column=1, pady=5, padx=5)
    set_resultados = {}
    tie_break_vars = {}
    tie_break_scores = {}
    def toggle_tiebreak_entry(num):
        if tie_break_vars[num].get():
            tie_break_scores[num].config(state='normal')
        else:
            tie_break_scores[num].delete(0, tk.END)
            tie_break_scores[num].config(state='disabled')
    for i in range(1, 4):
        tk.Label(root, text=f"Set {i} (ej: 6-4):", bg=background_color).grid(row=7 + i, column=0, sticky='e')
        set_resultados[i] = ttk.Entry(root)
        set_resultados[i].grid(row=7 + i, column=1, pady=5, padx=5)
        tie_break_vars[i] = tk.BooleanVar()
        cb = tk.Checkbutton(root, text="Tie-break", variable=tie_break_vars[i],
                            bg=background_color, command=lambda n=i: toggle_tiebreak_entry(n))
        cb.grid(row=7 + i, column=2, padx=5)
        tk.Label(root, text=f"Puntuación Tie-break Set {i}:", bg=background_color).grid(row=7 + i, column=3, sticky='e')
        tie_break_scores[i] = ttk.Entry(root, state='disabled')
        tie_break_scores[i].grid(row=7 + i, column=4, pady=5, padx=5)
    tk.Label(root, text="Lugar del Partido:", bg=background_color).grid(row=11, column=0, sticky='e')
    lugar_var = tk.StringVar(value="Ibaiondo")
    lugar_menu = ttk.Combobox(root, textvariable=lugar_var, values=["Ibaiondo", "Bakh", "Otro"], state='readonly')
    lugar_menu.grid(row=11, column=1, pady=5, padx=5)
    def registrar_partido():
        eq1j1 = equipo1_j1_var.get()
        eq1j2 = equipo1_j2_var.get()
        eq2j1 = equipo2_j1_var.get()
        eq2j2 = equipo2_j2_var.get()
        if not all([eq1j1, eq1j2, eq2j1, eq2j2]):
            messagebox.showerror("Error", "Faltan jugadores en uno de los equipos.")
            return
        lista_jug = [eq1j1, eq1j2, eq2j1, eq2j2]
        if len(set(lista_jug)) != 4:
            messagebox.showerror("Error", "No se pueden repetir jugadores en el mismo partido.")
            return
        ganador1er = ganador_primer_set_var.get()
        ganadorpart = ganador_partido_var.get()
        if not ganador1er or not ganadorpart:
            messagebox.showerror("Error", "Selecciona ganador de primer set y del partido.")
            return
        g1set_equip = (eq1j1, eq1j2) if ganador1er == "Equipo 1" else (eq2j1, eq2j2)
        gpart_equip = (eq1j1, eq1j2) if ganadorpart == "Equipo 1" else (eq2j1, eq2j2)
        mvp = mvp_jugador.get()
        if not mvp:
            messagebox.showerror("Error", "Selecciona un MVP.")
            return
        fecha_dt = fecha_var.get_date()
        fecha_str = fecha_dt.strftime('%Y-%m-%d')
        season = obtener_season(fecha_str)
        puntuaciones = []
        tie_breaks_total = 0
        for i in range(1, 4):
            set_val = set_resultados[i].get()
            if set_val:
                try:
                    s1, s2 = map(int, set_val.split('-'))
                except:
                    messagebox.showerror("Error", f"Set {i} inválido. Usa formato n-n.")
                    return
                if tie_break_vars[i].get():
                    tb_score = tie_break_scores[i].get()
                    if not tb_score:
                        messagebox.showerror("Error", f"Falta puntaje tie-break en set {i}.")
                        return
                    set_str = f"{s1}-{s2}({tb_score})"
                    tie_breaks_total += 1
                else:
                    set_str = f"{s1}-{s2}"
                puntuaciones.append(set_str)
        resultado = {
            "partido": ((eq1j1, eq1j2), (eq2j1, eq2j2)),
            "ganador_primer_set": g1set_equip,
            "ganador_partido": gpart_equip,
            "mvp": mvp,
            "puntuaciones": puntuaciones,
            "tie_breaks": tie_breaks_total,
            "lugar": lugar_var.get(),
            "fecha": fecha_str,
            "season": season
        }
        resultados.append(resultado)
        guardar_resultado_csv(resultado)
        messagebox.showinfo("OK", "Partido registrado correctamente.")
        equipo1_j1_var.set("")
        equipo1_j2_var.set("")
        equipo2_j1_var.set("")
        equipo2_j2_var.set("")
        ganador_primer_set_var.set("")
        ganador_partido_var.set("")
        mvp_jugador.set("")
        for i in range(1, 4):
            set_resultados[i].delete(0, tk.END)
            tie_break_vars[i].set(False)
            tie_break_scores[i].delete(0, tk.END)
            tie_break_scores[i].config(state='disabled')
    btn_frame = tk.Frame(root, bg=background_color)
    btn_frame.grid(row=12, columnspan=5, pady=10)
    tk.Button(btn_frame, text="Registrar Resultado",
              command=registrar_partido, bg=primary_color, fg='white').grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="Mostrar Ranking (Seasons)",
              command=mostrar_ranking_elo, bg=primary_color, fg='white').grid(row=0, column=1, padx=5)
    tk.Button(btn_frame, text="Mostrar Partidos (Seasons)",
              command=mostrar_partidos, bg=primary_color, fg='white').grid(row=0, column=2, padx=5)
    tk.Button(btn_frame, text="Gestión de Jugadores",
              command=lambda: gestionar_jugadores(), bg=primary_color, fg='white').grid(row=0, column=3, padx=5)
    def gestionar_jugadores():
        w = tk.Toplevel(root)
        w.title("Gestión de Jugadores")
        listbox = tk.Listbox(w)
        listbox.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(w, orient='vertical', command=listbox.yview)
        scroll.pack(side='left', fill='y')
        listbox.config(yscrollcommand=scroll.set)
        def refrescar():
            listbox.delete(0, tk.END)
            for jug in sorted(jugadores):
                listbox.insert(tk.END, jug)
        refrescar()
        def add_jug():
            name = simpledialog.askstring("Nuevo Jugador", "Nombre:")
            if name:
                name = name.strip()
                if name and name not in jugadores:
                    jugadores.append(name)
                    guardar_jugadores()
                    refrescar()
                    actualizar_datos_equipos()
                else:
                    messagebox.showerror("Error", "Jugador ya existe o inválido.")
        def edit_jug():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            old_name = jugadores[idx]
            new_name = simpledialog.askstring("Editar Jugador", "Nuevo nombre:", initialvalue=old_name)
            if new_name:
                new_name = new_name.strip()
                if new_name and new_name not in jugadores:
                    jugadores[idx] = new_name
                    guardar_jugadores()
                    refrescar()
                    actualizar_datos_equipos()
                else:
                    messagebox.showerror("Error", "Jugador ya existe o inválido.")
        def del_jug():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            jug = jugadores[idx]
            if messagebox.askyesno("Confirmar", f"¿Eliminar {jug}?"):
                jugadores.pop(idx)
                guardar_jugadores()
                refrescar()
                actualizar_datos_equipos()
        f_btn = tk.Frame(w)
        f_btn.pack(side='right', fill='y')
        tk.Button(f_btn, text="Agregar", command=add_jug).pack(pady=5)
        tk.Button(f_btn, text="Editar", command=edit_jug).pack(pady=5)
        tk.Button(f_btn, text="Eliminar", command=del_jug).pack(pady=5)
    leer_jugadores()
    leer_resultados()
    actualizar_datos_equipos()
    root.mainloop()

# ---------------------------------
# 13. Lanzar la aplicación
# ---------------------------------
if __name__ == "__main__":
    leer_jugadores()
    leer_resultados()
    leer_torneos()
    crear_interfaz()






