# DOKUMEN HASIL ASESMEN UJI KOMPETENSI (FR.IA.04A)
## SKEMA: PROGRAMMER BASIS DATA (DATABASE PROGRAMMER) - SKK-26/20/2024
**ID Asesi / Dokumen Terverifikasi:** `dcea8c3b-658a-491e-8a7c-6b47a6492a2f`  
**Studi Kasus:** Pengembangan Basis Data Sistem Inventori dan Penjualan Apotek Multi-Cabang  
**Perusahaan:** PT Sehat Bersama Farma  

---

## 1. METODE STAR (Situation – Task – Action – Result)

### S – Situation (Situasi)
PT Sehat Bersama Farma mengelola cabang apotek di Jabodetabek (Jakarta, Bandung, Surabaya, dll.). Permasalahan utama sistem lama:
1. Stok antar-cabang tidak sinkron dan rawan minus.
2. Kueri laporan penjualan bulanan sangat lambat (> 30 detik pada jam sibuk 17.00–20.00).
3. Modul penjualan legacy rawan SQL Injection, tanpa transaction rollback, dan tidak standar.
4. Kata sandi pengguna plain-text dan menggunakan akun `root`.
5. Tidak ada pemisahan environment (*Development, Staging, Production*).

### T – Task (Tugas)
Merancang arsitektur basis data relasional 3NF, menyusun DDL/DML, stored procedure, triggers, view, function, mengamankan akses database non-root, merefaktor modul legacy, mengimplementasikan algoritma pencarian & sorting, memantau resource, dan menyiapkan skrip migrasi FEFO di staging.

### A – Action (Langkah Kerja yang Dilakukan)
1. **Analisis Tools & Library:** Menggunakan MySQL/MariaDB (InnoDB), Python 3.14, Streamlit, `mysql-connector-python`, Pandas, dan Matplotlib.
2. **Normalisasi & ERD (3NF):** Merancang entitas `cabang`, `kategori_obat`, `pengguna`, `obat`, `stok`, `obat_batch`, `penjualan`, `detail_penjualan`, dan `log_aktivitas`.
3. **Penyusunan DDL & Integritas:** Menggunakan *Foreign Keys* dengan aksi `CASCADE`/`RESTRICT`, tipe data presisi moneter `DECIMAL(12,2)`, dan indeks B-Tree.
4. **Stored Procedure Atomik:** Membangun `sp_simpan_transaksi` dengan `START TRANSACTION`, `COMMIT`, dan `ROLLBACK` otomatis saat stok tidak mencukupi atau Kasir mencoba menjual Obat Keras.
5. **View Stok Kritis:** Membangun view `v_stok_kritis` untuk otomatisasi alert re-stock ketika stok fisik $\le$ stok minimum.
6. **Refaktorisasi Modul Legacy:** Menghapus konkatenasi string SQL Injection, menggantinya dengan Prepared Statement, dan mengoptimalkan kueri laporan bulanan.
7. **Multi-Environment:** Mengonfigurasi `config.py` yang memisahkan `development`, `staging`, dan `production`.
8. **Analisis FEFO:** Membuat skrip migrasi tabel `obat_batch` untuk penjualan berbasis kedaluwarsa tercepat beserta rencana rollback.
9. **Monitoring Resource:** Menampilkan visualisasi grafis koneksi jam sibuk dengan garis ambang batas kritis (Threshold: 50 koneksi).
10. **Standar Keamanan (ISO 27001):** Menyusun matriks RBAC dan tabel audit trail `log_aktivitas`.

### R – Result (Hasil Akhir & Demonstrasi)
- Sistem berjalan interaktif di web portal Streamlit.
- Transaksi otomatis memotong stok cabang dan menolak pembelian jika stok tidak cukup (*rollback*).
- Kasir diblokir saat mencoba menjual *Obat Keras* (hanya Apoteker yang berhak).
- Kasir dan Apoteker hanya dapat melihat stok cabangnya sendiri (*branch isolation*).
- Kueri laporan penjualan dipangkas dari > 30 detik menjadi < 0.05 detik.

---

## 2. MATRIKS UNIT KOMPETENSI (14 UNIT KOMPETENSI)

| No | Kode Unit | Judul Unit | Implementasi dalam Proyek |
|---|---|---|---|
| 1 | J.620100.001.01 | Menganalisis Tools | DBMS MySQL/MariaDB, IDE VS Code, Git, Streamlit Web Portal |
| 2 | J.620100.003.01 | Identifikasi Library / Framework | `mysql-connector-python`, `pandas`, `matplotlib` |
| 3 | J.620100.004.02 | Menggunakan Struktur Data | Tabel relasional 3NF, B-Tree index, Hash dictionary sesi |
| 4 | J.620100.007.01 | Mengimplementasikan Rancangan Entitas | ERD 3NF, relasi M:N diselesaikan via tabel `stok` dan `detail_penjualan` |
| 5 | J.620100.020.02 | Menggunakan SQL | DDL, DML seed, View `v_stok_kritis`, Procedure `sp_simpan_transaksi`, Function `fn_hitung_total_faktur`, Trigger `trg_audit_perubahan_harga`, COMMIT/ROLLBACK |
| 6 | J.620100.021.02 | Menerapkan Akses Basis Data | Koneksi Prepared Statement, akun `app_apotek` (bukan root), CRUD lengkap |
| 7 | J.620100.022.02 | Mengimplementasikan Algoritma | Searching nama obat ($O(\log N)$) & Sorting obat terlaris ($O(N \log N)$) |
| 8 | J.620100.025.02 | Melakukan Debugging | Penanganan kegagalan kueri, logging error, penangkapan exception database |
| 9 | J.620100.032.01 | Menerapkan Code Review | Perbaikan modul legacy (eliminasi SQL Injection) & optimasi kueri laporan |
| 10 | J.620100.042.01 | Konfigurasi Environment | File `config.py` memisahkan Development, Staging, dan Production |
| 11 | J.620100.043.01 | Menganalisis Dampak Perubahan | Fitur Batch & Tanggal Kedaluwarsa (FEFO) |
| 12 | J.620100.045.01 | Pemantauan Resource | Grafik pemantauan koneksi jam sibuk (17.00-20.00) vs batas atas 50 koneksi |
| 13 | J.620100.047.01 | Pembaharuan Perangkat Lunak | Skrip migrasi `migrasi_staging_fefo.sql` & skrip rollback di staging |
| 14 | J.62090.011.01 | Menerapkan Standar Keamanan | SNI ISO/IEC 27001, Matriks RBAC, Password Hashing SHA-256 (One-Way Hashing), Validasi Mandatory Input (Zero-Empty-Field) |

---

## 3. PANDUAN DEMONSTRASI PENGUJIAN ASESOR

1. **Uji 1: Penjualan Berhasil (Stok Berkurang Otomatis)**
   - Login sebagai `kasir_jkt` (Password: `kasir123`).
   - Pilih obat *Paracetamol 500mg (Obat Bebas)*, isi Qty = 2, klik Proses Pembayaran.
   - Hasil: Transaksi berhasil, nomor faktur tercatat, stok Paracetamol cabang JKT berkurang 2 unit.

2. **Uji 2: Penjualan Melebihi Stok (Ditolak & Rollback)**
   - Tetap di akun `kasir_jkt`.
   - Masukkan Qty = 9999 (melebihi stok fisik).
   - Hasil: Muncul pesan kesalahan, transaksi dibatalkan secara atomik (ROLLBACK), tidak ada pemotongan stok.

3. **Uji 3: Kasir Menjual Obat Keras (Ditolak Sistem)**
   - Tetap di akun `kasir_jkt`.
   - Pilih obat berkategori *Obat Keras* (contoh: *Amoxicillin 500mg*).
   - Hasil: Sistem menolak dengan pesan *“Kasir DILARANG menjual Obat Keras! Resep harus dilayani oleh Apoteker.”*

4. **Uji 4: Otorisasi Apoteker (Bisa Jual Obat Keras & Lihat Stok Kritis)**
   - Logout lalu Login sebagai `apoteker_jkt` (Password: `apoteker123`).
   - Pilih obat *Amoxicillin 500mg*, isi Qty = 1, klik Simpan Resep.
   - Hasil: Transaksi berhasil diproses.
   - Buka tab *Peringatan Stok Kritis*: Tampil data obat yang stoknya $\le$ stok minimum (`v_stok_kritis`).

5. **Uji 5: Admin_Pusat (CRUD Master Data & Monitoring)**
   - Logout lalu Login sebagai `admin_pusat` (Password: `admin123`).
   - Akses tab *Master Obat*, coba fitur Create (kode auto-increment OBTxxx), Update harga, dan Delete (dilengkapi Safety Guard di Production).
   - Akses tab *Master Cabang* (kode auto-increment CAB-xxx, nama unik).
   - Akses tab *Alokasi Stok Multi-Cabang* (dropdown dinamis membaca dari basis data).
   - Akses tab *Algoritma Search & Sort*, *Laporan Konsolidasi*, dan *Pemantauan Resource (Threads_connected vs batas 50)*.

6. **Uji 6: Demonstrasi Multi-Environment Staging vs Production (Poin 10 & 13)**
   - Di Sidebar, perhatikan switcher environment: **Development**, **Staging**, dan **Production**.
   - Saat beralih ke **Production**, sistem menampilkan banner merah mencolok dan safety confirmation checkbox pada aksi penghapusan data.
   - Saat beralih ke **Staging**, sistem terhubung ke `db_apotek_staging`.
   - Buka tab **"🚀 Staging & Production (DevOps)"** di portal Admin Pusat:
     - Tunjukkan perbandingan metrik tabel antara Staging dan Production.
     - Klik tombol **"▶️ Terapkan Patch FEFO ke Staging"**: skrip migrasi `migrasi_staging_fefo.sql` dieksekusi di Staging dan membuat tabel `obat_batch` tanpa mengganggu database Production (`db_apotek_sehat`).
     - Klik tombol **"⏪ Jalankan Rollback di Staging"**: skema Staging kembali ke 7 tabel murni ERD secara aman.
     - Ini membuktikan pemahaman mendalam tentang siklus rilis perangkat lunak (Release Lifecycle) dan mitigasi risiko operasional.
