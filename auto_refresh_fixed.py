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

print("SCS AUTO-REFRESH (Buzzer Fix Version)")
print("=" * 40)

# Test klik
pyautogui.click(REFRESH_X, REFRESH_Y)
print(f"Clicked at ({REFRESH_X}, {REFRESH_Y})")

# Cari file log terbaru
def get_latest_log_file():
    log_files = []
    for root, dirs, files in os.walk(LOG_DIR):
        for file in files:
            if "ErrorShow" in file and file.endswith(".log"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        if lines:
                            last_line = lines[-1].strip()
                            if last_line:
                                timestamp_str = last_line[:23]
                                try:
                                    from datetime import datetime
                                    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S:%f")
                                    timestamp = dt.timestamp()
                                    log_files.append((timestamp, full_path, last_line))
                                except:
                                    mod_time = os.path.getmtime(full_path)
                                    log_files.append((mod_time, full_path, last_line))
                except:
                    mod_time = os.path.getmtime(full_path)
                    log_files.append((mod_time, full_path, ""))
    
    if not log_files:
        return None, None
    
    log_files.sort(reverse=True)
    return log_files[0][1], log_files[0][2]

log_file, last_known_line = get_latest_log_file()
if not log_file:
    print("No log files found!")
    exit()

print(f"Using: {os.path.basename(log_file)}")
if last_known_line:
    print(f"Latest entry: {last_known_line[:80]}")

print(f"\nDelay awal: {INITIAL_DELAY} detik")
print(f"Refresh: setiap {REFRESH_INTERVAL} detik")
print(f"Buzzer: nyala setelah 1 menit")
print("Buzzer mati: Gerakkan mouse atau error selesai")
print("=" * 40)
print("Press Ctrl+C to stop\n")

# Variabel status global dengan threading lock
refresh_count = 0
last_line_content = last_known_line
error_start_time = None
initial_delay_passed = False
in_error_state = False
last_refresh_time = 0
buzzer_active = False
stop_buzzer = False
last_mouse_pos = pyautogui.position()
buzzer_thread = None
technician_attended = False
last_file_size = 0
last_file_mtime = 0
mouse_check_active = False
mouse_check_thread = None

# Lock untuk thread-safe variable access
status_lock = threading.Lock()

def continuous_buzzer():
    """Buzzer bunyi terus menerus"""
    global stop_buzzer, buzzer_active
    
    print("[BUZZER THREAD] Buzzer started")
    stop_buzzer = False
    
    while not stop_buzzer:
        winsound.Beep(1500, 300)
        time.sleep(0.7)
    
    print("[BUZZER THREAD] Buzzer stopped")
    with status_lock:
        buzzer_active = False

def check_mouse_movement():
    """Thread terpisah untuk memonitor pergerakan mouse secara kontinu"""
    global last_mouse_pos, technician_attended, stop_buzzer, mouse_check_active
    
    print("[MOUSE THREAD] Mouse monitoring started")
    mouse_check_active = True
    
    check_interval = 0.5  # Cek setiap 0.5 detik
    consecutive_moves = 0
    
    while mouse_check_active:
        try:
            current_pos = pyautogui.position()
            
            # Cek pergerakan mouse
            moved = (abs(current_pos.x - last_mouse_pos.x) > 10 or 
                     abs(current_pos.y - last_mouse_pos.y) > 10)
            
            last_mouse_pos = current_pos
            
            if moved:
                consecutive_moves += 1
                # Hanya trigger jika mouse bergerak 2 kali berturut-turut
                # (untuk menghindari false positive)
                if consecutive_moves >= 2:
                    with status_lock:
                        if buzzer_active and not technician_attended:
                            stop_buzzer = True
                            technician_attended = True
                            print("[MOUSE THREAD] Mouse moved - Buzzer stopped")
                            consecutive_moves = 0
            else:
                consecutive_moves = 0
            
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"[MOUSE THREAD] Error: {e}")
            break
    
    print("[MOUSE THREAD] Mouse monitoring stopped")

def find_latest_status_simple(content):
    """Parsing status dari log"""
    lines = content.strip().split('\n')
    
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        
        # Cari pattern ": 1" atau ": 0"
        if ": 1" in line:
            # Pastikan ini pattern status yang benar
            parts = line.split(": 1")
            if len(parts) > 1:
                rest = parts[-1]
                if not rest or rest.isspace():
                    return "ERROR", line
                elif rest and not rest[0].isdigit():
                    return "ERROR", line
        
        if ": 0" in line:
            parts = line.split(": 0")
            if len(parts) > 1:
                rest = parts[-1]
                if not rest or rest.isspace():
                    return "NORMAL", line
                elif rest and not rest[0].isdigit():
                    return "NORMAL", line
        
        # Cek akhir line
        if line.endswith(": 1"):
            return "ERROR", line
        elif line.endswith(": 0"):
            return "NORMAL", line
    
    return "UNKNOWN", None

# ===== INISIALISASI =====
print("Initializing...")
try:
    last_file_size = os.path.getsize(log_file)
    last_file_mtime = os.path.getmtime(log_file)
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    status, line = find_latest_status_simple(content)
    
    print(f"\nInitial status: {status}")
    if line:
        print(f"Latest line: {line[:80]}")
    
    if status == "ERROR":
        print("Starting in ERROR state!")
        error_start_time = time.time()
        in_error_state = True
        print(f"Waiting {INITIAL_DELAY} seconds before first refresh...")
    elif status == "NORMAL":
        print("Starting in NORMAL state - waiting for errors...")
    else:
        print("Unknown initial state")
        
except Exception as e:
    print(f"Initialization error: {e}")

# Start mouse monitoring thread
mouse_check_thread = threading.Thread(target=check_mouse_movement, daemon=True)
mouse_check_thread.start()

# ========== LOOP UTAMA ==========
print("\nStarting monitoring loop...")
monitor_count = 0

try:
    while True:
        timestamp = time.strftime("%H:%M:%S")
        monitor_count += 1
        
        # ===== 1. CEK PERUBAHAN FILE =====
        try:
            current_size = os.path.getsize(log_file)
            current_mtime = os.path.getmtime(log_file)
            
            file_changed = False
            
            if current_size != last_file_size or current_mtime != last_file_mtime:
                file_changed = True
                last_file_size = current_size
                last_file_mtime = current_mtime
                
                print(f"[{timestamp}] File changed: {current_size} bytes")
            
            # Baca file jika berubah atau untuk monitoring rutin
            if file_changed or monitor_count % 5 == 0:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                status, line = find_latest_status_simple(content)
                
                if file_changed:
                    print(f"[{timestamp}] Parsed status: {status}")
                    if line:
                        print(f"  Line: {line[:60]}...")
                
                # ===== 2. PROSES STATUS =====
                if line != last_line_content:
                    last_line_content = line
                    
                    if status == "ERROR":
                        with status_lock:
                            if not in_error_state:
                                print(f"\n[{timestamp}] ===== ERROR DETECTED =====")
                                print(f"Error line: {line}")
                                
                                # Reset semua timer
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
                        with status_lock:
                            if in_error_state:
                                duration = time.time() - error_start_time if error_start_time else 0
                                mins, secs = divmod(int(duration), 60)
                                
                                print(f"\n[{timestamp}] ===== SYSTEM BACK TO NORMAL =====")
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
                
                # ===== 3. LOGIKA ERROR STATE =====
                with status_lock:
                    if in_error_state and not technician_attended:
                        current_time = time.time()
                        error_duration = current_time - error_start_time
                        
                        # Delay awal
                        if not initial_delay_passed:
                            if error_duration >= INITIAL_DELAY:
                                initial_delay_passed = True
                                print(f"\n[{timestamp}] Delay selesai - Mulai auto-refresh setiap {REFRESH_INTERVAL} detik")
                        
                        # Auto-refresh (hanya sebelum 1 menit)
                        if initial_delay_passed and error_duration < ALARM_THRESHOLD:
                            if current_time - last_refresh_time >= REFRESH_INTERVAL:
                                # KLIK REFRESH
                                pyautogui.click(REFRESH_X, REFRESH_Y)
                                refresh_count += 1
                                last_refresh_time = current_time
                                
                                mins, secs = divmod(int(error_duration), 60)
                                print(f"[{timestamp}] Refresh #{refresh_count} (Error: {mins:02d}:{secs:02d})")
                        
                        # BUZZER setelah 1 menit
                        if error_duration >= ALARM_THRESHOLD and not buzzer_active:
                            print(f"\n[{timestamp}] ===== BUZZER NYALA! =====")
                            print(f"Error telah berlangsung > 1 menit ({int(error_duration)} detik)")
                            print("Auto-refresh dihentikan")
                            print("Gerakkan mouse untuk matikan buzzer")
                            
                            technician_attended = False  # Reset agar mouse bisa mematikan
                            buzzer_active = True
                            stop_buzzer = False
                            buzzer_thread = threading.Thread(target=continuous_buzzer, daemon=True)
                            buzzer_thread.start()
            
            # ===== 4. STATUS MONITORING =====
            if monitor_count % 15 == 0:
                print(f"[{timestamp}] Monitoring... ", end="")
                with status_lock:
                    if in_error_state:
                        if error_start_time:
                            duration = time.time() - error_start_time
                            mins, secs = divmod(int(duration), 60)
                            print(f"ERROR: {mins:02d}:{secs:02d}, Refresh: {refresh_count}x, Buzzer: {'ON' if buzzer_active else 'OFF'}")
                    else:
                        print("Status: NORMAL")
                        
        except Exception as e:
            print(f"[{timestamp}] Error: {e}")
        
        # Sleep pendek agar responsive
        time.sleep(1)
        
except KeyboardInterrupt:
    print(f"\n===== PROGRAM DIHENTIKAN =====")
    print(f"Total refresh: {refresh_count}")
    
    # Stop semua thread
    mouse_check_active = False
    stop_buzzer = True
    
    if in_error_state and error_start_time:
        duration = time.time() - error_start_time
        mins, secs = divmod(int(duration), 60)
        print(f"Error masih aktif: {mins:02d}:{secs:02d}")
    
    print("Waiting for threads to stop...")
    time.sleep(1)