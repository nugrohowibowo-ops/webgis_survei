import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import pytz  # Library untuk zona waktu
from streamlit_geolocation import streamlit_geolocation
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Input Data Online")

# --- FUNGSI UPLOAD KE IMGBB ---
def upload_to_imgbb(image_file):
    try:
        # Mengambil API Key dari Secrets Cloud
        # Jika dijalankan lokal tanpa secrets, pastikan Anda punya handle error-nya
        if "imgbb_key" in st.secrets:
            api_key = st.secrets["imgbb_key"]
        else:
            return None # Atau masukkan key manual untuk testing

        url = "https://api.imgbb.com/1/upload"
        payload = {"key": api_key, "expiration": 0}
        files = {"image": image_file.getvalue()}
        
        response = requests.post(url, data=payload, files=files)
        result = response.json()
        
        if result["success"]:
            return result["data"]["url"]
        return None
    except Exception as e:
        st.error(f"Error Upload: {e}")
        return None

# --- LOGIN SISTEM ---
def check_login():
    if st.session_state.get('logged_in', False):
        return True
    
    st.markdown("### 🔒 Halaman Input Terproteksi")
    c1, c2 = st.columns(2)
    user = c1.text_input("Username")
    pwd = c2.text_input("Password", type="password")
    
    if st.button("Masuk"):
        # Cek Password
        try:
            u_sah = st.secrets["db_username"]
            p_sah = st.secrets["db_password"]
        except:
            u_sah, p_sah = "admin", "123" # Password default jika di laptop
            
        if user == u_sah and pwd == p_sah:
            st.session_state['logged_in'] = True
            st.session_state['user_now'] = user
            st.rerun()
        else:
            st.error("Username/Password Salah!")
    return False

if not check_login():
    st.stop()

# --- APLIKASI UTAMA ---
st.title(f"📝 Input Data: {st.session_state['user_now']}")

# Koneksi GSheets
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    existing_data = conn.read(worksheet="Sheet1", usecols=list(range(8)), ttl=5)
    existing_data = existing_data.dropna(how="all")
except:
    st.warning("Menyiapkan database baru atau koneksi gagal...")
    existing_data = pd.DataFrame()

# GPS Logic
if 'lat' not in st.session_state: st.session_state['lat'] = -7.7
if 'lon' not in st.session_state: st.session_state['lon'] = 110.35

st.info("📍 Klik tombol di bawah untuk update lokasi GPS")
loc = streamlit_geolocation()
if loc['latitude'] is not None:
    st.session_state['lat'] = loc['latitude']
    st.session_state['lon'] = loc['longitude']
    st.success("Lokasi Terkunci!")

# Form Input
with st.form("form_submit"):
    c1, c2 = st.columns(2)
    with c1:
        nama = st.text_input("Nama Lokasi")
        lat = st.number_input("Lat", value=float(st.session_state['lat']), format="%.6f")
        lon = st.number_input("Lon", value=float(st.session_state['lon']), format="%.6f")
    with c2:
        kategori = st.selectbox("Risiko", ["Aman", "Waspada", "Bahaya"])
        ket = st.text_area("Keterangan")
    
    st.write("---")
    metode = st.radio("Foto", ["Kamera", "Upload File"], horizontal=True)
    img_file = None
    if metode == "Kamera": img_file = st.camera_input("Jepret")
    else: img_file = st.file_uploader("Upload", type=['jpg','png','jpeg'])
    
    submit = st.form_submit_button("🚀 Kirim Data")

# --- LOGIKA PENYIMPANAN ---
if submit:
    if nama:
        # 1. Upload Foto
        url_foto = ""
        if img_file:
            with st.spinner("Mengupload foto..."):
                res_url = upload_to_imgbb(img_file)
                if res_url:
                    url_foto = res_url
                else:
                    st.warning("Gagal upload foto, data tetap disimpan tanpa foto.")
        
        # 2. Ambil Waktu WIB (Asia/Jakarta)
        zona_wib = pytz.timezone('Asia/Jakarta')
        waktu_sekarang = datetime.now(zona_wib).strftime("%Y-%m-%d %H:%M:%S")
        
        # 3. Buat Data Baru
        new_data = pd.DataFrame([{
            "Nama": nama, 
            "Latitude": lat, 
            "Longitude": lon,
            "Keterangan": ket, 
            "Kategori": kategori, 
            "Foto": url_foto, 
            "Waktu": waktu_sekarang, # Menggunakan waktu WIB
            "User": st.session_state['user_now']
        }])
        
        # 4. Update ke Google Sheets
        try:
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success(f"Data Tersimpan pada {waktu_sekarang} WIB!")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"Gagal menyimpan ke Google Sheets: {e}")
            
    else:
        st.warning("Isi Nama Lokasi!")
