#Librerías utilizadas para ejecutar el programa
import pandas as pd
import numpy as np
from datetime import timedelta
import base64
from weasyprint import HTML
import geopandas as gpd
import matplotlib.pyplot as plt 
import plotly.express as px 

class Infosis():
    #Ocupamos una clase para estructurar la informacion de nuestra base datos.
    
    def __init__(self): #El constructor __init__ recibe el archivo CSV convertido ya en DataFrame.
        self.data_sis = None       # DataFrame con columnas de tiempo separadas por año, mes, día, etc.
        self.data_sis_time = None  # DataFrame con dateTime original ordenado
        self.elam = None           # Energía total liberada por año
        self.emed = None           # Energía media liberada por año
        self.amayem = None         # Años de mayor energía liberada
        self.tiempo = None         # Diferencia promedio de tiempo entre sismos
        self.name_csv = ""         # Guardar el nombre del archivo para reutilizarlo
    
    def _transformar_a_geodataframe(self, df):
        # Convierte un DataFrame normal a GeoDataFrame usando Lat/Long.
        # Toma las columnas de números del DataFrame (longitude y latitude) 
        # y las transforma en  grados de longitud y latitud.
        gdf = gpd.GeoDataFrame(
            df,
            geometry = gpd.points_from_xy(df['longitude'], df['latitude']),
            crs = "EPSG:4326"
        )
        return gdf

    def _graficar_con_geopandas(self, gdf, bbox=None, nombre_salida="sismos_global.jpg", titulo="Análisis Sísmico"):
        #Dibuja el mapa de fondo y encima plotea los sismos.
        fig, ax = plt.subplots(figsize=(14, 7))

        # Carga de mapas del repositorio GitHub, leyendo los datos geográficos con geopandas
        url_mundo = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
        mundo = gpd.read_file(url_mundo)  
        mundo.plot(ax = ax, color = 'lightgray', edgecolor = 'white')
        
        #Se utiliza un bloque TRY-EXCEPT para verificar que esté el archivo JSON con los límites interprovinciales de argentina.
        try:
            provincias = gpd.read_file("provincias.geojson")
            provincias.plot(ax = ax, color = 'gray', edgecolor = 'white')
        except Exception:
            pass # Si no están los archivos locales de provincias, continúa unicamente con el mapa mundial

        # Modulamos los tamaños de los círculos (sismos) para la escala visual
        escalado_tamaños = gdf['mag'] ** 2.5

        # Graficamos los sismos encima
        scatter = ax.scatter(
            gdf.geometry.x,
            gdf.geometry.y,
            s = escalado_tamaños,
            c = gdf['depth'],
            cmap = "magma_r",
            alpha = 0.75,
            edgecolors = 'black',
            linewidth = 0.20,
            zorder = 3
        )

        # Ajustes estéticos y acotación de ejes
        ax.set_title(titulo, fontsize=15, fontweight='bold')
        if bbox:
            #bbox significa Bounding Box (caja de delimitación). 
            #Es una lista con 4 coordenadas: [lon_min, lon_max, lat_min, lat_max].
            #Si se le pasa un bbox (los límites del área de estudio),
            #el código recorta el mapa y hace zoom exclusivamente en esa zona exacta.
            ax.set_xlim(bbox[0], bbox[1])
            ax.set_ylim(bbox[2], bbox[3])
        else:
            #Sino, se grafica todo el planisferio
            ax.set_xlim(-180, 180)
            ax.set_ylim(-90, 90)
            
        # Se rotulan los ejes cartesianos.
        ax.set_xlabel("Longitud (Grados)")
        ax.set_ylabel("Latitud (Grados)")

        # Barra de color para la profundidad
        cbar = fig.colorbar(scatter, ax = ax, shrink = 0.6)
        cbar.set_label("Profundidad (km)", fontsize = 11)

        # Leyenda manual para los tamaños de magnitud
        for mag in [4.5, 6.5, 8.5]:
            ax.scatter([], [], c = 'gray', alpha = 0.2, s = mag**2.5, label = f'M {mag}', edgecolors = 'black')
        ax.legend(title = "Magnitud", loc = "lower left", frameon = True)

        #Se utiliza libreria MatPlotLib para graficar
        plt.tight_layout() #Ajusta los márgenes automáticamente.
        plt.savefig(nombre_salida, dpi = 300) #Guarda el gráfico como una imagen de alta calidad ()
        return fig, ax

    def _graficar_sismos_3d_interactivo(self, df):
        # Crea un cubo interactivo 3D usando la librería Plotly Express.
        #Antes de ejecutar algo se corrobora que el DataFrame no esté vacío.
        if df.empty:
            print("⚠️ Error: El DataFrame está vacío. Revisa las coordenadas de filtrado.")
            return

        df['tamaño_visual'] = df['mag'] ** 3 #Se aumenta el tamaño de la magnitud para poder graficar los puntos(sismos).
        #Configuraciones para el gráfico.
        fig = px.scatter_3d(
            df,
            x = 'longitude',
            y = 'latitude',
            z = 'depth',
            color = 'depth',
            size = 'tamaño_visual',
            hover_data = {'mag': True, 'depth': ':.1f', 'tamaño_visual': False},
            title = 'Visualización 3D Interactiva de Sismicidad (Zonas de Subducción)',
            labels={'longitude': 'Longitud (°)', 'latitude': 'Latitud (°)', 'depth': 'Profundidad (km)'},
            color_continuous_scale='magma_r',
            opacity=0.8
        )

        fig.update_scenes(
            zaxis=dict(autorange="reversed"), #Como la profundidad aumenta hacia abajo, se invierte la direccion del eje z.
            xaxis_backgroundcolor="rgba(240, 240, 240, 0.5)",
            yaxis_backgroundcolor="rgba(240, 240, 240, 0.5)",
            zaxis_backgroundcolor="rgba(220, 220, 220, 0.5)"
        )
        fig.update_traces(marker=dict(sizeref=2, sizemode='area', line=dict(width=1, color='DarkSlateGrey')))
        fig.update_layout(margin=dict(l=0, r=0, b=0, t=40))

        #Guarda el gráfico como imagen en formato .png y luego lo muestra en pantalla.
        fig.write_image("grafico_sismos_3D.png", width=1200, height=800, scale=2)
        print("Gráfico estático guardado con éxito como 'grafico_sismos_3D.png'")
        fig.show()

    def carga_y_analisis_csv(self):
        self.name_csv = input("Ingrese el nombre del archivo CSV de la base de datos (sin .csv): ")
        sismos = pd.read_csv(f"{self.name_csv}.csv")
        sismos = sismos.drop_duplicates()
        
        columnas_a_borrar = ["nst", "gap", "dmin","rms","horizontalError","depthError","magType","net","updated","type","magError","magNst","status","locationSource","magSource"]
        columnas_existentes = [col for col in columnas_a_borrar if col in sismos.columns]
        sismos = sismos.drop(columnas_existentes, axis=1)
    
        self.data_sis = sismos.copy()
        self.data_sis_time = sismos.copy()

        self.data_sis["time"] = pd.to_datetime(sismos["time"], format='mixed')
        self.data_sis["año"] = self.data_sis["time"].dt.year
        self.data_sis["mes"] = self.data_sis["time"].dt.month
        self.data_sis["dia"] = self.data_sis["time"].dt.day
        self.data_sis["hora"] = self.data_sis["time"].dt.hour
        self.data_sis["minuto"] = self.data_sis["time"].dt.minute
        self.data_sis["segundo"] = self.data_sis["time"].dt.second
        self.data_sis = self.data_sis.drop(columns=["time"])
        self.data_sis["energia_J"] = 10**(1.5 * self.data_sis["mag"] + 4.8)

        self.elam = self.data_sis.groupby("año")["energia_J"].sum().reset_index()
        self.emed = self.data_sis.groupby("año").agg(energia_media=("energia_J", "mean")).reset_index()
        self.amayem = self.elam[self.elam["energia_J"] > 1.000000e+18]

        self.data_sis_time["time"] = pd.to_datetime(self.data_sis_time["time"], format='mixed')
        self.data_sis_time = self.data_sis_time.sort_values("time")
        sis_moderno = self.data_sis_time[self.data_sis_time['time'] >= '2010-01-01'].copy()
        
        if not sis_moderno.empty:
            sis_moderno["dt_segundos"] = sis_moderno["time"].diff().dt.total_seconds()
            promedio_segundos = sis_moderno["dt_segundos"].mean()
            self.tiempo = timedelta(seconds=promedio_segundos)
        else:
            self.tiempo = timedelta(seconds=0)
        
    def informe_tierra(self): 
        
        print("\nGenerando Gráfico Global...")
        gdf_global = self._transformar_a_geodataframe(self.data_sis_time)
        fig, ax = self._graficar_con_geopandas(gdf_global, nombre_salida="sismos_global.jpg", titulo="Análisis Sísmico Global - Magnitud y Profundidad")

        # Codificamos el gráfico en base64 para meterlo al HTML/PDF de la librería WeasyPrint
        # El siguiente bloque de código convierte la imagen del mapa en texto puro, 
        # lo que permite incrustar la imagen directamente dentro del código HTML 
        # sin depender de un archivo externo guardado en tu computadora.
        with open("sismos_global.jpg", "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Calculamos la profundidad promedio de los megaterretomos registrados en la base de datos.
        años_con_alta_energia = self.amayem["año"].unique()
        mag_may_años = self.data_sis[
            (self.data_sis["año"].isin(años_con_alta_energia)) & (self.data_sis["mag"] > 8.5)
        ]
        depth_mean = mag_may_años["depth"].mean() if not mag_may_años.empty else 0

        # Se clasifica al promedio de sismos según su profundidad.
        if depth_mean < 70:
            depth = "Corticales"
        elif 70 <= depth_mean < 300:
            depth = "Intermedios"
        else:
            depth = "Profundos"

        # Se filtran los datos de interes del DataFrame y designamos nuevas variables.
        tabla_sismos_m8 = mag_may_años[["place", "año", "mag", "depth"]]

        # .to_html(...) sirve para convertir esas variables a formato HTML,
        # también se les da a las mismas formato de tabla.
        html_tabla_2 = self.elam.to_html(index=False, classes="tabla-datos")
        html_tabla_4 = self.amayem.to_html(index=False, classes="tabla-datos")
        html_tabla_5 = tabla_sismos_m8.to_html(index=False, classes="tabla-datos")

        # Utiliza un f-string de Python para armar toda la estructura de una página web HTML.

        html_documento = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 20mm 15mm; }}
            body {{ font-family: 'Arial', sans-serif; color: #2c3e50; line-height: 1.6; font-size: 11pt; }}
            h1 {{ color: #1f3a52; text-transform: uppercase; border-bottom: 2px solid #1f3a52; padding-bottom: 5px; }}
            .punto {{ margin-bottom: 25px; }}
            .num {{ font-weight: bold; color: #1f3a52; }}
            table.tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 15px; font-size: 10pt; }}
            table.tabla-datos th {{ background-color: #1f3a52; color: white; text-align: left; padding: 8px; font-weight: bold; }}
            table.tabla-datos td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; }}
            table.tabla-datos tr:nth-child(even) {{ background-color: #f8fafc; }}
            .contenedor-mapa {{ text-align: center; margin-top: 25px; page-break-before: always; }}
            .mapa {{ width: 100%; height: auto; display: block; margin: 0 auto; }}
        </style>
        </head>
        <body>
            <h1>Reporte de Análisis Sísmico</h1>
            <p>Datos analizados sobre sismos de magnitud a partir de 4.5 a escala global desde 1964:</p>
            
            <div class="punto">
                <span class="num">1)</span> Cada {str(self.tiempo).split('.')[0]} ocurre un sismo de magnitud mayor a 4.5 en la escala de Richter.
            </div>
            <div class="punto">
                <span class="num">2)</span> Total de energía liberada en forma de ondas sísmicas por año a escala global:
                {html_tabla_2}
            </div>
            <div class="punto">
                <span class="num">4)</span> Años de mayor energía liberada en forma de ondas sísmicas:
                {html_tabla_4}
            </div>
            <div class="punto">
                <span class="num">5)</span> Megaterremotos de los años de mayor liberación energética:
                {html_tabla_5}
            </div>
            <div class="punto">
                <span class="num">6)</span> Profundidad promedio de los terremotos antes mencionados: <strong>{depth_mean:.2f} km</strong>, particularmente a esa profundidad los sismos se clasifican como <strong>{depth}</strong>.
            </div>

            <div class="contenedor-mapa">
                <h2>Distribución Sísmica Global</h2>
                <img class="mapa" src="data:image/jpeg;base64,{img_base64}" alt="Mapa Global">
            </div>
        </body>
        </html>
        """
        # se invoca a WeasyPrint (HTML(string=...).write_pdf(...)) 
        # para compilar el código en un archivo PDF con un diseño específico.
        HTML(string=html_documento).write_pdf("reporte_sismos_global.pdf")
        print("El PDF con el análisis global e imagen integrada de gran tamaño fue generado con éxito.")
        
        # Pregunta interactiva para abrir el gráfico 2D en ventana de Matplotlib
        # Se utiliza .lower() para evitar problemas si se utiliza Mayuscula o no.
        rta_2d = input("¿Desea observar la distribución global de los sismos en forma interactiva 2D? (s/n): ").lower()
        if rta_2d == "s":
            plt.figure(fig.number)
            plt.show()
        else:
            print("Entendido. Continuando al informe regional.")
        plt.close('all') # Cierra y borrar de la memoria de la computadora todas las figuras de Matplotlib que se crearon durante la ejecución del programa.
    
    def informe_area(self):
        # Esta función, actúa de una manera muy similar a la anterior.
        # La diferencia entre ambas radica en que antes de comenzar, se filtran los datos a utilizar del 
        # data frame para una región específica
        print("\nIndique ubicación y rango de profundidades del área de estudio. \n Se guardará un informe en formato PDF.")
        area = input("Ingrese el nombre del área, región, país o provincia: ")

        lat1 = float(input("Ingrese la latitud máxima: "))
        lat2 = float(input("Ingrese la latitud mínima: "))
        long1 = float(input("Ingrese la longitud máxima: "))
        long2 = float(input("Ingrese la longitud mínima: "))
        depth_limit1 = float(input("Ingrese la profundidad mínima (km): "))
        depth_limit2 = float(input("Ingrese la profundidad máxima (km): "))

        # 1. Filtrado por coordenadas
        sismos_area = self.data_sis_time[
            self.data_sis_time["latitude"].between(lat2, lat1) & 
            self.data_sis_time["longitude"].between(long2, long1)
        ].copy()

        sismos_area["año"] = sismos_area["time"].dt.year
        sismos_area["energia_J"] = 10 ** (1.5 * sismos_area["mag"] + 4.8)

        # Filtro de profundidad
        sismos_area_depth = sismos_area[
            (sismos_area["depth"] > depth_limit1) & (sismos_area["depth"] < depth_limit2)
        ].copy()

        # Generar gráfico regional acotado para incluirlo en el PDF
        print(f"Generando gráfico regional acotado para {area}...")
        gdf_regional = self._transformar_a_geodataframe(sismos_area_depth)
        
        # configuración del gráfico del área de estudio.
        # Márgenes para la visualización del grafico utilizando bbox y configuración del nombre del gráfico. 
        bbox = [long2 - 2, long1 + 2, lat2 - 2, lat1 + 2]
        nombre_grafico_area = f"sismos_{area.lower().replace(' ', '_')}.jpg"
        self._graficar_con_geopandas(gdf_regional, bbox=bbox, nombre_salida=nombre_grafico_area, titulo=f"Sismicidad Regional: {area}")

        # Codificar mapa regional a base64 para incluirlo en el PDF.
        with open(nombre_grafico_area, "rb") as img_file:
            img_reg_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        # 2. Calculamos el tiempo promedio que transcurre entre un sismo y el siguiente (Para ello se utiliza diff()).
        # Se filtran los datos a partir de 2010 por la disponibilidad de información.
        # Se devuelve el resultado en un formato de tiempo en segundos, que posteriormente se transforma 
        # en dias,horas, minutos y segundos .
        sis_area_moderno = sismos_area_depth[sismos_area_depth["año"] >= 2010].copy()
    
        if not sis_area_moderno.empty and len(sis_area_moderno) > 1:
            sis_area_moderno["dt_segundos"] = sis_area_moderno["time"].diff().dt.total_seconds()
            promedio_segundos = sis_area_moderno["dt_segundos"].mean()
            tiempo_promedio = str(timedelta(seconds=promedio_segundos)).split(".")[0]
        #.split(".")[0]: Elimina los milisegundos finales del texto para que el reporte muestre un número sin decimales.
        else:
            tiempo_promedio = "No hay datos suficientes desde 2010"

        # 3. Comparación de energía anual promedio en la region y estadísticas a partir de cálculos matemáticos.
        energy_lib_año_area = sismos_area.groupby("año")["energia_J"].sum().reset_index()
        energy_lib_año_area_depth = sismos_area_depth.groupby("año")["energia_J"].sum().reset_index()

        
        total_energia_mundo = np.sum(self.elam["energia_J"].to_numpy())
        total_energia_area = np.sum(energy_lib_año_area["energia_J"].to_numpy()) if not energy_lib_año_area.empty else 0
        total_energia_area_depth = np.sum(energy_lib_año_area_depth["energia_J"].to_numpy()) if not energy_lib_año_area_depth.empty else 0
        
        porcentaje_energia_area = (total_energia_area / total_energia_mundo) * 100 if total_energia_mundo > 0 else 0
        porcentaje_energia_area_depth = (total_energia_area_depth / total_energia_mundo) * 100 if total_energia_mundo > 0 else 0

        # 4. Estadísticas históricas
        sismos_filtrados_menos_años = sismos_area_depth[sismos_area_depth["año"] > 1964]

        if not sismos_filtrados_menos_años.empty:
            sismos_por_año_area = sismos_filtrados_menos_años.groupby("año").size().reset_index(name="cantidad")
            promedio_año_area = sismos_por_año_area["cantidad"].mean()
            html_tabla_cantidades = sismos_por_año_area.to_html(index=False, classes="tabla-datos")
        else:
            promedio_año_area = 0
            html_tabla_cantidades = "<p>No se registraron sismos en este rango de años.</p>"

        # 5. Estructura HTML
        html_documento = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 20mm 15mm; }}
            body {{ font-family: 'Arial', sans-serif; color: #2c3e50; line-height: 1.6; font-size: 11pt; }}
            h1 {{ color: #e67e22; text-transform: uppercase; border-bottom: 2px solid #e67e22; padding-bottom: 8px; margin-bottom: 20px; }}
            .destaque {{ background-color: #fdf2e9; border-left: 4px solid #e67e22; padding: 15px; margin-bottom: 25px; }}
            .punto {{ margin-bottom: 25px; }}
            .num {{ font-weight: bold; color: #e67e22; font-size: 12pt; }}
            table.tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 12px; margin-bottom: 12px; font-size: 10pt; }}
            table.tabla-datos th {{ background-color: #e67e22; color: white; text-align: left; padding: 10px; font-weight: bold; }}
            table.tabla-datos td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
            table.tabla-datos tr:nth-child(even) {{ background-color: #fdfefe; }}
            .contenedor-mapa {{ text-align: center; margin-top: 25px; page-break-before: always; }}
            .mapa {{ width: 100%; height: auto; display: block; margin: 0 auto; }}
        </style>
        </head>
        <body>
            <h1>Reporte Sísmico Regional: {area}</h1>
            
            <div class="destaque">
                <strong>Parámetros del Área Analizada:</strong><br>
                Coordenadas: Latitudes [{lat2} a {lat1}] | Longitudes [{long2} a {long1}]<br>
                Profundidad mínima: {depth_limit1} km | Profundidad máxima: {depth_limit2} km
            </div>

            <div class="punto">
                <span class="num">1)</span> Cada <strong>{tiempo_promedio}</strong> ocurre un sismo de magnitud mayor a 4.5 en la escala de Richter.
                <br><small>Nota: precaución, dato medido utilizando métricas desde el año 2010.</small>
            </div>
            <div class="punto">
                <span class="num">2)</span> Cantidad de sismos registrados por año en {area}:
                {html_tabla_cantidades}
            </div>
            <div class="punto">
                <span class="num">3)</span> Se esperan en promedio <strong>{promedio_año_area:.2f}</strong> sismos por año.
            </div>
            <div class="punto">
                <span class="num">4)</span> En el área indicada se libera el <strong>{porcentaje_energia_area:.4f}%</strong> del total de la energía mundial. A la profundidad indicada, únicamente se libera el <strong>{porcentaje_energia_area_depth:.4f}%</strong>.
            </div>

            <div class="contenedor-mapa">
                <h2>Mapa de Distribución Sísmica Regional</h2>
                <img class="mapa" src="data:image/jpeg;base64,{img_reg_base64}" alt="Mapa Regional">
            </div>
        </body>
        </html>
        """
        #Se crea un archivo PDF con toda la información.
        nombre_pdf = f"reporte_area_{area.lower().replace(' ', '_')}.pdf"
        HTML(string=html_documento).write_pdf(nombre_pdf)
        print(f"El PDF '{nombre_pdf}' ha sido generado exitosamente con su mapa acotado y ampliado.")

        # Pregunta condicional para el visor dinámico 3D
        rta = input(f"\n¿Desea abrir el modelo interactivo 3D para la región de '{area}'? (s/n): ").lower()
        if rta == 's':
            print("Inicializando visor 3D dinámico...")
            self._graficar_sismos_3d_interactivo(sismos_area_depth)
        else:
            print("Entendido. Proceso de área finalizado.")
        plt.close('all')

# ================= EJECUCIÓN DEL PROGRAMA =================

estudio = Infosis()
estudio.carga_y_analisis_csv() # Carga la base de datos
estudio.informe_tierra()        # Procesa análisis global, guarda PDF e interroga por interactivo 2D
estudio.informe_area()          # Filtra por Bounding Box, crea PDF regional e interroga por modelo 3D