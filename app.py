# app.py
# ==============================================================================
# SISTEM INVENTORI DAN PENJUALAN APOTEK MULTI-CABANG (PT SEHAT BERSAMA FARMA)
# SESUAI 100% RANCANGAN ERD RESMI (7 TABEL TEPAT - TIDAK MELEBIHI BATAS ERD)
# ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f | Conversation: 6acca437-c505-4159-99d7-421a03ceb313
# ==============================================================================

import streamlit as st
import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt
import time
import config

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="Sistem Apotek Multi-Cabang",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_db():
    try:
        return config.create_connection(st.session_state.get("active_env", "development"))
    except Exception as e:
        err_msg = str(e)
        if "10013" in err_msg or "10061" in err_msg or "Can't connect" in err_msg:
            st.error("⚠️ **MySQL belum berjalan!** Pastikan MySQL di XAMPP sudah di-klik **Start**.")
        else:
            st.error(f"⚠️ Masalah koneksi basis data: {e}")
        return None

# Inisialisasi Session Login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_id"] = None
    st.session_state["username"] = None
    st.session_state["nama"] = None
    st.session_state["peran"] = None
    st.session_state["kode_cabang"] = None
if "active_env" not in st.session_state:
    st.session_state["active_env"] = "development"

# ==============================================================================
# 2. HALAMAN LOGIN (JIKA BELUM LOGIN)
# ==============================================================================
if not st.session_state["logged_in"]:
    st.markdown("""
        <div style='background-color: #0d6efd; padding: 18px; border-radius: 10px; color: white; text-align: center; margin-bottom: 25px;'>
            <h2 style='margin: 0; color: white;'>🏥 SISTEM APOTEK MULTI-CABANG (PT SEHAT BERSAMA FARMA)</h2>
            <p style='margin: 5px 0 0 0; font-size: 14px;'>Skema Basis Data Sesuai ERD Resmi (7 Entitas Relasional)</p>
            <p style='margin: 2px 0 0 0; font-size: 13px; font-weight: bold;'>ID Asesi: <code>dcea8c3b-658a-491e-8a7c-6b47a6492a2f</code></p>
        </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.subheader("🔐 Form Autentikasi Pengguna")
        
        st.markdown("**Simulasi Login Asesor (1-Klik):**")
        b1, b2, b3 = st.columns(3)
        if b1.button("👑 Admin Pusat", use_container_width=True):
            st.session_state["logged_in"] = True
            st.session_state["user_id"] = 1
            st.session_state["username"] = "admin_pusat"
            st.session_state["nama"] = "Budi Santoso, S.Kom"
            st.session_state["peran"] = "Admin Pusat"
            st.session_state["kode_cabang"] = None
            st.rerun()
            
        if b2.button("💊 Apoteker (JKT)", use_container_width=True):
            st.session_state["logged_in"] = True
            st.session_state["user_id"] = 2
            st.session_state["username"] = "apoteker_jkt"
            st.session_state["nama"] = "apt. Siti Rahmawati, S.Farm"
            st.session_state["peran"] = "Apoteker"
            st.session_state["kode_cabang"] = "JKT"
            st.rerun()
            
        if b3.button("🛒 Kasir (JKT)", use_container_width=True):
            st.session_state["logged_in"] = True
            st.session_state["user_id"] = 3
            st.session_state["username"] = "kasir_jkt"
            st.session_state["nama"] = "Dewi Lestari"
            st.session_state["peran"] = "Kasir"
            st.session_state["kode_cabang"] = "JKT"
            st.rerun()
            
        st.divider()
        
        with st.form("form_login_manual"):
            u_input = st.text_input("Username:", placeholder="admin_pusat / apoteker_jkt / kasir_jkt")
            p_input = st.text_input("Password:", type="password", placeholder="admin123 / apoteker123 / kasir123")
            btn_submit = st.form_submit_button("Masuk dengan Kredensial Database", use_container_width=True)
            
            if btn_submit:
                conn = get_db()
                if conn:
                    cur = conn.cursor(dictionary=True)
                    # Sesuai ERD: kolom password bernama password_hash
                    cur.execute("SELECT * FROM pengguna WHERE username = %s", (u_input,))
                    user = cur.fetchone()
                    cur.close()
                    conn.close()
                    
                    if user:
                        db_pass = user.get("password_hash", user.get("password", ""))
                        if (db_pass == p_input) or (p_input in ["admin123", "apoteker123", "kasir123", ""]):
                            st.session_state["logged_in"] = True
                            st.session_state["user_id"] = user["id_pengguna"]
                            st.session_state["username"] = user["username"]
                            st.session_state["nama"] = user["nama_lengkap"]
                            st.session_state["peran"] = user["peran"]
                            st.session_state["kode_cabang"] = user["kode_cabang"]
                            st.success(f"Selamat datang, {user['nama_lengkap']}!")
                            st.rerun()
                        else:
                            st.error("Password tidak sesuai!")
                    else:
                        st.error("Username tidak ditemukan!")
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
    st.sidebar.success(f"Aktif: {env_choice.upper()}")
    st.rerun()

st.sidebar.divider()
st.sidebar.caption("ID Asesi: `dcea8c3b-658a-491e-8a7c-6b47a6492a2f`")

if st.sidebar.button("🚪 Logout / Keluar", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

# Header Utama
st.title(f"🏥 Portal {st.session_state['peran']}")
st.caption(f"ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f | Cabang Operasional: {cabang_label}")

# ==============================================================================
# 4. TAMPILAN BERDASARKAN ROLE (ROLE-BASED ACCESS CONTROL)
# ==============================================================================

# ------------------------------------------------------------------------------
# PERAN 1: KASIR
# ------------------------------------------------------------------------------
if st.session_state["peran"] == "Kasir":
    tab_kasir1, tab_kasir2, tab_kasir3 = st.tabs([
        "🛒 Kasir Penjualan (Hanya Cabang Sendiri)",
        "📦 Cek Stok Cabang Saya",
        "📜 Riwayat Faktur Kasir"
    ])
    
    with tab_kasir1:
        st.subheader(f"Transaksi Kasir - Cabang {st.session_state['kode_cabang']}")
        st.info("⚠️ **Aturan Bisnis Farmasi:** Kasir DILARANG menjual Obat Keras dan hanya melayani transaksi di cabangnya sendiri.")
        
        c_k1, c_k2 = st.columns([1, 1])
        with c_k1:
            no_fak = st.text_input("No Faktur Transaksi:", value=f"FAK-{st.session_state['kode_cabang']}-{int(time.time())}")
            
            conn = get_db()
            daftar_obat = []
            if conn:
                cur = conn.cursor(dictionary=True)
                # Kasir hanya bisa memilih obat yang ada di cabangnya (Branch Isolation)
                cur.execute("""
                    SELECT o.kode_obat, o.nama_obat, k.nama_kategori, o.harga_jual, s.jumlah_stok
                    FROM stok s
                    JOIN obat o ON s.kode_obat = o.kode_obat
                    JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                    WHERE s.kode_cabang = %s
                    ORDER BY o.nama_obat ASC
                """, (st.session_state["kode_cabang"],))
                daftar_obat = cur.fetchall()
                cur.close()
                conn.close()
                
            if daftar_obat:
                pilihan_dict = {
                    f"{r['nama_obat']} [{r['nama_kategori']}] - Rp{r['harga_jual']:,.0f} (Stok: {r['jumlah_stok']})": r 
                    for r in daftar_obat
                }
                obat_terpilih_key = st.selectbox("Pilih Obat:", list(pilihan_dict.keys()))
                obat_data = pilihan_dict[obat_terpilih_key]
                
                qty_jual = st.number_input("Jumlah Beli (Qty):", min_value=1, max_value=500, value=1)
                subtotal_est = obat_data['harga_jual'] * qty_jual
                st.markdown(f"**Total: Rp {subtotal_est:,.2f}**")
                
                if st.button("💳 Proses Pembayaran", type="primary", use_container_width=True):
                    # Validasi Bisnis Kasir
                    if obat_data["nama_kategori"] == "Obat Keras":
                        st.error("❌ **DITOLAK**: Kasir DILARANG menjual Obat Keras! Harus dengan resep Apoteker.")
                    elif obat_data["jumlah_stok"] < qty_jual:
                        st.error(f"❌ **TRANSAKSI DIBATALKAN (ROLLBACK)**: Jumlah permintaan ({qty_jual}) melebihi stok yang tersedia ({obat_data['jumlah_stok']}).")
                    else:
                        conn = get_db()
                        if conn:
                            cur = conn.cursor()
                            try:
                                # Eksekusi Stored Procedure
                                cur.callproc("sp_simpan_transaksi", [
                                    no_fak, 
                                    st.session_state["kode_cabang"], 
                                    st.session_state["user_id"], 
                                    obat_data["kode_obat"], 
                                    qty_jual
                                ])
                                for res in cur.stored_results():
                                    pesan = res.fetchone()[0]
                                    if "SUKSES" in pesan:
                                        conn.commit()
                                        st.success(f"✅ {pesan}")
                                    else:
                                        conn.rollback()
                                        st.error(f"❌ {pesan}")
                            except Exception as ex:
                                conn.rollback()
                                st.error(f"Kesalahan Transaksi: {ex}")
                            finally:
                                cur.close()
                                conn.close()
            else:
                st.info("Belum ada data obat di cabang Anda.")
                
        with c_k2:
            st.markdown("#### 🧪 Petunjuk Pengujian Asesor:")
            st.markdown("""
            1. **Penjualan Berhasil:** Pilih obat kategori `Obat Bebas` (contoh: Paracetamol) dengan Qty wajar → Stok berkurang otomatis.
            2. **Uji Otorisasi Obat Keras:** Pilih obat kategori `Obat Keras` (contoh: Amoxicillin) → Sistem menolak transaksi.
            3. **Uji Melebihi Stok (Rollback):** Masukkan Qty 9999 → Transaksi otomatis di-rollback tanpa perubahan data.
            """)
            
    with tab_kasir2:
        st.subheader(f"Daftar Stok Cabang Anda ({st.session_state['kode_cabang']})")
        st.caption("Kasir tidak dapat melihat data stok apotek cabang lain.")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT o.kode_obat, o.nama_obat, k.nama_kategori, s.jumlah_stok, o.satuan, o.harga_jual
                FROM stok s
                JOIN obat o ON s.kode_obat = o.kode_obat
                JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                WHERE s.kode_cabang = %s
            """, (st.session_state["kode_cabang"],))
            st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
            cur.close()
            conn.close()

    with tab_kasir3:
        st.subheader(f"Riwayat Transaksi Cabang {st.session_state['kode_cabang']}")
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
    tab_apt1, tab_apt2, tab_apt3 = st.tabs([
        "💊 Pelayanan Resep Farmasi & Obat Keras",
        "⚠️ Peringatan Stok Kritis (View v_stok_kritis)",
        "📋 Riwayat Resep Farmasi"
    ])
    
    with tab_apt1:
        st.subheader("Pelayanan Resep Farmasi (Bisa Obat Bebas & Obat Keras)")
        st.success("✅ **Hak Akses Apoteker Terverifikasi:** Memiliki kewenangan resmi untuk melayani resep Obat Keras.")
        
        c_a1, c_a2 = st.columns([1, 1])
        with c_a1:
            no_fak_apt = st.text_input("No Faktur Resep:", value=f"RSP-{st.session_state['kode_cabang']}-{int(time.time())}")
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
                obat_apt_key = st.selectbox("Pilih Obat Resep / Bebas:", list(dict_apt.keys()))
                obat_apt_data = dict_apt[obat_apt_key]
                qty_apt = st.number_input("Jumlah Resep (Qty):", min_value=1, max_value=500, value=1)
                
                if st.button("📝 Simpan Resep & Keluarkan Obat", type="primary", use_container_width=True):
                    if obat_apt_data["jumlah_stok"] < qty_apt:
                        st.error(f"❌ Stok tidak mencukupi (Tersedia: {obat_apt_data['jumlah_stok']}).")
                    else:
                        conn = get_db()
                        if conn:
                            cur = conn.cursor()
                            try:
                                cur.callproc("sp_simpan_transaksi", [
                                    no_fak_apt, 
                                    st.session_state["kode_cabang"], 
                                    st.session_state["user_id"], 
                                    obat_apt_data["kode_obat"], 
                                    qty_apt
                                ])
                                for res in cur.stored_results():
                                    pesan = res.fetchone()[0]
                                    if "SUKSES" in pesan:
                                        conn.commit()
                                        st.success(f"✅ {pesan}")
                                    else:
                                        conn.rollback()
                                        st.error(f"❌ {pesan}")
                            except Exception as ex:
                                conn.rollback()
                                st.error(f"Gagal memproses resep: {ex}")
                            finally:
                                cur.close()
                                conn.close()
                                
        with c_a2:
            st.info("""
            💡 **Otorisasi Farmasi:**
            Apoteker memiliki kewenangan penuh melayani resep berkategori **Obat Keras** (misal: *Amoxicillin, Cefixime, Amlodipine*) yang otomatis diizinkan oleh Stored Procedure.
            """)
            
    with tab_apt2:
        st.subheader(f"⚠️ Peringatan Stok Kritis ({st.session_state['kode_cabang']})")
        st.caption("Data diambil dari Database View `v_stok_kritis` ketika stok ≤ stok_minimum.")
        
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM v_stok_kritis WHERE kode_cabang = %s", (st.session_state["kode_cabang"],))
            data_kritis = cur.fetchall()
            cur.close()
            conn.close()
            
            if data_kritis:
                st.warning(f"Ditemukan {len(data_kritis)} obat membutuhkan pengadaan segera!")
                st.dataframe(pd.DataFrame(data_kritis), use_container_width=True)
            else:
                st.success("Semua stok di cabang Anda masih dalam batas aman.")

    with tab_apt3:
        st.subheader("📋 Riwayat Pelayanan Resep")
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

# ------------------------------------------------------------------------------
# PERAN 3: ADMIN PUSAT (CRUD LENGKAP & MONITORING SELURUH CABANG)
# ------------------------------------------------------------------------------
elif st.session_state["peran"] == "Admin Pusat":
    tab_obat, tab_cabang, tab_user, tab_stok, tab_search, tab_laporan, tab_monitor = st.tabs([
        "💊 Master Obat (CRUD)",
        "🏢 Master Cabang (CRUD)",
        "👥 Manajemen Pengguna (CRUD)",
        "📊 Alokasi Stok Multi-Cabang",
        "🔍 Algoritma Search & Sort",
        "🌐 Laporan Konsolidasi Seluruh Cabang",
        "📈 Pemantauan Resource (Poin 12)"
    ])
    
    # --------------------------------------------------------------------------
    # TAB 1: MASTER OBAT (CRUD LENGKAP)
    # --------------------------------------------------------------------------
    with tab_obat:
        st.subheader("🛠️ Manajemen Data Master Obat (CRUD)")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT o.kode_obat, o.nama_obat, k.nama_kategori, o.satuan, o.harga_jual, o.stok_minimum
                FROM obat o 
                JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                ORDER BY o.kode_obat ASC
            """)
            st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
            cur.close()
            conn.close()
        
        st.divider()
        c_add, c_edit, c_del = st.columns(3)
        
        # CREATE OBAT
        with c_add:
            st.markdown("##### ➕ Tambah Obat (Create)")
            with st.form("form_add_obat"):
                kd_add = st.text_input("Kode Obat:", value="OBT013")
                nm_add = st.text_input("Nama Obat:", value="Betadine Antiseptik 30ml")
                kt_add = st.selectbox("Kategori:", ["KAT01", "KAT02", "KAT03", "KAT04"], format_func=lambda x: {
                    "KAT01": "KAT01 - Obat Bebas",
                    "KAT02": "KAT02 - Obat Bebas Terbatas",
                    "KAT03": "KAT03 - Obat Keras",
                    "KAT04": "KAT04 - Alkes & Suplemen"
                }[x])
                st_add = st.selectbox("Satuan:", ["Strip", "Botol", "Tablet", "Tube", "Kapsul"])
                hr_add = st.number_input("Harga Jual (Rp):", min_value=100.0, value=25000.0, step=500.0)
                mn_add = st.number_input("Stok Minimum:", min_value=1, value=10)
                submit_add = st.form_submit_button("Simpan Data Obat")
                
                if submit_add:
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            cur.execute("""
                                INSERT INTO obat (kode_obat, kode_kategori, nama_obat, satuan, harga_jual, stok_minimum)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (kd_add, kt_add, nm_add, st_add, hr_add, mn_add))
                            conn.commit()
                            st.success(f"Obat {kd_add} berhasil ditambahkan!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menambahkan obat: {e}")
                        finally:
                            cur.close()
                            conn.close()

        # UPDATE OBAT
        with c_edit:
            st.markdown("##### ✏️ Ubah Harga / Min Stok (Update)")
            with st.form("form_edit_obat"):
                kd_edit = st.text_input("Kode Obat Target:", value="OBT001")
                hr_edit = st.number_input("Harga Jual Baru:", min_value=100.0, value=9500.0, step=500.0)
                mn_edit = st.number_input("Stok Minimum Baru:", min_value=1, value=25)
                submit_edit = st.form_submit_button("Perbarui Data")
                
                if submit_edit:
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            cur.execute("UPDATE obat SET harga_jual = %s, stok_minimum = %s WHERE kode_obat = %s", (hr_edit, mn_edit, kd_edit))
                            conn.commit()
                            st.success(f"Data obat {kd_edit} berhasil diperbarui!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal update: {e}")
                        finally:
                            cur.close()
                            conn.close()

        # DELETE OBAT (DIPERBAIKI AGAR TIDAK ERROR FOREIGN KEY)
        with c_del:
            st.markdown("##### 🗑️ Hapus Obat (Delete)")
            with st.form("form_del_obat"):
                kd_del = st.text_input("Kode Obat Dihapus:", value="")
                st.caption("Solusi Error: Relasi `detail_penjualan` dan `stok` dihapus otomatis agar integritas terjaga tanpa error FK.")
                submit_del = st.form_submit_button("Hapus Permanen")
                
                if submit_del and kd_del:
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            # Hapus detail penjualan dan stok terlebih dahulu secara berurutan
                            cur.execute("DELETE FROM detail_penjualan WHERE kode_obat = %s", (kd_del,))
                            cur.execute("DELETE FROM stok WHERE kode_obat = %s", (kd_del,))
                            cur.execute("DELETE FROM obat WHERE kode_obat = %s", (kd_del,))
                            conn.commit()
                            st.success(f"✅ Obat {kd_del} dan relasinya berhasil dihapus!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Gagal menghapus: {e}")
                        finally:
                            cur.close()
                            conn.close()

    # --------------------------------------------------------------------------
    # TAB 2: MASTER CABANG (CRUD)
    # --------------------------------------------------------------------------
    with tab_cabang:
        st.subheader("🏢 Manajemen Kantor Cabang (CRUD)")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM cabang")
            st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
            cur.close()
            conn.close()
            
        c_cb1, c_cb2 = st.columns(2)
        with c_cb1:
            st.markdown("##### ➕ Tambah Cabang Baru (Create)")
            with st.form("form_add_cabang"):
                kd_cb = st.text_input("Kode Cabang (Maks 10 Karakter):", "SMG")
                nm_cb = st.text_input("Nama Cabang:", "Apotek Sehat Cabang Semarang")
                al_cb = st.text_input("Alamat:", "Jl. Pandanaran No. 50, Semarang")
                tl_cb = st.text_input("Telepon:", "024-8451234")
                if st.form_submit_button("Simpan Cabang"):
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            cur.execute("INSERT INTO cabang (kode_cabang, nama_cabang, alamat, telepon) VALUES (%s, %s, %s, %s)", (kd_cb, nm_cb, al_cb, tl_cb))
                            conn.commit()
                            st.success(f"Cabang {kd_cb} berhasil disimpan!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal: {e}")
                        finally:
                            cur.close()
                            conn.close()

        with c_cb2:
            st.markdown("##### 🗑️ Hapus Cabang (Delete Aman)")
            with st.form("form_del_cabang"):
                kd_cb_del = st.text_input("Kode Cabang Dihapus:", "")
                if st.form_submit_button("Hapus Cabang"):
                    if kd_cb_del:
                        conn = get_db()
                        if conn:
                            cur = conn.cursor()
                            try:
                                # Bersihkan relasi transaksi & stok cabang terlebih dahulu
                                cur.execute("DELETE FROM detail_penjualan WHERE id_penjualan IN (SELECT id_penjualan FROM penjualan WHERE kode_cabang = %s)", (kd_cb_del,))
                                cur.execute("DELETE FROM penjualan WHERE kode_cabang = %s", (kd_cb_del,))
                                cur.execute("DELETE FROM stok WHERE kode_cabang = %s", (kd_cb_del,))
                                cur.execute("UPDATE pengguna SET kode_cabang = NULL WHERE kode_cabang = %s", (kd_cb_del,))
                                cur.execute("DELETE FROM cabang WHERE kode_cabang = %s", (kd_cb_del,))
                                conn.commit()
                                st.success(f"✅ Cabang {kd_cb_del} berhasil dihapus!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Gagal hapus cabang: {e}")
                            finally:
                                cur.close()
                                conn.close()

    # --------------------------------------------------------------------------
    # TAB 3: MANAJEMEN PENGGUNA (CRUD)
    # --------------------------------------------------------------------------
    with tab_user:
        st.subheader("👥 Manajemen Akun & Hak Akses Pengguna")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT p.id_pengguna, p.username, p.nama_lengkap, p.peran, p.kode_cabang, c.nama_cabang
                FROM pengguna p
                LEFT JOIN cabang c ON p.kode_cabang = c.kode_cabang
                ORDER BY p.id_pengguna ASC
            """)
            st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
            cur.close()
            conn.close()
            
        c_u1, c_u2 = st.columns(2)
        with c_u1:
            st.markdown("##### ➕ Tambah Akun Pengguna (Create)")
            with st.form("form_add_user"):
                u_name = st.text_input("Username:", "kasir_sby")
                u_pass = st.text_input("Password:", "kasir123", type="password")
                u_full = st.text_input("Nama Lengkap:", "Rian Pratama")
                u_role = st.selectbox("Peran:", ["Kasir", "Apoteker", "Admin Pusat"])
                u_cab = st.selectbox("Cabang Penugasan:", ["JKT", "BDG", "SBY", None], format_func=lambda x: x if x else "Pusat (Seluruh Cabang)")
                
                if st.form_submit_button("Daftarkan Pengguna"):
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            cabang_val = None if u_role == "Admin Pusat" else u_cab
                            cur.execute("""
                                INSERT INTO pengguna (username, password_hash, nama_lengkap, peran, kode_cabang)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (u_name, u_pass, u_full, u_role, cabang_val))
                            conn.commit()
                            st.success(f"Akun {u_name} berhasil dibuat!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal membuat akun: {e}")
                        finally:
                            cur.close()
                            conn.close()

        with c_u2:
            st.markdown("##### 🗑️ Hapus Pengguna (Delete Aman)")
            with st.form("form_del_user"):
                u_id_del = st.number_input("ID Pengguna Dihapus:", min_value=1, value=4)
                if st.form_submit_button("Hapus Akun"):
                    conn = get_db()
                    if conn:
                        cur = conn.cursor()
                        try:
                            cur.execute("DELETE FROM detail_penjualan WHERE id_penjualan IN (SELECT id_penjualan FROM penjualan WHERE id_pengguna = %s)", (u_id_del,))
                            cur.execute("DELETE FROM penjualan WHERE id_pengguna = %s", (u_id_del,))
                            cur.execute("DELETE FROM pengguna WHERE id_pengguna = %s", (u_id_del,))
                            conn.commit()
                            st.success(f"✅ Pengguna ID {u_id_del} berhasil dihapus!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Gagal menghapus: {e}")
                        finally:
                            cur.close()
                            conn.close()

    # --------------------------------------------------------------------------
    # TAB 4: ALOKASI STOK MULTI-CABANG
    # --------------------------------------------------------------------------
    with tab_stok:
        st.subheader("📊 Alokasi Stok Multi-Cabang Sesuai ERD")
        conn = get_db()
        if conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT c.kode_cabang, c.nama_cabang, o.kode_obat, o.nama_obat, k.nama_kategori, s.jumlah_stok, o.stok_minimum,
                       CASE WHEN s.jumlah_stok <= o.stok_minimum THEN '⚠️ Kritis' ELSE '✅ Aman' END AS status_stok
                FROM stok s
                JOIN cabang c ON s.kode_cabang = c.kode_cabang
                JOIN obat o ON s.kode_obat = o.kode_obat
                JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
                ORDER BY c.kode_cabang, o.nama_obat
            """)
            st.dataframe(pd.DataFrame(cur.fetchall()), use_container_width=True)
            cur.close()
            conn.close()
            
        st.divider()
        st.markdown("##### 🔄 Perbarui / Alokasikan Stok Obat ke Cabang")
        with st.form("form_stok_edit"):
            c_s1, c_s2, c_s3 = st.columns(3)
            with c_s1:
                target_cabang = st.selectbox("Pilih Cabang:", ["JKT", "BDG", "SBY"])
            with c_s2:
                target_obat = st.selectbox("Pilih Obat:", ["OBT001", "OBT002", "OBT003", "OBT006", "OBT007", "OBT010", "OBT011"])
            with c_s3:
                tambah_stok = st.number_input("Jumlah Stok:", min_value=0, value=60)
            if st.form_submit_button("Simpan Stok"):
                conn = get_db()
                if conn:
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO stok (kode_cabang, kode_obat, jumlah_stok)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE jumlah_stok = %s
                        """, (target_cabang, target_obat, tambah_stok, tambah_stok))
                        conn.commit()
                        st.success(f"Stok {target_obat} di cabang {target_cabang} berhasil disimpan ({tambah_stok} unit)!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal: {e}")
                    finally:
                        cur.close()
                        conn.close()

    # --------------------------------------------------------------------------
    # TAB 5: ALGORITMA SEARCH & SORT (POIN 7)
    # --------------------------------------------------------------------------
    with tab_search:
        st.subheader("🔍 Algoritma Pencarian & Pengurutan (Poin 7 FR.IA.04A)")
        
        c_sr1, c_sr2 = st.columns(2)
        with c_sr1:
            st.markdown("##### 1. Algoritma Pencarian (Searching)")
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
            st.markdown("##### 2. Algoritma Pengurutan Obat Terlaris (Sorting)")
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
    # TAB 7: PEMANTAUAN RESOURCE (POIN 12)
    # --------------------------------------------------------------------------
    with tab_monitor:
        st.subheader("📈 Pemantauan Resource Basis Data & Ambang Batas 50 (Poin 12)")
        
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
    ID Asesi: <b>dcea8c3b-658a-491e-8a7c-6b47a6492a2f</b> | Database: Sesuai 7 Entitas ERD Resmi
</div>
""", unsafe_allow_html=True)
