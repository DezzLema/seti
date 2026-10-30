import sys
import re
import subprocess

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QTextEdit, QComboBox,
    QMessageBox, QHeaderView, QGroupBox, QFormLayout,
    QCheckBox, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal


class WorkerThread(QThread):
    output_ready = Signal(str)
    error_ready = Signal(str)
    progress_update = Signal(int)
    finished_success = Signal()

    def __init__(self, cmd, total_steps=0):
        super().__init__()
        self.cmd = cmd
        self.total_steps = total_steps
        self.process = None
        self.is_running = True

    def run(self):
        try:
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="cp866",
                errors="replace",
                shell=False
            )

            stdout_lines = []
            count = 0
            for line in self.process.stdout:
                if not self.is_running:
                    self.process.terminate()
                    break
                stdout_lines.append(line)
                if self.total_steps > 0:
                    count += 1
                    progress = int((count / self.total_steps) * 100)
                    self.progress_update.emit(min(progress, 100))

            self.process.wait()
            stderr_output = self.process.stderr.read()

            self.output_ready.emit("".join(stdout_lines))
            if stderr_output:
                self.error_ready.emit(stderr_output)

            self.progress_update.emit(100)
            self.finished_success.emit()

        except Exception as e:
            self.error_ready.emit(str(e))
            self.progress_update.emit(100)

    def stop(self):
        self.is_running = False
        if self.process:
            self.process.terminate()


class PingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        params_box = QGroupBox("Параметры ping")
        form = QFormLayout()

        self.host_edit = QLineEdit("8.8.8.8")
        self.host_edit.setPlaceholderText("IP-адрес или доменное имя")

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(4)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(32, 65500)
        self.size_spin.setValue(64)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 10000)
        self.timeout_spin.setValue(1000)
        self.timeout_spin.setSuffix(" мс")

        self.ttl_spin = QSpinBox()
        self.ttl_spin.setRange(1, 255)
        self.ttl_spin.setValue(128)

        self.tos_spin = QSpinBox()
        self.tos_spin.setRange(0, 255)
        self.tos_spin.setValue(0)

        self.route_spin = QSpinBox()
        self.route_spin.setRange(1, 9)
        self.route_spin.setValue(1)

        self.timestamp_spin = QSpinBox()
        self.timestamp_spin.setRange(0, 4)
        self.timestamp_spin.setValue(0)

        self.j_list_edit = QLineEdit()
        self.j_list_edit.setPlaceholderText("192.168.1.1,192.168.1.2")

        self.k_list_edit = QLineEdit()
        self.k_list_edit.setPlaceholderText("192.168.1.1,192.168.1.2")

        self.cb_t = QCheckBox("Непрерывно (-t)")
        self.cb_a = QCheckBox("Разрешать имена (-a)")
        self.cb_f = QCheckBox("Не фрагментировать (-f)")

        form.addRow("Узел:", self.host_edit)
        form.addRow("Число запросов (-n):", self.count_spin)
        form.addRow("Размер пакета (-l):", self.size_spin)
        form.addRow("Таймаут (-w):", self.timeout_spin)
        form.addRow("Время жизни TTL (-i):", self.ttl_spin)
        form.addRow("Тип службы TOS (-v):", self.tos_spin)
        form.addRow("Запись маршрута (-r):", self.route_spin)
        form.addRow("Метка времени (-s):", self.timestamp_spin)
        form.addRow("Список узлов (-j):", self.j_list_edit)
        form.addRow("Список узлов (-k):", self.k_list_edit)
        form.addRow(self.cb_t)
        form.addRow(self.cb_a)
        form.addRow(self.cb_f)
        params_box.setLayout(form)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Запустить ping")
        self.run_btn.clicked.connect(self.run_ping)
        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.clicked.connect(self.stop_ping)
        self.stop_btn.setEnabled(False)
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setValue(0)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["№", "Ответ от", "Байт", "Время, мс", "TTL"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.stats = QTextEdit()
        self.stats.setReadOnly(True)
        self.stats.setMaximumHeight(120)

        layout.addWidget(params_box)
        layout.addLayout(btn_layout)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Ответы (по строкам):"))
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Статистика:"))
        layout.addWidget(self.stats)

    def run_ping(self):
        host = self.host_edit.text().strip()
        if not host:
            QMessageBox.warning(self, "Ошибка", "Введите узел!")
            return

        self.table.setRowCount(0)
        self.stats.clear()
        self.progress.setValue(0)

        cmd = ["ping"]
        if self.cb_t.isChecked():
            cmd.append("-t")
        if self.cb_a.isChecked():
            cmd.append("-a")
        if self.cb_f.isChecked():
            cmd.append("-f")

        cmd += ["-n", str(self.count_spin.value())]
        cmd += ["-l", str(self.size_spin.value())]
        cmd += ["-w", str(self.timeout_spin.value())]
        cmd += ["-i", str(self.ttl_spin.value())]
        cmd += ["-v", str(self.tos_spin.value())]

        if self.route_spin.value() > 1:
            cmd += ["-r", str(self.route_spin.value())]
        if self.timestamp_spin.value() > 0:
            cmd += ["-s", str(self.timestamp_spin.value())]

        j_text = self.j_list_edit.text().strip()
        if j_text:
            cmd += ["-j", j_text]

        k_text = self.k_list_edit.text().strip()
        if k_text:
            cmd += ["-k", k_text]

        cmd.append(host)

        self.stats.append(f"Команда: {' '.join(cmd)}\n")

        total = 0 if self.cb_t.isChecked() else self.count_spin.value()
        self.worker = WorkerThread(cmd, total_steps=total)
        self.worker.output_ready.connect(self.on_output)
        self.worker.error_ready.connect(self.on_error)
        self.worker.progress_update.connect(self.progress.setValue)
        self.worker.finished_success.connect(self.on_finished)

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.worker.start()

    def stop_ping(self):
        if self.worker:
            self.worker.stop()
            self.stop_btn.setEnabled(False)

    def on_output(self, out):
        row = 0
        pattern = re.compile(
            r"(?:Ответ от|Reply from)\s+([\d\.]+).*?"
            r"(?:байт|bytes)[=\s]+(\d+).*?"
            r"(?:время|time)[=<]?\s*([\d]+)\s*(?:мс|ms).*?"
            r"TTL[=\s]+(\d+)",
            re.IGNORECASE
        )

        for line in out.splitlines():
            m = pattern.search(line)
            if m:
                ip, size, time_ms, ttl = m.groups()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.table.setItem(row, 1, QTableWidgetItem(ip))
                self.table.setItem(row, 2, QTableWidgetItem(size))
                self.table.setItem(row, 3, QTableWidgetItem(time_ms))
                self.table.setItem(row, 4, QTableWidgetItem(ttl))
                row += 1

        if row == 0:
            for line in out.splitlines():
                if "Превышен интервал" in line or "Request timed out" in line:
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                    self.table.setItem(row, 1, QTableWidgetItem("*"))
                    self.table.setItem(row, 2, QTableWidgetItem("0"))
                    self.table.setItem(row, 3, QTableWidgetItem("-"))
                    self.table.setItem(row, 4, QTableWidgetItem("-"))
                    row += 1

        stats_lines = []
        for line in out.splitlines():
            if any(k in line for k in [
                "Статистика Ping", "Packets:", "Пакетов:",
                "Минимальное", "Maximum", "Approximate",
                "Минимальное время", "Максимальное время", "Среднее время",
                "Minimum", "Maximum", "Average"
            ]):
                stats_lines.append(line)

        if stats_lines:
            self.stats.append("\n".join(stats_lines))
        else:
            self.stats.append(out[-800:])

    def on_error(self, err):
        self.stats.append("\n[stderr]\n" + err)

    def on_finished(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def clear_all(self):
        self.table.setRowCount(0)
        self.stats.clear()
        self.progress.setValue(0)


class IpconfigTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.all_check = QComboBox()
        self.all_check.addItems([
            "Обычный вывод",
            "Полный вывод (/all)",
            "Сбросить кэш DNS (/flushdns)",
            "Показать кэш DNS (/displaydns)",
            "Обновить DHCP (/renew)",
            "Освободить DHCP (/release)",
            "Обновить регистрацию DNS (/registerdns)",
            "Показать класс DHCP (/showclassid)",
            "Установить класс DHCP (/setclassid)"
        ])

        self.adapter_edit = QLineEdit()
        self.adapter_edit.setPlaceholderText("Имя адаптера (для /renew, /release)")
        self.class_edit = QLineEdit()
        self.class_edit.setPlaceholderText("Код класса (для /setclassid)")

        self.run_btn = QPushButton("Выполнить ipconfig")
        self.run_btn.clicked.connect(self.run_ipconfig)
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_all)

        top.addWidget(QLabel("Режим:"))
        top.addWidget(self.all_check)
        top.addWidget(self.adapter_edit)
        top.addWidget(self.class_edit)
        top.addWidget(self.run_btn)
        top.addWidget(self.clear_btn)
        top.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.tabs = QTabWidget()

        layout.addLayout(top)
        layout.addWidget(self.progress)
        layout.addWidget(self.tabs)

    def run_ipconfig(self):
        self.tabs.clear()
        cmd = ["ipconfig"]
        idx = self.all_check.currentIndex()
        adapter = self.adapter_edit.text().strip()
        class_id = self.class_edit.text().strip()

        if idx == 1:
            cmd.append("/all")
        elif idx == 2:
            cmd.append("/flushdns")
        elif idx == 3:
            cmd.append("/displaydns")
        elif idx == 4:
            cmd.append("/renew")
            if adapter: cmd.append(adapter)
        elif idx == 5:
            cmd.append("/release")
            if adapter: cmd.append(adapter)
        elif idx == 6:
            cmd.append("/registerdns")
        elif idx == 7:
            cmd.append("/showclassid")
            if adapter: cmd.append(adapter)
        elif idx == 8:
            cmd.append("/setclassid")
            if adapter: cmd.append(adapter)
            if class_id: cmd.append(class_id)

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)

        self.worker = WorkerThread(cmd)
        self.worker.output_ready.connect(self.on_output)
        self.worker.error_ready.connect(lambda e: QMessageBox.warning(self, "Ошибка", e))
        self.worker.finished_success.connect(self.on_finished)
        self.worker.start()

    def on_output(self, out):
        lines = out.splitlines()
        adapter_blocks = []
        current_name = None
        current_lines = []

        header_re = re.compile(
            r"^(Адаптер\s+.+|Ethernet adapter\s+.+|"
            r"Tunnel adapter\s+.+|Беспроводная сеть.*|"
            r"Wireless LAN adapter\s+.+|"
            r"Неизвестный адаптер\s+.+|Unknown adapter\s+.+)\s*:\s*$",
            re.IGNORECASE
        )

        for line in lines:
            if header_re.match(line.strip()) and not line.startswith(" "):
                if current_name is not None:
                    adapter_blocks.append((current_name, current_lines))
                current_name = line.strip().rstrip(":")
                current_lines = []
            else:
                if current_name is not None:
                    current_lines.append(line)

        if current_name is not None:
            adapter_blocks.append((current_name, current_lines))

        if not adapter_blocks:
            tab = QTextEdit()
            tab.setReadOnly(True)
            tab.setPlainText(out)
            self.tabs.addTab(tab, "Весь вывод")
            return

        used_names = {}
        for name, block_lines in adapter_blocks:
            while block_lines and not block_lines[0].strip():
                block_lines.pop(0)
            while block_lines and not block_lines[-1].strip():
                block_lines.pop()

            text = name + ":\n" + "\n".join(block_lines)
            tab = QTextEdit()
            tab.setReadOnly(True)
            tab.setPlainText(text)

            short = name[:30]
            if short in used_names:
                used_names[short] += 1
                short = f"{short} ({used_names[short]})"
            else:
                used_names[short] = 1

            self.tabs.addTab(tab, short)

    def on_finished(self):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)

    def clear_all(self):
        self.tabs.clear()


class TracertTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        params_box = QGroupBox("Параметры tracert")
        form = QFormLayout()

        self.host_edit = QLineEdit("8.8.8.8")
        self.host_edit.setPlaceholderText("IP-адрес или доменное имя")

        self.max_hops = QSpinBox()
        self.max_hops.setRange(1, 255)
        self.max_hops.setValue(30)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 10000)
        self.timeout_spin.setValue(1000)
        self.timeout_spin.setSuffix(" мс")

        self.no_dns = QComboBox()
        self.no_dns.addItems(["Разрешать DNS-имена", "Не разрешать (-d)"])

        form.addRow("Узел:", self.host_edit)
        form.addRow("Макс. прыжков (-h):", self.max_hops)
        form.addRow("Таймаут (-w):", self.timeout_spin)
        form.addRow("DNS:", self.no_dns)
        params_box.setLayout(form)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Запустить tracert")
        self.run_btn.clicked.connect(self.run_tracert)
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Прыжок", "Узел (IP)", "RTT 1, мс", "RTT 2, мс", "RTT 3, мс"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.raw = QTextEdit()
        self.raw.setReadOnly(True)
        self.raw.setMaximumHeight(150)

        layout.addWidget(params_box)
        layout.addLayout(btn_layout)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Маршрут:"))
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Полный вывод:"))
        layout.addWidget(self.raw)

    def run_tracert(self):
        host = self.host_edit.text().strip()
        if not host:
            QMessageBox.warning(self, "Ошибка", "Введите узел!")
            return

        self.table.setRowCount(0)
        self.raw.clear()

        cmd = ["tracert",
               "-h", str(self.max_hops.value()),
               "-w", str(self.timeout_spin.value())]
        if self.no_dns.currentIndex() == 1:
            cmd.append("-d")
        cmd.append(host)

        self.raw.append(f"Команда: {' '.join(cmd)}\n")

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)

        self.worker = WorkerThread(cmd)
        self.worker.output_ready.connect(self.on_output)
        self.worker.error_ready.connect(lambda e: self.raw.append("[stderr]\n" + e))
        self.worker.finished_success.connect(self.on_finished)
        self.worker.start()

    def on_output(self, out):
        self.raw.append(out)

        row = 0
        pattern = re.compile(
            r"^\s*(\d+)\s+"  # номер прыжка
            r"(?:<?\s*\d+\s*ms\s+){1,3}"  # время отклика
            r"(.+?)\s*$"  # ip узла
        )
        rtt_pattern = re.compile(r"<?\s*(\d+)\s*ms")

        for line in out.splitlines():
            m = pattern.match(line)
            if not m:
                continue
            hop, node = m.group(1), m.group(2).strip()
            rtts = rtt_pattern.findall(line)
            while len(rtts) < 3:
                rtts.append("-")

            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(hop))
            self.table.setItem(row, 1, QTableWidgetItem(node))
            self.table.setItem(row, 2, QTableWidgetItem(rtts[0]))
            self.table.setItem(row, 3, QTableWidgetItem(rtts[1]))
            self.table.setItem(row, 4, QTableWidgetItem(rtts[2]))
            row += 1

    def on_finished(self):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)

    def clear_all(self):
        self.table.setRowCount(0)
        self.raw.clear()


class NetstatTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        params_box = QGroupBox("Параметры netstat")
        form = QFormLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Все соединения и порты (-a)",
            "Числовой формат (-n)",
            "Таблица маршрутов (-r)",
            "Статистика Ethernet (-e)",
            "Статистика по протоколам (-s)",
            "-a -n (все соединения, числовой)",
        ])
        form.addRow("Режим:", self.mode_combo)
        params_box.setLayout(form)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Выполнить netstat")
        self.run_btn.clicked.connect(self.run_netstat)
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Протокол", "Локальный адрес", "Внешний адрес", "Состояние", "PID"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.raw = QTextEdit()
        self.raw.setReadOnly(True)

        layout.addWidget(params_box)
        layout.addLayout(btn_layout)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Соединения:"))
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Полный вывод:"))
        layout.addWidget(self.raw)

    def run_netstat(self):
        idx = self.mode_combo.currentIndex()
        cmd = ["netstat"]
        if idx == 0:
            cmd.append("-a")
        elif idx == 1:
            cmd.append("-n")
        elif idx == 2:
            cmd.append("-r")
        elif idx == 3:
            cmd.append("-e")
        elif idx == 4:
            cmd.append("-s")
        elif idx == 5:
            cmd += ["-a", "-n"]

        self.table.setRowCount(0)
        self.raw.clear()
        self.raw.append(f"Команда: {' '.join(cmd)}\n")

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)

        self.worker = WorkerThread(cmd)
        self.worker.output_ready.connect(lambda out: self.on_output(out, idx))
        self.worker.error_ready.connect(lambda e: self.raw.append("[stderr]\n" + e))
        self.worker.finished_success.connect(self.on_finished)
        self.worker.start()

    def on_output(self, out, idx):
        self.raw.append(out)

        if idx not in (0, 1, 5):
            return

        row = 0
        for line in out.splitlines():
            parts = line.split()
            if not parts:
                continue
            if parts[0] not in ("TCP", "UDP"):
                continue

            if parts[0] == "TCP" and len(parts) >= 4:
                proto = parts[0]
                local = parts[1]
                remote = parts[2]
                state = parts[3]
                pid = parts[4] if len(parts) >= 5 else "-"
            elif parts[0] == "UDP" and len(parts) >= 3:
                proto = parts[0]
                local = parts[1]
                remote = parts[2]
                state = "-"
                pid = parts[3] if len(parts) >= 4 else "-"
            else:
                continue

            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(proto))
            self.table.setItem(row, 1, QTableWidgetItem(local))
            self.table.setItem(row, 2, QTableWidgetItem(remote))
            self.table.setItem(row, 3, QTableWidgetItem(state))
            self.table.setItem(row, 4, QTableWidgetItem(pid))
            row += 1

    def on_finished(self):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)

    def clear_all(self):
        self.table.setRowCount(0)
        self.raw.clear()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("lab1")
        self.resize(1000, 700)

        tabs = QTabWidget()
        tabs.addTab(PingTab(), "Ping")
        tabs.addTab(IpconfigTab(), "Ipconfig")
        tabs.addTab(TracertTab(), "Tracert")
        tabs.addTab(NetstatTab(), "Netstat")

        self.setCentralWidget(tabs)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()