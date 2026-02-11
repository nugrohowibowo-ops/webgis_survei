import streamlit as st
import folium
from folium.plugins import LocateControl
from streamlit_folium import st_folium
import pandas as pd
import os
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="WebGIS Seismik", layout="wide")
st.title("🌏 WebGIS Zona Bahaya Seismik")

# --- FUNGSI BANTUAN: Handle Gambar URL ---
def get_image_html(link_gambar, width=200):
    """Membuat tag HTML img dari URL ImgBB"""
    if pd.isna(link_gambar) or str(link_gambar).strip() == "":
        return ""
    # Pastikan link valid
    if str(link_gambar).startswith("http"):
        return f'<img src="{link_gambar}" width="{width}" style="border-radius:5px; margin-top:10px; border:1px solid #ddd;">'
    return ""

# --- 1. LOAD DATA DARI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Baca data, handle jika kosong
    df = conn.read(worksheet="Sheet1", usecols=list(range(8)), ttl=5)
    df = df.dropna(how="all")
except Exception as e:
    st.error(f"Gagal memuat data: {e}")
    df = pd.DataFrame()

# --- 2. KONFIGURASI PETA ---
m = folium.Map(location=[-7.7, 110.35], zoom_start=11)

# A. Layer Peta Dasar
folium.TileLayer('OpenStreetMap', name='Peta Jalan').add_to(m)
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attr='Google',
    name='Google Satellite',
    overlay=False
).add_to(m)

# B. Layer Overlay Gambar (Vs30)
# Pastikan file vs30.png ikut diupload ke GitHub nanti
nama_file_gambar = "vs30.png"
bounds = [[-8.246588, 109.933319], [-7.434855, 111.044312]] 

if os.path.exists(nama_file_gambar):
    folium.raster_layers.ImageOverlay(
        name="Peta Mikrozonasi (Vs30)",
        image=nama_file_gambar,
        bounds=bounds,
        opacity=0.6,
        zindex=1
    ).add_to(m)

# C. Layer Titik (Marker)
fg_titik = folium.FeatureGroup(name="Lokasi Survei")

if not df.empty:
    for index, row in df.iterrows():
        warna = 'blue'
        kategori = row['Kategori'] if 'Kategori' in row and pd.notna(row['Kategori']) else "Umum"
        
        if kategori == 'Bahaya': warna = 'red'
        elif kategori == 'Waspada': warna = 'orange'
        elif kategori == 'Aman': warna = 'green'
        
        # Ambil URL Foto
        path_foto = row['Foto'] if 'Foto' in row else None
        html_gambar = get_image_html(path_foto)
        
        html_popup = f"""
        <div style="font-family:sans-serif; width:220px;">
            <h4 style="margin-bottom:0;">{row['Nama']}</h4>
            <span style="background-color:{warna}; color:white; padding:2px 6px; border-radius:4px; font-size:10px;">{kategori}</span>
            <hr style="margin:5px 0;">
            {html_gambar}
            <p style="margin-top:5px; font-size:12px;">{row['Keterangan']}</p>
            <small style="color:gray;">User: {row['User']}</small>
        </div>
        """
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(html_popup, max_width=250),
            tooltip=row['Nama'],
            icon=folium.Icon(color=warna, icon='info-sign')
        ).add_to(fg_titik)

fg_titik.add_to(m)

# --- 3. RENDER PETA ---
LocateControl(auto_start=False).add_to(m)
folium.LayerControl(collapsed=False).add_to(m)
st_folium(m, width=1200, height=600)

with st.expander("Lihat Data Tabel"):
    st.dataframe(df, use_container_width=True)