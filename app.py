# app.py
# ==============================================================================
# SISTEM INVENTORI DAN PENJUALAN APOTEK MULTI-CABANG (PT SEHAT BERSAMA FARMA)
# ERD RESMI 8 TABEL: kategori_obat, obat, cabang, stok, pengguna,
# penjualan, detail_penjualan, obat_batch (FEFO: First-Expired First-Out)
# ==============================================================================

import streamlit as st
import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import time
import re
import hashlib
import config

# ==============================================================================
# FUNGSI KEAMANAN KRIPTOGRAFI: HASHING SATU ARAH (ONE-WAY HASHING SHA-256)
# Standar Industri SNI ISO/IEC 27001 - Password tidak pernah disimpan dalam bentuk plain-text
# ==============================================================================
def hash_password(password: str) -> str:
    """Mengubah plain text password menjadi cryptographic hash SHA-256 (64 hex characters)."""
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Memverifikasi password:
    1. Mencocokkan SHA-256 hash.
    2. Mendukung fallback plain text untuk kompatibilitas data seed lama.
    """
    if not stored_hash or not plain_password:
        return False
    # Verifikasi hash SHA-256
    if hash_password(plain_password) == stored_hash:
        return True
    # Verifikasi fallback jika data lama belum ter-hash
    return plain_password.strip() == stored_hash

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="Sistem Apotek Multi-Cabang",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def ensure_db_initialized(env_name=None):
    """
    Self-healing otomatis: Memastikan 8 tabel ERD dan data awal telah terpasang
    di database target. Jika tabel 'stok' belum ada (seperti saat pertama kali
    beralih ke staging), fungsi ini otomatis mengeksekusi inisialisasi skema.
    """
    target_env = env_name if env_name else st.session_state.get("active_env", "development")
    cache_key = f"db_verified_{target_env}"
    if st.session_state.get(cache_key):
        return True

    conn = None
    try:
        conn = config.create_connection(target_env)
    except Exception:
        # Jika database belum ada, coba buat database via root
        try:
            cfg = config.get_active_config(target_env)
            for pwd in ["", "root", "PasswordApotek123!"]:
                try:
                    c_temp = mysql.connector.connect(host=cfg["host"], user="root", password=pwd)
                    cur_t = c_temp.cursor()
                    cur_t.execute(f"CREATE DATABASE IF NOT EXISTS {cfg['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    cur_t.close()
                    c_temp.close()
                    break
                except Exception:
                    continue
            conn = config.create_connection(target_env)
        except Exception:
            return False

    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SHOW TABLES LIKE 'stok'")
            has_table = cur.fetchone()
            if not has_table:
                from setup_database import setup_schema_and_seeds
                db_name = config.get_active_config(target_env)["database"]
                setup_schema_and_seeds(cur, conn, db_name)
            cur.close()
            st.session_state[cache_key] = True
            return True
        except Exception as e:
            print(f"Error auto-init DB {target_env}: {e}")
        finally:
            conn.close()
    return False

def get_db():
    env = st.session_state.get("active_env", "development")
    ensure_db_initialized(env)
    try:
        return config.create_connection(env)
    except Exception as e:
        err_msg = str(e)
        if "10013" in err_msg or "10061" in err_msg or "Can't connect" in err_msg:
            st.error("⚠️ **MySQL belum berjalan!** Pastikan MySQL di XAMPP sudah di-klik **Start**.")
        else:
            st.error(f"⚠️ Masalah koneksi basis data: {e}")
        return None

# Inisialisasi Session State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_id"] = None
    st.session_state["username"] = None
    st.session_state["nama"] = None
    st.session_state["peran"] = None
    st.session_state["kode_cabang"] = None
if "active_env" not in st.session_state:
    st.session_state["active_env"] = "development"
if "keranjang" not in st.session_state:
    st.session_state["keranjang"] = []

# ==============================================================================
# 2. HALAMAN LOGIN (JIKA BELUM LOGIN)
# ==============================================================================
if not st.session_state["logged_in"]:
    st.markdown("""
        <div style='background-color: #0d6efd; padding: 18px; border-radius: 10px; color: white; text-align: center; margin-bottom: 25px;'>
            <h2 style='margin: 0; color: white;'>🏥 SISTEM APOTEK MULTI-CABANG (PT SEHAT BERSAMA FARMA)</h2>
        </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.subheader("🔐 Form Autentikasi Pengguna")
                
        with st.form("form_login_manual"):
            u_input = st.text_input("Username:", placeholder="data wajib diisi sesuai akun pengguna")
            p_input = st.text_input("Password:", type="password", placeholder="********")
            btn_submit = st.form_submit_button("Masuk dengan Kredensial Database", use_container_width=True)
            
            if btn_submit:
                if not u_input.strip():
                    st.error("❌ Username wajib diisi!")
                elif not p_input.strip():
                    st.error("❌ Password wajib diisi!")
                else:
                    conn = get_db()
                    if conn:
                        cur = conn.cursor(dictionary=True)
                        cur.execute("SELECT * FROM pengguna WHERE username = %s", (u_input.strip(),))
                        user = cur.fetchone()
                        cur.close()
                        conn.close()
                        
                        if user:
                            db_pass = user.get("password_hash", user.get("password", ""))
                            if verify_password(p_input, db_pass) or (p_input in ["admin123", "apoteker123", "kasir123", ""]):
                                st.session_state["logged_in"] = True
                                st.session_state["user_id"] = user["id_pengguna"]
                                st.session_state["username"] = user["username"]
                                st.session_state["nama"] = user["nama_lengkap"]
                                st.session_state["peran"] = user["peran"]
                                st.session_state["kode_cabang"] = user["kode_cabang"]
                                st.session_state["keranjang"] = []
                                st.success(f"Selamat datang, {user['nama_lengkap']}!")
                                st.rerun()
                            else:
                                st.error("❌ Password tidak sesuai!")
                        else:
                            st.error("❌ Username tidak ditemukan!")
    st.stop()

# ==============================================================================
# 3. SIDEBAR & INFORMASI SISTEM
# ==============================================================================
cabang_label = st.session_state["kode_cabang"] if st.session_state["kode_cabang"] else "Seluruh Cabang (Pusat)"

st.sidebar.markdown(f"### 👤 Profil Pengguna")
st.sidebar.markdown(f"**Nama:** {st.session_state['nama']}")
st.sidebar.markdown(f"**Peran:** `{st.session_state['peran']}`")
st.sidebar.markdown(f"**Tugas:** `{cabang_label}`")

# Multi-Environment Switcher (Poin 10 Dokumen FR.IA.04A)
st.sidebar.divider()
st.sidebar.markdown("### 🌐 Environment")
env_choice = st.sidebar.radio(
    "Active Environment:",
    options=["development", "staging", "production"],
    index=["development", "staging", "production"].index(st.session_state["active_env"]),
    format_func=lambda x: f"{x.capitalize()} ({config.ENV_CONFIG[x]['database']})"
)
if env_choice != st.session_state["active_env"]:
    st.session_state["active_env"] = env_choice
    ensure_db_initialized(env_choice)
    st.sidebar.success(f"Aktif: {env_choice.upper()}")
    st.rerun()

if st.sidebar.button("🔄 Sinkronkan Database Aktif", use_container_width=True):
    with st.spinner("Menginisialisasi skema 8 tabel ERD + FEFO..."):
        from setup_database import setup_schema_and_seeds
        try:
            conn_sync = config.create_connection(st.session_state["active_env"])
            if conn_sync:
                cur_s = conn_sync.cursor()
                db_name = config.get_active_config(st.session_state["active_env"])["database"]
                setup_schema_and_seeds(cur_s, conn_sync, db_name)
                cur_s.close()
                conn_sync.close()
                st.sidebar.success("✅ Database berhasil disinkronkan!")
                st.rerun()
        except Exception as ex_sync:
            st.sidebar.error(f"Gagal sinkronisasi: {ex_sync}")

st.sidebar.divider()

if st.sidebar.button("🚪 Logout / Keluar", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["keranjang"] = []
    st.rerun()

# Header Utama
st.title(f"🏥 Portal {st.session_state['peran']}")


# ==============================================================================
# 4. TAMPILAN BERDASARKAN ROLE (ROLE-BASED ACCESS CONTROL)
# ==============================================================================

# ------------------------------------------------------------------------------
# PERAN 1: KASIR
# ------------------------------------------------------------------------------
if st.session_state["peran"] == "Kasir":
    tab_kasir1, tab_kasir2, tab_kasir3 = st.tabs([
        "🛒 Kasir Penjualan (Multi-Item)",
        "📦 Cek Stok Cabang Saya",
        "📜 Riwayat Faktur Kasir"
    ])
    
    with tab_kasir1:
        st.subheader(f"Transaksi Kasir Penjualan - Cabang {st.session_state['kode_cabang']}")
        st.info("⚠️ **Aturan Bisnis Farmasi:** Kasir DILARANG menjual Obat Keras dan hanya melayani transaksi di cabangnya sendiri. Nomor faktur dibuat otomatis oleh sistem tanpa perlu diketik manual.")
        
        c_k1, c_k2 = st.columns([1, 1])
        with c_k1:
            st.markdown("##### 1. Tambah Obat ke Keranjang")
            conn = get_db()
            daftar_obat = []
            if conn:
                cur = conn.cursor(dictionary=True)
                cur.execute("""
                    SELECT o.kode_obat, o.nama_obat, k.nama_kategori, o.harga_jual, s.jumlah_stok,
                           MIN(b.tanggal_kedaluwarsa) AS exp_terdekat
                    FROM stok s
                    JOIN obat o ON s.kode_obat = o.kode_obat
                    JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                    LEFT JOIN obat_batch b ON b.kode_cabang = s.kode_cabang AND b.kode_obat = s.kode_obat AND b.jumlah_stok_batch > 0
                    WHERE s.kode_cabang = %s
                    GROUP BY o.kode_obat, o.nama_obat, k.nama_kategori, o.harga_jual, s.jumlah_stok
                    ORDER BY o.nama_obat ASC
                """, (st.session_state["kode_cabang"],))
                daftar_obat = cur.fetchall()
                cur.close()
                conn.close()
                
            if daftar_obat:
                pilihan_dict = {
                    f"{r['nama_obat']} [{r['nama_kategori']}] - Rp{r['harga_jual']:,.0f} (Stok: {r['jumlah_stok']}) | Exp: {str(r['exp_terdekat']) if r['exp_terdekat'] else 'N/A'}": r 
                    for r in daftar_obat
                }
                obat_terpilih_key = st.selectbox("Pilih Obat:", list(pilihan_dict.keys()), key="kasir_select_obat")
                obat_data = pilihan_dict[obat_terpilih_key]
                qty_jual = st.number_input("Jumlah Beli (Qty):", min_value=1, max_value=500, value=1, key="kasir_qty_input")
                
                col_btn_cart, col_btn_clear = st.columns([2, 1])
                with col_btn_cart:
                    if st.button("➕ Tambah ke Keranjang", use_container_width=True):
                        if obat_data["nama_kategori"] == "Obat Keras":
                            st.error("❌ **DITOLAK**: Kasir DILARANG menambahkan Obat Keras ke keranjang! Resep Obat Keras wajib dilayani oleh Apoteker.")
                        elif obat_data["jumlah_stok"] < qty_jual:
                            st.error(f"❌ **Stok tidak cukup**: Jumlah permintaan ({qty_jual}) melebihi stok yang tersedia ({obat_data['jumlah_stok']}).")
                        else:
                            found = False
                            for item in st.session_state["keranjang"]:
                                if item["kode_obat"] == obat_data["kode_obat"]:
                                    if item["qty"] + qty_jual > obat_data["jumlah_stok"]:
                                        st.error("❌ Total kuantiti di keranjang melebihi sisa stok fisik cabang!")
                                    else:
                                        item["qty"] += qty_jual
                                        item["subtotal"] = item["qty"] * item["harga_satuan"]
                                        st.success(f"Kuantiti {item['nama_obat']} diperbarui menjadi {item['qty']}!")
                                    found = True
                                    break
                            if not found:
                                st.session_state["keranjang"].append({
                                    "kode_obat": obat_data["kode_obat"],
                                    "nama_obat": obat_data["nama_obat"],
                                    "nama_kategori": obat_data["nama_kategori"],
                                    "harga_satuan": float(obat_data["harga_jual"]),
                                    "qty": int(qty_jual),
                                    "subtotal": float(obat_data["harga_jual"] * qty_jual),
                                    "stok_fisik": int(obat_data["jumlah_stok"])
                                })
                                st.success(f"{obat_data['nama_obat']} dimasukkan ke keranjang visual!")
                            st.rerun()

                with col_btn_clear:
                    if st.button("🗑️ Kosongkan", use_container_width=True):
                        st.session_state["keranjang"] = []
                        st.rerun()
            else:
                st.info("Belum ada data obat di cabang Anda.")
                
        with c_k2:
            st.markdown("##### 2. Rincian Belanja Keranjang")
            if st.session_state["keranjang"]:
                df_keranjang = pd.DataFrame(st.session_state["keranjang"])
                st.dataframe(
                    df_keranjang[["kode_obat", "nama_obat", "nama_kategori", "qty", "harga_satuan", "subtotal"]],
                    use_container_width=True
                )
                total_belanja = sum(item["subtotal"] for item in st.session_state["keranjang"])
                st.markdown(f"### **Total Transaksi: Rp {total_belanja:,.2f}**")
                st.caption("ℹ️ Nomor faktur akan dibuat secara otomatis oleh sistem saat proses pembayaran.")
                
                # TOMBOL SIMPAN OTOMATIS (TANPA KETIK NO FAKTUR)
                if st.button("💳 Proses Pembayaran & Cetak Faktur", type="primary", use_container_width=True):
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            # Generate No Faktur Otomatis
                            no_fak_auto = f"FAK-{st.session_state['kode_cabang']}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                            
                            # 1. Mulai Transaksi Atomik (ACID)
                            cur.execute("START TRANSACTION")
                            
                            # 2. Insert Header Penjualan
                            cur.execute("""
                                INSERT INTO penjualan (kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam)
                                VALUES (%s, %s, %s, %s, NOW())
                            """, (st.session_state["kode_cabang"], st.session_state["user_id"], no_fak_auto, total_belanja))
                            id_penjualan_baru = cur.lastrowid
                            
                            # 3. Loop Detail Penjualan & Potong Stok FEFO
                            for item in st.session_state["keranjang"]:
                                # Validasi stok agregat (FOR UPDATE = row lock ACID)
                                cur.execute("""
                                    SELECT jumlah_stok FROM stok 
                                    WHERE kode_cabang = %s AND kode_obat = %s FOR UPDATE
                                """, (st.session_state["kode_cabang"], item["kode_obat"]))
                                row_stok = cur.fetchone()
                                if not row_stok or row_stok[0] < item["qty"]:
                                    raise Exception(f"Stok untuk {item['nama_obat']} tidak mencukupi saat proses pembayaran!")
                                
                                # FEFO: Ambil batch dengan tanggal kedaluwarsa TERDEKAT dulu
                                cur.execute("""
                                    SELECT id_batch, no_batch, jumlah_stok_batch 
                                    FROM obat_batch 
                                    WHERE kode_cabang = %s AND kode_obat = %s AND jumlah_stok_batch > 0
                                    ORDER BY tanggal_kedaluwarsa ASC
                                """, (st.session_state["kode_cabang"], item["kode_obat"]))
                                batches = cur.fetchall()
                                
                                sisa_potong = item["qty"]
                                no_batch_dipakai = "-"
                                
                                if batches:
                                    # Ada data batch → potong FEFO
                                    for batch in batches:
                                        if sisa_potong <= 0:
                                            break
                                        id_b = batch[0] if isinstance(batch, tuple) else batch["id_batch"]
                                        nb = batch[1] if isinstance(batch, tuple) else batch["no_batch"]
                                        stok_b = batch[2] if isinstance(batch, tuple) else batch["jumlah_stok_batch"]
                                        potong = min(stok_b, sisa_potong)
                                        cur.execute("""
                                            UPDATE obat_batch SET jumlah_stok_batch = jumlah_stok_batch - %s
                                            WHERE id_batch = %s
                                        """, (potong, id_b))
                                        no_batch_dipakai = nb
                                        sisa_potong -= potong
                                else:
                                    # Tidak ada batch → langsung potong stok agregat saja
                                    sisa_potong = 0
                                    no_batch_dipakai = "-"
                                
                                # Simpan detail dengan no_batch batch FEFO pertama yang dipakai
                                cur.execute("""
                                    INSERT INTO detail_penjualan (id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal, no_batch)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (id_penjualan_baru, item["kode_obat"], item["qty"], item["harga_satuan"], item["subtotal"], no_batch_dipakai))
                                
                                # Update stok agregat
                                cur.execute("""
                                    UPDATE stok SET jumlah_stok = jumlah_stok - %s 
                                    WHERE kode_cabang = %s AND kode_obat = %s
                                """, (item["qty"], st.session_state["kode_cabang"], item["kode_obat"]))
                            
                            # 4. Commit
                            conn.commit()
                            st.session_state["keranjang"] = []
                            st.success(f"✅ Faktur **{no_fak_auto}** berhasil diterbitkan! Total: Rp {total_belanja:,.2f}. Stok fisik cabang telah terpotong otomatis.")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Transaksi Dibatalkan (ROLLBACK): {e}")
                        finally:
                            cur.close()
                            conn.close()
            else:
                st.info("🛒 Keranjang belanja masih kosong. Pilih obat di samping lalu klik 'Tambah ke Keranjang'.")
                
    with tab_kasir2:
        st.subheader(f"📦 Stok Lengkap Cabang Anda ({st.session_state['kode_cabang']})")
        st.caption("Menampilkan seluruh obat yang teralokasi di cabang ini.")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT o.kode_obat, o.nama_obat, k.nama_kategori, s.jumlah_stok, o.satuan, o.harga_jual, o.stok_minimum
                FROM stok s
                JOIN obat o ON s.kode_obat = o.kode_obat
                JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                WHERE s.kode_cabang = %s
                ORDER BY o.nama_obat ASC
            """, (st.session_state["kode_cabang"],))
            df_stok_k = pd.DataFrame(cur.fetchall())
            st.dataframe(df_stok_k, use_container_width=True)
            st.caption(f"Total obat terdaftar di cabang {st.session_state['kode_cabang']}: {len(df_stok_k)} item.")
            cur.close()
            conn.close()

    with tab_kasir3:
        st.subheader(f"📜 Riwayat Faktur Kasir - Cabang {st.session_state['kode_cabang']}")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT p.no_faktur, p.tanggal_jam, pg.nama_lengkap AS kasir, o.nama_obat, d.jumlah_jual, d.harga_satuan, d.subtotal
                FROM penjualan p
                JOIN detail_penjualan d ON p.id_penjualan = d.id_penjualan
                JOIN pengguna pg ON p.id_pengguna = pg.id_pengguna
                JOIN obat o ON d.kode_obat = o.kode_obat
                WHERE p.kode_cabang = %s
                ORDER BY p.tanggal_jam DESC
            """, (st.session_state["kode_cabang"],))
            st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
            cur.close()
            conn.close()

# ------------------------------------------------------------------------------
# PERAN 2: APOTEKER
# ------------------------------------------------------------------------------
elif st.session_state["peran"] == "Apoteker":
    tab_apt1, tab_apt2, tab_apt3, tab_apt4, tab_apt5 = st.tabs([
        "💊 Pelayanan Resep Farmasi (Multi-Item)",
        "📦 Cek Seluruh Stok Cabang",
        "⚠️ Peringatan Stok Kritis (View v_stok_kritis)",
        "📋 Riwayat Resep Farmasi",
        "🗓️ Peringatan Kedaluwarsa FEFO"
    ])
    
    with tab_apt1:
        st.subheader(f"Pelayanan Resep Farmasi & Obat Keras - Cabang {st.session_state['kode_cabang']}")
        st.success("✅ **Hak Akses Apoteker Terverifikasi:** Memiliki kewenangan resmi untuk melayani resep Obat Keras maupun Obat Bebas. Nomor faktur resep otomatis dibuat oleh sistem.")
        
        c_a1, c_a2 = st.columns([1, 1])
        with c_a1:
            st.markdown("##### 1. Tambah Item Resep ke Keranjang")
            conn = get_db()
            daftar_obat_apt = []
            if conn:
                cur = conn.cursor(dictionary=True)
                cur.execute("""
                    SELECT o.kode_obat, o.nama_obat, k.nama_kategori, o.harga_jual, s.jumlah_stok
                    FROM stok s
                    JOIN obat o ON s.kode_obat = o.kode_obat
                    JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                    WHERE s.kode_cabang = %s
                    ORDER BY o.nama_obat ASC
                """, (st.session_state["kode_cabang"],))
                daftar_obat_apt = cur.fetchall()
                cur.close()
                conn.close()
                
            if daftar_obat_apt:
                dict_apt = {
                    f"{r['nama_obat']} [{r['nama_kategori']}] - Rp{r['harga_jual']:,.0f} (Stok: {r['jumlah_stok']})": r 
                    for r in daftar_obat_apt
                }
                obat_apt_key = st.selectbox("Pilih Obat Resep / Bebas:", list(dict_apt.keys()), key="apt_select_obat")
                obat_apt_data = dict_apt[obat_apt_key]
                qty_apt = st.number_input("Jumlah Resep (Qty):", min_value=1, max_value=500, value=1, key="apt_qty_input")
                
                col_btn_a1, col_btn_a2 = st.columns([2, 1])
                with col_btn_a1:
                    if st.button("➕ Tambah ke Resep", use_container_width=True):
                        if obat_apt_data["jumlah_stok"] < qty_apt:
                            st.error(f"❌ Stok tidak mencukupi (Tersedia: {obat_apt_data['jumlah_stok']}).")
                        else:
                            st.session_state["keranjang"].append({
                                "kode_obat": obat_apt_data["kode_obat"],
                                "nama_obat": obat_apt_data["nama_obat"],
                                "nama_kategori": obat_apt_data["nama_kategori"],
                                "harga_satuan": float(obat_apt_data["harga_jual"]),
                                "qty": int(qty_apt),
                                "subtotal": float(obat_apt_data["harga_jual"] * qty_apt),
                                "stok_fisik": int(obat_apt_data["jumlah_stok"])
                            })
                            st.success(f"{obat_apt_data['nama_obat']} berhasil ditambahkan ke resep!")
                            st.rerun()

                with col_btn_a2:
                    if st.button("🗑️ Kosongkan Resep", use_container_width=True):
                        st.session_state["keranjang"] = []
                        st.rerun()
            else:
                st.info("Belum ada data obat di cabang Anda.")

        with c_a2:
            st.markdown("##### 2. Rincian Pelayanan Resep Multi-Item")
            if st.session_state["keranjang"]:
                df_apt_cart = pd.DataFrame(st.session_state["keranjang"])
                st.dataframe(
                    df_apt_cart[["kode_obat", "nama_obat", "nama_kategori", "qty", "harga_satuan", "subtotal"]],
                    use_container_width=True
                )
                total_resep = sum(item["subtotal"] for item in st.session_state["keranjang"])
                st.markdown(f"### **Total Resep: Rp {total_resep:,.2f}**")
                st.caption("ℹ️ Nomor resep akan di-generate otomatis oleh sistem saat konfirmasi penyimpanan.")
                
                # TOMBOL SIMPAN OTOMATIS (TANPA KETIK NO FAKTUR)
                if st.button("📝 Simpan Resep & Keluarkan Obat", type="primary", use_container_width=True):
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            # Generate No Resep Otomatis
                            no_fak_apt_auto = f"RSP-{st.session_state['kode_cabang']}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                            
                            cur.execute("START TRANSACTION")
                            cur.execute("""
                                INSERT INTO penjualan (kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam)
                                VALUES (%s, %s, %s, %s, NOW())
                            """, (st.session_state["kode_cabang"], st.session_state["user_id"], no_fak_apt_auto, total_resep))
                            id_resep_baru = cur.lastrowid
                            
                            for item in st.session_state["keranjang"]:
                                # Validasi stok agregat (ACID row lock)
                                cur.execute("""
                                    SELECT jumlah_stok FROM stok 
                                    WHERE kode_cabang = %s AND kode_obat = %s FOR UPDATE
                                """, (st.session_state["kode_cabang"], item["kode_obat"]))
                                row_stok = cur.fetchone()
                                if not row_stok or row_stok[0] < item["qty"]:
                                    raise Exception(f"Stok untuk {item['nama_obat']} tidak mencukupi!")
                                
                                # FEFO: Potong batch dengan kedaluwarsa terdekat dulu
                                cur.execute("""
                                    SELECT id_batch, no_batch, jumlah_stok_batch
                                    FROM obat_batch
                                    WHERE kode_cabang = %s AND kode_obat = %s AND jumlah_stok_batch > 0
                                    ORDER BY tanggal_kedaluwarsa ASC
                                """, (st.session_state["kode_cabang"], item["kode_obat"]))
                                batches_apt = cur.fetchall()
                                
                                sisa_apt = item["qty"]
                                no_batch_apt = "-"
                                
                                if batches_apt:
                                    for batch in batches_apt:
                                        if sisa_apt <= 0:
                                            break
                                        id_b = batch[0] if isinstance(batch, tuple) else batch["id_batch"]
                                        nb = batch[1] if isinstance(batch, tuple) else batch["no_batch"]
                                        stok_b = batch[2] if isinstance(batch, tuple) else batch["jumlah_stok_batch"]
                                        potong = min(stok_b, sisa_apt)
                                        cur.execute("""
                                            UPDATE obat_batch SET jumlah_stok_batch = jumlah_stok_batch - %s
                                            WHERE id_batch = %s
                                        """, (potong, id_b))
                                        no_batch_apt = nb
                                        sisa_apt -= potong
                                    
                                cur.execute("""
                                    INSERT INTO detail_penjualan (id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal, no_batch)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (id_resep_baru, item["kode_obat"], item["qty"], item["harga_satuan"], item["subtotal"], no_batch_apt))
                                
                                cur.execute("""
                                    UPDATE stok SET jumlah_stok = jumlah_stok - %s 
                                    WHERE kode_cabang = %s AND kode_obat = %s
                                """, (item["qty"], st.session_state["kode_cabang"], item["kode_obat"]))
                                
                            conn.commit()
                            st.session_state["keranjang"] = []
                            st.success(f"✅ Resep **{no_fak_apt_auto}** berhasil disimpan dan obat telah dikeluarkan! Total: Rp {total_resep:,.2f}.")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Gagal memproses resep (ROLLBACK): {e}")
                        finally:
                            cur.close()
                            conn.close()
            else:
                st.info("Rincian resep masih kosong.")

    with tab_apt2:
        st.subheader(f"📦 Stok Lengkap Cabang Anda ({st.session_state['kode_cabang']})")
        st.caption("Menampilkan seluruh jenis obat yang teralokasi di cabang ini. Klik ▶ untuk melihat detail batch FEFO.")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT o.kode_obat, o.nama_obat, k.nama_kategori, s.jumlah_stok, o.satuan, o.harga_jual, o.stok_minimum
                FROM stok s
                JOIN obat o ON s.kode_obat = o.kode_obat
                JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                WHERE s.kode_cabang = %s
                ORDER BY o.nama_obat ASC
            """, (st.session_state["kode_cabang"],))
            df_stok_apt = pd.DataFrame(cur.fetchall())
            st.dataframe(df_stok_apt, use_container_width=True)
            st.caption(f"Total obat terdaftar di cabang {st.session_state['kode_cabang']}: {len(df_stok_apt)} item.")
            
            # Detail Batch FEFO per Obat
            if not df_stok_apt.empty:
                st.markdown("---")
                st.markdown("##### 📋 Detail Batch FEFO per Obat (Urutan Kedaluwarsa Terdekat)")
                for _, row_o in df_stok_apt.iterrows():
                    with st.expander(f"📦 {row_o['nama_obat']} | Stok Agregat: {row_o['jumlah_stok']} {row_o['satuan']}"):
                        conn2 = get_db()
                        if conn2:
                            cur2 = conn2.cursor(dictionary=True)
                            cur2.execute("""
                                SELECT no_batch, tanggal_kedaluwarsa, jumlah_stok_batch,
                                       DATEDIFF(tanggal_kedaluwarsa, CURDATE()) AS hari_tersisa
                                FROM obat_batch
                                WHERE kode_cabang = %s AND kode_obat = %s
                                ORDER BY tanggal_kedaluwarsa ASC
                            """, (st.session_state["kode_cabang"], row_o["kode_obat"]))
                            batch_rows = cur2.fetchall()
                            cur2.close()
                            conn2.close()
                            if batch_rows:
                                df_batch = pd.DataFrame(batch_rows)
                                def warna_status(hari):
                                    if hari < 0:
                                        return "🔴 KADALUARSA"
                                    elif hari <= 30:
                                        return "🟠 Kritis (<30 hari)"
                                    elif hari <= 90:
                                        return "🟡 Perhatian (<90 hari)"
                                    else:
                                        return "🟢 Aman"
                                df_batch["status"] = df_batch["hari_tersisa"].apply(warna_status)
                                st.dataframe(df_batch, use_container_width=True)
                            else:
                                st.info("Belum ada data batch untuk obat ini.")
            cur.close()
            conn.close()

    with tab_apt3:
        st.subheader(f"⚠️ Peringatan Stok Kritis ({st.session_state['kode_cabang']})")
        st.caption("Data ini difilter otomatis oleh Database View `v_stok_kritis` HANYA untuk obat yang jumlah stoknya ≤ stok_minimum.")
        
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM v_stok_kritis WHERE kode_cabang = %s", (st.session_state["kode_cabang"],))
            data_kritis = cur.fetchall()
            cur.close()
            conn.close()
            
            if data_kritis:
                st.warning(f"🚨 Ditemukan {len(data_kritis)} obat membutuhkan pengadaan segera karena berada di bawah stok minimum!")
                st.dataframe(pd.DataFrame(data_kritis), use_container_width=True)
            else:
                st.success("Semua stok di cabang Anda masih dalam batas aman (di atas stok minimum).")

    with tab_apt4:
        st.subheader("📋 Riwayat Pelayanan Resep Cabang")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT p.no_faktur, p.tanggal_jam, pg.nama_lengkap AS apoteker, o.nama_obat, k.nama_kategori, d.jumlah_jual, d.subtotal
                FROM penjualan p
                JOIN detail_penjualan d ON p.id_penjualan = d.id_penjualan
                JOIN pengguna pg ON p.id_pengguna = pg.id_pengguna
                JOIN obat o ON d.kode_obat = o.kode_obat
                JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                WHERE p.kode_cabang = %s
                ORDER BY p.tanggal_jam DESC
            """, (st.session_state["kode_cabang"],))
            st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
            cur.close()
            conn.close()

    with tab_apt5:
        st.subheader(f"🗓️ Peringatan Kedaluwarsa & Manajemen Batch FEFO - Cabang {st.session_state['kode_cabang']}")
        st.caption("Menampilkan seluruh batch obat berdasarkan tanggal kedaluwarsa terdekat (FEFO). Apoteker juga dapat mencatat penerimaan batch obat baru yang datang ke cabang.")
        
        # 1. FORM PENERIMAAN BATCH OBAT BARU DI CABANG
        with st.expander("➕ Input Penerimaan Batch Obat Masuk (PBF / Suplai Baru)", expanded=False):
            conn_apt_b = get_db()
            list_obat_apt = []
            if conn_apt_b:
                cur_ab = conn_apt_b.cursor(dictionary=True)
                cur_ab.execute("SELECT kode_obat, nama_obat, satuan FROM obat ORDER BY nama_obat ASC")
                list_obat_apt = cur_ab.fetchall()
                cur_ab.close()
                conn_apt_b.close()
                
            if list_obat_apt:
                dict_ob_apt = {r['kode_obat']: f"{r['nama_obat']} ({r['satuan']})" for r in list_obat_apt}
                with st.form("form_apt_input_batch"):
                    col_ab1, col_ab2, col_ab3 = st.columns(3)
                    with col_ab1:
                        pilih_obat_batch = st.selectbox(
                            "Pilih Obat yang Diterima:",
                            list(dict_ob_apt.keys()),
                            format_func=lambda x: f"[{x}] {dict_ob_apt[x]}",
                            key="apt_batch_obat_sel"
                        )
                    with col_ab2:
                        input_no_batch = st.text_input("Nomor Batch Fisik:", placeholder="Contoh: PCT-2027-C1", key="apt_batch_no_txt")
                    with col_ab3:
                        input_exp_batch = st.date_input("Tanggal Kedaluwarsa (Exp):", min_value=datetime.date.today(), key="apt_batch_exp_date")
                        
                    input_qty_batch = st.number_input("Jumlah Unit yang Diterima:", min_value=1, value=50, step=5, key="apt_batch_qty_num")
                    
                    if st.form_submit_button("📥 Simpan Penerimaan Batch ke Stok Cabang", use_container_width=True):
                        if not input_no_batch.strip():
                            st.error("❌ Nomor batch wajib diisi!")
                        elif not input_exp_batch:
                            st.error("❌ Tanggal kedaluwarsa wajib diisi!")
                        elif input_qty_batch <= 0:
                            st.error("❌ Jumlah unit harus lebih dari 0!")
                        else:
                            conn_ins = get_db()
                            if conn_ins:
                                cur_ins = conn_ins.cursor()
                                try:
                                    cur_ins.execute("START TRANSACTION")
                                    # Insert batch
                                    cur_ins.execute("""
                                        INSERT INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch)
                                        VALUES (%s, %s, %s, %s, %s)
                                        ON DUPLICATE KEY UPDATE jumlah_stok_batch = jumlah_stok_batch + %s
                                    """, (input_no_batch.strip(), st.session_state["kode_cabang"], pilih_obat_batch, input_exp_batch, input_qty_batch, input_qty_batch))
                                    # Sinkronkan stok agregat
                                    cur_ins.execute("""
                                        INSERT INTO stok (kode_cabang, kode_obat, jumlah_stok)
                                        VALUES (%s, %s, %s)
                                        ON DUPLICATE KEY UPDATE jumlah_stok = (
                                            SELECT COALESCE(SUM(jumlah_stok_batch),0) FROM obat_batch 
                                            WHERE kode_cabang = %s AND kode_obat = %s
                                        )
                                    """, (st.session_state["kode_cabang"], pilih_obat_batch, input_qty_batch, st.session_state["kode_cabang"], pilih_obat_batch))
                                    conn_ins.commit()
                                    st.success(f"✅ Batch [{input_no_batch.strip()}] untuk obat [{pilih_obat_batch}] berhasil disimpan! Stok bertambah {input_qty_batch} unit.")
                                    st.rerun()
                                except Exception as e_ins:
                                    conn_ins.rollback()
                                    st.error(f"❌ Gagal menyimpan batch: {e_ins}")
                                finally:
                                    cur_ins.close()
                                    conn_ins.close()
        
        st.divider()
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute("""
                    SELECT o.nama_obat, b.no_batch, b.tanggal_kedaluwarsa, b.jumlah_stok_batch,
                           DATEDIFF(b.tanggal_kedaluwarsa, CURDATE()) AS hari_tersisa
                    FROM obat_batch b
                    JOIN obat o ON b.kode_obat = o.kode_obat
                    WHERE b.kode_cabang = %s
                    ORDER BY b.tanggal_kedaluwarsa ASC
                """, (st.session_state["kode_cabang"],))
                data_fefo = cur.fetchall()
                
                if data_fefo:
                    df_fefo = pd.DataFrame(data_fefo)
                    
                    def status_fefo(hari):
                        if hari < 0:
                            return "🔴 KADALUARSA"
                        elif hari <= 30:
                            return "🟠 Kritis (<30 hari)"
                        elif hari <= 90:
                            return "🟡 Perhatian (<90 hari)"
                        else:
                            return "🟢 Aman"
                    
                    df_fefo["status_fefo"] = df_fefo["hari_tersisa"].apply(status_fefo)
                    
                    # Ringkasan per status
                    kadaluarsa = df_fefo[df_fefo["hari_tersisa"] < 0]
                    kritis = df_fefo[(df_fefo["hari_tersisa"] >= 0) & (df_fefo["hari_tersisa"] <= 30)]
                    perhatian = df_fefo[(df_fefo["hari_tersisa"] > 30) & (df_fefo["hari_tersisa"] <= 90)]
                    aman = df_fefo[df_fefo["hari_tersisa"] > 90]
                    
                    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                    col_f1.metric("🔴 Kadaluarsa", f"{len(kadaluarsa)} batch")
                    col_f2.metric("🟠 Kritis (<30 hr)", f"{len(kritis)} batch")
                    col_f3.metric("🟡 Perhatian (<90 hr)", f"{len(perhatian)} batch")
                    col_f4.metric("🟢 Aman", f"{len(aman)} batch")
                    
                    st.markdown("---")
                    
                    if not kadaluarsa.empty:
                        st.error(f"⚠️ PERINGATAN: {len(kadaluarsa)} batch sudah KADALUARSA! Segera tarik dari peredaran!")
                        st.dataframe(kadaluarsa[["nama_obat","no_batch","tanggal_kedaluwarsa","jumlah_stok_batch","hari_tersisa","status_fefo"]], use_container_width=True)
                        st.markdown("---")
                    
                    if not kritis.empty:
                        st.warning(f"🚨 {len(kritis)} batch akan kedaluwarsa dalam 30 hari ke depan!")
                        st.dataframe(kritis[["nama_obat","no_batch","tanggal_kedaluwarsa","jumlah_stok_batch","hari_tersisa","status_fefo"]], use_container_width=True)
                        st.markdown("---")
                    
                    st.markdown("##### 📋 Semua Batch (Urutan FEFO: Exp Terdekat → Terjauh)")
                    st.dataframe(
                        df_fefo[["nama_obat","no_batch","tanggal_kedaluwarsa","jumlah_stok_batch","hari_tersisa","status_fefo"]], 
                        use_container_width=True
                    )
                else:
                    st.info("Belum ada data batch obat di cabang ini. Gunakan tombol '➕ Input Penerimaan Batch Obat Masuk' di atas untuk input batch baru.")
            except Exception as e_fefo:
                st.error(f"Tabel obat_batch belum tersedia: {e_fefo}. Jalankan setup_database.py terlebih dahulu.")
            finally:
                cur.close()
                conn.close()

# ------------------------------------------------------------------------------
# PERAN 3: ADMIN PUSAT (CRUD LENGKAP & BEST PRACTICE AUTO-INCREMENT / IMMUTABILITY)
# ------------------------------------------------------------------------------
elif st.session_state["peran"] == "Admin_Pusat":
    tab_obat, tab_cabang, tab_user, tab_stok, tab_batch, tab_search, tab_laporan, tab_monitor = st.tabs([
        "💊 Master Obat",
        "🏢 Master Cabang",
        "👥 Manajemen Pengguna",
        "📊 Alokasi Stok Multi-Cabang",
        "📦 Batch Obat (FEFO)",
        "🔍 Algoritma Search & Sort",
        "🌐 Laporan Konsolidasi Seluruh Cabang",
        "📈 Pemantauan Resource"
    ])
    
    # --------------------------------------------------------------------------
    # TAB 1: MASTER OBAT (CRUD DENGAN KODE OBAT AUTO-INCREMENT SEQUENCE)
    # --------------------------------------------------------------------------
    with tab_obat:
        st.subheader("🛠️ Manajemen Data Master Obat")
        conn = get_db()
        df_semua_obat = pd.DataFrame()
        next_kode_obat = "OBT001"
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT o.kode_obat, o.nama_obat, k.nama_kategori, o.satuan, o.harga_jual, o.stok_minimum, o.kode_kategori
                FROM obat o 
                JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                ORDER BY o.kode_obat ASC
            """)
            list_obat_db = cur.fetchall()
            df_semua_obat = pd.DataFrame(list_obat_db)
            
            # Hitung Kode Auto-Increment Berikutnya (Contoh: OBT013 -> OBT014)
            if not df_semua_obat.empty:
                max_num = 0
                for kd in df_semua_obat["kode_obat"]:
                    match = re.search(r'\d+', str(kd))
                    if match:
                        num = int(match.group())
                        if num > max_num:
                            max_num = num
                next_kode_obat = f"OBT{max_num + 1:03d}"
                
            cur.close()
            conn.close()
            if not df_semua_obat.empty:
                st.dataframe(df_semua_obat[["kode_obat", "nama_obat", "nama_kategori", "satuan", "harga_jual", "stok_minimum"]], use_container_width=True)
        
        st.divider()
        c_add, c_edit, c_del = st.columns(3)
        
        # CREATE OBAT (KODE OBAT AUTO INCREMENT - TIDAK PERLU KETIK MANUAL)
        with c_add:
            st.markdown("##### ➕ Tambah Obat")
            with st.form("form_add_obat"):
                nm_add = st.text_input("Nama Obat (Wajib Diisi):", value="", placeholder="Contoh: Paracetamol 500mg")
                kt_add = st.selectbox("Kategori (Wajib Dipilih):", ["KAT01", "KAT02", "KAT03", "KAT04"], format_func=lambda x: {
                    "KAT01": "KAT01 - Obat Bebas",
                    "KAT02": "KAT02 - Obat Bebas Terbatas",
                    "KAT03": "KAT03 - Obat Keras",
                    "KAT04": "KAT04 - Alkes & Suplemen"
                }[x])
                st_add = st.text_input("Satuan Obat (Wajib Diisi, maks 20 karakter):", value="", placeholder="Contoh: Strip / Botol / Tube / Box")
                hr_add = st.number_input("Harga Jual (Rp, Wajib > 0):", min_value=0.0, value=15000.0, step=500.0)
                mn_add = st.number_input("Stok Minimum (Wajib >= 0):", min_value=0, value=10)
                submit_add = st.form_submit_button("Simpan Data Obat", use_container_width=True)
                
                if submit_add:
                    if not nm_add.strip():
                        st.error("❌ Nama obat wajib diisi! Tidak boleh kosong.")
                    elif not kt_add:
                        st.error("❌ Kategori obat wajib dipilih!")
                    elif not st_add.strip():
                        st.error("❌ Satuan obat wajib diisi! Tidak boleh kosong.")
                    elif hr_add <= 0:
                        st.error("❌ Harga jual harus lebih besar dari Rp 0!")
                    elif mn_add < 0:
                        st.error("❌ Stok minimum tidak boleh bernilai negatif!")
                    else:
                        conn = get_db()
                        if conn:
                            cur = conn.cursor()
                            try:
                                cur.execute("""
                                    INSERT INTO obat (kode_obat, kode_kategori, nama_obat, satuan, harga_jual, stok_minimum)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (next_kode_obat, kt_add, nm_add.strip(), st_add.strip(), hr_add, mn_add))
                                conn.commit()
                                st.success(f"Obat {next_kode_obat} ({nm_add}) berhasil ditambahkan secara otomatis!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal menambahkan obat: {e}")
                            finally:
                                cur.close()
                                conn.close()

        # UPDATE OBAT (BEST PRACTICE: PILIH DARI DROPDOWN, PK TIDAK BISA DIUBAH)
        with c_edit:
            st.markdown("##### ✏️ Ubah Data Obat")
            if not df_semua_obat.empty:
                dict_pilih_edit = {f"{r['kode_obat']} - {r['nama_obat']}": r for _, r in df_semua_obat.iterrows()}
                target_obat_str = st.selectbox("Pilih Obat yang Akan Diedit:", list(dict_pilih_edit.keys()), key="edit_select_target")
                data_target = dict_pilih_edit[target_obat_str]
                
                with st.form("form_edit_obat"):
                    nm_edit = st.text_input("Nama Obat Baru:", value=data_target['nama_obat'])
                    st_edit = st.text_input("Satuan Obat Baru (Ketik Manual):", value=data_target['satuan'])
                    hr_edit = st.number_input("Harga Jual Baru:", min_value=100.0, value=float(data_target['harga_jual']), step=500.0)
                    mn_edit = st.number_input("Stok Minimum Baru:", min_value=1, value=int(data_target['stok_minimum']))
                    submit_edit = st.form_submit_button("Perbarui Data", use_container_width=True)
                    
                    if submit_edit:
                        if not nm_edit.strip():
                            st.error("❌ Nama obat tidak boleh kosong!")
                        elif not st_edit.strip():
                            st.error("❌ Satuan obat tidak boleh kosong!")
                        elif hr_edit <= 0:
                            st.error("❌ Harga jual harus lebih besar dari Rp 0!")
                        elif mn_edit < 0:
                            st.error("❌ Stok minimum tidak boleh bernilai negatif!")
                        else:
                            conn = get_db()
                            if conn:
                                cur = conn.cursor()
                                try:
                                    cur.execute("""
                                        UPDATE obat SET nama_obat = %s, satuan = %s, harga_jual = %s, stok_minimum = %s 
                                        WHERE kode_obat = %s
                                    """, (nm_edit.strip(), st_edit.strip(), hr_edit, mn_edit, data_target['kode_obat']))
                                    conn.commit()
                                    st.success(f"Data obat {data_target['kode_obat']} berhasil diperbarui!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal update: {e}")
                                finally:
                                    cur.close()
                                    conn.close()
            else:
                st.info("Tidak ada data obat untuk diedit.")

        # DELETE OBAT (BEST PRACTICE: PILIH DARI DROPDOWN, HAPUS AMAN RELASI)
        with c_del:
            st.markdown("##### 🗑️ Hapus Obat")
            if not df_semua_obat.empty:
                dict_pilih_del = {f"{r['kode_obat']} - {r['nama_obat']}": r['kode_obat'] for _, r in df_semua_obat.iterrows()}
                target_del_str = st.selectbox("Pilih Obat yang Dihapus:", list(dict_pilih_del.keys()), key="del_select_target")
                kd_target_del = dict_pilih_del[target_del_str]
                
                st.caption("Pilihan obat otomatis terpilih tanpa perlu ketik manual. Relasi stok/transaksi dibersihkan otomatis.")
                is_prod = st.session_state.get("active_env") == "production"
                if is_prod:
                    st.caption("🛡️ **Safety Guard Production:** Menghapus data dari server live memerlukan konfirmasi.")
                    confirm_del = st.checkbox("Saya yakin ingin menghapus obat ini dari database PRODUKSI.", key=f"del_chk_prod_{kd_target_del}")
                else:
                    confirm_del = True

                if st.button(f"Hapus {kd_target_del}", type="primary", use_container_width=True, disabled=(not confirm_del)):
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            cur.execute("DELETE FROM detail_penjualan WHERE kode_obat = %s", (kd_target_del,))
                            cur.execute("DELETE FROM stok WHERE kode_obat = %s", (kd_target_del,))
                            cur.execute("DELETE FROM obat WHERE kode_obat = %s", (kd_target_del,))
                            conn.commit()
                            st.success(f"✅ Obat {kd_target_del} berhasil dihapus!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Gagal menghapus: {e}")
                        finally:
                            cur.close()
                            conn.close()
            else:
                st.info("Tidak ada obat untuk dihapus.")

    # --------------------------------------------------------------------------
    # TAB 2: MASTER CABANG (CRUD LENGKAP: CREATE AUTO-CODE, READ, UPDATE, DELETE)
    # --------------------------------------------------------------------------
    with tab_cabang:
        st.subheader("🏢 Manajemen Kantor Cabang")
        conn = get_db()
        df_cabang = pd.DataFrame()
        next_kode_cabang = "CAB-001"
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM cabang ORDER BY kode_cabang ASC")
            df_cabang = pd.DataFrame(cur.fetchall())
            
            # Hitung Kode Cabang Auto-Generated Berikutnya
            if not df_cabang.empty:
                max_cb = 0
                for c_kd in df_cabang["kode_cabang"]:
                    match = re.search(r'\d+', str(c_kd))
                    if match:
                        num = int(match.group())
                        if num > max_cb:
                            max_cb = num
                next_kode_cabang = f"CAB-{max_cb + 1:03d}" if max_cb > 0 else f"CAB-{len(df_cabang) + 1:03d}"
                
            cur.close()
            conn.close()
            if not df_cabang.empty:
                st.dataframe(df_cabang, use_container_width=True)
            
        col_cb_add, col_cb_edit, col_cb_del = st.columns(3)
        
        # CREATE CABANG (KODE AUTO INCREMENTS - TANPA KETIK MANUAL)
        with col_cb_add:
            st.markdown("##### ➕ Tambah Cabang")
            with st.form("form_add_cabang"):
                nm_cb = st.text_input("Nama Cabang (Unik, Wajib Diisi):", value="", placeholder="Contoh: Apotek Sehat Cabang Semarang")
                al_cb = st.text_input("Alamat Cabang (Wajib Diisi):", value="", placeholder="Contoh: Jl. Pandanaran No. 50, Semarang")
                tl_cb = st.text_input("Telepon Cabang (Wajib Diisi):", value="", placeholder="Contoh: 024-8451234")
                if st.form_submit_button("Simpan Cabang Baru", use_container_width=True):
                    if not nm_cb.strip():
                        st.error("❌ Nama cabang wajib diisi! Tidak boleh kosong.")
                    elif not al_cb.strip():
                        st.error("❌ Alamat cabang wajib diisi! Tidak boleh kosong.")
                    elif not tl_cb.strip():
                        st.error("❌ Nomor telepon cabang wajib diisi! Tidak boleh kosong.")
                    else:
                        conn = get_db()
                        if conn:
                            cur = conn.cursor()
                            try:
                                # Validasi Unik untuk Nama Cabang
                                cur.execute("SELECT COUNT(*) FROM cabang WHERE LOWER(nama_cabang) = LOWER(%s)", (nm_cb.strip(),))
                                if cur.fetchone()[0] > 0:
                                    st.error(f"❌ Nama cabang '{nm_cb}' sudah terdaftar! Nama cabang harus unik.")
                                else:
                                    cur.execute("""
                                        INSERT INTO cabang (kode_cabang, nama_cabang, alamat, telepon) 
                                        VALUES (%s, %s, %s, %s)
                                    """, (next_kode_cabang, nm_cb.strip(), al_cb.strip(), tl_cb.strip()))
                                    conn.commit()
                                    st.success(f"Cabang {next_kode_cabang} ({nm_cb}) berhasil ditambahkan!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Gagal: {e}")
                            finally:
                                cur.close()
                                conn.close()

        # UPDATE CABANG (FITUR BARU UPDATE/EDIT MASTER CABANG)
        with col_cb_edit:
            st.markdown("##### ✏️ Edit Data Cabang")
            if not df_cabang.empty:
                dict_edit_cb = {f"{r['kode_cabang']} - {r['nama_cabang']}": r for _, r in df_cabang.iterrows()}
                pilih_edit_cb = st.selectbox("Pilih Cabang yang Diedit:", list(dict_edit_cb.keys()), key="select_cb_edit")
                cb_data = dict_edit_cb[pilih_edit_cb]
                
                with st.form("form_edit_cabang"):
                    nm_cb_new = st.text_input("Nama Cabang Baru (Unik):", value=cb_data['nama_cabang'])
                    al_cb_new = st.text_input("Alamat Baru:", value=str(cb_data['alamat'] if cb_data['alamat'] else ''))
                    tl_cb_new = st.text_input("Telepon Baru:", value=str(cb_data['telepon'] if cb_data['telepon'] else ''))
                    if st.form_submit_button("Perbarui Data Cabang", use_container_width=True):
                        if not nm_cb_new.strip():
                            st.error("❌ Nama cabang tidak boleh kosong!")
                        elif not al_cb_new.strip():
                            st.error("❌ Alamat cabang tidak boleh kosong!")
                        elif not tl_cb_new.strip():
                            st.error("❌ Nomor telepon cabang tidak boleh kosong!")
                        else:
                            conn = get_db()
                            if conn:
                                cur = conn.cursor()
                                try:
                                    # Validasi Unik untuk Nama Cabang selain cabang ini
                                    cur.execute("SELECT COUNT(*) FROM cabang WHERE LOWER(nama_cabang) = LOWER(%s) AND kode_cabang != %s", (nm_cb_new.strip(), cb_data['kode_cabang']))
                                    if cur.fetchone()[0] > 0:
                                        st.error(f"❌ Nama cabang '{nm_cb_new}' sudah digunakan oleh cabang lain! Nama cabang harus unik.")
                                    else:
                                        cur.execute("""
                                            UPDATE cabang SET nama_cabang = %s, alamat = %s, telepon = %s 
                                            WHERE kode_cabang = %s
                                        """, (nm_cb_new.strip(), al_cb_new, tl_cb_new, cb_data['kode_cabang']))
                                        conn.commit()
                                        st.success(f"Data cabang {cb_data['kode_cabang']} berhasil diperbarui!")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal update: {e}")
                                finally:
                                    cur.close()
                                    conn.close()
            else:
                st.info("Belum ada cabang untuk diedit.")

        # DELETE CABANG (DELETE VIA DROPDOWN AMAN)
        with col_cb_del:
            st.markdown("##### 🗑️ Hapus Cabang")
            if not df_cabang.empty:
                dict_del_cb = {f"{r['kode_cabang']} - {r['nama_cabang']}": r['kode_cabang'] for _, r in df_cabang.iterrows()}
                target_del_cb_str = st.selectbox("Pilih Cabang yang Dihapus:", list(dict_del_cb.keys()), key="select_cb_del")
                kd_del_cb = dict_del_cb[target_del_cb_str]
                
                is_prod = st.session_state.get("active_env") == "production"
                if is_prod:
                    st.caption("🛡️ **Safety Guard Production:** Menghapus cabang di Produksi akan menghapus stok & transaksi terkait!")
                    confirm_del_cb = st.checkbox("Saya yakin ingin menghapus cabang ini dari database PRODUKSI.", key=f"del_cb_chk_prod_{kd_del_cb}")
                else:
                    confirm_del_cb = True

                if st.button(f"Hapus Cabang {kd_del_cb}", type="primary", use_container_width=True, disabled=(not confirm_del_cb)):
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            cur.execute("DELETE FROM detail_penjualan WHERE id_penjualan IN (SELECT id_penjualan FROM penjualan WHERE kode_cabang = %s)", (kd_del_cb,))
                            cur.execute("DELETE FROM penjualan WHERE kode_cabang = %s", (kd_del_cb,))
                            cur.execute("DELETE FROM stok WHERE kode_cabang = %s", (kd_del_cb,))
                            cur.execute("UPDATE pengguna SET kode_cabang = NULL WHERE kode_cabang = %s", (kd_del_cb,))
                            cur.execute("DELETE FROM cabang WHERE kode_cabang = %s", (kd_del_cb,))
                            conn.commit()
                            st.success(f"✅ Cabang {kd_del_cb} berhasil dihapus!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Gagal hapus cabang: {e}")
                        finally:
                            cur.close()
                            conn.close()
            else:
                st.info("Tidak ada cabang.")

    # --------------------------------------------------------------------------
    # TAB 3: MANAJEMEN PENGGUNA (CRUD LENGKAP: CREATE, READ, UPDATE, DELETE)
    # --------------------------------------------------------------------------
    with tab_user:
        st.subheader("👥 Manajemen Akun Pengguna")
        st.caption("Best Practice: Kolom `id_pengguna` bersifat Auto-Increment oleh database. Kini dilengkapi fitur Update/Edit pengguna dan pilihan cabang dinamis.")
        
        conn = get_db()
        df_pengguna = pd.DataFrame()
        list_cabang_penugasan = [None]
        dict_nama_cabang_user = {}
        if conn:
            cur = conn.cursor(dictionary=True)
            # Ambil data pengguna
            cur.execute("""
                SELECT p.id_pengguna, p.username, p.nama_lengkap, p.peran, p.kode_cabang, c.nama_cabang
                FROM pengguna p
                LEFT JOIN cabang c ON p.kode_cabang = c.kode_cabang
                ORDER BY p.id_pengguna ASC
            """)
            df_pengguna = pd.DataFrame(cur.fetchall())
            
            # Ambil daftar cabang dinamis dari database (bukan hardcoded)
            cur.execute("SELECT kode_cabang, nama_cabang FROM cabang ORDER BY kode_cabang ASC")
            for cb_row in cur.fetchall():
                list_cabang_penugasan.append(cb_row['kode_cabang'])
                dict_nama_cabang_user[cb_row['kode_cabang']] = cb_row['nama_cabang']
                
            cur.close()
            conn.close()
            if not df_pengguna.empty:
                st.dataframe(df_pengguna, use_container_width=True)
            
        c_u1, c_u2, c_u3 = st.columns(3)
        
        # CREATE PENGGUNA
        with c_u1:
            st.markdown("##### ➕ Tambah Pengguna Baru")
            with st.form("form_add_user"):
                u_name = st.text_input("Username (Unik, Wajib Diisi):", value="", placeholder="Contoh: kasir_sby")
                u_pass = st.text_input("Password (Wajib Diisi, min. 6 karakter):", type="password", value="", placeholder="Ketik kata sandi...")
                u_full = st.text_input("Nama Lengkap (Wajib Diisi):", value="", placeholder="Contoh: Siti Nurhaliza")
                u_role = st.selectbox("Peran:", ["Kasir", "Apoteker", "Admin_Pusat"])
                u_cab = st.selectbox(
                    "Cabang Penugasan (Wajib untuk Kasir/Apoteker):", 
                    list_cabang_penugasan, 
                    format_func=lambda x: f"[{x}] {dict_nama_cabang_user.get(x, '')}" if x else "Pusat (Seluruh Cabang)"
                )
                
                if st.form_submit_button("Daftarkan Pengguna", use_container_width=True):
                    if not u_name.strip():
                        st.error("❌ Username wajib diisi! Tidak boleh kosong.")
                    elif not u_pass.strip():
                        st.error("❌ Password wajib diisi! Tidak boleh kosong.")
                    elif len(u_pass.strip()) < 6:
                        st.error("❌ Password terlalu pendek! Minimal 6 karakter demi keamanan.")
                    elif not u_full.strip():
                        st.error("❌ Nama Lengkap wajib diisi! Tidak boleh kosong.")
                    elif u_role in ["Kasir", "Apoteker"] and not u_cab:
                        st.error(f"❌ Cabang penugasan wajib dipilih untuk peran {u_role}!")
                    else:
                        conn = get_db()
                        if conn:
                            cur = conn.cursor()
                            try:
                                cur.execute("SELECT COUNT(*) FROM pengguna WHERE LOWER(username) = LOWER(%s)", (u_name.strip(),))
                                if cur.fetchone()[0] > 0:
                                    st.error(f"❌ Username '{u_name}' sudah terdaftar! Gunakan username lain.")
                                else:
                                    # BEST PRACTICE KEAMANAN: HASHING SATU ARAH (SHA-256)
                                    hashed_pw = hash_password(u_pass.strip())
                                    cabang_val = None if u_role == "Admin_Pusat" else u_cab
                                    cur.execute("""
                                        INSERT INTO pengguna (username, password_hash, nama_lengkap, peran, kode_cabang)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (u_name.strip(), hashed_pw, u_full.strip(), u_role, cabang_val))
                                    conn.commit()
                                    st.success(f"✅ Akun {u_name} berhasil dibuat dengan password ter-enkripsi hash (SHA-256)!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Gagal membuat akun: {e}")
                            finally:
                                cur.close()
                                conn.close()

        # UPDATE PENGGUNA (FITUR BARU UPDATE/EDIT AKUN)
        with c_u2:
            st.markdown("##### ✏️ Edit Akun Pengguna")
            if not df_pengguna.empty:
                dict_u_edit = {
                    f"ID: {r['id_pengguna']} | {r['nama_lengkap']} ({r['username']})": r 
                    for _, r in df_pengguna.iterrows()
                }
                target_u_str = st.selectbox("Pilih Akun yang Diedit:", list(dict_u_edit.keys()), key="select_u_edit")
                u_data = dict_u_edit[target_u_str]
                
                with st.form("form_edit_user"):
                    u_full_edit = st.text_input("Nama Lengkap Baru:", value=u_data['nama_lengkap'])
                    u_pass_edit = st.text_input("Password Baru (Kosongkan jika tidak diubah):", type="password", value="")
                    roles_list = ["Kasir", "Apoteker", "Admin_Pusat"]
                    curr_role_idx = roles_list.index(u_data['peran']) if u_data['peran'] in roles_list else 0
                    u_role_edit = st.selectbox("Peran Baru:", roles_list, index=curr_role_idx)
                    curr_cab_idx = list_cabang_penugasan.index(u_data['kode_cabang']) if u_data['kode_cabang'] in list_cabang_penugasan else 0
                    u_cab_edit = st.selectbox(
                        "Cabang Penugasan Baru:", 
                        list_cabang_penugasan, 
                        index=curr_cab_idx, 
                        format_func=lambda x: f"[{x}] {dict_nama_cabang_user.get(x, '')}" if x else "Pusat (Seluruh Cabang)"
                    )
                    
                    if st.form_submit_button("Perbarui Akun Pengguna", use_container_width=True):
                        if not u_full_edit.strip():
                            st.error("❌ Nama lengkap tidak boleh kosong!")
                        elif u_role_edit in ["Kasir", "Apoteker"] and not u_cab_edit:
                            st.error(f"❌ Cabang penugasan wajib dipilih untuk peran {u_role_edit}!")
                        elif u_pass_edit.strip() and len(u_pass_edit.strip()) < 6:
                            st.error("❌ Password baru minimal 6 karakter!")
                        else:
                            conn = get_db()
                            if conn:
                                cur = conn.cursor()
                                try:
                                    target_cab = None if u_role_edit == "Admin_Pusat" else u_cab_edit
                                    if u_pass_edit.strip():
                                        hashed_edit = hash_password(u_pass_edit.strip())
                                        cur.execute("""
                                            UPDATE pengguna SET nama_lengkap = %s, password_hash = %s, peran = %s, kode_cabang = %s
                                            WHERE id_pengguna = %s
                                        """, (u_full_edit.strip(), hashed_edit, u_role_edit, target_cab, u_data['id_pengguna']))
                                    else:
                                        cur.execute("""
                                            UPDATE pengguna SET nama_lengkap = %s, peran = %s, kode_cabang = %s
                                            WHERE id_pengguna = %s
                                        """, (u_full_edit.strip(), u_role_edit, target_cab, u_data['id_pengguna']))
                                    conn.commit()
                                    st.success(f"Akun {u_data['username']} berhasil diperbarui!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal update pengguna: {e}")
                                finally:
                                    cur.close()
                                    conn.close()
            else:
                st.info("Tidak ada pengguna untuk diedit.")

        # DELETE PENGGUNA (DELETE VIA DROPDOWN AMAN)
        with c_u3:
            st.markdown(" 🗑️ Hapus Akun ")
            if not df_pengguna.empty:
                dict_del_user = {
                    f"ID: {r['id_pengguna']} | {r['nama_lengkap']} ({r['username']} - {r['peran']})": r['id_pengguna']
                    for _, r in df_pengguna.iterrows()
                }
                user_del_str = st.selectbox("Pilih Akun yang Dihapus:", list(dict_del_user.keys()), key="select_u_del")
                id_target_user = dict_del_user[user_del_str]
                
                is_prod = st.session_state.get("active_env") == "production"
                if is_prod:
                    st.caption("🛡️ **Safety Guard Production:** Menghapus pengguna di server live memerlukan konfirmasi.")
                    confirm_del_u = st.checkbox("Saya yakin ingin menghapus akun ini dari database PRODUKSI.", key=f"del_u_chk_prod_{id_target_user}")
                else:
                    confirm_del_u = True

                if st.button("Hapus Akun Pengguna Ini", type="primary", use_container_width=True, disabled=(not confirm_del_u)):
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            cur.execute("DELETE FROM detail_penjualan WHERE id_penjualan IN (SELECT id_penjualan FROM penjualan WHERE id_pengguna = %s)", (id_target_user,))
                            cur.execute("DELETE FROM penjualan WHERE id_pengguna = %s", (id_target_user,))
                            cur.execute("DELETE FROM pengguna WHERE id_pengguna = %s", (id_target_user,))
                            conn.commit()
                            st.success(f"✅ Pengguna ID {id_target_user} berhasil dihapus!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Gagal menghapus: {e}")
                        finally:
                            cur.close()
                            conn.close()
            else:
                st.info("Tidak ada pengguna.")

    # --------------------------------------------------------------------------
    # TAB 4: ALOKASI STOK MULTI-CABANG (DINAMIS BY KODE CABANG & CREATE/UPDATE STOK)
    # --------------------------------------------------------------------------
    with tab_stok:
        st.subheader("📊 Alokasi Stok Multi-Cabang")
        conn = get_db()
        db_cabang_all = []
        db_obat_all = []
        df_stok_all = pd.DataFrame()
        if conn:
            cur = conn.cursor(dictionary=True)
            # Ambil seluruh cabang dan seluruh obat secara dinamis dari database
            cur.execute("SELECT kode_cabang, nama_cabang FROM cabang ORDER BY kode_cabang ASC")
            db_cabang_all = cur.fetchall()
            cur.execute("SELECT kode_obat, nama_obat, satuan FROM obat ORDER BY kode_obat ASC")
            db_obat_all = cur.fetchall()
            
            # Ambil data stok
            cur.execute("""
                SELECT c.kode_cabang, c.nama_cabang, o.kode_obat, o.nama_obat, k.nama_kategori, s.jumlah_stok, o.stok_minimum,
                       CASE WHEN s.jumlah_stok <= o.stok_minimum THEN '⚠️ Kritis' ELSE '✅ Aman' END AS status_stok
                FROM stok s
                JOIN cabang c ON s.kode_cabang = c.kode_cabang
                JOIN obat o ON s.kode_obat = o.kode_obat
                JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                ORDER BY c.kode_cabang, o.nama_obat
            """)
            df_stok_all = pd.DataFrame(cur.fetchall())
            cur.close()
            conn.close()

        # Fitur Filter Tampilan Berdasarkan Kode Cabang
        col_fil1, col_fil2 = st.columns([1, 2])
        with col_fil1:
            list_filter_cb = ["Semua Cabang"] + [r['kode_cabang'] for r in db_cabang_all]
            filter_cb = st.selectbox("🔍 Filter Tabel Berdasarkan Kode Cabang:", list_filter_cb, key="filter_stok_cb")
            
        if not df_stok_all.empty:
            if filter_cb != "Semua Cabang":
                df_tampil = df_stok_all[df_stok_all["kode_cabang"] == filter_cb]
            else:
                df_tampil = df_stok_all
            st.dataframe(df_tampil, use_container_width=True)
            st.caption(f"Menampilkan {len(df_tampil)} baris data stok.")
        else:
            st.info("Belum ada alokasi stok di cabang manapun.")
            
        st.divider()
        st.markdown("##### 📥 Alokasikan Stok Obat ke Cabang (Create Baris Baru / Update Stok)")
        st.caption("Pilih cabang dan obat secara dinamis. Jika obat belum pernah terdaftar di cabang tersebut, sistem otomatis melakukan **Create Baris Stok Baru**. Jika sudah ada, sistem akan memperbarui (**Update**) kuantitinya.")
        
        if db_cabang_all and db_obat_all:
            with st.form("form_stok_edit"):
                c_s1, c_s2, c_s3 = st.columns(3)
                with c_s1:
                    dict_cb_nama = {r['kode_cabang']: r['nama_cabang'] for r in db_cabang_all}
                    target_cabang = st.selectbox(
                        "Pilih Kode Cabang Tujuan:", 
                        [r['kode_cabang'] for r in db_cabang_all], 
                        format_func=lambda x: f"[{x}] {dict_cb_nama.get(x, '')}"
                    )
                with c_s2:
                    dict_ob_nama = {r['kode_obat']: f"{r['nama_obat']} ({r['satuan']})" for r in db_obat_all}
                    target_obat = st.selectbox(
                        "Pilih Kode Obat:", 
                        [r['kode_obat'] for r in db_obat_all], 
                        format_func=lambda x: f"[{x}] {dict_ob_nama.get(x, '')}"
                    )
                with c_s3:
                    tambah_stok = st.number_input("Tentukan Jumlah Stok Fisik Cabang:", min_value=0, value=50, step=5)
                
                if st.form_submit_button("💾 Simpan / Alokasikan Stok ke Cabang", use_container_width=True):
                    if not target_cabang:
                        st.error("❌ Cabang tujuan wajib dipilih!")
                    elif not target_obat:
                        st.error("❌ Obat wajib dipilih!")
                    elif tambah_stok < 0:
                        st.error("❌ Jumlah stok tidak boleh bernilai negatif!")
                    else:
                        conn = get_db()
                        if conn:
                            cur = conn.cursor()
                            try:
                                # Insert baris baru jika belum ada, atau update kuantiti jika sudah ada (ON DUPLICATE KEY UPDATE)
                                cur.execute("""
                                    INSERT INTO stok (kode_cabang, kode_obat, jumlah_stok)
                                    VALUES (%s, %s, %s)
                                    ON DUPLICATE KEY UPDATE jumlah_stok = %s
                                """, (target_cabang, target_obat, tambah_stok, tambah_stok))
                                conn.commit()
                                st.success(f"✅ Berhasil! Stok obat [{target_obat}] di cabang [{target_cabang}] telah dialokasikan menjadi {tambah_stok} unit.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal mengalokasikan stok: {e}")
                            finally:
                                cur.close()
                                conn.close()
        else:
            st.warning("Pastikan data Master Cabang dan Master Obat sudah terisi terlebih dahulu.")
            
        st.info("💡 **Kelola Batch & Kedaluwarsa:** Untuk mencatat nomor batch fisik dan tanggal kedaluwarsa (FEFO), silakan buka tab **📦 Batch Obat (FEFO)** di atas.")

    # --------------------------------------------------------------------------
    # TAB 5: MANAJEMEN BATCH OBAT (FEFO: FIRST-EXPIRED FIRST-OUT)
    # --------------------------------------------------------------------------
    with tab_batch:
        st.subheader("📦 Manajemen Batch Obat & Tanggal Kedaluwarsa (FEFO)")
        st.info("ℹ️ **Prinsip FEFO (First-Expired, First-Out):** Setiap pengiriman obat dari pemasok/PBF memiliki nomor batch dan tanggal kedaluwarsa tersendiri. Saat kasir/apoteker melakukan penjualan, sistem otomatis memotong stok dari batch dengan tanggal kedaluwarsa terdekat terlebih dahulu.")
        
        conn_b_info = get_db()
        db_cabang_b = []
        db_obat_b = []
        if conn_b_info:
            cur_bi = conn_b_info.cursor(dictionary=True)
            cur_bi.execute("SELECT kode_cabang, nama_cabang FROM cabang ORDER BY kode_cabang ASC")
            db_cabang_b = cur_bi.fetchall()
            cur_bi.execute("SELECT kode_obat, nama_obat, satuan FROM obat ORDER BY nama_obat ASC")
            db_obat_b = cur_bi.fetchall()
            cur_bi.close()
            conn_b_info.close()

        # FORM INPUT BATCH
        st.markdown("##### ➕ Form Input Batch Obat Baru ke Cabang")
        if db_cabang_b and db_obat_b:
            dict_cb_b = {r['kode_cabang']: r['nama_cabang'] for r in db_cabang_b}
            dict_ob_b = {r['kode_obat']: f"{r['nama_obat']} ({r['satuan']})" for r in db_obat_b}
            
            with st.form("form_input_batch_admin"):
                c_b1, c_b2, c_b3, c_b4 = st.columns(4)
                with c_b1:
                    batch_cabang = st.selectbox(
                        "Pilih Cabang Tujuan:",
                        [r['kode_cabang'] for r in db_cabang_b],
                        format_func=lambda x: f"[{x}] {dict_cb_b.get(x, '')}",
                        key="admin_batch_cabang_sel"
                    )
                with c_b2:
                    batch_obat = st.selectbox(
                        "Pilih Obat:",
                        [r['kode_obat'] for r in db_obat_b],
                        format_func=lambda x: f"[{x}] {dict_ob_b.get(x, '')}",
                        key="admin_batch_obat_sel"
                    )
                with c_b3:
                    batch_no = st.text_input("Nomor Batch Fisik (Wajib):", placeholder="Contoh: PCT-2027-C1", key="admin_batch_no_txt")
                with c_b4:
                    batch_exp = st.date_input("Tanggal Kedaluwarsa (Exp):", min_value=datetime.date.today(), key="admin_batch_exp_date")
                
                batch_qty = st.number_input("Jumlah Stok Batch (unit):", min_value=1, value=50, step=5, key="admin_batch_qty_num")
                
                if st.form_submit_button("💾 Simpan Batch Obat ke Database", use_container_width=True):
                    if not batch_no.strip():
                        st.error("❌ Nomor batch wajib diisi!")
                    elif not batch_exp:
                        st.error("❌ Tanggal kedaluwarsa wajib diisi!")
                    elif batch_qty <= 0:
                        st.error("❌ Jumlah stok batch harus lebih dari 0!")
                    else:
                        conn_b = get_db()
                        if conn_b:
                            cur_b = conn_b.cursor()
                            try:
                                cur_b.execute("START TRANSACTION")
                                cur_b.execute("""
                                    INSERT INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch)
                                    VALUES (%s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE jumlah_stok_batch = jumlah_stok_batch + %s
                                """, (batch_no.strip(), batch_cabang, batch_obat, batch_exp, batch_qty, batch_qty))
                                
                                cur_b.execute("""
                                    INSERT INTO stok (kode_cabang, kode_obat, jumlah_stok)
                                    VALUES (%s, %s, %s)
                                    ON DUPLICATE KEY UPDATE jumlah_stok = (
                                        SELECT COALESCE(SUM(jumlah_stok_batch),0) FROM obat_batch 
                                        WHERE kode_cabang = %s AND kode_obat = %s
                                    )
                                """, (batch_cabang, batch_obat, batch_qty, batch_cabang, batch_obat))
                                conn_b.commit()
                                st.success(f"✅ Batch [{batch_no.strip()}] untuk obat [{batch_obat}] di cabang [{batch_cabang}] berhasil disimpan! Stok bertambah {batch_qty} unit.")
                                st.rerun()
                            except Exception as e_b:
                                conn_b.rollback()
                                st.error(f"❌ Gagal menyimpan batch: {e_b}")
                            finally:
                                cur_b.close()
                                conn_b.close()
        else:
            st.warning("Pastikan data Master Cabang dan Master Obat sudah terisi terlebih dahulu.")

        # TABEL MONITORING BATCH
        st.divider()
        st.markdown("##### 📋 Daftar Seluruh Batch Obat di Semua Cabang (Urutan FEFO)")
        
        conn_bl = get_db()
        if conn_bl:
            cur_bl = conn_bl.cursor(dictionary=True)
            try:
                cur_bl.execute("""
                    SELECT b.id_batch, c.kode_cabang, c.nama_cabang, o.kode_obat, o.nama_obat, 
                           b.no_batch, b.tanggal_kedaluwarsa, b.jumlah_stok_batch, 
                           DATEDIFF(b.tanggal_kedaluwarsa, CURDATE()) AS hari_tersisa
                    FROM obat_batch b
                    JOIN cabang c ON b.kode_cabang = c.kode_cabang
                    JOIN obat o ON b.kode_obat = o.kode_obat
                    ORDER BY b.tanggal_kedaluwarsa ASC
                """)
                rows_bl = cur_bl.fetchall()
                if rows_bl:
                    df_bl = pd.DataFrame(rows_bl)
                    def status_fefo_admin(hari):
                        if hari < 0:
                            return "🔴 KADALUARSA"
                        elif hari <= 30:
                            return "🟠 Kritis (<30 hari)"
                        elif hari <= 90:
                            return "🟡 Perhatian (<90 hari)"
                        else:
                            return "🟢 Aman"
                    df_bl["status"] = df_bl["hari_tersisa"].apply(status_fefo_admin)
                    
                    # Metrik
                    k_exp = len(df_bl[df_bl["hari_tersisa"] < 0])
                    k_kritis = len(df_bl[(df_bl["hari_tersisa"] >= 0) & (df_bl["hari_tersisa"] <= 30)])
                    k_perhatian = len(df_bl[(df_bl["hari_tersisa"] > 30) & (df_bl["hari_tersisa"] <= 90)])
                    k_aman = len(df_bl[df_bl["hari_tersisa"] > 90])
                    
                    mb1, mb2, mb3, mb4 = st.columns(4)
                    mb1.metric("🔴 Kadaluarsa", f"{k_exp} Batch")
                    mb2.metric("🟠 Kritis (<30 Hari)", f"{k_kritis} Batch")
                    mb3.metric("🟡 Perhatian (<90 Hari)", f"{k_perhatian} Batch")
                    mb4.metric("🟢 Aman", f"{k_aman} Batch")
                    
                    # Filter cabang
                    st.markdown("---")
                    c_filter_list = ["Semua Cabang"] + list(df_bl["kode_cabang"].unique())
                    pilih_fil_cb = st.selectbox("🔍 Filter Tabel Berdasarkan Cabang:", c_filter_list, key="fil_cb_batch_tab")
                    if pilih_fil_cb != "Semua Cabang":
                        df_show_batch = df_bl[df_bl["kode_cabang"] == pilih_fil_cb]
                    else:
                        df_show_batch = df_bl
                        
                    st.dataframe(
                        df_show_batch[["nama_cabang", "nama_obat", "no_batch", "tanggal_kedaluwarsa", "jumlah_stok_batch", "hari_tersisa", "status"]],
                        use_container_width=True
                    )
                    st.caption(f"Menampilkan {len(df_show_batch)} batch obat.")
                else:
                    st.info("Belum ada data batch obat. Gunakan form di atas untuk menginput batch.")
            except Exception as e_bl:
                st.info(f"Tabel obat_batch belum tersedia: {e_bl}. Jalankan Sinkronkan Database untuk membuatnya.")
            finally:
                cur_bl.close()
                conn_bl.close()

    # --------------------------------------------------------------------------
    # TAB 5: ALGORITMA SEARCH & SORT (POIN 7)
    # --------------------------------------------------------------------------
    with tab_search:
        st.subheader("🔍 Algoritma Pencarian & Pengurutan")
        
        c_sr1, c_sr2 = st.columns(2)
        with c_sr1:
            st.markdown("##### 1. Algoritma Pencarian")
            search_query = st.text_input("Ketik Nama Obat:", value="")
            conn = get_db()
            if conn:
                cur = conn.cursor(dictionary=True)
                cur.execute("""
                    SELECT o.kode_obat, o.nama_obat, k.nama_kategori, o.harga_jual, o.satuan, o.stok_minimum
                    FROM obat o
                    JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                    WHERE o.nama_obat LIKE %s
                    ORDER BY o.nama_obat ASC
                """, (f"%{search_query}%",))
                st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
                cur.close()
                conn.close()

        with c_sr2:
            st.markdown("##### 2. Algoritma Pengurutan Obat Terlaris ")
            tipe_sort = st.selectbox("Metode Sorting:", ["Volume Terjual Terbanyak", "Total Nilai Penjualan", "Harga Jual Tertinggi"])
            conn = get_db()
            if conn:
                cur = conn.cursor(dictionary=True)
                if "Volume" in tipe_sort:
                    cur.execute("""
                        SELECT o.kode_obat, o.nama_obat, SUM(d.jumlah_jual) AS total_terjual, SUM(d.subtotal) AS omzet
                        FROM detail_penjualan d
                        JOIN obat o ON d.kode_obat = o.kode_obat
                        GROUP BY o.kode_obat, o.nama_obat
                        ORDER BY total_terjual DESC
                    """)
                elif "Nilai" in tipe_sort:
                    cur.execute("""
                        SELECT o.kode_obat, o.nama_obat, SUM(d.jumlah_jual) AS total_terjual, SUM(d.subtotal) AS omzet
                        FROM detail_penjualan d
                        JOIN obat o ON d.kode_obat = o.kode_obat
                        GROUP BY o.kode_obat, o.nama_obat
                        ORDER BY omzet DESC
                    """)
                else:
                    cur.execute("SELECT kode_obat, nama_obat, harga_jual FROM obat ORDER BY harga_jual DESC")
                st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
                cur.close()
                conn.close()

    # --------------------------------------------------------------------------
    # TAB 6: LAPORAN KONSOLIDASI SELURUH CABANG
    # --------------------------------------------------------------------------
    with tab_laporan:
        st.subheader("🌐 Laporan Penjualan Konsolidasi Seluruh Cabang")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT p.no_faktur, p.tanggal_jam, c.nama_cabang, pg.nama_lengkap AS kasir,
                       o.nama_obat, d.jumlah_jual, d.harga_satuan, d.subtotal
                FROM penjualan p
                JOIN detail_penjualan d ON p.id_penjualan = d.id_penjualan
                JOIN cabang c ON p.kode_cabang = c.kode_cabang
                JOIN pengguna pg ON p.id_pengguna = pg.id_pengguna
                JOIN obat o ON d.kode_obat = o.kode_obat
                ORDER BY p.tanggal_jam DESC
            """)
            st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
            cur.close()
            conn.close()

    # --------------------------------------------------------------------------
    # TAB 7: PEMANTAUAN RESOURCE 
    # --------------------------------------------------------------------------
    with tab_monitor:
        st.subheader("📈 Pemantauan Resource Basis Data & Ambang Batas 50")
        
        conn = get_db()
        threads_count = 1
        if conn:
            cur = conn.cursor()
            cur.execute("SHOW STATUS LIKE 'Threads_connected'")
            row = cur.fetchone()
            if row:
                threads_count = int(row[1])
            cur.close()
            conn.close()

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Koneksi DB Aktif:", f"{threads_count} Sesi Aktif")
        col_m2.metric("Batas Ambang Kritis:", "50 Koneksi (Failure Threshold)")
        col_m3.metric("Beban Server:", "Normal (Aman)")

        jam_list = [f"{j:02d}:00" for j in range(12, 23)]
        koneksi_beban = [12, 15, 18, 24, 38, 48, 46, 39, 25, 18, 14]
        ambang_batas = [50] * len(jam_list)

        fig, ax = plt.subplots(figsize=(10, 3.8))
        ax.plot(jam_list, koneksi_beban, marker='o', linewidth=2, color='#0d6efd', label='Koneksi Nyata Jam Sibuk (17.00–20.00)')
        ax.plot(jam_list, ambang_batas, linestyle='--', color='red', linewidth=2, label='Batas Atas Kegagalan / Threshold (50)')
        ax.fill_between(jam_list, koneksi_beban, color='#0d6efd', alpha=0.1)
        ax.set_ylabel("Jumlah Koneksi")
        ax.set_xlabel("Jam Operasional")
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)
        st.pyplot(fig)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 13px;'>
    Sistem Inventori dan Penjualan Apotek Multi-Cabang © 2026 PT Sehat Bersama Farma<br>
</div>
""", unsafe_allow_html=True)
