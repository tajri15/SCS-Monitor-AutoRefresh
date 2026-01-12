import pyautogui
import time
import os
import glob

# --- KONFIGURASI ---
REFRESH_X = 1470
REFRESH_Y = 2031
LOG_DIR = r"C:\SCS\ErrorShowLog"

print("🔄 SCS AUTO-REFRESH - ENCODING FIX")
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

if not log_files:
    print("❌ No log files found!")
    exit()

log_files.sort(reverse=True)
log_file = log_files[0][1]
print(f"✅ Using: {os.path.basename(log_file)}")

# Coba berbagai encoding
encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252', 'ascii']

print("\n🔍 Testing file encoding...")
correct_encoding = None
sample_content = None

for encoding in encodings:
    try:
        with open(log_file, 'r', encoding=encoding) as f:
            test_content = f.read(200)  # Baca 200 karakter pertama
        
        # Cek jika content terlihat normal (tidak ada karakter aneh)
        if 'system' in test_content.lower() or 'ready' in test_content.lower():
            correct_encoding = encoding
            sample_content = test_content
            print(f"✅ Found encoding: {encoding}")
            break
    except:
        continue

if not correct_encoding:
    print("⚠️  Cannot determine encoding, using utf-8 with errors ignore")
    correct_encoding = 'utf-8'

print("\n📄 Reading file with encoding:", correct_encoding)

# Baca file dengan encoding yang benar
try:
    with open(log_file, 'r', encoding=correct_encoding, errors='ignore') as f:
        content = f.read()
    
    print(f"File size: {len(content)} characters")
    
    # Split menjadi baris
    lines = content.split('\n')
    print(f"Total lines: {len(lines)}")
    
    # Tampilkan beberapa baris terakhir yang tidak kosong
    print("\nLast non-empty lines:")
    count = 0
    for i in range(len(lines)-1, -1, -1):
        line = lines[i].strip()
        if line:
            print(f"[{i+1}] {line[:80]}")
            count += 1
            if count >= 5:
                break
                
except Exception as e:
    print(f"❌ Error reading file: {e}")
    exit()

print("\n🚀 STARTING MONITORING...")
print("=" * 50)
print("Press Ctrl+C to stop\n")

def find_latest_status(content):
    """Cari status terbaru dalam content"""
    lines = content.split('\n')
    
    for line in reversed(lines):
        line = line.strip()
        if line:
            # Cari pattern ": 1" atau ": 0"
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

refresh_count = 0
last_status = None
last_line_content = None

while True:
    try:
        timestamp = time.strftime("%H:%M:%S")
        
        # Baca file
        try:
            with open(log_file, 'r', encoding=correct_encoding, errors='ignore') as f:
                content = f.read()
            
            # Cari status terbaru
            status, line = find_latest_status(content)
            
            if line != last_line_content:
                # Ada perubahan di log
                if status == "ERROR":
                    print(f"\n[{timestamp}] 🔴 ERROR DETECTED")
                    print(f"   Line: {line[:80]}")
                    
                    # KLIK REFRESH
                    pyautogui.click(REFRESH_X, REFRESH_Y)
                    refresh_count += 1
                    print(f"   🔄 REFRESH #{refresh_count}")
                    
                elif status == "NORMAL":
                    if last_status == "ERROR":
                        print(f"\n[{timestamp}] ✅ SYSTEM BACK TO NORMAL")
                        print(f"   Line: {line[:80]}")
                    # else: normal terus, tidak perlu print
                
                last_line_content = line
                last_status = status
                
            else:
                # Status sama, tidak ada perubahan
                if status == "ERROR" and int(time.time()) % 10 == 0:
                    # Setiap 10 detik saat error, lakukan refresh
                    pyautogui.click(REFRESH_X, REFRESH_Y)
                    refresh_count += 1
                    print(f"[{timestamp}] 🔄 Auto-refresh #{refresh_count}")
        
        except Exception as e:
            print(f"[{timestamp}] ❌ Read error: {e}")
        
        time.sleep(2)
        
    except KeyboardInterrupt:
        print(f"\n🛑 STOPPED. Total refreshes: {refresh_count}")
        break
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ Error: {e}")
        time.sleep(5)