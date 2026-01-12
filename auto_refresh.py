import pyautogui
import time
import os
import winsound
from datetime import datetime
import glob

# --- KONFIGURASI ---
REFRESH_BUTTON_POS = (1470, 2031) 
BASE_LOG_DIR = r"C:\SCS\ErrorShowLog"
REFRESH_DELAY = 10      
ALARM_THRESHOLD = 180   

def get_latest_log_file():
    """Mencari file log terbaru di dalam struktur folder TahunBulan/Tanggal/"""
    now = datetime.now()
    folder_thn_bln = now.strftime("%Y%m") # Contoh: 202601
    folder_tgl = now.strftime("%d")       # Contoh: 12
    
    # Path ke folder tanggal hari ini
    target_dir = os.path.join(BASE_LOG_DIR, folder_thn_bln, folder_tgl)
    
    if not os.path.exists(target_dir):
        return None, target_dir

    # Mencari semua file di dalam folder tersebut
    files = glob.glob(os.path.join(target_dir, "*"))
    if not files:
        return None, target_dir

    # Ambil file yang paling terakhir dimodifikasi (paling baru)
    latest_file = max(files, key=os.path.getmtime)
    return latest_file, target_dir

def jalankan_refresh():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> KLIK REFRESH! <<<")
    old_x, old_y = pyautogui.position()
    pyautogui.click(REFRESH_BUTTON_POS)
    pyautogui.moveTo(old_x, old_y)

def monitor_scs():
    print("--- MONITOR SCS AKTIF (VERSI FOLDER TANGGAL) ---")
    print(f"Target Koordinat: {REFRESH_BUTTON_POS}")
    
    error_start_time = None
    last_refresh_time = 0
    
    while True:
        log_path, current_dir = get_latest_log_file()
        
        # Jika folder atau file belum ada
        if log_path is None:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Menunggu file di: {current_dir}")
            time.sleep(10)
            continue

        try:
            # Menggunakan mode 'rb' dan seek untuk memastikan membaca data paling baru
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if not lines:
                    time.sleep(2)
                    continue
                
                # Ambil baris terakhir yang tidak kosong
                last_line = lines[-1].strip()
                if not last_line and len(lines) > 1:
                    last_line = lines[-2].strip()

                # LOGIKA DETEKSI STATUS
                if last_line.endswith(": 1"):
                    now = time.time()
                    if error_start_time is None:
                        print(f"MERAH! File: {os.path.basename(log_path)}")
                        print(f"Isi Log: {last_line}")
                        error_start_time = now
                    
                    # Refresh tiap 10 detik
                    if (now - last_refresh_time) >= REFRESH_DELAY:
                        jalankan_refresh()
                        last_refresh_time = now
                    
                    # Alarm jika sudah 3 menit
                    if (now - error_start_time) >= ALARM_THRESHOLD:
                        print("!!! ALARM: SUDAH 3 MENIT MASIH ERROR !!!")
                        winsound.Beep(2500, 800)
                
                elif last_line.endswith(": 0"):
                    if error_start_time is not None:
                        print("Sistem HIJAU (Normal).")
                    error_start_time = None
                    last_refresh_time = 0

        except Exception as e:
            print(f"Gagal membaca file {log_path}: {e}")

        time.sleep(2)

if __name__ == "__main__":
    monitor_scs()