import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

HOST = '127.0.0.1'
PORT = 5005
VARIANT = 5

S_TABLE = [
    0xa3,0xd7,0x09,0x83,0xf8,0x48,0xf6,0xf4,0xb3,0x21,0x15,0x78,0x99,0xb1,0xaf,0xf9,
    0xe7,0x2d,0x4d,0x8a,0xce,0x4c,0xca,0x2e,0x52,0x95,0xd9,0x1e,0x4e,0x38,0x44,0x28,
    0x0a,0xdf,0x02,0xa0,0x17,0xf1,0x60,0x68,0x12,0xb7,0x7a,0xc3,0xe9,0xfa,0x3d,0x53,
    0x96,0x84,0x6b,0xba,0xf2,0x63,0x9a,0x19,0x7c,0xae,0xe5,0xf5,0xf7,0x16,0x6a,0xa2,
    0x39,0xb6,0x7b,0x0f,0xc1,0x93,0x81,0x1b,0xee,0xb4,0x1a,0xea,0xd0,0x91,0x2f,0xb8,
    0x55,0xb9,0xda,0x85,0x3f,0x41,0xbf,0xe0,0x5a,0x58,0x80,0x5f,0x66,0x0b,0xd8,0x90,
    0x35,0xd5,0xc0,0xa7,0x33,0x06,0x65,0x69,0x45,0x00,0x94,0x56,0x6d,0x98,0x9b,0x76,
    0x97,0xfc,0xb2,0xc2,0xb0,0xfe,0xdb,0x20,0xe1,0xeb,0xd6,0xe4,0xdd,0x47,0x4a,0x1d,
    0x42,0xed,0x9e,0x6e,0x49,0x3c,0xcd,0x43,0x27,0xd2,0x07,0xd4,0xde,0xc7,0x67,0x18,
    0x89,0xcb,0x30,0x1f,0x8d,0xc6,0x8f,0xaa,0xc8,0x74,0xdc,0xc9,0x5d,0x5c,0x31,0xa4,
    0x70,0x88,0x61,0x2c,0x9f,0x0d,0x2b,0x87,0x50,0x82,0x54,0x64,0x26,0x7d,0x03,0x40,
    0x34,0x4b,0x1c,0x73,0xd1,0xc4,0xfd,0x3b,0xcc,0xfb,0x7f,0xab,0xe6,0x3e,0x5b,0xa5,
    0xad,0x04,0x23,0x9c,0x14,0x51,0x29,0x79,0x71,0x2a,0x0e,0x96,0x24,0x72,0x4f,0x08,
    0x86,0x11,0x8b,0x8e,0xfe,0xbe,0x36,0x3a,0x75,0x0c,0x8c,0x6c,0x22,0xb5,0x25,0x5e,
    0x0f,0x01,0xbd,0x57,0x62,0xac,0x92,0x7e,0x05,0x32,0x6f,0x2d,0x77,0x37,0x81,0x5a,
    0x15,0x1b,0xdc,0x9d,0x9a,0x1a,0x10,0x1e,0x2e,0x27,0x1f,0x35,0x28,0x20,0x21,0x3a,
]

MASK32 = 0xFFFFFFFF

def _lrot(x, n):
    x &= MASK32
    return ((x << n) | (x >> (32 - n))) & MASK32

def _rrot(x, n):
    x &= MASK32
    return ((x >> n) | (x << (32 - n))) & MASK32

def mahash8(data: bytes) -> int:
    length = len(data)
    hash1 = length
    hash2 = length
    for i, b in enumerate(data):
        hash1 = (hash1 + S_TABLE[(b + i) & 0xFF]) & MASK32
        hash1 = _lrot((hash1 + ((hash1 << 6) ^ (hash1 >> 11))) & MASK32, 14)
        hash2 = (hash2 + S_TABLE[(b + i) & 0xFF]) & MASK32
        hash2 = _rrot((hash2 + ((hash2 << 6) ^ (hash2 >> 11))) & MASK32, 14)
        sh1, sh2 = hash1, hash2
        hash1 = ((sh1 >> 16) & 0xFFFF) | ((sh2 & 0xFFFF) << 16)
        hash2 = ((sh2 >> 16) & 0xFFFF) | ((sh1 & 0xFFFF) << 16)
    return hash1 ^ hash2

def _keystream_byte(password: str, counter: int) -> int:
    seed = f"{password}:{counter}".encode('utf-8')
    return mahash8(seed) & 0xFF

def encrypt_text(text: str, password: str) -> str:
    if not password:
        return text
    raw = text.encode('utf-8')
    out = bytearray()
    for i, b in enumerate(raw):
        out.append(b ^ _keystream_byte(password, i))
    return out.hex()

def decrypt_text(cipher_hex: str, password: str) -> str:
    if not password:
        return cipher_hex
    try:
        raw = bytes.fromhex(cipher_hex)
    except ValueError:
        return cipher_hex  # если это не hex возвращаем как есть
    out = bytearray()
    for i, b in enumerate(raw):
        out.append(b ^ _keystream_byte(password, i))
    try:
        return out.decode('utf-8')
    except UnicodeDecodeError:
        return out.hex()

class CryptoServer:
    def __init__(self, log_widget):
        self.log = log_widget # ссылка на виджет
        self.server_socket = None # слушающий сокет
        self.running = False
        self.clients = set() # множество активных клиентских сокетов

    def log_msg(self, msg):
        self.log.insert(tk.END, msg + '\n')
        self.log.see(tk.END)

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # создаём tcp сокет ipv4
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # разрешаем повторно использовать адрес, потому что после остановки сервера порт может ещё висеть в состоянии TIME_WAIT
        self.server_socket.bind((HOST, PORT)) # привязываем сокет к паре. чтобы ос знала, что пакеты на этот порт нужно отдавать этому процессу
        self.server_socket.listen(5) # режим прослушивания. тут 5 макс размер очереди, пока они не пойдут в accept
        self.running = True
        self.log_msg(f"[СЕРВЕР] Запущен на {HOST}:{PORT} (MaHash8)")
        threading.Thread(target=self.accept_loop, daemon=True).start()

    def stop(self):
        self.running = False
        try:
            self.server_socket.close()
        except Exception:
            pass
        for c in list(self.clients):
            try:
                c.close()
            except Exception:
                pass
        self.clients.clear()
        self.log_msg("[СЕРВЕР] Остановлен")

    def accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept() # возвращает новый сокет связанный именно с этим клиентом. addr кортеж ip + порт
            except OSError:
                break
            self.clients.add(client_sock)
            self.log_msg(f"[+] Подключён клиент {addr}")
            threading.Thread(target=self.handle_client,
                             args=(client_sock, addr), daemon=True).start()

    def handle_client(self, conn, addr):
        buffer = ""
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8', errors='ignore')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    self.log_msg(f"[{addr}] << {line}")
                    response, close_flag = self.process_command(line)
                    self.log_msg(f"[{addr}] >> {response}")
                    conn.sendall((response + '\n').encode('utf-8'))
                    if close_flag:
                        conn.close()
                        self.clients.discard(conn)
                        self.log_msg(f"[-] Клиент {addr} отключён по bye")
                        return
        except ConnectionResetError:
            pass
        finally:
            conn.close()
            self.clients.discard(conn)
            self.log_msg(f"[-] Отключён клиент {addr}")

    def process_command(self, line: str):
        cmd, _, rest = line.partition(' ')
        cmd = cmd.lower().strip()
        rest = rest.strip()

        # hello <вариант>
        if cmd == 'hello':
            if rest == str(VARIANT):
                return f"hello variant {VARIANT}", False
            return f"error: expected 'hello {VARIANT}'", False

        # bye <вариант>
        if cmd == 'bye':
            if rest == str(VARIANT):
                return f"bye variant {VARIANT}", True
            return f"error: expected 'bye {VARIANT}'", False

        # encrypt
        if cmd == 'encrypt':
            if ' ' not in rest:
                return "error: usage encrypt <message> <password>", False
            message, password = rest.rsplit(' ', 1)
            if not message or not password:
                return "error: empty message or password", False
            encrypted = encrypt_text(message, password)
            return f"encrypted: {encrypted}", False

        # decrypt
        if cmd == 'decrypt':
            if ' ' not in rest:
                return "error: usage decrypt <hex> <password>", False
            cipher_hex, password = rest.rsplit(' ', 1)
            decrypted = decrypt_text(cipher_hex, password)
            return f"decrypted: {decrypted}", False

        return "error: unknown command", False


class ServerGUI:
    def __init__(self, root):
        self.root = root
        root.title("lab2 server")
        root.geometry("740x500")

        top = tk.Frame(root)
        top.pack(fill=tk.X, padx=8, pady=6)
        tk.Label(top, text=f"Порт: {PORT}   Вариант: {VARIANT}   Метод: MaHash8").pack(side=tk.LEFT)

        self.btn_start = tk.Button(top, text="Запустить сервер", command=self.start_server)
        self.btn_start.pack(side=tk.RIGHT, padx=4)
        self.btn_stop = tk.Button(top, text="Остановить", command=self.stop_server, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.RIGHT, padx=4)

        tk.Label(root, text="Журнал сервера:").pack(anchor=tk.W, padx=8)
        self.log = scrolledtext.ScrolledText(root, height=24, font=("Consolas", 10))
        self.log.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.server = CryptoServer(self.log)

    def start_server(self):
        try:
            self.server.start()
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить сервер:\n{e}")

    def stop_server(self):
        self.server.stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)


if __name__ == '__main__':
    root = tk.Tk()
    ServerGUI(root)
    root.mainloop()