import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

HOST = '127.0.0.1'
PORT = 5005
VARIANT = 5

class ClientGUI:
    def __init__(self, root):
        self.root = root
        root.title("lab2 client")
        root.geometry("760x580")

        self.sock = None
        self.connected = False

        # Подключение
        conn_frame = tk.LabelFrame(root, text="Подключение")
        conn_frame.pack(fill=tk.X, padx=8, pady=6)
        tk.Label(conn_frame, text="Хост:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.entry_host = tk.Entry(conn_frame, width=15)
        self.entry_host.insert(0, HOST)
        self.entry_host.grid(row=0, column=1, padx=4)
        tk.Label(conn_frame, text="Порт:").grid(row=0, column=2, sticky=tk.W, padx=4)
        self.entry_port = tk.Entry(conn_frame, width=8)
        self.entry_port.insert(0, str(PORT))
        self.entry_port.grid(row=0, column=3, padx=4)
        self.btn_connect = tk.Button(conn_frame, text="Подключиться", command=self.connect)
        self.btn_connect.grid(row=0, column=4, padx=6)
        self.btn_disconnect = tk.Button(conn_frame, text="Отключиться",
                                        command=self.disconnect, state=tk.DISABLED)
        self.btn_disconnect.grid(row=0, column=5, padx=6)

        # Ручной ввод команды
        manual_frame = tk.LabelFrame(root, text="Ручной ввод команды (Enter — отправить)")
        manual_frame.pack(fill=tk.X, padx=8, pady=6)
        self.entry_manual = tk.Entry(manual_frame, font=("Consolas", 11))
        self.entry_manual.pack(fill=tk.X, padx=4, pady=4)
        self.entry_manual.bind("<Return>", lambda e: self.send_manual())
        tk.Button(manual_frame, text="Отправить", command=self.send_manual).pack(anchor=tk.E, padx=4, pady=2)

        # Быстрые команды
        cmd_frame = tk.LabelFrame(root, text="Быстрые команды")
        cmd_frame.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(cmd_frame, text="Сообщение:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.entry_msg = tk.Entry(cmd_frame, width=50)
        self.entry_msg.grid(row=0, column=1, columnspan=3, padx=4, pady=4, sticky=tk.EW)

        tk.Label(cmd_frame, text="Пароль:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.entry_pass = tk.Entry(cmd_frame, width=50)
        self.entry_pass.grid(row=1, column=1, columnspan=3, padx=4, pady=4, sticky=tk.EW)

        btn_frame = tk.Frame(cmd_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=6)
        tk.Button(btn_frame, text="hello", width=10,
                  command=lambda: self.send_raw(f"hello {VARIANT}")).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="encrypt", width=10,
                  command=self.do_encrypt).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="decrypt", width=10,
                  command=self.do_decrypt).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="bye", width=10,
                  command=lambda: self.send_raw(f"bye {VARIANT}")).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="Очистить поля", width=14,
                  command=self.clear_fields).pack(side=tk.LEFT, padx=3)
        cmd_frame.columnconfigure(1, weight=1)

        # Журнал
        tk.Label(root, text="Журнал обмена:").pack(anchor=tk.W, padx=8)
        self.log = scrolledtext.ScrolledText(root, height=14, font=("Consolas", 10))
        self.log.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    # сеть
    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.entry_host.get(), int(self.entry_port.get()))) # блокирующий
            self.connected = True
            self.log_msg("[КЛИЕНТ] Соединение установлено")
            self.btn_connect.config(state=tk.DISABLED)
            self.btn_disconnect.config(state=tk.NORMAL)
            threading.Thread(target=self.recv_loop, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Ошибка подключения", str(e))

    def disconnect(self):
        self.connected = False
        try:
            self.sock.close()
        except Exception:
            pass
        self.log_msg("[КЛИЕНТ] Соединение закрыто")
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)

    # прием ответов от сервера
    def recv_loop(self):
        buffer = ""
        try:
            while self.connected:
                data = self.sock.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8', errors='ignore')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self.log_msg(f"[СЕРВЕР] << {line.strip()}")
        except Exception:
            pass
        finally:
            if self.connected:
                self.disconnect()

    def send_raw(self, text):
        if not self.connected:
            messagebox.showwarning("Нет соединения", "Сначала подключитесь к серверу")
            return
        try:
            self.sock.sendall((text + '\n').encode('utf-8'))
            self.log_msg(f"[КЛИЕНТ] >> {text}")
        except Exception as e:
            messagebox.showerror("Ошибка отправки", str(e))

    # действия
    def send_manual(self):
        text = self.entry_manual.get().strip()
        if not text:
            return
        self.send_raw(text)
        self.entry_manual.delete(0, tk.END)

    def do_encrypt(self):
        msg = self.entry_msg.get().strip()
        pwd = self.entry_pass.get().strip()
        if not msg or not pwd:
            messagebox.showwarning("Внимание", "Введите сообщение и пароль")
            return
        # сообщение может содержать пробелы — отправляем как есть,
        # пароль идёт последним словом
        self.send_raw(f"encrypt {msg} {pwd}")

    def do_decrypt(self):
        cipher = self.entry_msg.get().strip()
        pwd = self.entry_pass.get().strip()
        if not cipher or not pwd:
            messagebox.showwarning("Внимание", "Введите шифротекст (hex) и пароль")
            return
        self.send_raw(f"decrypt {cipher} {pwd}")

    def clear_fields(self):
        self.entry_msg.delete(0, tk.END)
        self.entry_pass.delete(0, tk.END)

    def log_msg(self, msg):
        self.log.insert(tk.END, msg + '\n')
        self.log.see(tk.END)


if __name__ == '__main__':
    root = tk.Tk()
    ClientGUI(root)
    root.mainloop()