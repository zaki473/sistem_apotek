# setup_database.py
# ==============================================================================
# INISIALISASI DATABASE SISTEM APOTEK MULTI-CABANG (PT SEHAT BERSAMA FARMA)
# SESUAI 100% RANCANGAN ERD RESMI (7 TABEL TEPAT)
# ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f
# ==============================================================================

import mysql.connector

def run_setup():
    print("=" * 60)
    print("Menjalankan Sinkronisasi Database Sesuai ERD Resmi...")
    print("ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f")
    print("=" * 60)

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
        cur.execute("CREATE DATABASE IF NOT EXISTS db_apotek_sehat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute("CREATE DATABASE IF NOT EXISTS db_apotek_staging CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute("USE db_apotek_sehat")

        # HAPUS TABEL DAN OBJEK DI LUAR BATAS ERD (log_aktivitas & obat_batch)
        print("Membersihkan tabel di luar ERD...")
        cur.execute("DROP TABLE IF EXISTS log_aktivitas")
        cur.execute("DROP TABLE IF EXISTS obat_batch")
        cur.execute("DROP TRIGGER IF EXISTS trg_audit_perubahan_harga")
        cur.execute("DROP FUNCTION IF EXISTS fn_hitung_total_faktur")
        conn.commit()

        # Bersihkan juga di db_apotek_staging
        try:
            cur.execute("USE db_apotek_staging")
            cur.execute("DROP TABLE IF EXISTS log_aktivitas")
            cur.execute("DROP TABLE IF EXISTS obat_batch")
            cur.execute("DROP TRIGGER IF EXISTS trg_audit_perubahan_harga")
            cur.execute("DROP FUNCTION IF EXISTS fn_hitung_total_faktur")
            conn.commit()
            cur.execute("USE db_apotek_sehat")
        except Exception:
            pass

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

        # 3. cabang
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cabang (
                kode_cabang VARCHAR(10) NOT NULL,
                nama_cabang VARCHAR(100) NOT NULL,
                alamat VARCHAR(255) NULL,
                telepon VARCHAR(20) NULL,
                CONSTRAINT pk_cabang PRIMARY KEY (kode_cabang)
            ) ENGINE=InnoDB
        """)

        # 4. stok (Composite PK)
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
                peran ENUM('Admin Pusat', 'Apoteker', 'Kasir') NOT NULL,
                CONSTRAINT pk_pengguna PRIMARY KEY (id_pengguna),
                CONSTRAINT uq_pengguna_username UNIQUE (username),
                CONSTRAINT fk_pengguna_cabang FOREIGN KEY (kode_cabang) 
                    REFERENCES cabang(kode_cabang) ON UPDATE CASCADE ON DELETE SET NULL
            ) ENGINE=InnoDB
        """)

        # Pastikan kolom password_hash ada jika sebelumnya bernama password
        try:
            cur.execute("ALTER TABLE pengguna CHANGE COLUMN password password_hash VARCHAR(255) NOT NULL")
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

        # Pastikan kolom total_penjualan ada jika sebelumnya bernama total_transaksi
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

        # Pastikan kolom id_detail_penjualan ada jika sebelumnya bernama id_detail
        try:
            cur.execute("ALTER TABLE detail_penjualan CHANGE COLUMN id_detail id_detail_penjualan INT AUTO_INCREMENT NOT NULL")
        except Exception:
            pass

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
            # Pengguna (password_hash)
            "INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES (1, NULL, 'admin_pusat', 'admin123', 'Budi Santoso, S.Kom', 'Admin Pusat')",
            "INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES (2, 'JKT', 'apoteker_jkt', 'apoteker123', 'apt. Siti Rahmawati, S.Farm', 'Apoteker')",
            "INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES (3, 'JKT', 'kasir_jkt', 'kasir123', 'Dewi Lestari', 'Kasir')",
            "INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES (4, 'BDG', 'kasir_bdg', 'kasir123', 'Ahmad Dani', 'Kasir')",
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
        ]

        for s in seeds:
            try:
                cur.execute(s)
            except Exception:
                pass

        conn.commit()
        print("✅ Sinkronisasi skema 7 tabel ERD dan Stored Procedure berhasil!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_setup()
