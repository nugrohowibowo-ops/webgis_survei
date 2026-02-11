import streamlit as st
import folium
from folium.plugins import LocateControl
from streamlit_folium import st_folium
import pandas as pd
import os
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="WebGIS Survei Gempa", layout="wide")

# --- HEADER CUSTOM (LOGO + JUDUL KECIL) ---
# Kita buat 2 kolom.
# col1 = Sempit (untuk logo)
# col2 = Lebar (untuk tulisan)
col1, col2 = st.columns([1, 15]) 

with col1:
    # Ganti 'logo_kantor.png' dengan nama file logo asli Anda
    # width=70 mengatur lebar logo (bisa dibesarkan/dikecilkan)
    if os.path.exists("BMKG.png"):
        st.image("BMKG.png", width=70)
    else:
        st.write("🌏") # Fallback jika logo tidak ketemu

with col2:
    # Kita pakai HTML <h3> (Heading 3) agar font lebih kecil dari st.title (H1)
    # style='margin-top: 15px' digunakan agar teks pas di tengah vertikal logo
    st.markdown("""
        <h3 style='margin-top: 15px; margin-bottom: 0;'>
            WebGIS Survei Gempa Merusak
        </h3>
    """, unsafe_allow_html=True)

# Garis pembatas (opsional, agar terlihat rapi)
st.markdown("---")

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