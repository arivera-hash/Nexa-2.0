import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static  # Cambiamos a folium_static
import requests
import polyline
from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Localizador Nexa 2.0", layout="wide")

# --- FUNCIONES LÓGICAS ---
def distancia_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    return 2 * R * asin(sqrt(sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2))

def obtener_ruta(lat1, lon1, lat2, lon2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=polyline"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            res = response.json()
            if res.get('code') == 'Ok':
                return polyline.decode(res['routes'][0]['geometry'])
        return None
    except Exception:
        return None

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    df = pd.read_excel("estaciones.xlsx")
    df.columns = df.columns.str.strip()
    return df

df_estaciones = cargar_datos()

# --- INTERFAZ DE USUARIO (SIDEBAR) ---
st.sidebar.header("📍 Tu Viaje")
origen_txt = st.sidebar.text_input("Origen", "Madrid, España")
destino_txt = st.sidebar.text_input("Destino", "Valencia, España")
desvio_km = st.sidebar.slider("Desvío máx. (km)", 1, 50, 10)
btn_buscar = st.sidebar.button("🔍 Buscar Ruta")

# --- LÓGICA PRINCIPAL ---
if btn_buscar:
    with st.spinner('Calculando ruta...'):
        geolocator = Nominatim(user_agent="nexa_replica_v3")
        loc_org = geolocator.geocode(origen_txt)
        loc_des = geolocator.geocode(destino_txt)

        if loc_org and loc_des:
            puntos_ruta = obtener_ruta(loc_org.latitude, loc_org.longitude, loc_des.latitude, loc_des.longitude)
            
            if puntos_ruta:
                # Filtrado de estaciones
                encontradas = []
                # Muestreo de la ruta para no saturar (un punto cada ~1km)
                puntos_muestreo = puntos_ruta[::20] 
                
                for _, est in df_estaciones.iterrows():
                    for p in puntos_muestreo:
                        if distancia_haversine(est['LATITUD'], est['LONGITUD'], p[0], p[1]) <= desvio_km:
                            encontradas.append(est)
                            break
                df_res = pd.DataFrame(encontradas)

                # Creación del Mapa
                m = folium.Map(location=[(loc_org.latitude + loc_des.latitude)/2, 
                                         (loc_org.longitude + loc_des.longitude)/2], 
                               zoom_start=7)
                
                folium.PolyLine(puntos_ruta, color="#2563eb", weight=5, opacity=0.7).add_to(m)

                for _, est in df_res.iterrows():
                    # Link oficial de Google Maps Directions
                    link = f"https://www.google.com/maps/dir/?api=1&origin={origen_txt.replace(' ','+')}&destination={destino_txt.replace(' ','+')}&waypoints={est['LATITUD']},{est['LONGITUD']}&travelmode=driving"
                    
                    html = f"""
                    <div style='font-family: Arial; font-size: 13px; width: 160px;'>
                        <b style='color: #d32f2f;'>{est['Nombre Estación']}</b><br>
                        <small>{est.get('Producto Nexa', '')}</small><br><br>
                        <a href='{link}' target='_blank' style='background: #4285F4; color: white; padding: 8px; text-decoration: none; border-radius: 4px; display: block; text-align: center;'>Abrir Ruta</a>
                    </div>
                    """
                    folium.Marker(
                        [est['LATITUD'], est['LONGITUD']], 
                        popup=folium.Popup(html, max_width=200), 
                        icon=folium.Icon(color='red', icon='gas-pump', prefix='fa')
                    ).add_to(m)
                
                # Renderizamos el mapa de forma estática (sin parpadeos)
                folium_static(m, width=1000, height=600)
                st.success(f"Encontradas {len(df_res)} estaciones Nexa cerca de tu ruta.")
            else:
                st.error("No se pudo trazar la ruta por carretera.")
        else:
            st.error("Revisa los nombres de las ciudades.")
