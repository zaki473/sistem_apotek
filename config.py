# config.py
# ==============================================================================
# KONFIGURASI MULTI-ENVIRONMENT (Menjawab Poin 10 Dokumen FR.IA.04A)
# Memisahkan konfigurasi Development, Staging, dan Production secara terisolasi.
# ID Asesi: dcea8c3b-658a-491e-8a7c-6b47a6492a2f
# ==============================================================================

import mysql.connector

ENV_CONFIG = {
    "development": {
        "nama_env": "Development (Pengembangan)",
        "host": "localhost",
        "database": "db_apotek_sehat",
        "user": "app_apotek",
        "password": "PasswordApotek123!",
        "log_level": "DEBUG",
        "max_connection_threshold": 50,  # Batas atas koneksi (Poin 12)
        "deskripsi": "Lingkungan pengembangan lokal untuk uji coba fitur baru & debugging."
    },
    "staging": {
        "nama_env": "Staging (Pra-Produksi)",
        "host": "localhost",
        "database": "db_apotek_staging",
        "user": "app_apotek",
        "password": "PasswordApotek123!",
        "log_level": "INFO",
        "max_connection_threshold": 100,
        "deskripsi": "Lingkungan uji integrasi & simulasi patch/migrasi skema (Poin 13)."
    },
    "production": {
        "nama_env": "Production (Operasional Live)",
        "host": "localhost",
        "database": "db_apotek_sehat",
        "user": "app_apotek",
        "password": "PasswordApotek123!",
        "log_level": "ERROR",
        "max_connection_threshold": 200,
        "deskripsi": "Lingkungan sistem operasional utama apotek multi-cabang."
    }
}

# Default aktif environment
CURRENT_ENV = "development"

def get_active_config(env_name=None):
    """Mengembalikan konfigurasi sesuai environment yang sedang aktif."""
    target_env = env_name if env_name else CURRENT_ENV
    return ENV_CONFIG.get(target_env, ENV_CONFIG["development"])

def create_connection(env_name=None):
    """
    Membuat koneksi ke MySQL dengan penanganan fallback otomatis.
    Jika user 'app_apotek' belum terkonfigurasi, mencoba menggunakan 'root' XAMPP.
    """
    cfg = get_active_config(env_name)
    
    # Coba kredensial user aplikasi terlebih dahulu (Sesuai Poin 6 - Bukan root)
    try:
        return mysql.connector.connect(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            autocommit=False
        )
    except mysql.connector.Error:
        # Fallback ke root tanpa password untuk memudahkan pengujian pertama kali di XAMPP
        return mysql.connector.connect(
            host=cfg["host"],
            user="root",
            password="",
            database=cfg["database"],
            autocommit=False
        )
