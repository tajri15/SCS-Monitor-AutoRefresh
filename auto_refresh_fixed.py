import pyautogui
import time
import os
import threading
import winsound

# --- KONFIGURASI ---
REFRESH_X = 1470
REFRESH_Y = 2031
LOG_DIR = r"C:\SCS\ErrorShowLog"
INITIAL_DELAY = 5
REFRESH_INTERVAL = 5
ALARM_THRESHOLD = 60

print("SCS AUTO-REFRESH")
print("=" * 40)

# Test klik
pyautogui.click(REFRESH_X, REFRESH_Y)
print(f"Clicked at ({REFRESH_X}, {REFRESH_Y})")

# Cari file log terbaru
def get_latest_log_file():
    """Cari file log dengan timestamp terbaru di CONTENT"""
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
print("=" * 40)
print("Press Ctrl+C to stop\n")

# Variabel status global
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

def continuous_buzzer():
    """Buzzer bunyi terus menerus - FIXED VERSION"""
    global stop_buzzer
    
    print("  [BUZZER THREAD] Started")
    
    while not stop_buzzer:
        try:
            # Pecah beep menjadi interval kecil agar bisa check stop_buzzer lebih sering
            winsound.Beep(1500, 200)  # Beep 200ms
            
            # Check stop_buzzer setiap 100ms
            for _ in range(5):  # 5 x 100ms = 500ms total delay
                if stop_buzzer:
                    print("  [BUZZER THREAD] Stop signal received!")
                    return
                time.sleep(0.1)
                
        except Exception as e:
            print(f"  [BUZZER THREAD] Error: {e}")
            break
    
    print("  [BUZZER THREAD] Stopped normally")

def check_mouse_moved():
    """Cek apakah mouse bergerak dari posisi terakhir - IMPROVED"""
    global last_mouse_pos
    current_pos = pyautogui.position()
    
    # Sensitivity: 10 pixel
    moved = (abs(current_pos.x - last_mouse_pos.x) > 10 or 
             abs(current_pos.y - last_mouse_pos.y) > 10)
    
    if moved:
        print(f"  [MOUSE] Detected movement: ({last_mouse_pos.x},{last_mouse_pos.y}) → ({current_pos.x},{current_pos.y})")
    
    last_mouse_pos = current_pos
    return moved

def find_latest_status_simple(content):
    """Parsing untuk format log SCS"""
    lines = content.strip().split('\n')
    
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        
        if ": 1" in line:
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
        
        if line.endswith(": 1"):
            return "ERROR", line
        elif line.endswith(": 0"):
            return "NORMAL", line
        
        parts = line.split(":")
        if len(parts) >= 2:
            last_part = parts[-1].strip()
            if last_part == "1":
                return "ERROR", line
            elif last_part == "0":
                return "NORMAL", line
        
        cleaned = line.rstrip()
        if cleaned:
            for char in reversed(cleaned):
                if char.isdigit():
                    if char == '1':
                        return "ERROR", line
                    elif char == '0':
                        return "NORMAL", line
                    break
    
    return "UNKNOWN", None

# ===== INISIALISASI =====
print("Initializing...")
try:
    last_file_size = os.path.getsize(log_file)
    last_file_mtime = os.path.getmtime(log_file)
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    if lines:
        print(f"DEBUG - Last 5 lines of log:")
        for i, l in enumerate(lines[-5:]):
            print(f"  Line {i-4}: {l}")
    
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
        print("Unknown initial state - will monitor for changes")
        
except Exception as e:
    print(f"Initialization error: {e}")

# ========== LOOP UTAMA ==========
print("\nStarting monitoring loop...")
monitor_count = 0

while True:
    try:
        timestamp = time.strftime("%H:%M:%S")
        monitor_count += 1
        
        # ===== 1. CEK MOUSE UNTUK MATIKAN BUZZER - FIXED! =====
        if buzzer_active and not technician_attended:
            if check_mouse_moved():
                print(f"\n[{timestamp}] ===== MOUSE MOVED - STOPPING BUZZER =====")
                
                # Set flag stop
                stop_buzzer = True
                
                # Tunggu thread selesai
                if buzzer_thread and buzzer_thread.is_alive():
                    print("  Waiting for buzzer thread to stop...")
                    buzzer_thread.join(timeout=2.0)  # Tunggu max 2 detik
                    
                    if buzzer_thread.is_alive():
                        print("  Warning: Buzzer thread still running (force continue)")
                    else:
                        print("  Buzzer thread stopped successfully")
                
                buzzer_active = False
                technician_attended = True
                print(f"[{timestamp}] Buzzer dimatikan - Technician attended\n")
                
                # Reset mouse position agar tidak trigger lagi
                last_mouse_pos = pyautogui.position()
                time.sleep(1)
        
        # ===== 2. CEK PERUBAHAN FILE =====
        try:
            current_size = os.path.getsize(log_file)
            current_mtime = os.path.getmtime(log_file)
            
            file_changed = False
            
            if current_size != last_file_size or current_mtime != last_file_mtime:
                file_changed = True
                last_file_size = current_size
                last_file_mtime = current_mtime
                print(f"[{timestamp}] File changed: {current_size} bytes")
            
            if file_changed or monitor_count % 5 == 0:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if file_changed:
                    lines = content.strip().split('\n')
                    if lines:
                        last_line = lines[-1].strip()
                        print(f"[{timestamp}] Last line: {last_line[:80]}")
                
                status, line = find_latest_status_simple(content)
                
                if file_changed:
                    print(f"[{timestamp}] Parsed status: {status}")
                    if line:
                        print(f"  Parsed from: {line[:60]}...")
                
                # ===== 3. PROSES STATUS =====
                if line != last_line_content:
                    last_line_content = line
                    
                    if status == "ERROR":
                        if not in_error_state:
                            print(f"\n[{timestamp}] ===== ERROR DETECTED =====")
                            print(f"Error line: {line}")
                            print(f"Error code: {line.split(':')[1] if ':' in line else 'Unknown'}")
                            
                            error_start_time = time.time()
                            initial_delay_passed = False
                            in_error_state = True
                            last_refresh_time = 0
                            refresh_count = 0
                            technician_attended = False
                            
                            if buzzer_active:
                                stop_buzzer = True
                                if buzzer_thread:
                                    buzzer_thread.join(timeout=2.0)
                                buzzer_active = False
                            
                            print(f"Waiting {INITIAL_DELAY} seconds before first refresh...")
                        
                    elif status == "NORMAL":
                        if in_error_state:
                            duration = time.time() - error_start_time if error_start_time else 0
                            mins, secs = divmod(int(duration), 60)
                            
                            print(f"\n[{timestamp}] ===== SYSTEM BACK TO NORMAL =====")
                            print(f"Durasi error: {mins:02d}:{secs:02d}")
                            print(f"Total refresh: {refresh_count} kali")
                            
                            if buzzer_active:
                                stop_buzzer = True
                                if buzzer_thread:
                                    buzzer_thread.join(timeout=2.0)
                                buzzer_active = False
                            
                            in_error_state = False
                            error_start_time = None
                            initial_delay_passed = False
                            refresh_count = 0
                            technician_attended = False
                
                # ===== 4. LOGIKA ERROR STATE =====
                if in_error_state and not technician_attended:
                    current_time = time.time()
                    error_duration = current_time - error_start_time
                    
                    if not initial_delay_passed:
                        if error_duration >= INITIAL_DELAY:
                            initial_delay_passed = True
                            print(f"\n[{timestamp}] Delay selesai - Mulai auto-refresh setiap {REFRESH_INTERVAL} detik")
                    
                    if initial_delay_passed and error_duration < ALARM_THRESHOLD:
                        if current_time - last_refresh_time >= REFRESH_INTERVAL:
                            pyautogui.click(REFRESH_X, REFRESH_Y)
                            refresh_count += 1
                            last_refresh_time = current_time
                            
                            mins, secs = divmod(int(error_duration), 60)
                            print(f"[{timestamp}] Refresh #{refresh_count} (Error durasi: {mins:02d}:{secs:02d})")
                    
                    # BUZZER setelah 1 menit
                    if error_duration >= ALARM_THRESHOLD and not buzzer_active:
                        print(f"\n[{timestamp}] ===== BUZZER NYALA! =====")
                        print(f"Error telah berlangsung > 1 menit ({int(error_duration)} detik)")
                        print("Auto-refresh dihentikan")
                        print("GERAKKAN MOUSE UNTUK MATIKAN BUZZER")
                        print("=" * 40)
                        
                        buzzer_active = True
                        stop_buzzer = False
                        
                        # Start buzzer thread
                        buzzer_thread = threading.Thread(target=continuous_buzzer, daemon=True)
                        buzzer_thread.start()
                        
                        # Update mouse position
                        last_mouse_pos = pyautogui.position()
                        print(f"Current mouse position: {last_mouse_pos}")
            
            # ===== 5. STATUS MONITORING =====
            if monitor_count % 15 == 0:
                print(f"[{timestamp}] Monitoring... ", end="")
                if in_error_state:
                    if error_start_time:
                        duration = time.time() - error_start_time
                        mins, secs = divmod(int(duration), 60)
                        status_msg = f"ERROR: Durasi {mins:02d}:{secs:02d}, Refresh: {refresh_count}x"
                        if buzzer_active:
                            status_msg += " [BUZZER ACTIVE]"
                        print(status_msg)
                    else:
                        print("ERROR state")
                else:
                    print("Status: NORMAL")
                    
        except Exception as e:
            print(f"[{timestamp}] File read error: {e}")
        
        time.sleep(1)  # Dikurangi jadi 1 detik agar mouse detection lebih responsif
        
    except KeyboardInterrupt:
        print(f"\n===== PROGRAM DIHENTIKAN =====")
        print(f"Total refresh: {refresh_count}")
        
        if buzzer_active:
            stop_buzzer = True
            if buzzer_thread:
                buzzer_thread.join(timeout=2.0)
            print("Buzzer dimatikan")
        
        if in_error_state and error_start_time:
            duration = time.time() - error_start_time
            mins, secs = divmod(int(duration), 60)
            print(f"Error masih aktif: {mins:02d}:{secs:02d}")
        break
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
        time.sleep(5)