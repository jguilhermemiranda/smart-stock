from __future__ import annotations

import tkinter as tk
import json
import ipaddress
import re
from tkinter import filedialog, messagebox, ttk

from api.client import DeviceClient, DeviceError
from config.settings import Settings
from database.db import Database
from data.excel_service import ExcelError, ExcelService
from sync.service import SyncService


class SmartStockApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Smart Stock | Console de Operacao")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.configure(background="#f5f6fb")
        self.setup_style()
        self.settings = Settings()
        self.database = Database()
        self.client = DeviceClient(self.settings.values["esp32_host"], self.settings.values["esp32_port"])
        self.sync_service = SyncService(self.database, self.client)
        self.excel_service = ExcelService()
        self.status_text = tk.StringVar(value="Disconnected")
        self.connection_detail = tk.StringVar(value="Nenhuma consulta realizada")
        self.build_ui()
        self.refresh_local()
        self.refresh_sync_state()

    def setup_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 9))
        style.configure("TFrame", background="#f5f6fb")
        style.configure("TLabel", background="#f5f6fb", foreground="#2c3871")
        style.configure("TLabelframe", background="#f5f6fb", foreground="#2c3871", bordercolor="#dfe2f3")
        style.configure("TLabelframe.Label", background="#f5f6fb", foreground="#4c5692")
        style.configure("App.TFrame", background="#f5f6fb")
        style.configure("Header.TFrame", background="#2c3871")
        style.configure("Header.TLabel", background="#2c3871", foreground="#ffffff")
        style.configure("Title.TLabel", background="#f5f6fb", foreground="#2c3871", font=("Segoe UI", 19, "bold"))
        style.configure("Subtitle.TLabel", background="#f5f6fb", foreground="#6c74b3", font=("Segoe UI", 9))
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#4c5692", font=("Segoe UI", 9, "bold"))
        style.configure("CardValue.TLabel", background="#ffffff", foreground="#2c3871", font=("Segoe UI", 18, "bold"))
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground="#2c3871", rowheight=32, font=("Segoe UI", 9), bordercolor="#dfe2f3")
        style.configure("Treeview.Heading", background="#6c74b3", foreground="#ffffff", font=("Segoe UI", 9, "bold"), padding=(8, 7))
        style.map("Treeview", background=[("selected", "#6c74b3")], foreground=[("selected", "#ffffff")])
        style.configure("Primary.TButton", background="#4c5692", foreground="#ffffff", padding=(14, 8), font=("Segoe UI", 9, "bold"))
        style.map("Primary.TButton", background=[("active", "#2c3871"), ("pressed", "#2c3871")])
        style.configure("TButton", background="#ffffff", foreground="#2c3871", padding=(12, 8), bordercolor="#adb1f5")
        style.map("TButton", background=[("active", "#adb1f5"), ("pressed", "#8d93d4")], foreground=[("active", "#2c3871"), ("pressed", "#ffffff")])
        style.configure("TEntry", fieldbackground="#ffffff", foreground="#2c3871", bordercolor="#adb1f5", padding=6)
        style.configure("TCombobox", fieldbackground="#ffffff", foreground="#2c3871", bordercolor="#adb1f5", padding=5)
        style.configure("TNotebook", background="#f5f6fb", borderwidth=0)
        style.configure("TNotebook.Tab", background="#e3e5f5", foreground="#4c5692", padding=(18, 9))
        style.map("TNotebook.Tab", background=[("selected", "#2c3871")], foreground=[("selected", "#ffffff")])

    def build_ui(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(24, 18)); header.pack(fill="x")
        ttk.Label(header, text="SMART STOCK", style="Header.TLabel", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(header, text="Console de administracao", style="Header.TLabel").pack(side="left", padx=18)
        ttk.Label(header, textvariable=self.status_text, style="Header.TLabel", font=("Segoe UI", 10, "bold")).pack(side="right")
        toolbar = ttk.Frame(self, style="App.TFrame", padding=(24, 16, 24, 6)); toolbar.pack(fill="x")
        primary_actions = ttk.Frame(toolbar, style="App.TFrame"); primary_actions.pack(side="left")
        ttk.Button(primary_actions, text="Atualizar status", command=self.refresh_status, style="Primary.TButton").pack(side="left")
        ttk.Button(primary_actions, text="Sincronizar dados", command=self.synchronize).pack(side="left", padx=8)
        ttk.Button(primary_actions, text="Puxar dados do ESP", command=self.pull_from_device).pack(side="left")
        data_actions = ttk.Frame(toolbar, style="App.TFrame"); data_actions.pack(side="right")
        ttk.Button(data_actions, text="Configuração", command=lambda: notebook.select(self.configuration)).pack(side="left", padx=(0, 8))
        ttk.Button(data_actions, text="Importar Excel", command=self.import_excel).pack(side="left")
        ttk.Button(data_actions, text="Exportar Excel", command=self.export_excel).pack(side="left", padx=8)
        ttk.Button(data_actions, text="Executar HOME", command=self.home).pack(side="left")
        ttk.Label(self, textvariable=self.connection_detail, style="Subtitle.TLabel", anchor="e", padding=(24, 0, 24, 8)).pack(fill="x")
        notebook = ttk.Notebook(self); notebook.pack(fill="both", expand=True, padx=24, pady=(4, 20))
        self.dashboard = ttk.Frame(notebook, padding=12); notebook.add(self.dashboard, text="Dashboard")
        cards = ttk.Frame(notebook, padding=12); notebook.add(cards, text="Cards")
        drawers = ttk.Frame(notebook, padding=12); notebook.add(drawers, text="Drawers")
        self.configuration = ttk.Frame(notebook, padding=12); notebook.add(self.configuration, text="Configuração")
        self.build_dashboard(); self.build_cards(cards); self.build_drawers(drawers); self.build_configuration()

    def build_dashboard(self) -> None:
        self.dashboard.configure(style="App.TFrame")
        ttk.Label(self.dashboard, text="Visao geral", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.dashboard, text="Estado da rede, controlador e ultima operacao", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 14))
        cards = ttk.Frame(self.dashboard, style="App.TFrame"); cards.pack(fill="x")
        self.dashboard_values = {}
        for name, label in (("wifi", "Wi-Fi"), ("bridge", "ESP-01 / Bridge"), ("arduino", "Arduino"), ("operation", "Operacao")):
            card = ttk.Frame(cards, style="Card.TFrame", padding=14); card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            ttk.Label(card, text=label.upper(), style="CardTitle.TLabel").pack(anchor="w")
            value = tk.StringVar(value="--"); self.dashboard_values[name] = value
            ttk.Label(card, textvariable=value, style="CardValue.TLabel").pack(anchor="w", pady=(8, 0))
        log_frame = ttk.LabelFrame(self.dashboard, text="Detalhes", padding=10); log_frame.pack(fill="both", expand=True, pady=(18, 0))
        self.dashboard_text = tk.Text(log_frame, height=16, state="disabled", relief="flat", background="#ffffff", font=("Consolas", 9))
        self.dashboard_text.pack(fill="both", expand=True)

    def build_cards(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Cartoes RFID", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Cadastre identificacao e proprietario antes de sincronizar.", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 14))
        form = ttk.LabelFrame(parent, text="Novo cartao", padding=12); form.pack(fill="x")
        self.uid = tk.StringVar(); self.owner = tk.StringVar(); self.card_attributes = tk.StringVar()
        ttk.Label(form, text="UID hexadecimal").grid(row=0, column=0, sticky="w", padx=(0, 8)); ttk.Entry(form, textvariable=self.uid, width=28).grid(row=0, column=1, sticky="ew")
        ttk.Label(form, text="Proprietario").grid(row=0, column=2, sticky="w", padx=(18, 8)); ttk.Entry(form, textvariable=self.owner, width=28).grid(row=0, column=3, sticky="ew")
        ttk.Label(form, text="Atributos extras").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(form, textvariable=self.card_attributes, width=75).grid(row=1, column=1, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Label(form, text="ex.: matricula=123; cpf=000.000.000-00", style="Subtitle.TLabel").grid(row=2, column=1, columnspan=3, sticky="w")
        ttk.Button(form, text="Adicionar cartao", command=self.add_card).grid(row=0, column=4, padx=(18, 0)); form.columnconfigure(3, weight=1)
        table = ttk.Frame(parent); table.pack(fill="both", expand=True, pady=(16, 0))
        self.cards_view = ttk.Treeview(table, columns=("uid", "owner", "attributes", "status"), show="headings")
        for column in ("uid", "owner", "attributes", "status"): self.cards_view.heading(column, text=column.title())
        self.cards_view.column("uid", width=180); self.cards_view.column("owner", width=220); self.cards_view.column("attributes", width=360); self.cards_view.column("status", width=100)
        self.cards_view.pack(side="left", fill="both", expand=True)
        card_actions = ttk.Frame(parent); card_actions.pack(fill="x", pady=(8, 0))
        ttk.Button(card_actions, text="Autorizar / desautorizar selecionado", command=self.toggle_card_status).pack(side="left")
        ttk.Scrollbar(table, orient="vertical", command=self.cards_view.yview).pack(side="right", fill="y")

    def build_drawers(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Gavetas", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Coordenadas reais sao obrigatorias para movimentacao.", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 14))
        form = ttk.LabelFrame(parent, text="Nova gaveta", padding=12); form.pack(fill="x")
        self.drawer_label = tk.StringVar(); self.drawer_x = tk.StringVar(); self.drawer_y = tk.StringVar(); self.drawer_z = tk.StringVar()
        for column, (label, variable) in enumerate((("Nome", self.drawer_label), ("X mm", self.drawer_x), ("Y mm", self.drawer_y), ("Z mm", self.drawer_z))):
            ttk.Label(form, text=label).grid(row=0, column=column * 2, sticky="w", padx=(0, 6)); ttk.Entry(form, textvariable=variable, width=15).grid(row=0, column=column * 2 + 1, sticky="ew", padx=(0, 12))
        ttk.Button(form, text="Adicionar gaveta", command=self.add_drawer).grid(row=0, column=8); form.columnconfigure(1, weight=1)
        details = ttk.Frame(parent); details.pack(fill="x", pady=(12, 0))
        inventory = ttk.LabelFrame(details, text="Conteudo da gaveta", padding=10); inventory.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.item_drawer = tk.StringVar(); self.item_name = tk.StringVar(); self.item_quantity = tk.StringVar(value="0")
        ttk.Label(inventory, text="Gaveta").grid(row=0, column=0, sticky="w"); self.item_drawer_box = ttk.Combobox(inventory, textvariable=self.item_drawer, state="readonly", width=10); self.item_drawer_box.grid(row=0, column=1, padx=6)
        ttk.Label(inventory, text="Item").grid(row=0, column=2, sticky="w"); ttk.Entry(inventory, textvariable=self.item_name, width=20).grid(row=0, column=3, padx=6)
        ttk.Label(inventory, text="Quantidade").grid(row=0, column=4, sticky="w"); ttk.Entry(inventory, textvariable=self.item_quantity, width=8).grid(row=0, column=5, padx=6)
        ttk.Button(inventory, text="Salvar item", command=self.add_inventory).grid(row=0, column=6)
        permissions = ttk.LabelFrame(details, text="Quem pode retirar", padding=10); permissions.pack(side="left", fill="x", expand=True)
        self.permission_drawer = tk.StringVar(); self.permission_card = tk.StringVar()
        ttk.Label(permissions, text="Gaveta").grid(row=0, column=0, sticky="w"); self.permission_drawer_box = ttk.Combobox(permissions, textvariable=self.permission_drawer, state="readonly", width=10); self.permission_drawer_box.grid(row=0, column=1, padx=6)
        ttk.Label(permissions, text="Cartao").grid(row=0, column=2, sticky="w"); self.permission_card_box = ttk.Combobox(permissions, textvariable=self.permission_card, state="readonly", width=20); self.permission_card_box.grid(row=0, column=3, padx=6)
        ttk.Button(permissions, text="Autorizar", command=self.add_permission).grid(row=0, column=4)
        table = ttk.Frame(parent); table.pack(fill="both", expand=True, pady=(16, 0))
        self.drawers_view = ttk.Treeview(table, columns=("id", "label", "items", "quantity", "owners", "x", "y", "z", "calibrated"), show="headings")
        headings = {"id": "ID", "label": "Gaveta", "items": "Itens", "quantity": "Qtd.", "owners": "Podem retirar", "x": "X mm", "y": "Y mm", "z": "Z mm", "calibrated": "Calibrada"}
        for column, heading in headings.items(): self.drawers_view.heading(column, text=heading)
        self.drawers_view.column("items", width=180); self.drawers_view.column("owners", width=180); self.drawers_view.column("quantity", width=55)
        self.drawers_view.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(table, orient="vertical", command=self.drawers_view.yview).pack(side="right", fill="y")
        ttk.Button(parent, text="Editar gaveta selecionada", command=self.edit_selected_drawer).pack(anchor="w", pady=(8, 0))

    def build_configuration(self) -> None:
        self.configuration.configure(style="App.TFrame")
        ttk.Label(self.configuration, text="Configuração do sistema", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.configuration, text="Edite os parâmetros do motor, da comunicação e da rede nesta aba.", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 14))

        machine = ttk.LabelFrame(self.configuration, text="Motor e máquina", padding=12)
        machine.pack(fill="x", pady=(0, 12))
        local_machine = self.database.machine_config()
        local_steps = local_machine.get("steps_per_mm", {})
        defaults = {
            "drawer_count": str(local_machine.get("drawer_count", 18)),
            "steps_per_mm_x": str(local_steps.get("x", 1.0)),
            "steps_per_mm_y": str(local_steps.get("y", 1.0)),
            "steps_per_mm_z": str(local_steps.get("z", 1.0)),
        }
        self.machine_config_vars = {name: tk.StringVar(value=default) for name, default in defaults.items()}
        fields = (
            ("Número de gavetas", "drawer_count"),
            ("Passos por mm - X", "steps_per_mm_x"),
            ("Passos por mm - Y", "steps_per_mm_y"),
            ("Passos por mm - Z", "steps_per_mm_z"),
        )
        for index, (label, name) in enumerate(fields):
            row, column = divmod(index, 4)
            ttk.Label(machine, text=label).grid(row=row * 2, column=column, sticky="w", padx=(0, 12), pady=(0, 4))
            ttk.Entry(machine, textvariable=self.machine_config_vars[name], width=20).grid(row=row * 2 + 1, column=column, sticky="ew", padx=(0, 12), pady=(0, 10))
            machine.columnconfigure(column, weight=1)
        machine_actions = ttk.Frame(machine, style="App.TFrame")
        machine_actions.grid(row=4, column=0, columnspan=4, sticky="ew")
        ttk.Button(machine_actions, text="Ler do ESP32", command=self.load_machine_configuration).pack(side="left")
        ttk.Button(machine_actions, text="Salvar parâmetros", style="Primary.TButton", command=self.save_machine_configuration).pack(side="right")

        connection = ttk.LabelFrame(self.configuration, text="Conexão do computador", padding=12)
        connection.pack(fill="x", pady=(0, 12))
        self.config_host = tk.StringVar(value=str(self.settings.values.get("esp32_host", "smartstock.local")))
        self.config_port = tk.StringVar(value=str(self.settings.values.get("esp32_port", 80)))
        ttk.Label(connection, text="ESP32 / Host").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(connection, textvariable=self.config_host).grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(connection, text="Porta").grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Entry(connection, textvariable=self.config_port, width=10).grid(row=0, column=3)
        connection.columnconfigure(1, weight=1)

        network = ttk.LabelFrame(self.configuration, text="Rede do ESP32 e ponte ESP-01", padding=12)
        network.pack(fill="x", pady=(0, 12))
        self.config_ssid = tk.StringVar()
        self.config_password = tk.StringVar()
        self.config_bridge_host = tk.StringVar(value=str(self.settings.values.get("bridge_host", "espbridge.local")))
        self.config_bridge_port = tk.StringVar(value=str(self.settings.values.get("bridge_port", 8899)))
        ttk.Label(network, text="SSID").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(network, textvariable=self.config_ssid).grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(network, text="Senha").grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Entry(network, textvariable=self.config_password, show="*").grid(row=0, column=3, sticky="ew")
        ttk.Label(network, text="Host do ESP-01").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0))
        ttk.Entry(network, textvariable=self.config_bridge_host).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(10, 0))
        ttk.Label(network, text="Porta da ponte").grid(row=1, column=2, sticky="w", padx=(0, 8), pady=(10, 0))
        ttk.Entry(network, textvariable=self.config_bridge_port, width=10).grid(row=1, column=3, sticky="w", pady=(10, 0))
        network.columnconfigure(1, weight=1); network.columnconfigure(3, weight=1)
        actions = ttk.Frame(self.configuration, style="App.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Salvar conexão local", command=self.save_tab_connection).pack(side="left")
        ttk.Button(actions, text="Enviar rede ao ESP32", command=self.send_tab_network_configuration).pack(side="right")

    def load_machine_configuration(self) -> None:
        self.status_text.set("CARREGANDO CONFIGURAÇÃO")
        try:
            machine = self.client.config().get("machine_config", {})
            steps = machine.get("steps_per_mm", {})
            values = {
                "drawer_count": machine.get("drawer_count", 18),
                "steps_per_mm_x": steps.get("x", 1.0),
                "steps_per_mm_y": steps.get("y", 1.0),
                "steps_per_mm_z": steps.get("z", 1.0),
            }
            for name, value in values.items(): self.machine_config_vars[name].set(str(value))
            self.status_text.set("CONFIGURAÇÃO CARREGADA")
            messagebox.showinfo("Configuração", "Parâmetros carregados do ESP32.")
        except DeviceError as exc:
            self.status_text.set("ERRO AO CARREGAR")
            messagebox.showerror("Configuração", str(exc))

    def save_machine_configuration(self) -> None:
        if not self.require_configuration_permission() or not self.ensure_machine_stopped():
            return
        if not messagebox.askyesno("Confirmar configuração", "Aplicar estes parâmetros com a máquina parada?"):
            return
        self.status_text.set("SALVANDO CONFIGURAÇÃO")
        try:
            values = self.machine_config_vars
            payload = {
                "drawer_count": int(values["drawer_count"].get()),
                "steps_per_mm_x": float(values["steps_per_mm_x"].get()),
                "steps_per_mm_y": float(values["steps_per_mm_y"].get()),
                "steps_per_mm_z": float(values["steps_per_mm_z"].get()),
            }
            if payload["drawer_count"] < 1 or payload["drawer_count"] > 18 or any(payload[name] <= 0 for name in ("steps_per_mm_x", "steps_per_mm_y", "steps_per_mm_z")):
                raise ValueError
            existing_count = len(self.database.rows("SELECT id FROM drawers"))
            if payload["drawer_count"] < existing_count:
                if not messagebox.askyesno("Redução de gavetas", f"Já existem {existing_count} gavetas cadastradas. Reduzir a capacidade para {payload['drawer_count']} sem apagar dados?"):
                    return
            previous_drawer_count = int(self.database.machine_config().get("drawer_count", 18))
            self.database.set_machine_config_pending(payload, previous_drawer_count)
            try:
                self.sync_service.synchronize()
            except DeviceError:
                self.status_text.set("NÃO SINCRONIZADO")
                messagebox.showwarning("Configuração", "Salvo no computador, mas não sincronizado com o ESP32.")
                return
            self.status_text.set("SINCRONIZADO")
            messagebox.showinfo("Configuração", "Parâmetros salvos no computador e sincronizados com o ESP32.")
        except ValueError:
            messagebox.showerror("Configuração", "Revise os valores numéricos e os limites informados.")
        except DeviceError as exc:
            self.status_text.set("ERRO DE SINCRONIZAÇÃO")
            messagebox.showerror("Configuração", f"Não foi possível sincronizar: {exc}")

    def require_configuration_permission(self) -> bool:
        return self.require_role({"administrator", "maintenance"}, "Somente administrador ou manutenção pode alterar configurações.")

    def require_role(self, allowed: set[str], message: str) -> bool:
        """Local role check only; smartstock.json is not cryptographic authentication."""
        role = str(self.settings.values.get("role", "operator")).lower()
        if role not in allowed:
            messagebox.showerror("Permissão", message)
            return False
        return True

    @staticmethod
    def valid_host(value: str) -> bool:
        if not value or len(value) > 253 or ".." in value:
            return False
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", value))

    def ensure_machine_stopped(self) -> bool:
        try:
            status = self.client.status()
        except DeviceError as exc:
            messagebox.showerror("Máquina", f"Não foi possível verificar o estado da máquina: {exc}")
            return False
        arduino_status = str(status.get("arduino_status", ""))
        operation_status = str(status.get("operation_status", ""))
        if status.get("arduino_state") == "BUSY" or "STATE=BUSY" in arduino_status or operation_status in {"accepted", "running", "busy"}:
            messagebox.showwarning("Máquina em movimento", "Pare a máquina antes de alterar configurações mecânicas.")
            return False
        return True

    def save_tab_connection(self) -> None:
        if not self.require_role({"maintenance"}, "Somente manutenção pode alterar a comunicação."):
            return
        try:
            host = self.config_host.get().strip(); port = int(self.config_port.get().strip())
            bridge_host = self.config_bridge_host.get().strip(); bridge_port = int(self.config_bridge_port.get().strip())
            if not self.valid_host(host) or not 1 <= port <= 65535 or not self.valid_host(bridge_host) or not 1 <= bridge_port <= 65535: raise ValueError
        except ValueError:
            messagebox.showerror("Conexão", "Informe endereços e portas válidos para o ESP32 e o ESP-01.")
            return
        self.settings.values.update({"esp32_host": host, "esp32_port": port, "bridge_host": bridge_host, "bridge_port": bridge_port})
        self.settings.save(); self.client = DeviceClient(host, port); self.sync_service = SyncService(self.database, self.client)
        self.connection_detail.set(f"ESP32: {host}:{port}")
        messagebox.showinfo("Conexão", "Conexão local salva.")

    def send_tab_network_configuration(self) -> None:
        if not self.require_role({"maintenance"}, "Somente manutenção pode configurar a rede."):
            return
        self.send_network_configuration(self.config_host, self.config_port, self.config_ssid, self.config_password, self.config_bridge_host, self.config_bridge_port)

    def write_dashboard(self, value: object) -> None:
        self.dashboard_text.configure(state="normal")
        self.dashboard_text.delete("1.0", "end")
        self.dashboard_text.insert("end", json.dumps(value, indent=2, ensure_ascii=False, default=str) if isinstance(value, dict) else str(value))
        self.dashboard_text.configure(state="disabled")

    def update_dashboard_cards(self, status: dict) -> None:
        self.dashboard_values["wifi"].set("Conectado" if status.get("wifi_connected") else "Offline")
        self.dashboard_values["bridge"].set("Conectado" if status.get("bridge_connected") else "Offline")
        self.dashboard_values["arduino"].set(status.get("arduino_state", "Desconhecido"))
        self.dashboard_values["operation"].set(status.get("operation_status") or "Nenhuma")

    def refresh_status(self) -> None:
        try:
            status = self.client.status()
            self.status_text.set("ONLINE")
            self.connection_detail.set(f"ESP32: {self.settings.values['esp32_host']}:{self.settings.values['esp32_port']}")
            self.update_dashboard_cards(status)
            self.write_dashboard(status)
        except DeviceError as exc:
            self.status_text.set("OFFLINE")
            self.connection_detail.set("Falha ao consultar o ESP32")
            for value in self.dashboard_values.values(): value.set("Offline")
            self.write_dashboard(str(exc))

    def synchronize(self) -> None:
        try:
            result = self.sync_service.synchronize()
            self.status_text.set("SINCRONIZADO")
            self.write_dashboard(result)
            messagebox.showinfo("Sincronizacao", "Dados enviados ao ESP32 com sucesso.")
        except DeviceError as exc:
            self.status_text.set("ERRO DE SINCRONIZAÇÃO")
            messagebox.showerror("Sincronizacao", str(exc))

    def refresh_sync_state(self) -> None:
        state = self.database.sync_state()
        if state["state"] == "failed":
            self.status_text.set("NÃO SINCRONIZADO")
        elif state["state"] == "pending":
            self.status_text.set("SINCRONIZAÇÃO PENDENTE")

    def synchronize_local_change(self) -> None:
        try:
            self.sync_service.synchronize()
            self.status_text.set("SINCRONIZADO")
        except DeviceError as exc:
            self.status_text.set("NÃO SINCRONIZADO")
            messagebox.showwarning("Sincronização", f"Alteração salva no computador, mas não no ESP32: {exc}")

    def pull_from_device(self) -> None:
        if not messagebox.askyesno("Puxar dados", "Substituir os dados locais pelo banco armazenado no ESP?"):
            return
        try:
            result = self.sync_service.pull_from_device()
            self.refresh_local()
            self.status_text.set("DADOS IMPORTADOS")
            self.write_dashboard(result)
            messagebox.showinfo("Puxar dados", f"Importados {result['cards']} cartoes e {result['drawers']} gavetas.")
        except (DeviceError, KeyError, ValueError) as exc:
            messagebox.showerror("Puxar dados", str(exc))

    def export_excel(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Exportar inventário para Excel",
            defaultextension=".xlsx",
            filetypes=(("Planilha Excel", "*.xlsx"), ("Todos os arquivos", "*.*")),
        )
        if not path:
            return
        try:
            self.excel_service.export(self.database, path)
            self.status_text.set("EXCEL EXPORTADO")
            messagebox.showinfo("Excel", "Dados exportados com sucesso.")
        except ExcelError as exc:
            messagebox.showerror("Excel", str(exc))

    def import_excel(self) -> None:
        path = filedialog.askopenfilename(
            title="Importar inventário do Excel",
            filetypes=(("Planilha Excel", "*.xlsx"), ("Todos os arquivos", "*.*")),
        )
        if not path or not messagebox.askyesno("Importar Excel", "A importação substituirá os dados locais. Continuar?"):
            return
        try:
            result = self.excel_service.import_file(self.database, path)
            self.refresh_local()
            self.status_text.set("EXCEL IMPORTADO")
            messagebox.showinfo("Excel", f"Importados {result['cards']} cartões e {result['drawers']} gavetas.")
        except ExcelError as exc:
            messagebox.showerror("Excel", str(exc))

    def open_configuration(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Configuração do Smart Stock")
        dialog.geometry("560x520")
        dialog.minsize(520, 480)
        dialog.transient(self)
        dialog.grab_set()

        content = ttk.Frame(dialog, padding=24, style="App.TFrame")
        content.pack(fill="both", expand=True)
        ttk.Label(content, text="Configuração", style="Title.TLabel").pack(anchor="w")
        ttk.Label(content, text="Edite o endereço do controlador e configure a rede sem usar o Monitor Serial.", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 18))

        connection = ttk.LabelFrame(content, text="Conexão com o ESP32", padding=12)
        connection.pack(fill="x", pady=(0, 12))
        host = tk.StringVar(value=str(self.settings.values.get("esp32_host", "smartstock.local")))
        port = tk.StringVar(value=str(self.settings.values.get("esp32_port", 80)))
        ttk.Label(connection, text="Endereço / IP").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(connection, textvariable=host).grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(connection, text="Porta").grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Entry(connection, textvariable=port, width=8).grid(row=0, column=3, sticky="ew")
        ttk.Button(connection, text="Usar AP inicial", command=lambda: self.use_initial_access(host, port)).grid(row=1, column=1, sticky="w", pady=(10, 0))
        connection.columnconfigure(1, weight=1)

        network = ttk.LabelFrame(content, text="Wi-Fi do ESP32", padding=12)
        network.pack(fill="x", pady=(0, 12))
        ssid = tk.StringVar()
        password = tk.StringVar()
        networks: list[str] = []
        ttk.Label(network, text="Rede Wi-Fi").grid(row=0, column=0, sticky="w", padx=(0, 8))
        network_box = ttk.Combobox(network, textvariable=ssid, state="normal")
        network_box.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(network, text="Buscar redes", command=lambda: self.scan_wifi(host, port, network_box, networks)).grid(row=0, column=2)
        ttk.Label(network, text="Você pode selecionar uma rede encontrada ou digitar o nome manualmente.", style="Subtitle.TLabel").grid(row=1, column=1, columnspan=2, sticky="w", pady=(6, 10))
        ttk.Label(network, text="Senha").grid(row=2, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(network, textvariable=password, show="*").grid(row=2, column=1, columnspan=2, sticky="ew")
        network.columnconfigure(1, weight=1)

        bridge = ttk.LabelFrame(content, text="ESP-01 / Bridge", padding=12)
        bridge.pack(fill="x", pady=(0, 12))
        bridge_host = tk.StringVar(value="espbridge.local")
        bridge_port = tk.StringVar(value="8899")
        ttk.Label(bridge, text="Host").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(bridge, textvariable=bridge_host).grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(bridge, text="Porta").grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Entry(bridge, textvariable=bridge_port, width=8).grid(row=0, column=3)
        bridge.columnconfigure(1, weight=1)

        actions = ttk.Frame(content, style="App.TFrame")
        actions.pack(fill="x", side="bottom")
        ttk.Button(actions, text="Salvar conexão do computador", command=lambda: self.save_connection_settings(host, port, dialog)).pack(side="left")
        ttk.Button(actions, text="Enviar configuração ao ESP32", style="Primary.TButton", command=lambda: self.send_network_configuration(host, port, ssid, password, bridge_host, bridge_port)).pack(side="right")

    def scan_wifi(self, host: tk.StringVar, port: tk.StringVar, network_box: ttk.Combobox, networks: list[str]) -> None:
        try:
            target = DeviceClient(host.get().strip(), int(port.get().strip()))
            values = [str(network.get("ssid", "")).strip() for network in target.wifi_scan().get("networks", [])]
            values = list(dict.fromkeys(value for value in values if value))
            networks[:] = values
            network_box["values"] = values
            if not values:
                messagebox.showinfo("Wi-Fi", "Nenhuma rede encontrada.")
        except (DeviceError, ValueError) as exc:
            messagebox.showerror("Wi-Fi", f"Não foi possível buscar redes: {exc}")

    @staticmethod
    def use_initial_access(host: tk.StringVar, port: tk.StringVar) -> None:
        host.set("192.168.4.1")
        port.set("80")

    def save_connection_settings(self, host: tk.StringVar, port: tk.StringVar, dialog: tk.Toplevel) -> None:
        if not self.require_role({"maintenance"}, "Somente manutenção pode alterar a comunicação."):
            return
        try:
            selected_host = host.get().strip()
            selected_port = int(port.get().strip())
            if not self.valid_host(selected_host) or not 1 <= selected_port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Configuração", "Informe um endereço e uma porta válidos.")
            return
        self.settings.values["esp32_host"] = selected_host
        self.settings.values["esp32_port"] = selected_port
        self.settings.save()
        self.client = DeviceClient(selected_host, selected_port)
        self.sync_service = SyncService(self.database, self.client)
        self.connection_detail.set(f"ESP32: {selected_host}:{selected_port}")
        messagebox.showinfo("Configuração", "Conexão do computador salva.")
        dialog.destroy()

    def send_network_configuration(
        self,
        host: tk.StringVar,
        port: tk.StringVar,
        ssid: tk.StringVar,
        password: tk.StringVar,
        bridge_host: tk.StringVar,
        bridge_port: tk.StringVar,
    ) -> None:
        if not self.require_role({"maintenance"}, "Somente manutenção pode configurar a rede."):
            return
        if not ssid.get().strip():
            messagebox.showerror("Wi-Fi", "Selecione uma rede ou digite o nome dela.")
            return
        try:
            target_host = host.get().strip(); target_port = int(port.get().strip())
            target_bridge = bridge_host.get().strip(); target_bridge_port = int(bridge_port.get().strip())
            if not self.valid_host(target_host) or not 1 <= target_port <= 65535 or not self.valid_host(target_bridge) or not 1 <= target_bridge_port <= 65535:
                raise ValueError
            self.status_text.set("ENVIANDO REDE")
            target = DeviceClient(target_host, target_port)
            target.configure_network(ssid.get().strip(), password.get(), target_bridge, target_bridge_port)
            self.status_text.set("REDE ENVIADA")
            messagebox.showinfo("Wi-Fi", "Configuração enviada. O ESP32 vai reiniciar e conectar à rede escolhida.")
        except (DeviceError, ValueError) as exc:
            self.status_text.set("ERRO DE REDE")
            messagebox.showerror("Wi-Fi", f"Não foi possível enviar a configuração: {exc}")

    def home(self) -> None:
        if not messagebox.askyesno("Confirmar HOME", "Executar homing agora? Certifique-se de que a area esta livre."): return
        try:
            result = self.client.home(); self.write_dashboard(result); self.status_text.set("HOME EXECUTADO")
        except DeviceError as exc: messagebox.showerror("HOME", str(exc))

    def add_card(self) -> None:
        uid = "".join(self.uid.get().split()).upper()
        owner = self.owner.get().strip()
        attributes = {}
        for pair in self.card_attributes.get().split(";"):
            if not pair.strip():
                continue
            if "=" not in pair:
                return messagebox.showerror("Cartao", "Atributos devem usar o formato nome=valor, separados por ponto e virgula.")
            name, value = (part.strip() for part in pair.split("=", 1))
            if not name or not value:
                return messagebox.showerror("Cartao", "O nome e o valor de cada atributo sao obrigatorios.")
            attributes[name] = value
        if not uid or not all(character in "0123456789ABCDEF" for character in uid): return messagebox.showerror("Cartao", "O UID deve conter apenas hexadecimal.")
        if not owner: return messagebox.showerror("Cartao", "Informe o proprietario.")
        try: self.database.execute("INSERT INTO cards (uid, owner_name, attributes_json) VALUES (?, ?, ?)", (uid, owner, json.dumps(attributes, ensure_ascii=False)))
        except Exception as exc: return messagebox.showerror("Cartao", str(exc))
        self.uid.set(""); self.owner.set(""); self.card_attributes.set("")
        self.refresh_local()

    def toggle_card_status(self) -> None:
        selected = self.cards_view.selection()
        if not selected:
            return messagebox.showerror("Cartao", "Selecione um cartao.")
        card_id = int(selected[0])
        current = self.database.rows("SELECT status, owner_name FROM cards WHERE id = ?", (card_id,))
        if not current:
            return messagebox.showerror("Cartao", "Cartao nao encontrado.")
        old_status = current[0]["status"]
        new_status = "revoked" if old_status == "active" else "active"
        self.database.execute("UPDATE cards SET status = ? WHERE id = ?", (new_status, card_id))
        self.refresh_local()

    def add_drawer(self) -> None:
        if not self.require_configuration_permission() or not self.ensure_machine_stopped(): return
        if not messagebox.askyesno("Confirmar gaveta", "Adicionar esta gaveta com status NÃO CALIBRADA?"): return
        values = (self.drawer_x.get().strip(), self.drawer_y.get().strip(), self.drawer_z.get().strip())
        if any(values): return messagebox.showwarning("Calibração", "O JOG ainda não está implementado. Crie a gaveta sem posição; ela ficará NÃO CALIBRADA.")
        if not self.drawer_label.get().strip(): return messagebox.showerror("Gaveta", "Informe um nome.")
        configured_count = self.database.machine_config().get("drawer_count", 18)
        if len(self.database.rows("SELECT id FROM drawers")) >= configured_count:
            return messagebox.showerror("Gaveta", f"A quantidade configurada de gavetas ({configured_count}) já foi atingida.")
        self.database.insert_drawer_pending(self.drawer_label.get().strip())
        self.drawer_label.set(""); self.drawer_x.set(""); self.drawer_y.set(""); self.drawer_z.set("")
        self.refresh_local(); self.synchronize_local_change()

    def edit_selected_drawer(self) -> None:
        selected = self.drawers_view.selection()
        if not selected: return messagebox.showerror("Gaveta", "Selecione uma gaveta.")
        drawer_id = int(self.drawers_view.item(selected[0], "values")[0])
        rows = self.database.rows("SELECT label, pos_x_mm, pos_y_mm, pos_z_mm, calibrated FROM drawers WHERE id = ?", (drawer_id,))
        if not rows: return messagebox.showerror("Gaveta", "Gaveta não encontrada.")
        drawer = rows[0]
        dialog = tk.Toplevel(self); dialog.title("Editar gaveta"); dialog.transient(self); dialog.grab_set()
        content = ttk.Frame(dialog, padding=18, style="App.TFrame"); content.pack(fill="both", expand=True)
        label = tk.StringVar(value=drawer["label"])
        coordinates = [tk.StringVar(value="" if not drawer["calibrated"] else str(drawer[column])) for column in ("pos_x_mm", "pos_y_mm", "pos_z_mm")]
        ttk.Label(content, text=f"ID: {drawer_id}").pack(anchor="w")
        ttk.Label(content, text="Nome/Label").pack(anchor="w", pady=(10, 2)); ttk.Entry(content, textvariable=label, width=35).pack(fill="x")
        for name, variable in zip(("X mm", "Y mm", "Z mm"), coordinates):
            ttk.Label(content, text=name).pack(anchor="w", pady=(8, 2)); ttk.Entry(content, textvariable=variable, width=20).pack(fill="x")
        ttk.Label(content, text="Alterar posição não calibra a gaveta; o JOG ainda não está implementado.", style="Subtitle.TLabel", wraplength=330).pack(anchor="w", pady=(10, 12))

        def save() -> None:
            if not self.require_configuration_permission() or not self.ensure_machine_stopped(): return
            if not label.get().strip(): return messagebox.showerror("Gaveta", "Informe um nome.", parent=dialog)
            raw_values = tuple(variable.get().strip() for variable in coordinates)
            old_values = (drawer["pos_x_mm"], drawer["pos_y_mm"], drawer["pos_z_mm"])
            if not any(raw_values):
                if drawer["calibrated"]: return messagebox.showerror("Gaveta", "Uma gaveta calibrada precisa manter sua posição.", parent=dialog)
                values = (None, None, None); calibrated = 0
            else:
                try: values = tuple(float(value) for value in raw_values)
                except ValueError: return messagebox.showerror("Gaveta", "A calibração manual ainda não está implementada.", parent=dialog)
                if not drawer["calibrated"] or values != old_values:
                    return messagebox.showwarning("Calibração", "O JOG ainda não está implementado; a posição só pode ser alterada por calibração real.", parent=dialog)
                calibrated = 1
            if not messagebox.askyesno("Confirmar gaveta", "Salvar a alteração?", parent=dialog): return
            self.database.update_drawer_pending(drawer_id, label.get().strip(), values, calibrated)
            dialog.destroy(); self.refresh_local()
            self.synchronize_local_change()

        ttk.Button(content, text="Salvar", command=save, style="Primary.TButton").pack(anchor="e", pady=(4, 0))

    def selected_id(self, value: str) -> int | None:
        try: return int(value.split(" - ", 1)[0])
        except (ValueError, AttributeError): return None

    def add_inventory(self) -> None:
        drawer_id = self.selected_id(self.item_drawer.get())
        item_name = self.item_name.get().strip()
        try: quantity = int(self.item_quantity.get())
        except ValueError: return messagebox.showerror("Inventario", "A quantidade deve ser um numero inteiro.")
        if drawer_id is None or not item_name: return messagebox.showerror("Inventario", "Informe gaveta e item.")
        if quantity < 0: return messagebox.showerror("Inventario", "A quantidade nao pode ser negativa.")
        self.database.execute(
            "INSERT INTO drawer_inventory (drawer_id, item_name, quantity) VALUES (?, ?, ?) "
            "ON CONFLICT(drawer_id, item_name) DO UPDATE SET quantity = excluded.quantity",
            (drawer_id, item_name, quantity),
        )
        self.item_name.set(""); self.item_quantity.set("0"); self.refresh_local()

    def add_permission(self) -> None:
        drawer_id = self.selected_id(self.permission_drawer.get())
        card_id = self.selected_id(self.permission_card.get())
        if drawer_id is None or card_id is None: return messagebox.showerror("Permissoes", "Selecione gaveta e cartao.")
        self.database.execute(
            "INSERT OR IGNORE INTO card_drawer_permissions (card_id, drawer_id) VALUES (?, ?)",
            (card_id, drawer_id),
        )
        self.refresh_local()

    def refresh_local(self) -> None:
        if not hasattr(self, "cards_view"): return
        card_rows = self.database.rows("SELECT id, uid, owner_name, status, attributes_json FROM cards ORDER BY id")
        for item in self.cards_view.get_children(): self.cards_view.delete(item)
        for row in card_rows:
            try: attributes = json.loads(row["attributes_json"] or "{}")
            except json.JSONDecodeError: attributes = {}
            attribute_text = "; ".join(f"{name}={value}" for name, value in attributes.items())
            self.cards_view.insert("", "end", iid=str(row["id"]), values=(row["uid"], row["owner_name"], attribute_text, row["status"]))
        drawer_rows = self.database.rows("SELECT id, label, pos_x_mm, pos_y_mm, pos_z_mm, calibrated FROM drawers ORDER BY id")
        for item in self.drawers_view.get_children(): self.drawers_view.delete(item)
        drawer_options = [f"{row['id']} - {row['label']}" for row in drawer_rows]
        card_options = [f"{row['id']} - {row['owner_name']}" for row in card_rows]
        self.item_drawer_box["values"] = drawer_options; self.permission_drawer_box["values"] = drawer_options; self.permission_card_box["values"] = card_options
        for row in drawer_rows:
            items = self.database.drawer_inventory(row["id"])
            item_text = ", ".join(f"{item['item_name']} ({item['quantity']})" for item in items) or "Vazio"
            quantity = sum(item["quantity"] for item in items)
            owners = ", ".join(self.database.authorized_owners(row["id"])) or "Ninguem"
            position = (row["pos_x_mm"], row["pos_y_mm"], row["pos_z_mm"]) if row["calibrated"] else ("---", "---", "---")
            self.drawers_view.insert("", "end", values=(row["id"], row["label"], item_text, quantity, owners, *position, "Sim" if row["calibrated"] else "NÃO CALIBRADA"))

if __name__ == "__main__":
    SmartStockApp().mainloop()
