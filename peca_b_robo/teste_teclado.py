"""
Diagnostico: testa 3 metodos de enviar teclas para o SIMN.

Uso:
  1. Abrir SIMN, chegar ao form Vendedor(es), CURSOR NO CAMPO 'Nº Contribuinte'.
  2. Alt+Tab para o PowerShell.
  3. Correr: python peca_b_robo/teste_teclado.py
  4. Depois do countdown, ALT+TAB PARA O SIMN e nao mexer.
  5. Ver o que aparece no campo Nº Contribuinte.

Interpretacao do resultado:
  - Se aparecer 'A_1234' → pyautogui funciona
  - Se aparecer 'B_5678' → pywinauto.keyboard funciona
  - Se aparecer 'C_ABCD' → keyboard module funciona
  - Se aparecerem os tres → todos funcionam, problema esta noutro sitio
  - Se aparecer NADA → problema mais profundo (ex: UAC bloqueia mesmo elevado,
    ou SIMN nao recebe teclas de outros processos)
"""
from __future__ import annotations

import time

print("=" * 60)
print("TESTE de metodos de envio de teclas")
print("=" * 60)
print()
print("Focar o campo Nº Contribuinte no SIMN e Alt+Tab de volta.")
print("Em 5 segundos comeca. NAO MEXAS depois do Alt+Tab.")
print()
for i in range(5, 0, -1):
    print(f"  {i}...", flush=True)
    time.sleep(1)

# METODO A: pyautogui (o que estamos a usar)
print("\n[A] A tentar pyautogui.write('A_1234')...")
try:
    import pyautogui
    pyautogui.write('A_1234', interval=0.05)
    print("[A] pyautogui.write executou sem erro.")
except Exception as e:
    print(f"[A] FALHOU: {e}")
time.sleep(1)

# METODO B: pywinauto.keyboard.send_keys
print("\n[B] A tentar pywinauto.keyboard.send_keys('B_5678')...")
try:
    from pywinauto.keyboard import send_keys
    send_keys('B_5678', with_spaces=True, pause=0.05)
    print("[B] send_keys executou sem erro.")
except Exception as e:
    print(f"[B] FALHOU: {e}")
time.sleep(1)

# METODO C: keyboard library
print("\n[C] A tentar keyboard.write('C_ABCD')...")
try:
    import keyboard
    keyboard.write('C_ABCD', delay=0.05)
    print("[C] keyboard.write executou sem erro.")
except ImportError:
    print("[C] SALTADO: 'keyboard' nao instalado. Faz pip install keyboard e repete.")
except Exception as e:
    print(f"[C] FALHOU: {e}")

print()
print("=" * 60)
print("Terminado. Ve o campo Nº Contribuinte no SIMN e reporta o que aparece.")
print("=" * 60)
