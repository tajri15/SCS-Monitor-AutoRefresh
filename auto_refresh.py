import pyautogui
import time
import os
import glob
from datetime import datetime
import sys

# --- KONFIGURASI ---
REFRESH_BUTTON_POS = (1470, 2031)  # Koordinat tombol Refresh
BASE_LOG_DIR = r"C:\SCS\ErrorShowLog"
REFRESH_DELAY = 10                  # Detik antara setiap refresh saat error
ALARM_THRESHOLD = 180               # Detik (3 menit) sebelum alarm berbunyi
CHECK_INTERVAL = 2                  # Detik antara pemeriksaan log

# Variabel status
is_error_state = False
error_start_time = None
last_refresh_time = 0
refresh_count = 0

def get_today_folder():
    """Path folder log hari ini: YYYYMM/DD"""
    now = datetime.now()
    year_month = now.strftime("%Y%m")  # 202601
    day = now.strftime("%d")           # 12
    return os.path.join(BASE_LOG_DIR, year_month, day)

def get_latest_log_file(folder):
    """Ambil file log terbaru di folder"""
    if not os.path.exists(folder):
        return None
    
    # Cari semua file ErrorShow*.log
    files = glob.glob(os.path.join(folder, "ErrorShow*.log"))
    if not files:
        return None
    
    # Urutkan, ambil yang terakhir (paling baru)
    files.sort()
    return files[-1]

def check_status(log_file):
    """Cek status dari baris terakhir file log"""
    if not log_file or not os.path.exists(log_file):
        return False
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if not lines:
            return False
        
        last_line = lines[-1].strip()
        return last_line.endswith(": 1")  # True jika error
    except:
        return False

def do_refresh():
    """Klik tombol refresh"""
    try:
        pyautogui.click(REFRESH_BUTTON_POS)
        return True
    except:
        return False

def main():
    """Program utama"""
    print("🔄 SCS Auto-Refresh")
    print(f"📍 Koordinat: {REFRESH_BUTTON_POS}")
    print(f"📁 Folder: {BASE_LOG_DIR}")
    print("⏳ Monitoring dimulai...\n")
    
    while True:
        try:
            # 1. Dapatkan folder dan file log
            folder = get_today_folder()
            log_file = get_latest_log_file(folder)
            
            if not log_file:
                time.sleep(5)
                continue
            
            # 2. Cek status
            is_error = check_status(log_file)
            
            # 3. Jika error, lakukan refresh
            if is_error:
                current_time = time.time()
                
                # Jika baru error
                if not is_error_state:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Error terdeteksi")
                    is_error_state = True
                    error_start_time = current_time
                    last_refresh_time = 0
                    refresh_count = 0
                
                # Hitung durasi error
                error_duration = current_time - error_start_time
                
                # Refresh setiap REFRESH_DELAY detik
                if current_time - last_refresh_time >= REFRESH_DELAY:
                    if do_refresh():
                        refresh_count += 1
                        last_refresh_time = current_time
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Refresh #{refresh_count}")
                
                # Alarm setelah 3 menit
                if error_duration >= ALARM_THRESHOLD:
                    mins = int(error_duration // 60)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 Error sudah {mins} menit")
            
            # 4. Jika kembali normal
            elif is_error_state:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Sistem normal")
                is_error_state = False
                error_start_time = None
                refresh_count = 0
            
            # Tunggu sebelum cek lagi
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n🛑 Program dihentikan")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()