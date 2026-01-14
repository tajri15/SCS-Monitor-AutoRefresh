import pyautogui
import time
import os
import glob
import winsound
import threading

# --- KONFIGURASI ---
REFRESH_X = 1470
REFRESH_Y = 2031
LOG_DIR = r"C:\SCS\ErrorShowLog"
WAIT_AFTER_ERROR = 5
REFRESH_EVERY = 4
ALARM_AFTER = 60

print("🔄 SCS AUTO-REFRESH")
print("=" * 50)

# Test klik
print("Testing mouse click...")
pyautogui.click(REFRESH_X, REFRESH_Y)
print(f"✅ Clicked at ({REFRESH_X}, {REFRESH_Y})")

# Cari file log terbaru
print("\nFinding latest log file...")
log_files = []
for root, dirs, files in os.walk(LOG_DIR):
    for file in files:
        if "ErrorShow" in file and file.endswith(".log"):
            full_path = os.path.join(root, file)
            mod_time = os.path.getmtime(full_path)
            log_files.append((mod_time, full_path))

log_files.sort(reverse=True)
log_file = log_files[0][1]
print(f"✅ Using: {os.path.basename(log_file)}")

print(f"\n⏱️  Delay awal: {WAIT_AFTER_ERROR} detik")
print(f"🔄 Refresh: setiap {REFRESH_EVERY} detik")
print(f"🚨 Buzzer: nyala setelah {ALARM_AFTER//60} menit error")
print(f"   ⏹️  Berhenti: mouse digerakkan/error selesai")
print("=" * 50)
print("Ctrl+C to stop\n")

# Variabel status
error_active = False
error_start_time = 0
refresh_count = 0
buzzer_active = False
last_line = ""
last_mouse_pos = pyautogui.position()
buzzer_thread = None
stop_buzzer = False

def continuous_buzzer():
    """Buzzer bunyi terus menerus (beep berulang)"""
    global stop_buzzer
    
    print("   🔊 BUZZER NYALA (beep terus)")
    stop_buzzer = False
    
    while not stop_buzzer:
        winsound.Beep(1500, 300)
        time.sleep(0.7)
        if stop_buzzer:
            break

def check_mouse_moved():
    """Cek apakah mouse bergerak dari posisi terakhir"""
    global last_mouse_pos
    current_pos = pyautogui.position()
    
    if (abs(current_pos.x - last_mouse_pos.x) > 5 or 
        abs(current_pos.y - last_mouse_pos.y) > 5):
        last_mouse_pos = current_pos
        return True
    return False

while True:
    try:
        # Baca file log
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if lines:
            # Cari baris terakhir yang tidak kosong
            current_line = ""
            for line in reversed(lines):
                if line.strip():
                    current_line = line.strip()
                    break
            
            if current_line != last_line:
                last_line = current_line
                
                # CEK ERROR
                if ": 1" in current_line and (current_line.endswith(": 1") or current_line.split(":")[-1].strip() == "1"):
                    if not error_active:
                        error_active = True
                        error_start_time = time.time()
                        refresh_count = 0
                        buzzer_active = False
                        stop_buzzer = False
                        print(f"\n[{time.strftime('%H:%M:%S')}] ⚠️  ERROR DETECTED")
                        print(f"   ⏳ Tunggu {WAIT_AFTER_ERROR} detik sebelum refresh...")
                
                # CEK NORMAL (ERROR SELESAI)
                elif ": 0" in current_line and (current_line.endswith(": 0") or current_line.split(":")[-1].strip() == "0"):
                    if error_active:
                        # HITUNG DURASI
                        duration = time.time() - error_start_time
                        minutes = int(duration // 60)
                        seconds = int(duration % 60)
                        
                        print(f"\n[{time.strftime('%H:%M:%S')}] ✅ ERROR SELESAI")
                        print(f"   ⏱️  Durasi: {minutes} menit {seconds} detik")
                        print(f"   🔄 Total refresh: {refresh_count} kali")
                        
                        # MATIKAN BUZZER JIKA NYALA
                        if buzzer_active:
                            stop_buzzer = True
                            buzzer_active = False
                            print("   🔇 Buzzer dimatikan (error selesai)")
                        
                        # RESET STATUS
                        error_active = False
                        error_start_time = 0
            
            # LOGIKA REFRESH SAAT ERROR
            if error_active:
                current_time = time.time()
                error_duration = current_time - error_start_time
                
                # 1. TUNGGU DELAY AWAL DULU
                if error_duration >= WAIT_AFTER_ERROR:
                    # 2. REFRESH SETIAP REFRESH_EVERY DETIK
                    if refresh_count == 0 or (current_time - error_start_time - WAIT_AFTER_ERROR) // REFRESH_EVERY > refresh_count - 1:
                        pyautogui.click(REFRESH_X, REFRESH_Y)
                        refresh_count += 1
                        
                        # Tampilkan status
                        mins = int(error_duration // 60)
                        secs = int(error_duration % 60)
                        print(f"[{time.strftime('%H:%M:%S')}] 🔄 Refresh #{refresh_count} (Error: {mins}:{secs:02d})")
                
                # 3. ⭐ BUZZER NYALA SETELAH 1 MENIT (ALARM_AFTER = 60) ⭐
                if error_duration >= ALARM_AFTER and not buzzer_active:
                    print(f"\n[{time.strftime('%H:%M:%S')}] 🚨 BUZZER NYALA! (setelah {ALARM_AFTER//60} menit)")
                    print("   🔊 Beep terus menerus...")
                    print("   🖱️  Gerakkan mouse untuk matikan buzzer")
                    
                    # NYALAKAN BUZZER DI THREAD TERPISAH
                    buzzer_active = True
                    stop_buzzer = False
                    buzzer_thread = threading.Thread(target=continuous_buzzer)
                    buzzer_thread.daemon = True
                    buzzer_thread.start()
                
                # 4. CEK JIKA MOUSE DIGERAKKAN (MATIKAN BUZZER)
                if buzzer_active and check_mouse_moved():
                    stop_buzzer = True
                    buzzer_active = False
                    print(f"\n[{time.strftime('%H:%M:%S')}] 🖱️  Mouse digerakkan!")
                    print("   🔇 Buzzer dimatikan")
            
            # TAMPILKAN STATUS NORMAL SETIAP 60 DETIK
            elif int(time.time()) % 60 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] ✅ System normal")
        
        time.sleep(2)
        
    except KeyboardInterrupt:
        print(f"\n🛑 PROGRAM DIHENTIKAN")
        print(f"   Total refresh: {refresh_count}")
        
        # Pastikan buzzer dimatikan
        if buzzer_active:
            stop_buzzer = True
            print("   🔇 Buzzer dimatikan (program exit)")
        
        if error_active:
            duration = time.time() - error_start_time
            print(f"   Error masih aktif: {int(duration)} detik")
        break
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ Error: {e}")
        time.sleep(5)