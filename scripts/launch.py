# -*- coding: utf-8 -*-
import os
import sys
import io
import time
import urllib.request
import webbrowser
import subprocess

if sys.stdout.buffer:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.buffer:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PORT = 8085
URL = f"http://localhost:{PORT}/"
STATE_URL = f"http://127.0.0.1:{PORT}/api/state"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def is_server_alive():
    try:
        with urllib.request.urlopen(STATE_URL, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def kill_port_processes():
    print(f"[*] ポート {PORT} の競合プロセスを確認中...")
    try:
        out = subprocess.check_output(f'netstat -ano | findstr ":{PORT} .*LISTENING"', shell=True, text=True)
        for line in out.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid.isdigit() and int(pid) != os.getpid():
                    print(f"[*] 停止したゾンビプロセス (PID: {pid}) をクリーンアップ中...")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
    except Exception:
        pass

def main():
    print("========================================================")
    print("  ターニャ先生のロシア語学習アプリ (Tanya Russian)")
    print("========================================================")
    
    if is_server_alive():
        print(f"[OK] サーバーは既にポート {PORT} で正常稼働中です。")
    else:
        kill_port_processes()
        print(f"[*] サーバーを起動しています (ポート {PORT})...")
        server_py = os.path.join(BASE_DIR, "server.py")
        subprocess.Popen(
            [sys.executable, "-u", server_py],
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        print("[*] サーバーの応答待機中...")
        started = False
        for _ in range(15):
            time.sleep(0.4)
            if is_server_alive():
                started = True
                break
        if started:
            print("[OK] サーバーの正常起動を確認しました！")
        else:
            print("[警告] サーバー応答待機がタイムアウトしましたが、ブラウザを開きます。")

    print(f"[*] ブラウザでアプリを表示します: {URL}")
    try:
        webbrowser.open(URL)
    except Exception:
        pass
    print("\n[完了] アプリがブラウザで開きました♪")
    time.sleep(2)

if __name__ == '__main__':
    main()
