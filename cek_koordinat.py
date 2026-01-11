import pyautogui
import time

print("--- PENCARI KOORDINAT ---")
print("Arahkan mouse ke tombol Refresh di aplikasi SCS...")
for i in range(5, 0, -1):
    print(f"Ambil posisi dalam {i}...")
    time.sleep(1)

x, y = pyautogui.position()
print(f"\nKOORDINAT ANDA: ({x}, {y})")
input("Tekan Enter untuk keluar...")