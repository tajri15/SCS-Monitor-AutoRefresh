import pyautogui
import time
import os
import winsound
from datetime import datetime

# --- KONFIGURASI ---
# Koordinat tombol Refresh yang baru saja Anda dapatkan
REFRESH_BUTTON_POS = (1470, 2031) 

# Lokasi folder log sesuai struktur Anda
BASE_LOG_DIR = r"C:\SCS\ErrorShowLog"

# Pengaturan Jeda
REFRESH_DELAY = 10      # Klik refresh setiap 10 detik selama status masih merah
ALARM_THRESHOLD = 180   # Bunyi alarm jika setelah 3 menit (180 detik) tetap merah

def get_current_log_path():
    """Mencari folder YYYYMM dan file ErrorShow_YYYY-MM-DD.log secara otomatis"""
    now = datetime.now()
    folder_bulan = now.strftime("%Y%m") # Contoh: 202601
    nama_file = f"ErrorShow_{now.strftime('%Y-%m-%d')}.log" # Contoh: ErrorShow_2026-01-11.log
    return os.path.join(BASE_LOG_DIR, folder_bulan, nama_file)

def jalankan_refresh():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Status MERAH: Melakukan Refresh Otomatis...")
    posisi_awal = pyautogui.position()
    pyautogui.click(REFRESH_BUTTON_POS)
    pyautogui.moveTo(posisi_awal)

def monitor_scs():
    print("--- MONITOR SCS AKTIF ---")
    print(f"Target Koordinat: {REFRESH_BUTTON_POS}")
    
    error_start_time = None
    last_refresh_time = 0
    
    while True:
        log_path = get_current_log_path()
        
        # Cek apakah file log untuk hari ini sudah ada
        if not os.path.exists(log_path):
            time.sleep(10)
            continue

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    time.sleep(2)
                    continue
                
                # Membaca baris paling bawah untuk status terbaru
                last_line = lines[-1].strip()
                
                # Jika status di log adalah : 1 (Error/Merah)
                if last_line.endswith(": 1"):
                    current_time = time.time()
                    
                    if error_start_time is None:
                        print(f"ERROR TERDETEKSI: {last_line}")
                        error_start_time = current_time
                    
                    # 1. Lakukan refresh berkala setiap 10 detik selama status masih : 1
                    if (current_time - last_refresh_time) >= REFRESH_DELAY:
                        jalankan_refresh()
                        last_refresh_time = current_time
                    
                    # 2. Jika sudah mencapai 3 menit masih tetap : 1, nyalakan alarm
                    durasi_error = current_time - error_start_time
                    if durasi_error >= ALARM_THRESHOLD:
                        print(f"!!! ALARM: SUDAH {int(durasi_error/60)} MENIT TETAP ERROR !!!")
                        winsound.Beep(2500, 1000) # Suara Beep frekuensi 2500Hz selama 1 detik
                
                # Jika status di log adalah : 0 (Normal/Hijau)
                elif last_line.endswith(": 0"):
                    if error_start_time is not None:
                        print("Sistem kembali Normal (HIJAU). Timer direset.")
                    error_start_time = None
                    last_refresh_time = 0

        except Exception as e:
            print(f"Kesalahan saat membaca log: {e}")

        time.sleep(2)

if __name__ == "__main__":
    monitor_scs()