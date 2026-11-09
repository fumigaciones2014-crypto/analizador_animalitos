import sys
import json
import statistics
import os
from collections import Counter
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QComboBox, QMessageBox)
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

# --- 1. CARGA DE DATOS INTELIGENTE ---
def cargar_datos():
    carpeta_actual = os.path.dirname(os.path.abspath(__file__))
    archivos_base = ['mapeo_gua', 'mapeo_lotto', 'mapeo_mini']
    nombres_loterias = ['Guacharo', 'Lotto Activo', 'Guacharito Millonario']
    datos = {}
    
    for nombre, base in zip(nombres_loterias, archivos_base):
        posibles_nombres = [f"{base}.json", f"{base}.json.json", base]
        ruta_encontrada = None
        
        for posible in posibles_nombres:
            ruta_prueba = os.path.join(carpeta_actual, posible)
            if os.path.exists(ruta_prueba):
                ruta_encontrada = ruta_prueba
                break
        
        if ruta_encontrada:
            try:
                with open(ruta_encontrada, 'r', encoding='utf-8') as f:
                    datos[nombre] = json.load(f)
            except Exception as e:
                print(f"Error al leer {ruta_encontrada}: {e}")
                datos[nombre] = []
        else:
            print(f"No se encontró el archivo para {nombre}")
            datos[nombre] = []
            
    return datos

# --- 2. LÓGICA MATEMÁTICA ---
def voltear_numero(num):
    s = str(num)
    if len(s) == 1: return num
    return int(s[::-1])

def analizar_numero_individual(datos_loteria, numero_objetivo):
    historial_numeros = []
    fechas_horas = []
    
    for registro in datos_loteria:
        try:
            num_str = str(registro.get('numero', '')).strip()
            if num_str == '??' or not num_str.isdigit(): continue
            num = int(num_str)
            hora_str = registro.get('hora', '')
            hora_dt = datetime.strptime(hora_str, "%I:%M %p")
            
            hora_decimal = hora_dt.hour + (hora_dt.minute / 60.0)
            
            historial_numeros.append(num)
            fechas_horas.append((registro.get('fecha'), hora_str, num, hora_decimal))
        except Exception:
            continue 

    if not historial_numeros: return None

    indices_apariciones = [i for i, n in enumerate(historial_numeros) if n == numero_objetivo]
    
    if not indices_apariciones:
        return {"num": numero_objetivo, "subidas": 0, "bajadas": 0, "ciclo": 0, "ultima": "No registrado", "fechas_horas": fechas_horas, "prediccion": "Sin datos", "fecha_estimada": "N/A", "dias_retraso": 0, "dias_desde_ultima": 999, "top_atrayentes": [], "franjas": {}, "zona_equilibrio": None, "tendencia_hora": [], "vector_info": {}}

    subidas = 0
    bajadas = 0
    for idx in indices_apariciones:
        if idx > 0:
            if historial_numeros[idx] > historial_numeros[idx-1]: subidas += 1
            elif historial_numeros[idx] < historial_numeros[idx-1]: bajadas += 1

    ciclos = []
    for i in range(1, len(indices_apariciones)):
        try:
            f1 = datetime.strptime(fechas_horas[indices_apariciones[i-1]][0], "%Y-%m-%d")
            f2 = datetime.strptime(fechas_horas[indices_apariciones[i]][0], "%Y-%m-%d")
            dias = (f2 - f1).days
            if dias > 0: ciclos.append(dias)
        except: pass

    promedio_ciclo = round(statistics.mean(ciclos), 1) if ciclos else 0
    ultima_aparicion = fechas_horas[indices_apariciones[-1]]
    ultima_fecha_str = f"{ultima_aparicion[0]} ({ultima_aparicion[1]})"

    prediccion = "Neutro"
    if subidas > bajadas: prediccion = "MAÑANA (Flanco de Bajada)"
    elif bajadas > subidas: prediccion = "TARDE (Flanco de Subida)"

    fecha_est = "N/A"
    dias_retraso = 0
    dias_desde_ultima = 999
    hoy = datetime.now().date()
    
    if promedio_ciclo > 0 and ultima_fecha_str != "No registrado":
        try:
            fecha_base = datetime.strptime(ultima_fecha_str.split(" ")[0], "%Y-%m-%d").date()
            dias_desde_ultima = (hoy - fecha_base).days
            fecha_estimada_dt = fecha_base + timedelta(days=int(round(promedio_ciclo)))
            fecha_est = fecha_estimada_dt.strftime('%Y-%m-%d')
            dias_retraso = (hoy - fecha_estimada_dt).days
        except: pass

    # --- NÚMEROS VECINOS (ANTES Y DESPUÉS UNIFICADOS) ---
    numeros_vecinos = []
    for idx in indices_apariciones:
        if idx - 1 >= 0:
            numeros_vecinos.append(historial_numeros[idx - 1])
        if idx + 1 < len(historial_numeros):
            numeros_vecinos.append(historial_numeros[idx + 1])
            
    conteo_atrayentes = Counter(numeros_vecinos)
    top_atrayentes = conteo_atrayentes.most_common(5)

    tendencia_hora = [fechas_horas[i][3] for i in indices_apariciones]

    # --- ANÁLISIS DE VECTOR Y DIVISIÓN ---
    vector_info = {}
    zona_equilibrio = {}
    
    if len(tendencia_hora) >= 3:
        x_vals = np.arange(1, len(tendencia_hora) + 1)
        y_vals = np.array(tendencia_hora)
        
        # Regresión lineal
        m, b = np.polyfit(x_vals, y_vals, 1)
        
        # Calcular la próxima hora
        proxima_hora_est = m * (len(tendencia_hora) + 1) + b
        proxima_hora_est = max(8, min(20, proxima_hora_est))
        
        if m < -0.1:
            direccion = "DESCENDENTE (Migrando a la Mañana) 🌅"
            color_dir = "#00ffcc"
        elif m > 0.1:
            direccion = "ASCENDENTE (Migrando a la Tarde) 🌇"
            color_dir = "#ffcc00"
        else:
            direccion = "ESTABLE (Se mantiene en su horario) ⏸️"
            color_dir = "#ffffff"
            
        vector_info = {
            "pendiente": round(m, 3),
            "direccion": direccion,
            "color": color_dir,
            "proxima_hora_decimal": proxima_hora_est,
            "proxima_hora_str": f"{int(proxima_hora_est):02d}:{int((proxima_hora_est % 1) * 60):02d}"
        }
        
        # --- DIVISIÓN DEL VECTOR ---
        puntos_debajo = 0
        puntos_encima = 0
        
        for i in range(len(tendencia_hora)):
            hora_real = tendencia_hora[i]
            hora_linea = m * (i + 1) + b
            
            if hora_real < hora_linea:
                puntos_debajo += 1
            elif hora_real > hora_linea:
                puntos_encima += 1
                
        if puntos_debajo < puntos_encima:
            zona_equilibrio = {
                "tipo": "deba",
                "mensaje": "Mitad Inferior (Mañana/Mediodía)",
                "detalle": f"Hay {puntos_debajo} salidas por debajo de la línea vs {puntos_encima} por encima.",
                "color": "#00ffcc",
                "rango": "08:00 AM - 02:00 PM (aprox)"
            }
        elif puntos_encima < puntos_debajo:
            zona_equilibrio = {
                "tipo": "encima",
                "mensaje": "Mitad Superior (Tarde/Noche)",
                "detalle": f"Hay {puntos_encima} salidas por encima de la línea vs {puntos_debajo} por debajo.",
                "color": "#ffcc00",
                "rango": "02:00 PM - 08:00 PM (aprox)"
            }
        else:
            zona_equilibrio = {
                "tipo": "equilibrado",
                "mensaje": "Equilibrio Perfecto",
                "detalle": f"{puntos_debajo} salidas abajo y {puntos_encima} arriba. El vector está balanceado.",
                "color": "#ffffff",
                "rango": "Sin sesgo claro"
            }

    franjas = {
        "08:00 AM - 11:00 AM": 0,
        "11:00 AM - 02:00 PM": 0,
        "02:00 PM - 05:00 PM": 0,
        "05:00 PM - 08:00 PM": 0
    }
    for idx in indices_apariciones:
        h_dec = fechas_horas[idx][3]
        if 8 <= h_dec < 11: franjas["08:00 AM - 11:00 AM"] += 1
        elif 11 <= h_dec < 14: franjas["11:00 AM - 02:00 PM"] += 1
        elif 14 <= h_dec < 17: franjas["02:00 PM - 05:00 PM"] += 1
        elif 17 <= h_dec <= 20: franjas["05:00 PM - 08:00 PM"] += 1

    return {
        "num": numero_objetivo, "subidas": subidas, "bajadas": bajadas, "ciclo": promedio_ciclo,
        "ultima": ultima_fecha_str, "fechas_horas": fechas_horas, "prediccion": prediccion,
        "fecha_estimada": fecha_est, "dias_retraso": dias_retraso, "dias_desde_ultima": dias_desde_ultima,
        "top_atrayentes": top_atrayentes, "franjas": franjas, "zona_equilibrio": zona_equilibrio,
        "tendencia_hora": tendencia_hora, "vector_info": vector_info
    }

# --- NUEVA FUNCIÓN MULTI-CADENA (3 SECUENCIAS) ---
def generar_multiples_secuencias(datos_loteria, numero_inicial, cantidad_cadenas=3):
    cadenas = []
    # Evaluamos los primeros atrayentes para crear diferentes caminos
    res_inicial = analizar_numero_individual(datos_loteria, numero_inicial)
    
    if not res_inicial or not res_inicial['top_atrayentes']:
        return [[numero_inicial]]

    # Tomamos hasta 'cantidad_cadenas' opciones de atrayentes iniciales para diversificar
    opciones_iniciales = [at[0] for at in res_inicial['top_atrayentes'][:cantidad_cadenas]]
    
    for opcion in opciones_iniciales:
        secuencia = [numero_inicial, opcion]
        actual = opcion
        
        # Completamos la cadena hasta tener 4 números
        while len(secuencia) < 4:
            res = analizar_numero_individual(datos_loteria, actual)
            
            if not res or not res['top_atrayentes']:
                break
                
            siguiente = None
            # Buscamos el atrayente más fuerte que NO esté ya en la secuencia
            for num_at, _ in res['top_atrayentes']:
                if num_at not in secuencia:
                    siguiente = num_at
                    break
                    
            if siguiente is None:
                break # No hay más números únicos para continuar
                
            secuencia.append(siguiente)
            actual = siguiente
            
        cadenas.append(secuencia)
        
    # Si por alguna razón no se generaron suficientes cadenas, rellenamos con la original
    if not cadenas:
        cadenas.append([numero_inicial])
        
    return cadenas

def buscar_pendientes_por_dias(datos, loteria_seleccionada, dias_exactos):
    resultados = []
    datos_principales = datos.get(loteria_seleccionada, [])
    if not datos_principales: return resultados

    limite_max = 36 if loteria_seleccionada == 'Lotto Activo' else 99 if loteria_seleccionada == 'Guacharo Millonario' else 75

    for num in range(0, limite_max + 1):
        stats = analizar_numero_individual(datos_principales, num)
        if stats and stats['dias_retraso'] == dias_exactos:
            if stats['subidas'] > stats['bajadas']:
                jornada, color_j = "MAÑANA 🌅", "#00ffcc"
            elif stats['bajadas'] > stats['subidas']:
                jornada, color_j = "TARDE 🌇", "#ffcc00"
            else:
                jornada, color_j = "INDEFINIDA", "#ffffff"
                
            num_inverso = voltear_numero(num)
            sustitucion = False
            if num_inverso != num:
                stats_inv = analizar_numero_individual(datos_principales, num_inverso)
                if stats_inv and stats_inv['dias_desde_ultima'] <= 2: sustitucion = True
                    
            resultados.append((num, stats['fecha_estimada'], stats['ciclo'], stats['subidas'], stats['bajadas'], jornada, color_j, sustitucion, num_inverso))
    return resultados

def modo_automatico_aut(datos, loteria_seleccionada):
    fecha_hoy = datetime.now().date()
    fecha_manana = fecha_hoy + timedelta(days=1)
    numeros_manana, numeros_tarde, numeros_vencidos = [], [], []
    datos_principales = datos.get(loteria_seleccionada, [])
    if not datos_principales: return numeros_manana, numeros_tarde, numeros_vencidos

    try:
        ultima_fecha_data = datetime.strptime(datos_principales[-1]['fecha'], "%Y-%m-%d").date()
        if ultima_fecha_data > fecha_hoy:
            fecha_hoy, fecha_manana = ultima_fecha_data, ultima_fecha_data + timedelta(days=1)
    except: pass

    numeros_recientes = set()
    fecha_limite_reciente = fecha_hoy - timedelta(days=30)
    for reg in datos_principales:
        try:
            f_reg = datetime.strptime(reg['fecha'], "%Y-%m-%d").date()
            if f_reg >= fecha_limite_reciente:
                num_str = str(reg.get('numero', '')).strip()
                if num_str.isdigit(): numeros_recientes.add(int(num_str))
        except: pass

    limite_max = 36 if loteria_seleccionada == 'Lotto Activo' else 99 if loteria_seleccionada == 'Guacharo Millonario' else 75
    pares_procesados = set()
    
    for num in range(0, limite_max + 1): 
        if num not in numeros_recientes: continue
        num_volteado = voltear_numero(num)
        par_id = tuple(sorted([num, num_volteado]))
        if par_id in pares_procesados: continue
        pares_procesados.add(par_id)
        
        stats1 = analizar_numero_individual(datos_principales, num)
        stats2 = analizar_numero_individual(datos_principales, num_volteado) if num != num_volteado else None
        
        total_sub = stats1['subidas'] + (stats2['subidas'] if stats2 else 0)
        total_baj = stats1['bajadas'] + (stats2['bajadas'] if stats2 else 0)
        ciclos_validos = [s['ciclo'] for s in [stats1, stats2] if s and s['ciclo'] > 0]
        ciclo_comb = sum(ciclos_validos) / len(ciclos_validos) if ciclos_validos else 0
        
        fechas = []
        if stats1['ultima'] != "No registrado": fechas.append(stats1['ultima'])
        if stats2 and stats2['ultima'] != "No registrado": fechas.append(stats2['ultima'])
        if not fechas or ciclo_comb == 0: continue
            
        fecha_mas_reciente = sorted(fechas, key=lambda x: datetime.strptime(x.split(" ")[0], "%Y-%m-%d"))[-1]
        try:
            fecha_base = datetime.strptime(fecha_mas_reciente.split(" ")[0], "%Y-%m-%d").date()
            fecha_estimada = fecha_base + timedelta(days=int(round(ciclo_comb)))
            dias_retraso = (fecha_hoy - fecha_estimada).days
        except: continue

        etiqueta = f"{num}/{num_volteado}" if num != num_volteado else str(num)
        if fecha_estimada == fecha_hoy or fecha_estimada == fecha_manana:
            if abs(total_sub - total_baj) >= 1: 
                if total_sub > total_baj: numeros_manana.append((etiqueta, num, num_volteado, fecha_estimada, ciclo_comb, total_sub, total_baj))
                elif total_baj > total_sub: numeros_tarde.append((etiqueta, num, num_volteado, fecha_estimada, ciclo_comb, total_sub, total_baj))
        elif 3 <= dias_retraso <= 15:
            numeros_vencidos.append((etiqueta, num, num_volteado, fecha_estimada, dias_retraso, total_sub, total_baj))
                    
    return numeros_manana, numeros_tarde, numeros_vencidos

# --- 3. INTERFAZ GRÁFICA (PyQt6) ---
class VentanaAnalizador(QMainWindow):
    def __init__(self):
        super().__init__()
        self.datos = cargar_datos()
        self.initUI()
        self.verificar_datos()

    def verificar_datos(self):
        if sum(len(v) for v in self.datos.values()) == 0:
            QMessageBox.warning(self, "Error", "No se pudieron cargar los JSON.")

    def initUI(self):
        self.setWindowTitle("JARVIS - MULTI-ANÁLIZADOR V16")
        self.setGeometry(100, 100, 1100, 850)
        self.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QVBoxLayout(central_widget)

        titulo = QLabel("MAPA CARTESIANO DE DESPLAZAMIENTO Y FLANCOS CÍCLICOS")
        titulo.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet("color: #00aaff; margin-bottom: 10px;")
        layout_principal.addWidget(titulo)

        layout_controles = QHBoxLayout()
        self.combo_loteria = QComboBox()
        self.combo_loteria.addItems(list(self.datos.keys()))
        self.combo_loteria.setStyleSheet("background-color: #444; padding: 5px;")
        
        self.input_numero = QLineEdit()
        self.input_numero.setPlaceholderText("Núm")
        self.input_numero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_numero.setStyleSheet("background-color: #eee; color: #000; padding: 5px; font-weight: bold;")
        self.input_numero.setMaxLength(2)
        self.input_numero.setFixedWidth(60)

        self.btn_proyectar = QPushButton("Proyectar")
        self.btn_proyectar.setStyleSheet("background-color: #003366; color: white; padding: 8px; font-weight: bold;")
        self.btn_proyectar.clicked.connect(self.ejecutar_analisis_manual)

        self.btn_aut = QPushButton("MODO AUT")
        self.btn_aut.setStyleSheet("background-color: #006633; color: white; padding: 8px; font-weight: bold;")
        self.btn_aut.clicked.connect(self.ejecutar_modo_aut)

        self.combo_pendientes = QComboBox()
        self.combo_pendientes.addItems(["Pendientes < 5 Días", "Atrasados 1 día", "Atrasados 2 días", "Atrasados 3 días", "Atrasados 4 días", "Atrasados 5 días"])
        self.combo_pendientes.setStyleSheet("background-color: #551111; color: white; padding: 5px; font-weight: bold;")
        self.combo_pendientes.currentIndexChanged.connect(self.ejecutar_busqueda_pendientes)

        layout_controles.addWidget(QLabel("Lotería:"))
        layout_controles.addWidget(self.combo_loteria)
        layout_controles.addWidget(self.input_numero)
        layout_controles.addWidget(self.btn_proyectar)
        layout_controles.addWidget(self.btn_aut)
        layout_controles.addWidget(self.combo_pendientes)
        layout_principal.addLayout(layout_controles)

        self.fig, self.ax = plt.subplots(figsize=(8, 3), facecolor='#2b2b2b')
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15)
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.canvas = FigureCanvas(self.fig)
        layout_principal.addWidget(self.canvas)

        self.texto_resultados = QTextEdit()
        self.texto_resultados.setReadOnly(True)
        self.texto_resultados.setStyleSheet("background-color: #1e1e1e; color: #00ffcc; font-family: Consolas; font-size: 11pt; border: 1px solid #444;")
        layout_principal.addWidget(self.texto_resultados)

    def actualizar_grafico(self, tendencia_hora, vector_info, zona_equilibrio):
        self.ax.clear()
        self.ax.set_facecolor('#2b2b2b')
        
        if not tendencia_hora:
            self.canvas.draw()
            return

        x_vals = range(1, len(tendencia_hora) + 1)
        y_vals = tendencia_hora
        
        self.ax.plot(x_vals, y_vals, color='#00ffcc', linewidth=1.5, marker='o', markerfacecolor='#2b2b2b', markersize=5, alpha=0.8, zorder=4)
        
        if len(y_vals) > 5 and vector_info:
            x_plot = np.array(x_vals)
            z = np.polyfit(x_plot, y_vals, 1)
            p = np.poly1d(z)
            self.ax.plot(x_plot, p(x_plot), color='#ff00cc', linewidth=2, linestyle='--', zorder=5, label="Tendencia (Vector)")
            
            next_x = len(tendencia_hora) + 1
            next_y = vector_info['proxima_hora_decimal']
            self.ax.scatter([next_x], [next_y], color='#ffff00', s=100, marker='*', zorder=6, label="Próxima Hora Estimada")
            
            self.ax.legend(loc='upper right', facecolor='#2b2b2b', edgecolor='white', labelcolor='white')

        self.ax.set_xlim(1, len(x_vals) + 2)
        self.ax.set_xlabel("Aparición N°", color='white', fontweight='bold')
        
        self.ax.set_ylim(8, 20)
        self.ax.set_yticks([8, 11, 14, 17, 20])
        self.ax.set_yticklabels(['08:00 AM', '11:00 AM', '02:00 PM', '05:00 PM', '08:00 PM'], color='white', fontweight='bold')
        
        self.ax.grid(True, color='#444', linestyle='--', alpha=0.5, zorder=1)
        
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)

        zonas = [
            (8, 11, '#00ffcc', 0.1),
            (11, 14, '#00aa55', 0.1),
            (14, 17, '#ffcc00', 0.1),
            (17, 20, '#ff6600', 0.1),
        ]
        
        for inicio, fin, color, alpha in zonas:
            self.ax.axhspan(inicio, fin, facecolor=color, alpha=alpha, zorder=0)

        self.canvas.draw()

    def ejecutar_analisis_manual(self):
        self.combo_pendientes.setCurrentIndex(0)
        loteria = self.combo_loteria.currentText()
        num_str = self.input_numero.text().strip()
        
        if not num_str.isdigit():
            QMessageBox.warning(self, "Error", "Ingrese un número válido.")
            return
            
        num_original = int(num_str)
        num_volteado = voltear_numero(num_original)
        datos_loteria = self.datos.get(loteria, [])
        
        res_orig = analizar_numero_individual(datos_loteria, num_original)
        res_volt = analizar_numero_individual(datos_loteria, num_volteado) if num_original != num_volteado else None

        if res_orig is None or res_orig['fechas_horas'] is None:
            self.texto_resultados.setText(f"No hay datos válidos.")
            return

        self.actualizar_grafico(res_orig['tendencia_hora'], res_orig['vector_info'], res_orig['zona_equilibrio'])

        texto = f"<h3>Análisis de Flancos para [{num_original}] en {loteria}:</h3>"
        
        texto += f"<div style='background-color: #222; padding: 10px; border-left: 4px solid #00ffcc; margin-bottom: 10px;'>"
        texto += f"<b>Número Solicitado [{num_original}]:</b><br>"
        texto += f"• Flancos: Subidas ({res_orig['subidas']}) | Bajadas ({res_orig['bajadas']})<br>"
        texto += f"• Ciclo Promedio: {res_orig['ciclo']} días<br>"
        texto += f"• Última Aparición: {res_orig['ultima']}<br>"
        
        color_orig = "#ffffff"
        if "MAÑANA" in res_orig['prediccion']: color_orig = "#00ffcc"
        elif "TARDE" in res_orig['prediccion']: color_orig = "#ffcc00"
        
        texto += f"• Proyección: <span style='color: {color_orig}; font-weight: bold;'>{res_orig['prediccion']}</span><br>"
        if res_orig['fecha_estimada'] != "N/A":
            texto += f"• Fecha Estimada: {res_orig['fecha_estimada']}"
            if res_orig['dias_retraso'] > 0:
                 texto += f" <span style='color: #ff5555;'>(Retrasado {res_orig['dias_retraso']} días)</span>"
            elif res_orig['dias_retraso'] == 0:
                 texto += f" <span style='color: #ffff00;'>(Para hoy)</span>"
        texto += f"</div>"

        if res_orig['vector_info']:
            vec = res_orig['vector_info']
            texto += f"<div style='background-color: #112233; padding: 10px; border-left: 4px solid {vec['color']}; margin-bottom: 10px;'>"
            texto += f"<b style='color: {vec['color']};'>🧭 VECTOR DE DESPLAZAMIENTO:</b><br>"
            texto += f"• Dirección: <span style='font-weight: bold; color: {vec['color']};'>{vec['direccion']}</span><br>"
            texto += f"• Pendiente (Fuerza): {vec['pendiente']} (Mientras más lejos de 0, más rápido cambia de horario)<br>"
            texto += f"• <b>Proyección de Próxima Hora (Estrella Amarilla):</b> {vec['proxima_hora_str']}<br>"
            texto += f"<i>Si la tendencia continúa, este es el horario exacto en el que debería aparecer.</i>"
            texto += f"</div>"

        if res_orig['zona_equilibrio']:
            zona_eq = res_orig['zona_equilibrio']
            texto += f"<div style='background-color: #1a1a1a; padding: 10px; border-left: 4px solid {zona_eq['color']}; margin-bottom: 10px;'>"
            texto += f"<b style='color: {zona_eq['color']};'>⚖️ ANÁLISIS DE DIVISIÓN POR VECTOR:</b><br>"
            texto += f"{zona_eq['detalle']}<br>"
            
            if zona_eq['tipo'] == 'equilibrado':
                texto += f"<b>Resultado:</b> El número tiene una distribución perfecta respecto a su línea de tendencia. No hay un sesgo claro.<br>"
            else:
                texto += f"<b>Zona Candidata de Equilibrio:</b> <span style='background-color: {zona_eq['color']}; color: black; padding: 2px 5px; border-radius: 3px; font-weight: bold;'>{zona_eq['mensaje']}</span><br>"
                texto += f"<i>Para mantener la simetría respecto al vector, la próxima salida debería ocurrir en el rango aproximado de {zona_eq['rango']}.</i>"
            
            texto += f"</div>"

        if res_orig['franjas']:
            texto += f"<div style='background-color: #1a1a1a; padding: 10px; border-left: 4px solid #00aaff; margin-bottom: 10px;'>"
            texto += f"<b style='color: #00aaff;'>📊 FRECUENCIA DETALLADA POR FRANJA:</b><br>"
            texto += f"<table style='width: 100%; border-collapse: collapse; margin-top: 5px;'>"
            
            colores_franjas = {
                "08:00 AM - 11:00 AM": "#00ffcc",
                "11:00 AM - 02:00 PM": "#00aa55",
                "02:00 PM - 05:00 PM": "#ffcc00",
                "05:00 PM - 08:00 PM": "#ff6600"
            }
            
            for franja, cant in res_orig['franjas'].items():
                color = colores_franjas[franja]
                texto += f"<tr>"
                texto += f"<td style='padding: 4px;'><div style='width: 15px; height: 15px; background-color: {color}; display: inline-block; border-radius: 3px;'></div></td>"
                texto += f"<td style='padding: 4px;'>{franja}</td>"
                texto += f"<td style='padding: 4px; font-weight: bold; color: {color};'>{cant} veces</td>"
                texto += f"</tr>"
                
            texto += f"</table></div>"

        if res_orig['top_atrayentes']:
            texto += f"<div style='background-color: #1a1a2e; padding: 10px; border-left: 4px solid #ffcc00; margin-bottom: 10px;'>"
            texto += f"<b style='color: #ffcc00;'>🧲 NÚMEROS QUE ATRAE (Basado en el historial):</b><br>"
            texto += f"Cuando sale el <b>{num_original}</b>, los números que más veces han salido <b>justo antes o después</b> son:<br>"
            
            for i, (num_at, cant) in enumerate(res_orig['top_atrayentes']):
                color_rank = "#ffcc00" if i == 0 else "#00ffcc"
                texto += f"• <span style='font-size: 12pt; font-weight: bold; color: {color_rank};'>[{num_at}]</span> (atraído {cant} veces)<br>"
                
            texto += f"</div>"

        # --- NUEVA SECCIÓN: 3 CADENAS DE ATRACCIÓN ---
        cadenas = generar_multiples_secuencias(datos_loteria, num_original, cantidad_cadenas=3)
        if cadenas:
            texto += f"<div style='background-color: #2a1133; padding: 10px; border-left: 4px solid #ff00cc; margin-bottom: 10px;'>"
            texto += f"<b style='color: #ff00cc;'>🔗 TRIPLE CADENA DE ATRACCIÓN (SECUENCIAS PROYECTADAS):</b><br>"
            texto += f"Basado en la conexión directa de los números más atrayentes, estas son las rutas más probables:<br><br>"
            
            colores_secuencia = ["#00ffcc", "#ffcc00", "#ff6600", "#ff00cc"]
            
            for idx_cadena, secuencia_4 in enumerate(cadenas):
                texto += f"<b>Ruta {idx_cadena + 1}:</b> "
                for i, num_sec in enumerate(secuencia_4):
                    color = colores_secuencia[i % len(colores_secuencia)]
                    texto += f"<span style='font-size: 14pt; font-weight: bold; color: {color};'>[{num_sec}]</span>"
                    if i < len(secuencia_4) - 1:
                        texto += f" <span style='color: #888;'>➔</span> "
                texto += f"<br>"
                
            texto += f"<br><i>Estas cadenas muestran los caminos de alta probabilidad. Si un número de la ruta sale, es altamente probable que el siguiente en su misma línea también lo haga.</i>"
            texto += f"</div>"

        if res_volt and res_volt['ultima'] != "No registrado":
            texto += f"<div style='background-color: #222; padding: 10px; border-left: 4px solid #ff00cc; margin-bottom: 10px;'>"
            texto += f"<b>Número Volteado [{num_volteado}]:</b><br>"
            texto += f"• Flancos: Subidas ({res_volt['subidas']}) | Bajadas ({res_volt['bajadas']})<br>"
            texto += f"• Ciclo Promedio: {res_volt['ciclo']} días<br>"
            texto += f"• Última Aparición: {res_volt['ultima']}<br>"
            
            color_volt = "#ffffff"
            if "MAÑANA" in res_volt['prediccion']: color_volt = "#00ffcc"
            elif "TARDE" in res_volt['prediccion']: color_volt = "#ffcc00"
            
            texto += f"• Proyección: <span style='color: {color_volt}; font-weight: bold;'>{res_volt['prediccion']}</span><br>"
            if res_volt['fecha_estimada'] != "N/A":
                texto += f"• Fecha Estimada: {res_volt['fecha_estimada']}"
                if res_volt['dias_retraso'] > 0:
                     texto += f" <span style='color: #ff5555;'>(Retrasado {res_volt['dias_retraso']} días)</span>"
                elif res_volt['dias_retraso'] == 0:
                     texto += f" <span style='color: #ffff00;'>(Para hoy)</span>"
            texto += f"</div>"
        elif num_original == num_volteado:
            texto += f"<p style='color: #888;'>El número es capicúa (se lee igual al revés).</p>"

        texto += "<h3 style='color: #00aaff;'>🧠 LÓGICA DE COMPRENSIÓN AVANZADA:</h3>"
        
        if res_volt and res_volt['ultima'] != "No registrado":
            orig_vencido = res_orig['dias_retraso'] > 0
            volt_reciente = res_volt['dias_retraso'] <= 0
            volt_vencido = res_volt['dias_retraso'] > 0
            orig_reciente = res_orig['dias_retraso'] <= 0
            
            if orig_vencido and volt_reciente:
                texto += f"<div style='background-color: #331111; padding: 10px; border: 1px solid #ff5555; margin-bottom: 10px;'>"
                texto += f"<b style='color: #ff5555;'>¡EFECTO ESPEJO DETECTADO!</b><br>"
                texto += f"El número <b>{num_original}</b> está vencido (debía salir hace {res_orig['dias_retraso']} días). "
                texto += f"La lotería ha estado enviando su invertido, el <b>{num_volteado}</b>, para negar su salida. "
                texto += f"Es altamente probable que liberen al <b>{num_original}</b> pronto."
                texto += f"</div>"
            elif volt_vencido and orig_reciente:
                texto += f"<div style='background-color: #331111; padding: 10px; border: 1px solid #ff5555; margin-bottom: 10px;'>"
                texto += f"<b style='color: #ff5555;'>¡EFECTO ESPEJO DETECTADO!</b><br>"
                texto += f"El número <b>{num_volteado}</b> está vencido. La lotería está usando al <b>{num_original}</b> como pantalla."
                texto += f"</div>"
            elif res_orig['dias_retraso'] <= 1 and res_volt['dias_retraso'] <= 1:
                if res_orig['prediccion'] == res_volt['prediccion'] and "Neutro" not in res_orig['prediccion']:
                    jornada = "MAÑANA 🌅" if "MAÑANA" in res_orig['prediccion'] else "TARDE 🌇"
                    texto += f"<div style='background-color: #113311; padding: 10px; border: 1px solid #00ffcc; margin-bottom: 10px;'>"
                    texto += f"<b style='color: #00ffcc;'>¡SINERGIA DE FLANCOS!</b><br>"
                    texto += f"Ambos números apuntan a la <b>{jornada}</b>. Señal de alta probabilidad."
                    texto += f"</div>"
                else:
                    texto += f"<div style='background-color: #332b11; padding: 10px; border: 1px solid #ffaa00; margin-bottom: 10px;'>"
                    texto += f"<b style='color: #ffaa00;'>TRAMPA DE FLANCOS</b><br>"
                    texto += f"Uno apunta a Mañana y otro a Tarde. Juega el de <b>ciclo más corto</b>."
                    texto += f"</div>"
            elif "Neutro" not in res_orig['prediccion'] or "Neutro" not in res_volt['prediccion']:
                 texto += f"<p style='font-size: 12pt; color: #ccc;'>El flanco dominante lo tiene el número <b>[{num_original if 'Neutro' not in res_orig['prediccion'] else num_volteado}]</b> apuntando a <b>{res_orig['prediccion'] if 'Neutro' not in res_orig['prediccion'] else res_volt['prediccion']}</b>.</p>"
            else:
                texto += f"<p style='color: #888;'>No se detectan patrones claros. Los números están en equilibrio.</p>"
        else:
            if res_orig['dias_retraso'] > 0:
                 texto += f"<div style='background-color: #331111; padding: 10px; border: 1px solid #ff5555; margin-bottom: 10px;'>"
                 texto += f"<b style='color: #ff5555;'>NÚMERO VENCIDO SIN ESPEJO</b><br>"
                 texto += f"El número tiene {res_orig['dias_retraso']} días de retraso. Su volteado no tiene actividad. Candidato fuerte."
                 texto += f"</div>"
            else:
                 texto += f"<p style='font-size: 12pt;'>Proyección única para <b>[{num_original}]</b>: <b>{res_orig['prediccion']}</b>.</p>"

        self.texto_resultados.setHtml(texto)

    def ejecutar_busqueda_pendientes(self, index):
        if index == 0: return
        dias_buscados = index
        loteria = self.combo_loteria.currentText()
        self.texto_resultados.clear()
        resultados = buscar_pendientes_por_dias(self.datos, loteria, dias_buscados)
        
        texto = f"<h3>⏳ NÚMEROS ATRASADOS {dias_buscados} DÍAS ({loteria})</h3>"
        texto += f"<p>Números que debieron salir hace exactamente <b>{dias_buscados} días</b> según su ciclo promedio.</p>"
        
        if resultados:
            resultados.sort(key=lambda x: x[0])
            texto += "<ul>"
            for num, f_est, ciclo, sub, baj, jornada, color_j, sustitucion, num_inv in resultados:
                texto += f"<li style='margin-bottom: 12px;'>"
                texto += f"<b style='font-size: 14pt; color: #00ffcc;'>[{num}]</b> - Debía salir el: <b>{f_est}</b><br>"
                texto += f"<span style='color: #ccc;'>Ciclo: {ciclo} días | Flancos: Sub({sub}) / Baj({baj})</span><br>"
                
                if sustitucion:
                    texto += f"Probable Salida: <span style='color: {color_j}; font-weight: bold;'>{jornada}</span><br>"
                    texto += f"<span style='background-color: #551111; color: #ff5555; padding: 3px; border-radius: 3px; font-size: 9pt; display: inline-block; margin-top: 4px;'>"
                    texto += f"⚠️ SUSTITUCIÓN DETECTADA: Salieron con su inverso [{num_inv}]"
                    texto += f"</span>"
                else:
                    texto += f"Probable Salida: <span style='color: {color_j}; font-weight: bold;'>{jornada}</span>"
                texto += f"</li>"
            texto += "</ul>"
        else:
            texto += f"<p style='color: #ffaa00;'>No se encontraron números con {dias_buscados} día(s) de retraso.</p>"
            
        self.texto_resultados.setHtml(texto)
        
        self.ax.clear()
        self.ax.set_facecolor('#2b2b2b')
        categorias = ['Mañana', 'Tarde', 'Indefinidos']
        m_count = sum(1 for r in resultados if "MAÑANA" in r[5])
        t_count = sum(1 for r in resultados if "TARDE" in r[5])
        i_count = sum(1 for r in resultados if "INDEFINIDA" in r[5])
        valores = [m_count, t_count, i_count]
        colores = ['#00ffcc', '#ffcc00', '#888888']
        max_visual = max(valores) if max(valores) > 0 else 5
        self.ax.bar(categorias, valores, color=colores)
        self.ax.set_ylim(0, max_visual + 2) 
        self.ax.tick_params(colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.grid(True, color='#444', linestyle='--', alpha=0.5, axis='y')
        self.canvas.draw()

    def ejecutar_modo_aut(self):
        self.combo_pendientes.setCurrentIndex(0)
        self.texto_resultados.clear()
        loteria_seleccionada = self.combo_loteria.currentText()
        fecha_actual_str = datetime.now().strftime("%Y-%m-%d")
        self.texto_resultados.append(f"Iniciando Barrido Matemático para {loteria_seleccionada}...\n")
        
        nums_manana, nums_tarde, nums_vencidos = modo_automatico_aut(self.datos, loteria_seleccionada)
        
        texto = f"<h3>🤖 ESCANEO AUTOMÁTICO: {loteria_seleccionada.upper()}</h3>"
        texto += f"<p>Filtro aplicado para el día de hoy ({fecha_actual_str}) y mañana. Se incluyen números volteados.</p>"
        
        texto += "<h4 style='color: #00ffcc;'>🌅 Proyectados para la MAÑANA (Antes de 12 PM):</h4>"
        if nums_manana:
            nums_manana.sort(key=lambda x: x[0]) 
            lista_m = "<br>".join([f"• <b>[{et}]</b> - Estimado: {f.strftime('%Y-%m-%d')} | Ciclo: {c:.1f} días | Sub: {s} / Baj: {b}" for et, n, nv, f, c, s, b in nums_manana])
            texto += f"<p style='font-size: 11pt;'>{lista_m}</p>"
        else:
            texto += "<p style='color: #888;'>Ningún número cumple con los filtros para la mañana.</p>"

        texto += "<br><h4 style='color: #ffcc00;'>🌇 Proyectados para la TARDE (Después de 12 PM):</h4>"
        if nums_tarde:
            nums_tarde.sort(key=lambda x: x[0])
            lista_t = "<br>".join([f"• <b>[{et}]</b> - Estimado: {f.strftime('%Y-%m-%d')} | Ciclo: {c:.1f} días | Sub: {s} / Baj: {b}" for et, n, nv, f, c, s, b in nums_tarde])
            texto += f"<p style='font-size: 11pt;'>{lista_t}</p>"
        else:
            texto += "<p style='color: #888;'>Ningún número cumple con los filtros para la tarde.</p>"

        texto += "<br><h4 style='color: #ff5555;'>⚠️ Números Vencidos (3 a 15 días de retraso):</h4>"
        if nums_vencidos:
            nums_vencidos.sort(key=lambda x: x[4], reverse=True) 
            lineas_vencidos = []
            for et, n, nv, f, d, s, b in nums_vencidos[:15]: 
                if s > b:
                    hora_probable = "LA TARDE 🌇"
                    color_hora = "#ffcc00"
                elif b > s:
                    hora_probable = "LA MAÑANA 🌅"
                    color_hora = "#00ffcc"
                else:
                    hora_probable = "CUALQUIER HORA"
                    color_hora = "#ffffff"
                linea = f"• <b>[{et}]</b> - Debía salir: {f.strftime('%Y-%m-%d')} | Retraso: {d} días | (Sub: {s} / Baj: {b}) | <span style='color: {color_hora};'><b>Posible Aparición en {hora_probable}</b></span>"
                lineas_vencidos.append(linea)
            texto += f"<p style='font-size: 11pt;'>{'<br>'.join(lineas_vencidos)}</p>"
            if len(nums_vencidos) > 15:
                texto += f"<p style='color: #888; font-size: 10pt;'>... y {len(nums_vencidos)-15} números más con retraso.</p>"
        else:
            texto += "<p style='color: #888;'>No hay números con retraso significativo.</p>"
            
        texto += "<br><hr><p><i>Nota: El análisis de vencidos ignora números sin actividad en los últimos 30 días. Los pares de números volteados se analizan en conjunto.</i></p>"
        self.texto_resultados.setHtml(texto)
        
        self.ax.clear()
        self.ax.set_facecolor('#2b2b2b')
        categorias = ['Mañana', 'Tarde', 'Vencidos']
        valores = [len(nums_manana), len(nums_tarde), len(nums_vencidos)]
        colores = ['#00ffcc', '#ffcc00', '#ff5555']
        max_visual = max(valores) if max(valores) > 0 else 5
        self.ax.bar(categorias, valores, color=colores)
        self.ax.set_ylim(0, max_visual + 2) 
        self.ax.tick_params(colors='white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.grid(True, color='#444', linestyle='--', alpha=0.5, axis='y')
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    app.setPalette(palette)

    ventana = VentanaAnalizador()
    ventana.show()
    sys.exit(app.exec())