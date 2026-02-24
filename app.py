import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import polyline
from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Localizador Nexa Replicado", layout="wide")

# --- FUNCIONES LÓGICAS (Las mismas que probamos en Colab) ---
def distancia_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    return 2 * R * asin(sqrt(sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2))

def obtener_ruta(lat1, lon1, lat2, lon2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=polyline"
    res = requests.get(url).json()
    return polyline.decode(res['routes'][0]['geometry']) if res['code'] == 'Ok' else None

# --- INTERFAZ DE USUARIO (SIDEBAR) ---
st.sidebar.header("📍 Tu Viaje")
origen_txt = st.sidebar.text_input("Origen", "Madrid, España")
destino_txt = st.sidebar.text_input("Destino", "Valencia, España")
desvio_km = st.sidebar.slider("Desvío máx. (km)", 1, 50, 10)
btn_buscar = st.sidebar.button("🔍 Buscar Ruta")

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    # Asegúrate de subir tu Excel con el nombre 'estaciones.xlsx' al mismo sitio que este script
    df = pd.read_excel("estaciones.xlsx")
    df.columns = df.columns.str.strip()
    return df

df_estaciones = cargar_datos()

# --- LÓGICA PRINCIPAL ---
if btn_buscar:
    geolocator = Nominatim(user_agent="nexa_replica")
    loc_org = geolocator.geocode(origen_txt)
    loc_des = geolocator.geocode(destino_txt)

    if loc_org and loc_des:
        puntos_ruta = obtener_ruta(loc_org.latitude, loc_org.longitude, loc_des.latitude, loc_des.longitude)
        
        # Filtrado de estaciones
        encontradas = []
        puntos_muestreo = puntos_ruta[::10]
        for _, est in df_estaciones.iterrows():
            for p in puntos_muestreo:
                if distancia_haversine(est['LATITUD'], est['LONGITUD'], p[0], p[1]) <= desvio_km:
                    encontradas.append(est)
                    break
        df_res = pd.DataFrame(encontradas)

        # Creación del Mapa
        m = folium.Map(location=[loc_org.latitude, loc_org.longitude], zoom_start=7)
        folium.PolyLine(puntos_ruta, color="#2563eb", weight=5).add_to(m)

        for _, est in df_res.iterrows():
            link = f"https://www.google.com/maps/dir/?api=1&origin={origen_txt.replace(' ','+')}&destination={destino_txt.replace(' ','+')}&waypoints={est['LATITUD']},{est['LONGITUD']}"
            html = f"<b>{est['Nombre Estación']}</b><br><a href='{link}' target='_blank'>Ir en Google Maps</a>"
            folium.Marker([est['LATITUD'], est['LONGITUD']], popup=folium.Popup(html, max_width=200), icon=folium.Icon(color='red', icon='fuel', prefix='fa')).add_to(m)

        st_folium(m, width="100%", height=600)
    else:
        st.error("No se pudieron encontrar las ubicaciones.")
