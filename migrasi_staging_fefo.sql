-- ==============================================================================
-- DOKUMEN MIGRASI & PATCH STAGING: FITUR BATCH & KEDALUWARSA (FEFO)
-- Menjawab Poin 11 & Poin 13 Dokumen FR.IA.04A
-- ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f
-- Target Environment: db_apotek_staging
-- ==============================================================================

USE db_apotek_staging;

-- ------------------------------------------------------------------------------
-- 1. SKRIP PEMBARUAN (MIGRATION PATCH)
-- ------------------------------------------------------------------------------
-- Langkah 1.1: Pembuatan Tabel Batch Obat
CREATE TABLE IF NOT EXISTS obat_batch (
    id_batch INT AUTO_INCREMENT NOT NULL,
    no_batch VARCHAR(50) NOT NULL,
    kode_cabang VARCHAR(10) NOT NULL,
    kode_obat VARCHAR(10) NOT NULL,
    tanggal_kedaluwarsa DATE NOT NULL,
    jumlah_stok_batch INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_obat_batch PRIMARY KEY (id_batch),
    CONSTRAINT uq_batch_cabang UNIQUE (no_batch, kode_cabang, kode_obat),
    CONSTRAINT fk_batch_cabang FOREIGN KEY (kode_cabang) REFERENCES cabang(kode_cabang) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_batch_obat FOREIGN KEY (kode_obat) REFERENCES obat(kode_obat) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- Langkah 1.2: Pembuatan Indeks Pencarian Tanggal Kedaluwarsa Tercepat (FEFO)
CREATE INDEX idx_batch_expiry ON obat_batch(kode_cabang, kode_obat, tanggal_kedaluwarsa);

-- Langkah 1.3: Tambah Kolom no_batch pada detail_penjualan jika belum ada
ALTER TABLE detail_penjualan ADD COLUMN IF NOT EXISTS no_batch VARCHAR(50) NULL AFTER kode_obat;

-- ------------------------------------------------------------------------------
-- 2. SKRIP ROLLBACK (RENCANA PEMULIHAN JIKA MIGRASI GAGAL DI STAGING)
-- ------------------------------------------------------------------------------
-- Jalankan blok di bawah ini jika migrasi perlu dibatalkan (Rollback Plan):
/*
ALTER TABLE detail_penjualan DROP COLUMN IF EXISTS no_batch;
DROP TABLE IF EXISTS obat_batch;
*/
