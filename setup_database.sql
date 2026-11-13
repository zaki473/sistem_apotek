-- ==============================================================================
-- SKRIP BASIS DATA SISTEM APOTEK MULTI-CABANG (PT SEHAT BERSAMA FARMA)
-- SESUAI RANCANGAN ERD RESMI (7 TABEL TEPAT - TIDAK MELEBIHI BATAS ERD)
-- ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS db_apotek_sehat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE db_apotek_sehat;

-- ------------------------------------------------------------------------------
-- PEMBERSIHAN TABEL & OBJEK DI LUAR BATAS ERD RESMI
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS log_aktivitas;
DROP TABLE IF EXISTS obat_batch;
DROP TRIGGER IF EXISTS trg_audit_perubahan_harga;
DROP FUNCTION IF EXISTS fn_hitung_total_faktur;

-- ------------------------------------------------------------------------------
-- 1. TABEL: kategori_obat
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kategori_obat (
    kode_kategori VARCHAR(10) NOT NULL,
    nama_kategori VARCHAR(50) NOT NULL,
    CONSTRAINT pk_kategori_obat PRIMARY KEY (kode_kategori)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 2. TABEL: obat
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS obat (
    kode_obat VARCHAR(20) NOT NULL,
    kode_kategori VARCHAR(10) NOT NULL,
    nama_obat VARCHAR(150) NOT NULL,
    satuan VARCHAR(20) NOT NULL,
    harga_jual DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    stok_minimum INT NOT NULL DEFAULT 10,
    CONSTRAINT pk_obat PRIMARY KEY (kode_obat),
    CONSTRAINT fk_obat_kategori FOREIGN KEY (kode_kategori) 
        REFERENCES kategori_obat(kode_kategori) 
        ON UPDATE CASCADE 
        ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 3. TABEL: cabang
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cabang (
    kode_cabang VARCHAR(10) NOT NULL,
    nama_cabang VARCHAR(100) NOT NULL,
    alamat VARCHAR(255) NULL,
    telepon VARCHAR(20) NULL,
    CONSTRAINT pk_cabang PRIMARY KEY (kode_cabang)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 4. TABEL: stok (COMPOSITE PK: kode_cabang, kode_obat)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stok (
    kode_cabang VARCHAR(10) NOT NULL,
    kode_obat VARCHAR(20) NOT NULL,
    jumlah_stok INT NOT NULL DEFAULT 0,
    CONSTRAINT pk_stok PRIMARY KEY (kode_cabang, kode_obat),
    CONSTRAINT fk_stok_cabang FOREIGN KEY (kode_cabang) 
        REFERENCES cabang(kode_cabang) 
        ON UPDATE CASCADE 
        ON DELETE CASCADE,
    CONSTRAINT fk_stok_obat FOREIGN KEY (kode_obat) 
        REFERENCES obat(kode_obat) 
        ON UPDATE CASCADE 
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 5. TABEL: pengguna (KOLOM: password_hash)
-- ------------------------------------------------------------------------------
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
        REFERENCES cabang(kode_cabang) 
        ON UPDATE CASCADE 
        ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 6. TABEL: penjualan (KOLOM: total_penjualan)
-- ------------------------------------------------------------------------------
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
        REFERENCES cabang(kode_cabang) 
        ON UPDATE CASCADE 
        ON DELETE RESTRICT,
    CONSTRAINT fk_penjualan_pengguna FOREIGN KEY (id_pengguna) 
        REFERENCES pengguna(id_pengguna) 
        ON UPDATE CASCADE 
        ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 7. TABEL: detail_penjualan (KOLOM: id_detail_penjualan)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detail_penjualan (
    id_detail_penjualan INT AUTO_INCREMENT NOT NULL,
    id_penjualan INT NOT NULL,
    kode_obat VARCHAR(20) NOT NULL,
    jumlah_jual INT NOT NULL,
    harga_satuan DECIMAL(12,2) NOT NULL,
    subtotal DECIMAL(14,2) NOT NULL,
    CONSTRAINT pk_detail_penjualan PRIMARY KEY (id_detail_penjualan),
    CONSTRAINT fk_detail_penjualan FOREIGN KEY (id_penjualan) 
        REFERENCES penjualan(id_penjualan) 
        ON UPDATE CASCADE 
        ON DELETE CASCADE,
    CONSTRAINT fk_detail_obat FOREIGN KEY (kode_obat) 
        REFERENCES obat(kode_obat) 
        ON UPDATE CASCADE 
        ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- INDEKS PERFORMA
-- ------------------------------------------------------------------------------
CREATE INDEX idx_obat_nama ON obat(nama_obat);
CREATE INDEX idx_penjualan_tgl ON penjualan(tanggal_jam);

-- ------------------------------------------------------------------------------
-- VIEW: v_stok_kritis (Kebutuhan Peringatan Stok)
-- ------------------------------------------------------------------------------
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
WHERE s.jumlah_stok <= o.stok_minimum;

-- ------------------------------------------------------------------------------
-- STORED PROCEDURE: sp_simpan_transaksi (Sesuai ID & ERD)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_simpan_transaksi;
DELIMITER $$
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

    -- Validasi 1: Peran pengguna
    SELECT peran INTO v_peran FROM pengguna WHERE id_pengguna = p_id_pengguna;

    -- Validasi 2: Kategori dan harga obat
    SELECT k.nama_kategori, o.harga_jual 
    INTO v_kategori, v_harga
    FROM obat o
    JOIN kategori_obat k ON o.kode_kategori = k.kode_kategori
    WHERE o.kode_obat = p_kode_obat;

    -- Aturan Bisnis: Kasir dilarang menjual Obat Keras
    IF v_peran = 'Kasir' AND v_kategori = 'Obat Keras' THEN
        SELECT 'GAGAL: Kasir DILARANG menjual Obat Keras! Harus dengan resep Apoteker.' AS pesan;
        LEAVE proc_label;
    END IF;

    -- Validasi 3: Cek stok di cabang
    SELECT jumlah_stok INTO v_stok_tersedia 
    FROM stok 
    WHERE kode_cabang = p_kode_cabang AND kode_obat = p_kode_obat;

    IF v_stok_tersedia IS NULL OR v_stok_tersedia < p_qty THEN
        SELECT CONCAT('GAGAL: Stok tidak mencukupi! Sisa stok cabang: ', IFNULL(v_stok_tersedia, 0)) AS pesan;
        LEAVE proc_label;
    END IF;

    -- Eksekusi Transaksi Atomik
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

END proc_label$$
DELIMITER ;

-- ------------------------------------------------------------------------------
-- DATA SEED CONTOH SESUAI ERD
-- ------------------------------------------------------------------------------
INSERT IGNORE INTO cabang (kode_cabang, nama_cabang, alamat, telepon) VALUES
('JKT', 'Apotek Sehat Jakarta Pusat', 'Jl. Sudirman No. 45, Jakarta Pusat', '021-5551234'),
('BDG', 'Apotek Sehat Bandung', 'Jl. Asia Afrika No. 108, Bandung', '022-7209876'),
('SBY', 'Apotek Sehat Surabaya', 'Jl. Pemuda No. 12, Surabaya', '031-8976543');

INSERT IGNORE INTO kategori_obat (kode_kategori, nama_kategori) VALUES
('KAT01', 'Obat Bebas'),
('KAT02', 'Obat Bebas Terbatas'),
('KAT03', 'Obat Keras'),
('KAT04', 'Alat Kesehatan & Suplemen');

INSERT IGNORE INTO pengguna (id_pengguna, kode_cabang, username, password_hash, nama_lengkap, peran) VALUES
(1, NULL, 'admin_pusat', 'admin123', 'Budi Santoso, S.Kom', 'Admin Pusat'),
(2, 'JKT', 'apoteker_jkt', 'apoteker123', 'apt. Siti Rahmawati, S.Farm', 'Apoteker'),
(3, 'JKT', 'kasir_jkt', 'kasir123', 'Dewi Lestari', 'Kasir'),
(4, 'BDG', 'kasir_bdg', 'kasir123', 'Ahmad Dani', 'Kasir');

INSERT IGNORE INTO obat (kode_obat, kode_kategori, nama_obat, satuan, harga_jual, stok_minimum) VALUES
('OBT001', 'KAT01', 'Paracetamol 500mg', 'Strip', 8500.00, 20),
('OBT002', 'KAT01', 'Antasida Doen Tablet', 'Strip', 6000.00, 15),
('OBT003', 'KAT01', 'Panadol Extra Tablet', 'Strip', 13500.00, 20),
('OBT004', 'KAT02', 'CTM 4mg Antialergi', 'Strip', 4000.00, 10),
('OBT005', 'KAT02', 'Decolgen Flu & Batuk', 'Strip', 9500.00, 15),
('OBT006', 'KAT03', 'Amoxicillin 500mg', 'Strip', 16000.00, 20),
('OBT007', 'KAT03', 'Cefixime 100mg', 'Strip', 38000.00, 10),
('OBT008', 'KAT03', 'Amlodipine 10mg', 'Strip', 22000.00, 15),
('OBT009', 'KAT03', 'Metformin 500mg', 'Strip', 18000.00, 15),
('OBT010', 'KAT04', 'Vitamin C 1000mg Effervescent', 'Tube', 38000.00, 10),
('OBT011', 'KAT04', 'Imboost Force Tablet', 'Strip', 45000.00, 10),
('OBT012', 'KAT04', 'Minyak Kayu Putih 120ml', 'Botol', 28000.00, 12);

INSERT IGNORE INTO stok (kode_cabang, kode_obat, jumlah_stok) VALUES
('JKT', 'OBT001', 100),
('JKT', 'OBT002', 80),
('JKT', 'OBT003', 60),
('JKT', 'OBT004', 50),
('JKT', 'OBT005', 40),
('JKT', 'OBT006', 45),
('JKT', 'OBT007', 30),
('JKT', 'OBT008', 35),
('JKT', 'OBT009', 25),
('JKT', 'OBT010', 8),
('JKT', 'OBT011', 5),
('JKT', 'OBT012', 40),
('BDG', 'OBT001', 75),
('BDG', 'OBT002', 50),
('BDG', 'OBT006', 30),
('BDG', 'OBT010', 20),
('SBY', 'OBT001', 90),
('SBY', 'OBT007', 20),
('SBY', 'OBT011', 15);

INSERT IGNORE INTO penjualan (id_penjualan, kode_cabang, id_pengguna, no_faktur, total_penjualan, tanggal_jam) VALUES
(1, 'JKT', 3, 'FAK-20260901-001', 17000.00, '2026-09-01 10:15:00'),
(2, 'JKT', 3, 'FAK-20260902-002', 27000.00, '2026-09-02 14:30:00'),
(3, 'JKT', 2, 'FAK-20260903-003', 32000.00, '2026-09-03 18:45:00'),
(4, 'BDG', 4, 'FAK-20260905-004', 12000.00, '2026-09-05 11:20:00'),
(5, 'JKT', 2, 'FAK-20260908-005', 38000.00, '2026-09-08 19:10:00');

INSERT IGNORE INTO detail_penjualan (id_detail_penjualan, id_penjualan, kode_obat, jumlah_jual, harga_satuan, subtotal) VALUES
(1, 1, 'OBT001', 2, 8500.00, 17000.00),
(2, 2, 'OBT003', 2, 13500.00, 27000.00),
(3, 3, 'OBT006', 2, 16000.00, 32000.00),
(4, 4, 'OBT002', 2, 6000.00, 12000.00),
(5, 5, 'OBT007', 1, 38000.00, 38000.00);
