from __future__ import annotations

import tkinter as tk
import json
from tkinter import messagebox, ttk

from api.client import DeviceClient, DeviceError
from config.settings import Settings
from database.db import Database
from sync.service import SyncService

class SmartStockApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Smart Stock | Console de Operacao")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.configure(background="#edf1f5")
        self.setup_style()
        self.settings = Settings()
        self.database = Database()
        self.client = DeviceClient(self.settings.values["esp32_host"], self.settings.values["esp32_port"])
        self.sync_service = SyncService(self.database, self.client)
        self.status_text = tk.StringVar(value="Disconnected")
        self.connection_detail = tk.StringVar(value="Nenhuma consulta realizada")
        self.build_ui()
        self.refresh_local()

    def setup_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#edf1f5")
        style.configure("Header.TFrame", background="#17212b")
        style.configure("Header.TLabel", background="#17212b", foreground="#ffffff")
        style.configure("Title.TLabel", font=("Segoe UI", 19, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9))
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#65717d", font=("Segoe UI", 9, "bold"))
        style.configure("CardValue.TLabel", background="#ffffff", foreground="#17212b", font=("Segoe UI", 18, "bold"))
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Primary.TButton", padding=(12, 7), font=("Segoe UI", 9, "bold"))

    def build_ui(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(24, 18)); header.pack(fill="x")
        ttk.Label(header, text="SMART STOCK", style="Header.TLabel", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(header, text="Console de administracao", style="Header.TLabel").pack(side="left", padx=18)
        ttk.Label(header, textvariable=self.status_text, style="Header.TLabel", font=("Segoe UI", 10, "bold")).pack(side="right")
        toolbar = ttk.Frame(self, style="App.TFrame", padding=(24, 14, 24, 4)); toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Atualizar status", command=self.refresh_status, style="Primary.TButton").pack(side="left")
        ttk.Button(toolbar, text="Sincronizar dados", command=self.synchronize).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Executar HOME", command=self.home).pack(side="left")
        ttk.Label(toolbar, textvariable=self.connection_detail, style="Subtitle.TLabel").pack(side="right")
        notebook = ttk.Notebook(self); notebook.pack(fill="both", expand=True, padx=24, pady=(8, 20))
        self.dashboard = ttk.Frame(notebook, padding=12); notebook.add(self.dashboard, text="Dashboard")
        cards = ttk.Frame(notebook, padding=12); notebook.add(cards, text="Cards")
        drawers = ttk.Frame(notebook, padding=12); notebook.add(drawers, text="Drawers")
        self.build_dashboard(); self.build_cards(cards); self.build_drawers(drawers)

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
        self.uid = tk.StringVar(); self.owner = tk.StringVar()
        ttk.Label(form, text="UID hexadecimal").grid(row=0, column=0, sticky="w", padx=(0, 8)); ttk.Entry(form, textvariable=self.uid, width=28).grid(row=0, column=1, sticky="ew")
        ttk.Label(form, text="Proprietario").grid(row=0, column=2, sticky="w", padx=(18, 8)); ttk.Entry(form, textvariable=self.owner, width=28).grid(row=0, column=3, sticky="ew")
        ttk.Button(form, text="Adicionar cartao", command=self.add_card).grid(row=0, column=4, padx=(18, 0)); form.columnconfigure(3, weight=1)
        table = ttk.Frame(parent); table.pack(fill="both", expand=True, pady=(16, 0))
        self.cards_view = ttk.Treeview(table, columns=("uid", "owner", "status"), show="headings")
        for column in ("uid", "owner", "status"): self.cards_view.heading(column, text=column.title())
        self.cards_view.column("uid", width=210); self.cards_view.column("owner", width=280); self.cards_view.column("status", width=100)
        self.cards_view.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(table, orient="vertical", command=self.cards_view.yview).pack(side="right", fill="y")

    def build_drawers(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Gavetas", style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text="Coordenadas reais sao obrigatorias para movimentacao.", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 14))
        form = ttk.LabelFrame(parent, text="Nova gaveta calibrada", padding=12); form.pack(fill="x")
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
        except DeviceError as exc: messagebox.showerror("Sincronizacao", str(exc))

    def home(self) -> None:
        if not messagebox.askyesno("Confirmar HOME", "Executar homing agora? Certifique-se de que a area esta livre."): return
        try:
            result = self.client.home(); self.write_dashboard(result); self.status_text.set("HOME EXECUTADO")
        except DeviceError as exc: messagebox.showerror("HOME", str(exc))

    def add_card(self) -> None:
        uid = "".join(self.uid.get().split()).upper()
        owner = self.owner.get().strip()
        if not uid or not all(character in "0123456789ABCDEF" for character in uid): return messagebox.showerror("Cartao", "O UID deve conter apenas hexadecimal.")
        if not owner: return messagebox.showerror("Cartao", "Informe o proprietario.")
        try: self.database.execute("INSERT INTO cards (uid, owner_name) VALUES (?, ?)", (uid, owner))
        except Exception as exc: return messagebox.showerror("Cartao", str(exc))
        self.uid.set(""); self.owner.set("")
        self.refresh_local()

    def add_drawer(self) -> None:
        try: coordinates = tuple(float(value.get()) for value in (self.drawer_x, self.drawer_y, self.drawer_z))
        except ValueError: return messagebox.showerror("Gaveta", "As coordenadas devem ser numericas.")
        if not self.drawer_label.get().strip(): return messagebox.showerror("Gaveta", "Informe um nome.")
        self.database.execute("INSERT INTO drawers (label, pos_x_mm, pos_y_mm, pos_z_mm, calibrated) VALUES (?, ?, ?, ?, 1)", (self.drawer_label.get().strip(), *coordinates))
        self.drawer_label.set(""); self.drawer_x.set(""); self.drawer_y.set(""); self.drawer_z.set("")
        self.refresh_local()

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
        card_rows = self.database.rows("SELECT id, uid, owner_name, status FROM cards ORDER BY id")
        for item in self.cards_view.get_children(): self.cards_view.delete(item)
        for row in card_rows: self.cards_view.insert("", "end", iid=str(row["id"]), values=(row["uid"], row["owner_name"], row["status"]))
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
            self.drawers_view.insert("", "end", values=(row["id"], row["label"], item_text, quantity, owners, row["pos_x_mm"], row["pos_y_mm"], row["pos_z_mm"], "Sim" if row["calibrated"] else "Nao"))

if __name__ == "__main__":
    SmartStockApp().mainloop()
