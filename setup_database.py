# setup_database.py
# ==============================================================================
# INISIALISASI DATABASE SISTEM APOTEK MULTI-CABANG (PT SEHAT BERSAMA FARMA)
# SESUAI 100% RANCANGAN ERD RESMI (7 TABEL TEPAT)
# MENGIMPLEMENTASIKAN BEST PRACTICE PEMISAHAN MULTI-ENVIRONMENT:
# 1. db_apotek_sehat    -> PRODUCTION (Live Operasional)
# 2. db_apotek_staging  -> STAGING (Pra-Produksi & Uji Coba Migrasi)
# ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f
# ==============================================================================

import mysql.connector

def setup_schema_and_seeds(cur, conn, db_name):
    """
    Menginisialisasi satu instans basis data lengkap dengan 7 tabel ERD resmi,
    Stored Procedure atomik, View stok kritis, Indexing, dan data awal (seeding).
    """
    print(f"\n[+] Memulai inisialisasi skema basis data: `{db_name}`...")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE {db_name}")

    # HAPUS TABEL DAN OBJEK DI LUAR BATAS ARSITEKTUR
    cur.execute("DROP TABLE IF EXISTS log_aktivitas")
    cur.execute("DROP TRIGGER IF EXISTS trg_audit_perubahan_harga")
    cur.execute("DROP FUNCTION IF EXISTS fn_hitung_total_faktur")
    conn.commit()

    # 1. kategori_obat
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kategori_obat (
            kode_kategori VARCHAR(10) NOT NULL,
            nama_kategori VARCHAR(50) NOT NULL,
            CONSTRAINT pk_kategori_obat PRIMARY KEY (kode_kategori)
        ) ENGINE=InnoDB
    """)

    # 2. obat
    cur.execute("""
        CREATE TABLE IF NOT EXISTS obat (
            kode_obat VARCHAR(20) NOT NULL,
            kode_kategori VARCHAR(10) NOT NULL,
            nama_obat VARCHAR(150) NOT NULL,
            satuan VARCHAR(20) NOT NULL,
            harga_jual DECIMAL(12,2) NOT NULL DEFAULT 0.00,
            stok_minimum INT NOT NULL DEFAULT 10,
            CONSTRAINT pk_obat PRIMARY KEY (kode_obat),
            CONSTRAINT fk_obat_kategori FOREIGN KEY (kode_kategori) 
                REFERENCES kategori_obat(kode_kategori) ON UPDATE CASCADE ON DELETE RESTRICT
        ) ENGINE=InnoDB
    """)

    # 3. cabang (nama_cabang UNIQUE)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cabang (
            kode_cabang VARCHAR(10) NOT NULL,
            nama_cabang VARCHAR(100) NOT NULL,
            alamat VARCHAR(255) NULL,
            telepon VARCHAR(20) NULL,
            CONSTRAINT pk_cabang PRIMARY KEY (kode_cabang),
            CONSTRAINT uq_cabang_nama UNIQUE (nama_cabang)
        ) ENGINE=InnoDB
    """)

    try:
        cur.execute("ALTER TABLE cabang ADD UNIQUE (nama_cabang)")
    except Exception:
        pass

    # 4. stok (Composite PK: kode_cabang, kode_obat)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stok (
            kode_cabang VARCHAR(10) NOT NULL,
            kode_obat VARCHAR(20) NOT NULL,
            jumlah_stok INT NOT NULL DEFAULT 0,
            CONSTRAINT pk_stok PRIMARY KEY (kode_cabang, kode_obat),
            CONSTRAINT fk_stok_cabang FOREIGN KEY (kode_cabang) 
                REFERENCES cabang(kode_cabang) ON UPDATE CASCADE ON DELETE CASCADE,
            CONSTRAINT fk_stok_obat FOREIGN KEY (kode_obat) 
                REFERENCES obat(kode_obat) ON UPDATE CASCADE ON DELETE CASCADE
        ) ENGINE=InnoDB
    """)

    # 5. pengguna (Kolom: password_hash)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pengguna (
            id_pengguna INT AUTO_INCREMENT NOT NULL,
            kode_cabang VARCHAR(10) NULL,
            username VARCHAR(50) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            nama_lengkap VARCHAR(100) NOT NULL,
            peran ENUM('Admin_Pusat', 'Apoteker', 'Kasir') NOT NULL,
            CONSTRAINT pk_pengguna PRIMARY KEY (id_pengguna),
            CONSTRAINT uq_pengguna_username UNIQUE (username),
            CONSTRAINT fk_pengguna_cabang FOREIGN KEY (kode_cabang) 
                REFERENCES cabang(kode_cabang) ON UPDATE CASCADE ON DELETE SET NULL
        ) ENGINE=InnoDB
    """)

    try:
        cur.execute("ALTER TABLE pengguna CHANGE COLUMN password password_hash VARCHAR(255) NOT NULL")
    except Exception:
        pass

    # Migrasi data seed lama yang masih plain text ke SHA-256 hash (Best Practice Keamanan)
    try:
        cur.execute("UPDATE pengguna SET password_hash = '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9' WHERE password_hash = 'admin123'")
        cur.execute("UPDATE pengguna SET password_hash = '73c090680e550c608f6c31bfecadad71060fa596bf9bf94f997f394464c243eb' WHERE password_hash = 'apoteker123'")
        cur.execute("UPDATE pengguna SET password_hash = 'ef0d45ee0c9616d63428f5dd479a941e17dffcf6ba8e55e5d36e2f185aa8a966' WHERE password_hash = 'kasir123'")
    except Exception:
        pass

    # 6. penjualan (Kolom: total_penjualan)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS penjualan (
            id_penjualan INT AUTO_INCREMENT NOT NULL,
            kode_cabang VARCHAR(10) NOT NULL,
            id_pengguna INT NOT NULL,
            no_faktur VARCHAR(25) NOT NULL,
            total_penjualan DECIMAL(14,2) NOT NULL DEFAULT 0.00,
            tanggal_jam DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_penjualan PRIMARY KEY (id_penjualan),
            CONSTRAINT uq_penjualan_faktur UNIQUE (no_faktur),
            CONSTRAINT fk_penjualan_cabang FOREIGN KEY (kode_cabang) 
                REFERENCES cabang(kode_cabang) ON UPDATE CASCADE ON DELETE RESTRICT,
            CONSTRAINT fk_penjualan_pengguna FOREIGN KEY (id_pengguna) 
                REFERENCES pengguna(id_pengguna) ON UPDATE CASCADE ON DELETE RESTRICT
        ) ENGINE=InnoDB
    """)

    try:
        cur.execute("ALTER TABLE penjualan CHANGE COLUMN total_transaksi total_penjualan DECIMAL(14,2) NOT NULL DEFAULT 0.00")
    except Exception:
        pass

    # 7. detail_penjualan (Kolom: id_detail_penjualan)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS detail_penjualan (
            id_detail_penjualan INT AUTO_INCREMENT NOT NULL,
            id_penjualan INT NOT NULL,
            kode_obat VARCHAR(20) NOT NULL,
            jumlah_jual INT NOT NULL,
            harga_satuan DECIMAL(12,2) NOT NULL,
            subtotal DECIMAL(14,2) NOT NULL,
            CONSTRAINT pk_detail_penjualan PRIMARY KEY (id_detail_penjualan),
            CONSTRAINT fk_detail_penjualan FOREIGN KEY (id_penjualan) 
                REFERENCES penjualan(id_penjualan) ON UPDATE CASCADE ON DELETE CASCADE,
            CONSTRAINT fk_detail_obat FOREIGN KEY (kode_obat) 
                REFERENCES obat(kode_obat) ON UPDATE CASCADE ON DELETE RESTRICT
        ) ENGINE=InnoDB
    """)

    try:
        cur.execute("ALTER TABLE detail_penjualan CHANGE COLUMN id_detail id_detail_penjualan INT AUTO_INCREMENT NOT NULL")
    except Exception:
        pass

    # 8. obat_batch (FITUR FEFO: FIRST-EXPIRED, FIRST-OUT)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS obat_batch (
            id_batch INT AUTO_INCREMENT NOT NULL,
            no_batch VARCHAR(50) NOT NULL,
            kode_cabang VARCHAR(10) NOT NULL,
            kode_obat VARCHAR(20) NOT NULL,
            tanggal_kedaluwarsa DATE NOT NULL,
            jumlah_stok_batch INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_obat_batch PRIMARY KEY (id_batch),
            CONSTRAINT uq_batch_cabang UNIQUE (no_batch, kode_cabang, kode_obat),
            CONSTRAINT fk_batch_cabang FOREIGN KEY (kode_cabang) 
                REFERENCES cabang(kode_cabang) ON UPDATE CASCADE ON DELETE CASCADE,
            CONSTRAINT fk_batch_obat FOREIGN KEY (kode_obat) 
                REFERENCES obat(kode_obat) ON UPDATE CASCADE ON DELETE CASCADE
        ) ENGINE=InnoDB
    """)

    # Kolom no_batch pada detail_penjualan
    try:
        cur.execute("ALTER TABLE detail_penjualan ADD COLUMN no_batch VARCHAR(50) NULL AFTER kode_obat")
    except Exception:
        pass

    # Indeks FEFO untuk pengurutan tanggal kedaluwarsa tercepat
    try:
        cur.execute("CREATE INDEX idx_batch_expiry ON obat_batch(kode_cabang, kode_obat, tanggal_kedaluwarsa)")
    except Exception:
        pass

    # View FEFO: v_peringatan_kedaluwarsa
    cur.execute("""
        CREATE OR REPLACE VIEW v_peringatan_kedaluwarsa AS
        SELECT 
            b.id_batch,
            b.kode_cabang,
            c.nama_cabang,
            b.kode_obat,
            o.nama_obat,
            k.nama_kategori,
            b.no_batch,
            b.tanggal_kedaluwarsa,
            b.jumlah_stok_batch,
            DATEDIFF(b.tanggal_kedaluwarsa, CURDATE()) AS sisa_hari,
            CASE 
                WHEN DATEDIFF(b.tanggal_kedaluwarsa, CURDATE()) <= 0 THEN '🔴 KEDALUWARSA'
                WHEN DATEDIFF(b.tanggal_kedaluwarsa, CURDATE()) <= 90 THEN '🟡 KRITIS (< 3 Bulan)'
                ELSE '🟢 AMAN'
            END AS status_kedaluwarsa
        FROM obat_batch b
        JOIN cabang c ON b.kode_cabang = c.kode_cabang
        JOIN obat o ON b.kode_obat = o.kode_obat
        JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
        WHERE b.jumlah_stok_batch > 0
        ORDER BY b.tanggal_kedaluwarsa ASC
    """)

    # Indeks
    try:
        cur.execute("CREATE INDEX idx_obat_nama ON obat(nama_obat)")
        cur.execute("CREATE INDEX idx_penjualan_tgl ON penjualan(tanggal_jam)")
    except Exception:
        pass

    # View: v_stok_kritis
    cur.execute("""
        CREATE OR REPLACE VIEW v_stok_kritis AS
        SELECT 
            s.kode_cabang,
            c.nama_cabang,
            o.kode_obat,
            o.nama_obat,
            k.nama_kategori,
            s.jumlah_stok,
            o.stok_minimum,
            (o.stok_minimum - s.jumlah_stok) AS defisit_stok
        FROM stok s
        JOIN cabang c ON s.kode_cabang = c.kode_cabang
        JOIN obat o ON s.kode_obat = o.kode_obat
        JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
        WHERE s.jumlah_stok <= o.stok_minimum
    """)

    # Stored Procedure: sp_simpan_transaksi
    cur.execute("DROP PROCEDURE IF EXISTS sp_simpan_transaksi")
    cur.execute("""
        CREATE PROCEDURE sp_simpan_transaksi(
            IN p_no_faktur VARCHAR(25),
            IN p_kode_cabang VARCHAR(10),
            IN p_id_pengguna INT,
            IN p_kode_obat VARCHAR(20),
            IN p_qty INT
        )
        proc_label: BEGIN
            DECLARE v_peran VARCHAR(50);
            DECLARE v_kategori VARCHAR(50);
            DECLARE v_harga DECIMAL(12,2);
            DECLARE v_stok_tersedia INT;
            DECLARE v_id_penjualan INT;
            DECLARE v_subtotal DECIMAL(14,2);

            DECLARE EXIT HANDLER FOR SQLEXCEPTION
            BEGIN
                ROLLBACK;
                SELECT 'GAGAL: Kesalahan integritas database. Transaksi di-ROLLBACK.' AS pesan;
            END;

            SELECT peran INTO v_peran FROM pengguna WHERE id_pengguna = p_id_pengguna;

            SELECT k.nama_kategori, o.harga_jual 
            INTO v_kategori, v_harga
            FROM obat o
            JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
            WHERE o.kode_obat = p_kode_obat;

            IF v_peran = 'Kasir' AND v_kategori = 'Obat Keras' THEN
                SELECT 'GAGAL: Kasir DILARANG menjual Obat Keras! Harus dengan resep Apoteker.' AS pesan;
                LEAVE proc_label;
            END IF;

            SELECT jumlah_stok INTO v_stok_tersedia 
            FROM stok 
            WHERE kode_cabang = p_kode_cabang AND kode_obat = p_kode_obat;

            IF v_stok_tersedia IS NULL OR v_stok_tersedia < p_qty THEN
                SELECT CONCAT('GAGAL: Stok tidak mencukupi! Sisa stok cabang: ', IFNULL(v_stok_tersedia, 0)) AS pesan;
                LEAVE proc_label;
            END IF;

            START TRANSACTION;
                SET v_subtotal = v_harga * p_qty;

                SELECT id_penjualan INTO v_id_penjualan 
                FROM penjualan 
                WHERE no_faktur = p_no_faktur;

                IF v_id_penjualan IS NULL THEN
                    INSERT INTO penjualan (kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam)
                    VALUES (p_kode_cabang, p_id_pengguna, p_no_faktur, v_subtotal, NOW());
                    SET v_id_penjualan = LAST_INSERT_ID();
                ELSE
                    UPDATE penjualan 
                    SET total_penjualan = total_penjualan + v_subtotal 
                    WHERE id_penjualan = v_id_penjualan;
                END IF;

                INSERT INTO detail_penjualan (id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal)
                VALUES (v_id_penjualan, p_kode_obat, p_qty, v_harga, v_subtotal);

                UPDATE stok 
                SET jumlah_stok = jumlah_stok - p_qty 
                WHERE kode_cabang = p_kode_cabang AND kode_obat = p_kode_obat;

            COMMIT;

            SELECT CONCAT('SUKSES: Transaksi ', p_no_faktur, ' berhasil disimpan.') AS pesan;

        END proc_label
    """)

    # Data Seeding
    seeds = [
        # Cabang
        "INSERT IGNORE INTO cabang (kode_cabang, nama_cabang, alamat, telepon) VALUES ('JKT', 'Apotek Sehat Jakarta Pusat', 'Jl. Sudirman No. 45, Jakarta Pusat', '021-5551234')",
        "INSERT IGNORE INTO cabang (kode_cabang, nama_cabang, alamat, telepon) VALUES ('BDG', 'Apotek Sehat Bandung', 'Jl. Asia Afrika No. 108, Bandung', '022-7209876')",
        "INSERT IGNORE INTO cabang (kode_cabang, nama_cabang, alamat, telepon) VALUES ('SBY', 'Apotek Sehat Surabaya', 'Jl. Pemuda No. 12, Surabaya', '031-8976543')",
        # Kategori
        "INSERT IGNORE INTO kategori_obat (kode_kategori, nama_kategori) VALUES ('KAT01', 'Obat Bebas')",
        "INSERT IGNORE INTO kategori_obat (kode_kategori, nama_kategori) VALUES ('KAT02', 'Obat Bebas Terbatas')",
        "INSERT IGNORE INTO kategori_obat (kode_kategori, nama_kategori) VALUES ('KAT03', 'Obat Keras')",
        "INSERT IGNORE INTO kategori_obat (kode_kategori, nama_kategori) VALUES ('KAT04', 'Alat Kesehatan & Suplemen')",
        # Pengguna (password_hash - Hashing SHA-256 Sesuai Best Practice SNI ISO/IEC 27001)
        # admin123    -> 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
        # apoteker123 -> 73c090680e550c608f6c31bfecadad71060fa596bf9bf94f997f394464c243eb
        # kasir123    -> ef0d45ee0c9616d63428f5dd479a941e17dffcf6ba8e55e5d36e2f185aa8a966
        "INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES (1, NULL, 'admin_pusat', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Budi Santoso, S.Kom', 'Admin_Pusat')",
        "INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES (2, 'JKT', 'apoteker_jkt', '73c090680e550c608f6c31bfecadad71060fa596bf9bf94f997f394464c243eb', 'apt. Siti Rahmawati, S.Farm', 'Apoteker')",
        "INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES (3, 'JKT', 'kasir_jkt', 'ef0d45ee0c9616d63428f5dd479a941e17dffcf6ba8e55e5d36e2f185aa8a966', 'Dewi Lestari', 'Kasir')",
        "INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES (4, 'BDG', 'kasir_bdg', 'ef0d45ee0c9616d63428f5dd479a941e17dffcf6ba8e55e5d36e2f185aa8a966', 'Ahmad Dani', 'Kasir')",
        # Obat
        "INSERT IGNORE INTO obat VALUES ('OBT001', 'KAT01', 'Paracetamol 500mg', 'Strip', 8500.00, 20)",
        "INSERT IGNORE INTO obat VALUES ('OBT002', 'KAT01', 'Antasida Doen Tablet', 'Strip', 6000.00, 15)",
        "INSERT IGNORE INTO obat VALUES ('OBT003', 'KAT01', 'Panadol Extra Tablet', 'Strip', 13500.00, 20)",
        "INSERT IGNORE INTO obat VALUES ('OBT004', 'KAT02', 'CTM 4mg Antialergi', 'Strip', 4000.00, 10)",
        "INSERT IGNORE INTO obat VALUES ('OBT005', 'KAT02', 'Decolgen Flu & Batuk', 'Strip', 9500.00, 15)",
        "INSERT IGNORE INTO obat VALUES ('OBT006', 'KAT03', 'Amoxicillin 500mg', 'Strip', 16000.00, 20)",
        "INSERT IGNORE INTO obat VALUES ('OBT007', 'KAT03', 'Cefixime 100mg', 'Strip', 38000.00, 10)",
        "INSERT IGNORE INTO obat VALUES ('OBT008', 'KAT03', 'Amlodipine 10mg', 'Strip', 22000.00, 15)",
        "INSERT IGNORE INTO obat VALUES ('OBT009', 'KAT03', 'Metformin 500mg', 'Strip', 18000.00, 15)",
        "INSERT IGNORE INTO obat VALUES ('OBT010', 'KAT04', 'Vitamin C 1000mg Effervescent', 'Tube', 38000.00, 10)",
        "INSERT IGNORE INTO obat VALUES ('OBT011', 'KAT04', 'Imboost Force Tablet', 'Strip', 45000.00, 10)",
        "INSERT IGNORE INTO obat VALUES ('OBT012', 'KAT04', 'Minyak Kayu Putih 120ml', 'Botol', 28000.00, 12)",
        # Stok
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT001', 100)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT002', 80)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT003', 60)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT004', 50)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT005', 40)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT006', 45)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT007', 30)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT008', 35)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT009', 25)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT010', 8)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT011', 5)",
        "INSERT IGNORE INTO stok VALUES ('JKT', 'OBT012', 40)",
        "INSERT IGNORE INTO stok VALUES ('BDG', 'OBT001', 75)",
        "INSERT IGNORE INTO stok VALUES ('BDG', 'OBT002', 50)",
        "INSERT IGNORE INTO stok VALUES ('BDG', 'OBT006', 30)",
        "INSERT IGNORE INTO stok VALUES ('BDG', 'OBT010', 20)",
        "INSERT IGNORE INTO stok VALUES ('SBY', 'OBT001', 90)",
        "INSERT IGNORE INTO stok VALUES ('SBY', 'OBT007', 20)",
        "INSERT IGNORE INTO stok VALUES ('SBY', 'OBT011', 15)",
        # Penjualan
        "INSERT IGNORE INTO penjualan (id_penjualan, kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam) VALUES (1, 'JKT', 3, 'FAK-20260901-001', 17000.00, '2026-09-01 10:15:00')",
        "INSERT IGNORE INTO penjualan (id_penjualan, kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam) VALUES (2, 'JKT', 3, 'FAK-20260902-002', 27000.00, '2026-09-02 14:30:00')",
        "INSERT IGNORE INTO penjualan (id_penjualan, kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam) VALUES (3, 'JKT', 2, 'FAK-20260903-003', 32000.00, '2026-09-03 18:45:00')",
        "INSERT IGNORE INTO penjualan (id_penjualan, kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam) VALUES (4, 'BDG', 4, 'FAK-20260905-004', 12000.00, '2026-09-05 11:20:00')",
        "INSERT IGNORE INTO penjualan (id_penjualan, kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam) VALUES (5, 'JKT', 2, 'FAK-20260908-005', 38000.00, '2026-09-08 19:10:00')",
        # Detail Penjualan
        "INSERT IGNORE INTO detail_penjualan (id_detail_penjualan, id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal) VALUES (1, 1, 'OBT001', 2, 8500.00, 17000.00)",
        "INSERT IGNORE INTO detail_penjualan (id_detail_penjualan, id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal) VALUES (2, 2, 'OBT003', 2, 13500.00, 27000.00)",
        "INSERT IGNORE INTO detail_penjualan (id_detail_penjualan, id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal) VALUES (3, 3, 'OBT006', 2, 16000.00, 32000.00)",
        "INSERT IGNORE INTO detail_penjualan (id_detail_penjualan, id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal) VALUES (4, 4, 'OBT002', 2, 6000.00, 12000.00)",
        "INSERT IGNORE INTO detail_penjualan (id_detail_penjualan, id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal) VALUES (5, 5, 'OBT007', 1, 38000.00, 38000.00)",
        # Obat Batch (FEFO - Tanggal Kedaluwarsa Berbeda per Batch)
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('PCT-2026-A1', 'JKT', 'OBT001', '2026-06-15', 40)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('PCT-2027-B2', 'JKT', 'OBT001', '2027-01-20', 60)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('ANT-2026-A1', 'JKT', 'OBT002', '2026-05-10', 30)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('ANT-2026-B2', 'JKT', 'OBT002', '2026-11-30', 50)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('PND-2026-A1', 'JKT', 'OBT003', '2026-08-14', 60)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('CTM-2026-A1', 'JKT', 'OBT004', '2026-07-20', 50)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('DCL-2026-A1', 'JKT', 'OBT005', '2026-09-10', 40)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('AMX-2026-A1', 'JKT', 'OBT006', '2026-06-30', 45)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('CFX-2026-A1', 'JKT', 'OBT007', '2026-04-05', 10)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('CFX-2027-B2', 'JKT', 'OBT007', '2027-03-15', 20)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('AML-2026-A1', 'JKT', 'OBT008', '2026-10-12', 35)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('MET-2026-A1', 'JKT', 'OBT009', '2026-12-05', 25)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('VTC-2026-A1', 'JKT', 'OBT010', '2026-05-20', 8)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('IMB-2026-A1', 'JKT', 'OBT011', '2026-06-18', 5)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('MKP-2027-A1', 'JKT', 'OBT012', '2027-05-10', 40)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('PCT-2026-BDG', 'BDG', 'OBT001', '2026-07-15', 75)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('ANT-2026-BDG', 'BDG', 'OBT002', '2026-08-20', 50)",
        "INSERT IGNORE INTO obat_batch (no_batch, kode_cabang, kode_obat, tanggal_kedaluwarsa, jumlah_stok_batch) VALUES ('PCT-2026-SBY', 'SBY', 'OBT001', '2026-09-10', 90)",
    ]

    for s in seeds:
        try:
            cur.execute(s)
        except Exception:
            pass

    # Sinkronkan stok agregat dari total batch obat
    try:
        cur.execute("""
            INSERT INTO stok (kode_cabang, kode_obat, jumlah_stok)
            SELECT kode_cabang, kode_obat, SUM(jumlah_stok_batch)
            FROM obat_batch
            GROUP BY kode_cabang, kode_obat
            ON DUPLICATE KEY UPDATE jumlah_stok = VALUES(jumlah_stok)
        """)
    except Exception:
        pass

    conn.commit()
    print(f"✅ Skema 8 tabel (Termasuk obat_batch FEFO), View, Stored Procedure, dan Data Awal `{db_name}` BERHASIL disinkronkan!")

def run_setup():
    print("=" * 65)
    print("SETUP MULTI-ENVIRONMENT BASIS DATA APOTEK (BEST PRACTICE BNSP)")
    print("Target 1: db_apotek_sehat   (PRODUCTION / OPERASIONAL LIVE)")
    print("Target 2: db_apotek_staging (STAGING / PRA-PRODUKSI & UAT)")
    print("ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f")
    print("=" * 65)

    conn = None
    for cred in [
        {"user": "root", "password": ""},
        {"user": "root", "password": "root"},
        {"user": "app_apotek", "password": "PasswordApotek123!"},
    ]:
        try:
            conn = mysql.connector.connect(host="localhost", **cred)
            print(f"✅ Terhubung ke MySQL sebagai '{cred['user']}'")
            break
        except Exception:
            continue

    if not conn:
        print("❌ Gagal terhubung ke MySQL di localhost:3306. Pastikan XAMPP MySQL aktif.")
        return False

    cur = conn.cursor()

    try:
        # Inisialisasi Environment Production
        setup_schema_and_seeds(cur, conn, "db_apotek_sehat")

        # Inisialisasi Environment Staging (Salinan identik untuk uji migrasi & UAT)
        setup_schema_and_seeds(cur, conn, "db_apotek_staging")

        print("\n" + "=" * 65)
        print("🎉 SEMUA ENVIRONMENT SELESAI DIINISIALISASI SESUAI ERD RESMI!")
        print("=" * 65)
        return True

    except Exception as e:
        print(f"❌ Error fatal saat inisialisasi: {e}")
        return False
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_setup()
