# -*- coding: utf-8 -*-
"""
Лабораторная работа №1. Вариант 5.
Команды: ping, ipconfig, tracert, netstat.
Оценка: "хорошо" (GUI + удобный вывод).
Реализация на PySide6.
"""

import sys
import re
import subprocess

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QTextEdit, QComboBox,
    QMessageBox, QHeaderView, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt


# ============================================================
# Вспомогательные функции запуска команд Windows
# ============================================================
def run_command(args):
    """Запускает команду и возвращает (stdout, stderr)."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="cp866",   # кодировка консоли Windows
            errors="replace",
            shell=False
        )
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)


# ============================================================
# Вкладка PING
# ============================================================
class PingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        # --- Панель параметров ---
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

        form.addRow("Узел:", self.host_edit)
        form.addRow("Число запросов (-n):", self.count_spin)
        form.addRow("Размер пакета (-l):", self.size_spin)
        form.addRow("Таймаут (-w):", self.timeout_spin)
        params_box.setLayout(form)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Запустить ping")
        self.run_btn.clicked.connect(self.run_ping)
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()

        # --- Таблица результатов ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["№", "Ответ от", "Байт", "Время, мс", "TTL"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # --- Итоговая статистика ---
        self.stats = QTextEdit()
        self.stats.setReadOnly(True)
        self.stats.setMaximumHeight(120)

        layout.addWidget(params_box)
        layout.addLayout(btn_layout)
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

        cmd = [
            "ping", "-n", str(self.count_spin.value()),
            "-l", str(self.size_spin.value()),
            "-w", str(self.timeout_spin.value()),
            host
        ]
        self.stats.append(f"Команда: {' '.join(cmd)}\n")

        out, err = run_command(cmd)

        # Парсим строки ответов
        # Рус.: "Ответ от 8.8.8.8: число байт=32 время=15мс TTL=117"
        # Англ.: "Reply from 8.8.8.8: bytes=32 time=15ms TTL=117"
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

        # Если строки ответов не распознались (таймауты)
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

        # Статистика — выводим из хвоста вывода ping
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

        if err.strip():
            self.stats.append("\n[stderr]\n" + err)

    def clear_all(self):
        self.table.setRowCount(0)
        self.stats.clear()


# ============================================================
# Вкладка IPCONFIG (результаты по каждому интерфейсу — на отдельной вкладке)
# ============================================================
class IpconfigTab(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.all_check = QComboBox()
        self.all_check.addItems(["Обычный вывод", "Полный вывод (/all)"])
        self.run_btn = QPushButton("Выполнить ipconfig")
        self.run_btn.clicked.connect(self.run_ipconfig)
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_all)

        top.addWidget(QLabel("Режим:"))
        top.addWidget(self.all_check)
        top.addWidget(self.run_btn)
        top.addWidget(self.clear_btn)
        top.addStretch()

        self.tabs = QTabWidget()

        layout.addLayout(top)
        layout.addWidget(self.tabs)

    def run_ipconfig(self):
        self.tabs.clear()
        cmd = ["ipconfig"]
        if self.all_check.currentIndex() == 1:
            cmd.append("/all")

        out, err = run_command(cmd)
        if err.strip():
            QMessageBox.warning(self, "Ошибка", err)

        # Разбиваем вывод на блоки по адаптерам
        blocks = re.split(r"\n\s*\n", out.strip())
        adapter_blocks = []
        for b in blocks:
            b = b.strip()
            if not b:
                continue
            first_line = b.splitlines()[0]
            if first_line and not first_line.startswith(" ") and first_line.endswith(":"):
                adapter_blocks.append(b)

        if not adapter_blocks:
            tab = QTextEdit()
            tab.setReadOnly(True)
            tab.setPlainText(out)
            self.tabs.addTab(tab, "Весь вывод")
            return

        for block in adapter_blocks:
            name = block.splitlines()[0].rstrip(":").strip()
            tab = QTextEdit()
            tab.setReadOnly(True)
            tab.setPlainText(block)
            self.tabs.addTab(tab, name[:30])

    def clear_all(self):
        self.tabs.clear()


# ============================================================
# Вкладка TRACERT
# ============================================================
class TracertTab(QWidget):
    def __init__(self):
        super().__init__()
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
        out, err = run_command(cmd)
        self.raw.append(out)
        if err.strip():
            self.raw.append("[stderr]\n" + err)

        row = 0
        pattern = re.compile(
            r"^\s*(\d+)\s+"
            r"(?:<?\s*\d+\s*ms\s+){1,3}"
            r"(.+?)\s*$"
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

    def clear_all(self):
        self.table.setRowCount(0)
        self.raw.clear()


# ============================================================
# Вкладка NETSTAT
# ============================================================
class NetstatTab(QWidget):
    def __init__(self):
        super().__init__()
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

        out, err = run_command(cmd)
        self.raw.append(out)
        if err.strip():
            self.raw.append("[stderr]\n" + err)

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

    def clear_all(self):
        self.table.setRowCount(0)
        self.raw.clear()


# ============================================================
# Главное окно
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР №1 — Вариант 5: ping, ipconfig, tracert, netstat")
        self.resize(1000, 700)

        tabs = QTabWidget()
        tabs.addTab(PingTab(), "Ping")
        tabs.addTab(IpconfigTab(), "Ipconfig")
        tabs.addTab(TracertTab(), "Tracert")
        tabs.addTab(NetstatTab(), "Netstat")

        self.setCentralWidget(tabs)


# ============================================================
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()