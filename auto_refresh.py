import pyautogui
import time
import os
import winsound
from datetime import datetime

# Masukkan koordinat hasil dari cek_koordinat.py
REFRESH_BUTTON_POS = (382, 908) 

# Lokasi folder utama log
BASE_LOG_DIR = r"C:\SCS\ErrorShowLog"

# Pengaturan Waktu
REFRESH_DELAY = 5
ALARM_THRESHOLD = 180

def get_current_log_path():
    """Membangun path log berdasarkan tanggal saat ini"""
    now = datetime.now()
    folder_bulan = now.strftime("%Y%m")
    nama_file = f"ErrorShow_{now.strftime('%Y-%m-%d')}.log"
    return os.path.join(BASE_LOG_DIR, folder_bulan, nama_file)

def jalankan_refresh():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mencoba Refresh Otomatis...")
    posisi_awal = pyautogui.position()
    pyautogui.click(REFRESH_BUTTON_POS)
    pyautogui.moveTo(posisi_awal)

def bunyikan_alarm():
    print("!!! ALARM: ERROR PERSISTEN LEBIH DARI 3 MENIT !!!")
    for _ in range(5):
        winsound.Beep(2000, 1000)
        time.sleep(0.5)

def monitor_scs():
    print("--- PROGRAM MONITOR SCS AKTIF ---")
    error_start_time = None
    last_refresh_time = 0
    
    while True:
        log_path = get_current_log_path()
        
        if not os.path.exists(log_path):
            # Jika file hari ini belum dibuat, tunggu
            time.sleep(10)
            continue

        with open(log_path, "r", encoding="utf-8") as f:
            # Baca baris terakhir saja
            lines = f.readlines()
            if not lines:
                time.sleep(2)
                continue
                
            last_line = lines[-1].strip()
            
            # Cek status error di akhir baris (Status : 1)
            if last_line.endswith(": 1"):
                # 1. Catat waktu awal error jika baru muncul
                if error_start_time is None:
                    print(f"Error Terdeteksi: {last_line}")
                    error_start_time = time.time()
                
                # 2. Lakukan refresh terus-menerus setiap REFRESH_DELAY detik
                current_time = time.time()
                if (current_time - last_refresh_time) >= REFRESH_DELAY:
                    jalankan_refresh()
                    last_refresh_time = current_time
                
                # 3. Cek jika sudah lebih dari 3 menit masih error
                durasi_error = current_time - error_start_time
                if durasi_error >= ALARM_THRESHOLD:
                    bunyikan_alarm()
            
            # Jika status normal (Status : 0)
            elif last_line.endswith(": 0"):
                if error_start_time is not None:
                    print("Sistem kembali normal. Timer direset.")
                error_start_time = None

        time.sleep(2)

if __name__ == "__main__":
    try:
        monitor_scs()
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        input("Tekan Enter untuk menutup...")