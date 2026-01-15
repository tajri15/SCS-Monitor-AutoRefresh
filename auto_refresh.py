import pyautogui
import time
import os
import threading
import winsound

# --- KONFIGURASI ---
REFRESH_X = 1470
REFRESH_Y = 2031
LOG_DIR = r"C:\SCS\ErrorShowLog"
INITIAL_DELAY = 10
REFRESH_INTERVAL = 10
ALARM_THRESHOLD = 60

print("SCS AUTO-REFRESH")
print("=" * 40)

# Test klik
pyautogui.click(REFRESH_X, REFRESH_Y)
print(f"Clicked at ({REFRESH_X}, {REFRESH_Y})")

# Cari file log terbaru
log_files = []
for root, dirs, files in os.walk(LOG_DIR):
    for file in files:
        if "ErrorShow" in file and file.endswith(".log"):
            full_path = os.path.join(root, file)
            mod_time = os.path.getmtime(full_path)
            log_files.append((mod_time, full_path))

if not log_files:
    print("No log files found!")
    exit()

log_files.sort(reverse=True)
log_file = log_files[0][1]
print(f"Using: {os.path.basename(log_file)}")

print(f"\nDelay awal: {INITIAL_DELAY} detik")
print(f"Refresh: setiap {REFRESH_INTERVAL} detik")
print(f"Buzzer: nyala setelah 1 menit")
print("=" * 40)
print("Press Ctrl+C to stop\n")

# Variabel status global
refresh_count = 0
last_line_content = None
error_start_time = None
initial_delay_passed = False
in_error_state = False
last_refresh_time = 0
buzzer_active = False
stop_buzzer = False
last_mouse_pos = pyautogui.position()
buzzer_thread = None
technician_attended = False

def continuous_buzzer():
    """Buzzer bunyi terus menerus"""
    global stop_buzzer
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
    
    moved = (abs(current_pos.x - last_mouse_pos.x) > 10 or 
             abs(current_pos.y - last_mouse_pos.y) > 10)
    
    last_mouse_pos = current_pos
    return moved

def find_latest_status(content):
    """Cari status terbaru dalam content"""
    lines = content.split('\n')
    
    for line in reversed(lines):
        line = line.strip()
        if line:
            if line.endswith(": 1"):
                return "ERROR", line
            elif line.endswith(": 0"):
                return "NORMAL", line
            elif ": 1" in line:
                parts = line.split(":")
                if len(parts) >= 2 and parts[-1].strip() == "1":
                    return "ERROR", line
            elif ": 0" in line:
                parts = line.split(":")
                if len(parts) >= 2 and parts[-1].strip() == "0":
                    return "NORMAL", line
    
    return "UNKNOWN", None

# Baca encoding file
encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'ascii']
correct_encoding = 'utf-8'
for encoding in encodings:
    try:
        with open(log_file, 'r', encoding=encoding) as f:
            test_content = f.read(200)
        if 'system' in test_content.lower() or 'ready' in test_content.lower():
            correct_encoding = encoding
            break
    except:
        continue

# Inisialisasi status awal
try:
    with open(log_file, 'r', encoding=correct_encoding, errors='ignore') as f:
        content = f.read()
    
    status, line = find_latest_status(content)
    last_line_content = line
    
    if status == "ERROR":
        error_start_time = time.time()
        in_error_state = True
        
except Exception as e:
    pass

# ========== LOOP UTAMA ==========
while True:
    try:
        timestamp = time.strftime("%H:%M:%S")
        
        # Cek mouse untuk matikan buzzer
        if buzzer_active and not technician_attended:
            if check_mouse_moved():
                stop_buzzer = True
                buzzer_active = False
                technician_attended = True
                print(f"[{timestamp}] Mouse digerakkan - Buzzer dimatikan")
                time.sleep(1)
        
        # Baca file log
        try:
            with open(log_file, 'r', encoding=correct_encoding, errors='ignore') as f:
                content = f.read()
            
            status, line = find_latest_status(content)
            
            if line != last_line_content:
                last_line_content = line
                
                if status == "ERROR":
                    if not in_error_state:
                        print(f"[{timestamp}] ERROR DETECTED")
                        print(f"Line: {line[:80]}")
                        
                        error_start_time = time.time()
                        initial_delay_passed = False
                        in_error_state = True
                        last_refresh_time = 0
                        refresh_count = 0
                        technician_attended = False
                        
                        if buzzer_active:
                            stop_buzzer = True
                            buzzer_active = False
                        
                        print(f"Waiting {INITIAL_DELAY} seconds before first refresh...")
                    
                elif status == "NORMAL":
                    if in_error_state:
                        duration = time.time() - error_start_time if error_start_time else 0
                        mins, secs = divmod(int(duration), 60)
                        
                        print(f"[{timestamp}] SYSTEM BACK TO NORMAL")
                        print(f"Durasi error: {mins:02d}:{secs:02d}")
                        print(f"Total refresh: {refresh_count} kali")
                        
                        if buzzer_active:
                            stop_buzzer = True
                            buzzer_active = False
                        
                        in_error_state = False
                        error_start_time = None
                        initial_delay_passed = False
                        refresh_count = 0
                        technician_attended = False
            
            # Logika error state
            if in_error_state and not technician_attended:
                current_time = time.time()
                error_duration = current_time - error_start_time
                
                # Delay awal
                if not initial_delay_passed:
                    if error_duration >= INITIAL_DELAY:
                        initial_delay_passed = True
                        print(f"[{timestamp}] Mulai auto-refresh")
                
                # Auto-refresh (hanya sebelum 1 menit)
                if initial_delay_passed and error_duration < ALARM_THRESHOLD:
                    if current_time - last_refresh_time >= REFRESH_INTERVAL:
                        pyautogui.click(REFRESH_X, REFRESH_Y)
                        refresh_count += 1
                        last_refresh_time = current_time
                        
                        mins, secs = divmod(int(error_duration), 60)
                        print(f"[{timestamp}] Refresh #{refresh_count} (Error: {mins:02d}:{secs:02d})")
                
                # Buzzer setelah 1 menit
                if error_duration >= ALARM_THRESHOLD and not buzzer_active:
                    print(f"[{timestamp}] BUZZER NYALA! (Error > 1 menit)")
                    print("Auto-refresh dihentikan")
                    print("Gerakkan mouse untuk matikan buzzer")
                    
                    buzzer_active = True
                    stop_buzzer = False
                    buzzer_thread = threading.Thread(target=continuous_buzzer, daemon=True)
                    buzzer_thread.start()
        
        except Exception as e:
            pass
        
        time.sleep(1)
        
    except KeyboardInterrupt:
        print(f"\nPROGRAM DIHENTIKAN")
        print(f"Total refresh: {refresh_count}")
        
        if buzzer_active:
            stop_buzzer = True
        
        if in_error_state and error_start_time:
            duration = time.time() - error_start_time
            mins, secs = divmod(int(duration), 60)
            print(f"Error masih aktif: {mins:02d}:{secs:02d}")
        break
        
    except Exception as e:
        time.sleep(5)