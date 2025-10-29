import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import sqlite3
import os
import re
import datetime
import logging


# Configuração básica de logging
logging.basicConfig(filename='app_errors.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


# --- SQLiteDatabase Class ---
class SQLiteDatabase:
    def __init__(self, db_name="records_gui.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        """Estabelece uma conexão com o banco de dados SQLite."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            logging.error(f"Erro ao conectar ao banco de dados: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao conectar ao banco de dados: {e}")

    def disconnect(self):
        """Fecha a conexão com o banco de dados."""
        if self.conn:
            self.conn.close()

    def create_table(self, table_name, columns):
        """Cria uma tabela com o nome e colunas especificados e um índice no campo 'name'."""
        column_defs = ", ".join([f"{col_name} {col_type}" for col_name, col_type in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs})"
        try:
            self.cursor.execute(query)
            #índice na coluna 'name' se ele não existir, para melhorar a performance de busca
            self.cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_name ON {table_name} (name)")
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao criar a tabela '{table_name}' ou índice: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao criar a tabela '{table_name}' ou índice: {e}")
            return False

    def insert_record(self, table_name, data):
        """Insere um novo registro na tabela."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        values = tuple(data.values())
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        try:
            self.cursor.execute(query, values)
            self.conn.commit()
            print(f"DEBUG: Record inserted successfully. Name: {data.get('name')}, ID: {self.cursor.lastrowid}")
            return self.cursor.lastrowid
        except sqlite3.IntegrityError as e: #erro de unicidade
            logging.error(f"Erro de unicidade ao inserir registro: {e}")
            messagebox.showerror("Erro de Unicidade", "Um ticket com este código já existe. Por favor, use um código diferente.")
            return None
        except sqlite3.Error as e:
            logging.error(f"Erro ao inserir registro: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao inserir registro: {e}")
            return None

    def select_all_records(self, table_name, order_by="date", ascending=False):
        """Recupera todos os registros da tabela, com opção de ordenação."""
        order_direction = "ASC" if ascending else "DESC"
        
        #ordenação de data no formato 'dd/mm/yyyy'
        if order_by == "date":
            #'dd/mm/yyyy' para 'yyyymmdd' para ordenação cronológica correta
            sort_expression = "SUBSTR(date, 7, 4) || SUBSTR(date, 4, 2) || SUBSTR(date, 1, 2)"
        elif order_by not in ["id", "name", "type", "status"]: #Fallback para colunas válidas
            order_by = "id" #Fallback para uma coluna segura
            sort_expression = order_by
        else: #nome de coluna simples e válido
            sort_expression = order_by
            
        query = f"SELECT * FROM {table_name} ORDER BY {sort_expression} {order_direction}"
        
        try:
            self.cursor.execute(query)
            columns = [description[0] for description in self.cursor.description]
            records = self.cursor.fetchall()
            print(f"DEBUG (select_all_records): Query executed: '{query}' - Fetched {len(records)} records.")
            return columns, records
        except sqlite3.Error as e:
            logging.error(f"Erro ao selecionar todos os registros: {e} - Query: {query}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao selecionar todos os registros: {e}")
            return [], []

    def select_record_by_id(self, table_name, record_id):
        """Recupera um único registro pelo seu ID."""
        query = f"SELECT * FROM {table_name} WHERE id = ?"
        try:
            self.cursor.execute(query, (record_id,))
            columns = [description[0] for description in self.cursor.description]
            record = self.cursor.fetchone()
            return columns, record
        except sqlite3.Error as e:
            logging.error(f"Erro ao selecionar registro por ID: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao selecionar registro por ID: {e}")
            return [], None

    def select_records_by_name(self, table_name, name_query):
        """Recupera registros com base no nome (usando LIKE para busca parcial)."""
        query = f"SELECT * FROM {table_name} WHERE name LIKE ?"
        try:
            self.cursor.execute(query, (f"%{name_query}%",))
            columns = [description[0] for description in self.cursor.description]
            records = self.cursor.fetchall()
            return columns, records
        except sqlite3.Error as e:
            logging.error(f"Erro ao selecionar registros por nome: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao selecionar registros por nome: {e}")
            return [], []
            
    def select_records_by_date(self, table_name, date_query):
        """Recupera registros com base na data exata."""
        query = f"SELECT * FROM {table_name} WHERE date = ?"
        try:
            self.cursor.execute(query, (date_query,))
            columns = [description[0] for description in self.cursor.description]
            records = self.cursor.fetchall()
            return columns, records
        except sqlite3.Error as e:
            logging.error(f"Erro ao selecionar registros por data: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao selecionar registros por data: {e}")
            return [], []

    def select_records_by_status(self, table_name, status_query, order_by="date", ascending=False):
        """Recupera registros com base no status exato, com opção de ordenação."""
        order_direction = "ASC" if ascending else "DESC"
        
        if order_by == "date":
            sort_expression = "SUBSTR(date, 7, 4) || SUBSTR(date, 4, 2) || SUBSTR(date, 1, 2)"
        elif order_by not in ["id", "name", "type", "status"]:
            order_by = "id"
            sort_expression = order_by
        else:
            sort_expression = order_by
            
        query = f"SELECT * FROM {table_name} WHERE status = ? ORDER BY {sort_expression} {order_direction}"
        try:
            self.cursor.execute(query, (status_query,))
            columns = [description[0] for description in self.cursor.description]
            records = self.cursor.fetchall()
            return columns, records
        except sqlite3.Error as e:
            logging.error(f"Erro ao selecionar registros por status: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao selecionar registros por status: {e}")
            return [], []

    def select_records_by_type(self, table_name, type_query, order_by="date", ascending=False):
        """Recupera registros com base no tipo exato, com opção de ordenação."""
        order_direction = "ASC" if ascending else "DESC"
        
        if order_by == "date":
            sort_expression = "SUBSTR(date, 7, 4) || SUBSTR(date, 4, 2) || SUBSTR(date, 1, 2)"
        elif order_by not in ["id", "name", "type", "status"]:
            order_by = "id"
            sort_expression = order_by
        else:
            sort_expression = order_by
            
        query = f"SELECT * FROM {table_name} WHERE type = ? ORDER BY {sort_expression} {order_direction}"
        try:
            self.cursor.execute(query, (type_query,))
            columns = [description[0] for description in self.cursor.description]
            records = self.cursor.fetchall()
            return columns, records
        except sqlite3.Error as e:
            logging.error(f"Erro ao selecionar registros por tipo: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao selecionar registros por tipo: {e}")
            return [], []

    def update_record(self, table_name, record_id, new_data):
        """Atualiza um registro existente pelo ID."""
        set_clause = ", ".join([f"{key} = ?" for key in new_data.keys()])
        values = tuple(new_data.values()) + (record_id,)
        query = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
        try:
            self.cursor.execute(query, values)
            self.conn.commit()
            if self.cursor.rowcount > 0:
                print(f"DEBUG: Record {record_id} updated successfully.")
                return True
            else:
                print(f"DEBUG: Record {record_id} not found or no changes made.")
                return False
        except sqlite3.IntegrityError as e: #erro de unicidade ao atualizar
            logging.error(f"Erro de unicidade ao atualizar registro {record_id}: {e}")
            messagebox.showerror("Erro de Unicidade", "O código do ticket que você está tentando usar já existe em outro registro.")
            return False
        except sqlite3.Error as e:
            logging.error(f"Erro ao atualizar registro {record_id}: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao atualizar registro {record_id}: {e}")
            return False

    def delete_record(self, table_name, record_id):
        """Deleta um registro pelo seu ID."""
        query = f"DELETE FROM {table_name} WHERE id = ?"
        try:
            self.cursor.execute(query, (record_id,))
            self.conn.commit()
            if self.cursor.rowcount > 0:
                print(f"DEBUG: Record {record_id} deleted successfully.")
                return True
            else:
                print(f"DEBUG: Record {record_id} not found for deletion.")
                return False
        except sqlite3.Error as e:
            logging.error(f"Erro ao deletar registro {record_id}: {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao deletar registro {record_id}: {e}")
            return False
            
    def delete_all_records(self, table_name):
        """Deleta todos os registros da tabela."""
        query = f"DELETE FROM {table_name}"
        try:
            self.cursor.execute(query)
            self.conn.commit()
            print(f"DEBUG: All records from {table_name} deleted successfully.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao deletar todos os registros da tabela '{table_name}': {e}")
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao deletar todos os registros da tabela '{table_name}': {e}")
            return False

    def count_total_records(self, table_name):
        """Conta o número total de registros na tabela."""
        query = f"SELECT COUNT(*) FROM {table_name}"
        try:
            self.cursor.execute(query)
            count = self.cursor.fetchone()[0]
            print(f"DEBUG (count_total_records): Total records in {table_name}: {count}")
            return count
        except sqlite3.Error as e:
            logging.error(f"Erro ao contar registros da tabela '{table_name}': {e}")
            return 0


# --- Tkinter GUI Application ---
class DatabasePanel:
    def __init__(self, master, db_name="records_gui.db"):
        self.master = master
        master.title("Mahnrattan Database")
        master.geometry("480x500")
        master.resizable(False, False)

        #Tema escuro
        self.bg_color = "#202020"
        self.fg_color = "#E0E0E0"
        self.entry_bg = "#303030"
        self.entry_fg = "#FFFFFF"
        self.placeholder_fg = "grey"
        self.button_bg = "#404040"
        self.button_fg = "#FFFFFF"
        self.highlight_color = "#007ACC"

        master.config(bg=self.bg_color)

        #common font for a modern minimalist look
        self.default_font = ("Comfortaa", 10)
        self.bold_font = ("Comfortaa", 10, "bold")
        #fonte monoespaçada para a exibição da tabela para alinhamento
        self.monospace_font = ("TkFixedFont", 10)

        self.db = SQLiteDatabase(db_name)
        self.table_name = "tickets"
        self.table_columns = {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL UNIQUE",
            "type": "TEXT",
            "date": "TEXT",
            "status": "TEXT"
        }
        self.db.create_table(self.table_name, self.table_columns)

        self.type_options = [
            "Acessos", "Acompanhamento", "Agendamento", "CFTV", "Conexões",
            "Disponibilidade", "Erros", "Formatação", "Impressoras", "Instalação/Configuração",
            "Office365", "Requisição", "Outros"
        ]
        self.status_options = ["Pendente", "Em atendimento", "Resolvido"]

        self.name_entry = None
        self.type_combobox = None
        self.date_entry = None
        self.status_combobox = None
        self.id_entry = None
        self.ticket_count_label = None

        self.create_widgets()
        self.update_ticket_count()

        # Listar todos os tickets ao iniciar
        self.show_all_records_entry()

    def add_placeholder(self, entry_widget, text):
        """Adiciona funcionalidade de placeholder a um widget Entry."""
        entry_widget.insert(0, text)
        entry_widget.config(fg=self.placeholder_fg)

        def on_focus_in(event):
            if entry_widget.get() == text and entry_widget.cget('fg') == self.placeholder_fg:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg=self.entry_fg)

        def on_focus_out(event):
            if not entry_widget.get():
                entry_widget.insert(0, text)
                entry_widget.config(fg=self.placeholder_fg)

        entry_widget.bind("<FocusIn>", on_focus_in)
        entry_widget.bind("<FocusOut>", on_focus_out)

    def _validate_date(self, date_string):
        """Valida se a string é uma data real no formato dd/mm/aaaa."""
        try:
            datetime.datetime.strptime(date_string, "%d/%m/%Y")
            return True
        except ValueError:
            return False

    def format_date_entry(self, event=None):
        """Formata o campo de data para dd/mm/aaaa."""
        current_text = self.date_entry.get().replace("/", "")
        new_text = ""
        
        digits_only = "".join(filter(str.isdigit, current_text))

        if len(digits_only) > 8:
            digits_only = digits_only[:8]

        if len(digits_only) > 0:
            new_text += digits_only[:2]
            if len(digits_only) > 2:
                new_text += "/" + digits_only[2:4]
            if len(digits_only) > 4:
                new_text += "/" + digits_only[4:8]

        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, new_text)

        if self.date_entry.cget('fg') == self.placeholder_fg and len(new_text) > 0:
            self.date_entry.config(fg=self.entry_fg)
        elif len(new_text) == 0:
            self.date_entry.delete(0, tk.END)
            self.add_placeholder(self.date_entry, "dd/mm/aaaa")


    def create_widgets(self):
        # Input Frame (Controle de Tickets Mahnrattan)
        input_frame = tk.LabelFrame(self.master, text="Controle de Tickets Mahnrattan", padx=10, pady=10,
                                    bg=self.bg_color, fg=self.fg_color,
                                    font=self.bold_font)
        input_frame.pack(padx=10, pady=10, fill="x")

        input_frame.grid_columnconfigure(0, weight=0)
        input_frame.grid_columnconfigure(1, weight=1)
        input_frame.grid_columnconfigure(2, weight=0)

        # --- Input Fields ---
        tk.Label(input_frame, text="Ticket:", bg=self.bg_color, fg=self.fg_color, font=self.bold_font) \
            .grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.name_entry = tk.Entry(input_frame, width=40, bg=self.entry_bg, fg=self.entry_fg,
                                   insertbackground=self.fg_color, font=self.default_font,
                                   highlightbackground=self.highlight_color, highlightthickness=1, bd=0)
        self.name_entry.grid(row=0, column=1, pady=5, padx=5, sticky="ew")
        self.add_placeholder(self.name_entry, "Código do Ticket (INC123456)")

        tk.Label(input_frame, text="Tipo:", bg=self.bg_color, fg=self.fg_color, font=self.bold_font) \
            .grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.type_combobox = ttk.Combobox(input_frame, values=self.type_options, state="readonly", width=38,
                                          font=self.default_font)
        self.type_combobox.grid(row=1, column=1, pady=5, padx=5, sticky="ew")
        self.type_combobox.set(self.type_options[0])

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox',
                        fieldbackground=self.entry_bg,
                        background=self.button_bg,
                        foreground=self.entry_fg,
                        selectbackground=self.highlight_color,
                        selectforeground=self.entry_fg,
                        bordercolor=self.highlight_color,
                        lightcolor=self.entry_bg,
                        darkcolor=self.entry_bg,
                        arrowcolor=self.fg_color,
                        font=self.default_font)
        style.map('TCombobox',
                  fieldbackground=[('readonly', self.entry_bg)],
                  foreground=[('readonly', self.entry_fg)])

        tk.Label(input_frame, text="Data:", bg=self.bg_color, fg=self.fg_color, font=self.bold_font) \
            .grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.date_entry = tk.Entry(input_frame, width=40, bg=self.entry_bg, fg=self.entry_fg,
                                    insertbackground=self.fg_color, font=self.default_font,
                                    highlightbackground=self.highlight_color, highlightthickness=1, bd=0)
        self.date_entry.grid(row=2, column=1, pady=5, padx=5, sticky="ew")
        self.add_placeholder(self.date_entry, "dd/mm/aaaa")
        self.date_entry.bind("<KeyRelease>", self.format_date_entry)

        tk.Label(input_frame, text="Status:", bg=self.bg_color, fg=self.fg_color, font=self.bold_font) \
            .grid(row=3, column=0, sticky="w", pady=5, padx=5)
        self.status_combobox = ttk.Combobox(input_frame, values=self.status_options, state="readonly", width=38,
                                           font=self.default_font)
        self.status_combobox.grid(row=3, column=1, pady=5, padx=5, sticky="ew")
        self.status_combobox.set(self.status_options[0])

        tk.Label(input_frame, text="ID:", bg=self.bg_color, fg=self.fg_color, font=self.bold_font) \
            .grid(row=4, column=0, sticky="w", pady=5, padx=5)
        self.id_entry = tk.Entry(input_frame, width=40, bg=self.entry_bg, fg=self.entry_fg,
                                 insertbackground=self.fg_color, font=self.default_font,
                                 highlightbackground=self.highlight_color, highlightthickness=1, bd=0)
        self.id_entry.grid(row=4, column=1, pady=5, padx=5, sticky="ew")
        self.add_placeholder(self.id_entry, "Para Atualizar/Deletar")

        #Botões de Ação na coluna 2
        column2_buttons_data = [
            ("Adicionar Ticket", self.add_record),
            ("Atualizar Ticket", self.update_record_entry),
            ("Deletar Ticket", self.delete_record_entry),
            ("Mostrar por Todos", self.show_all_records_entry),
            ("Mostrar por Ticket", self.get_record_by_name_entry),
        ]

        for i, (text, command) in enumerate(column2_buttons_data):
            tk.Button(input_frame, text=text, command=command, width=15,
                      bg=self.button_bg, fg=self.button_fg, font=self.default_font,
                      activebackground=self.highlight_color, activeforeground=self.entry_fg,
                      bd=0, highlightbackground=self.highlight_color, highlightthickness=1,
                      relief="flat", cursor="hand2") \
                .grid(row=i, column=2, padx=5, pady=2, sticky="ew")

        #Frame para botões centralizados
        centralized_buttons_frame = tk.Frame(input_frame, bg=self.bg_color)
        # Ajuste a linha para acomodar o novo botão na coluna 2
        centralized_buttons_frame.grid(row=len(column2_buttons_data), column=0, columnspan=3, pady=10, padx=5, sticky="ew")

        centralized_buttons_frame.grid_columnconfigure(0, weight=1)
        centralized_buttons_frame.grid_columnconfigure(1, weight=1)
        centralized_buttons_frame.grid_rowconfigure(0, weight=1)
        centralized_buttons_frame.grid_rowconfigure(1, weight=1)
        centralized_buttons_frame.grid_rowconfigure(2, weight=1)

        centralized_buttons_data = [
            ("Filtrar por Data", self.filter_records_by_date),
            ("Limpar Campos", self.clear_entries),
            ("Filtrar por Status", self.filter_records_by_status),
            ("Limpar Registros", self.clear_all_records_prompt),
            ("Filtrar por Tipo", self.filter_records_by_type),
            ("Ajuda", self.show_help_message)           
            
        ]

        button_positions = [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)] 

        for i, (text, command) in enumerate(centralized_buttons_data):
            row, col = button_positions[i]
            tk.Button(centralized_buttons_frame, text=text, command=command,
                      bg=self.button_bg, fg=self.button_fg, font=self.default_font,
                      activebackground=self.highlight_color, activeforeground=self.entry_fg,
                      bd=0, highlightbackground=self.highlight_color, highlightthickness=1,
                      relief="flat", cursor="hand2") \
                .grid(row=row, column=col, padx=5, pady=2, sticky="ew")

        #Área de exibição de saída
        output_header_frame = tk.Frame(self.master, bg=self.bg_color)
        output_header_frame.pack(padx=10, pady=(5, 0), fill='x')

        output_header_frame.grid_columnconfigure(0, weight=1)
        output_header_frame.grid_columnconfigure(1, weight=1)
        
        self.output_label = tk.Label(output_header_frame, text="Tickets:",
                                     bg=self.bg_color, fg=self.fg_color,
                                     font=self.bold_font,
                                     anchor='w')
        self.output_label.grid(row=0, column=0, sticky="w")

        self.ticket_count_label = tk.Label(output_header_frame, text="Total: 0",
                                          bg=self.bg_color, fg=self.fg_color,
                                          font=self.bold_font,
                                          anchor='e')
        self.ticket_count_label.grid(row=0, column=1, sticky="e")

        self.output_text = scrolledtext.ScrolledText(self.master, width=70, height=20, wrap=tk.WORD,
                                                     bg=self.entry_bg, fg=self.entry_fg,
                                                     font=self.monospace_font,
                                                     insertbackground=self.fg_color,
                                                     highlightbackground=self.highlight_color,
                                                     highlightthickness=1, bd=0)
        self.output_text.pack(padx=10, pady=(0, 5), fill='both', expand=True)

    def update_ticket_count(self):
        """Atualiza o contador de tickets exibido."""
        count = self.db.count_total_records(self.table_name)
        self.ticket_count_label.config(text=f"Total: {count}")

    def display_message(self, message, append=False):
        """Exibe uma mensagem na área de texto de saída."""
        if not append:
            self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)

    def clear_entries(self):
        """Limpa todos os campos de entrada e redefine os placeholders/valores padrão."""
        entry_placeholders = {
            self.name_entry: "Código do Ticket (INC123456)",
            self.date_entry: "dd/mm/aaaa",
            self.id_entry: "Para Atualizar/Deletar"
        }
        for entry, placeholder_text in entry_placeholders.items():
            entry.delete(0, tk.END)
            self.add_placeholder(entry, placeholder_text)

        self.type_combobox.set(self.type_options[0])
        self.status_combobox.set(self.status_options[0])

        self.display_message("Campos de entrada limpos.")
        self.output_label.config(text="Tickets:") # Resetar o label

    def add_record(self):
        """Adiciona um novo registro ao banco de dados."""
        name = self.name_entry.get().strip()
        record_type = self.type_combobox.get().strip()
        date_val = self.date_entry.get().strip()
        status_val = self.status_combobox.get().strip()

        if name == "Código do Ticket (INC123456)" or not name:
            messagebox.showerror("Erro nos Dados", "O campo 'Ticket' não pode estar vazio.")
            return

        if date_val == "dd/mm/aaaa": date_val = ""
        
        if date_val:
            if not re.match(r"^\d{2}/\d{2}/\d{4}$", date_val):
                messagebox.showerror("Erro nos Dados", "Formato de data inválido. Use dd/mm/aaaa.")
                return
            if not self._validate_date(date_val):
                messagebox.showerror("Erro nos Dados", "Data inválida. Por favor, insira uma data real no formato dd/mm/aaaa.")
                return

        record_data = {"name": name, "type": record_type, "date": date_val, "status": status_val}
        
        new_id = self.db.insert_record(self.table_name, record_data)
        if new_id:
            self.display_message(f"Ticket '{name}' adicionado com ID: {new_id}")
            
            self.clear_entries()
            
            self.id_entry.delete(0, tk.END)
            self.id_entry.insert(0, str(new_id))
            self.id_entry.config(fg=self.entry_fg)

            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, name)
            self.name_entry.config(fg=self.entry_fg)

            self.update_ticket_count()
            self.show_all_records_entry() 
            
    def update_record_entry(self):
        """Atualiza um registro existente com base no ID."""
        record_id_str = self.id_entry.get().strip()
        if record_id_str == "Para Atualizar/Deletar" or not record_id_str:
            messagebox.showerror("Erro nos Dados", "Por favor, forneça um ID para atualizar.")
            return

        try:
            record_id = int(record_id_str)
        except ValueError:
            messagebox.showerror("Erro nos Dados", "O ID deve ser um número inteiro.")
            return

        update_data = {}
        name = self.name_entry.get().strip()
        record_type = self.type_combobox.get().strip()
        date_val = self.date_entry.get().strip()
        status_val = self.status_combobox.get().strip()

        if name != "Código do Ticket (INC123456)" and name: update_data["name"] = name
        if record_type: update_data["type"] = record_type
        if status_val: update_data["status"] = status_val

        if date_val != "dd/mm/aaaa" and date_val:
            if not re.match(r"^\d{2}/\d{2}/\d{4}$", date_val):
                messagebox.showerror("Erro nos Dados", "Formato de data inválido. Use dd/mm/aaaa.")
                return
            if not self._validate_date(date_val):
                messagebox.showerror("Erro nos Dados", "Data inválida. Por favor, insira uma data real no formato dd/mm/aaaa.")
                return
            update_data["date"] = date_val
        
        if not update_data:
            messagebox.showinfo("Nenhuma Alteração", "Nenhum dado fornecido para atualização. Preencha os campos que deseja alterar.")
            return

        if self.db.update_record(self.table_name, record_id, update_data):
            self.display_message(f"Ticket com ID {record_id} atualizado com sucesso.")
            self.clear_entries()
            
            self.id_entry.delete(0, tk.END)
            self.id_entry.insert(0, str(record_id))
            self.id_entry.config(fg=self.entry_fg)
            
            if "name" in update_data:
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, update_data["name"])
                self.name_entry.config(fg=self.entry_fg)

            self.update_ticket_count()
            self.show_all_records_entry() 
            
    def delete_record_entry(self):
        """Deleta um registro com base no ID."""
        record_id_str = self.id_entry.get().strip()
        if record_id_str == "Para Atualizar/Deletar" or not record_id_str:
            messagebox.showerror("Erro nos Dados", "Por favor, forneça um ID para deletar.")
            return

        try:
            record_id = int(record_id_str)
        except ValueError:
            messagebox.showerror("Erro nos Dados", "O ID deve ser um número inteiro.")
            return

        if messagebox.askyesno("Confirmar Exclusão", f"Você tem certeza que deseja deletar o ticket com ID {record_id}?"):
            if self.db.delete_record(self.table_name, record_id):
                self.display_message(f"Ticket com ID {record_id} deletado com sucesso.")
                self.clear_entries()
                self.update_ticket_count()
                self.show_all_records_entry() 

    def show_all_records_entry(self):
        """Recupera e exibe todos os registros, ordenados pela data mais recente."""
        columns, records = self.db.select_all_records(self.table_name, order_by="date", ascending=False)
        self._display_records_in_output(columns, records, "Todos os Tickets")
        self.output_label.config(text="Tickets:") # Atualiza o label superior

    def get_record_by_name_entry(self):
        """Recupera e exibe registros com base no nome e preenche os campos com o primeiro."""
        name_query = self.name_entry.get().strip()
        if name_query == "Código do Ticket (INC123456)" or not name_query:
            messagebox.showerror("Erro nos Dados", "Por favor, forneça um código de ticket (ou parte dele) para buscar.")
            return

        columns, records = self.db.select_records_by_name(self.table_name, name_query)
        if records:
            self._display_records_in_output(columns, records, f"Tickets encontrados com '{name_query}'")
            self.output_label.config(text=f"Tickets encontrados com '{name_query}':") # Atualiza o label superior
            first_record_dict = dict(zip(columns, records[0]))
            
            self.clear_entries()
            
            self.id_entry.delete(0, tk.END)
            self.id_entry.insert(0, str(first_record_dict["id"]))
            self.id_entry.config(fg=self.entry_fg)

            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, first_record_dict["name"])
            self.name_entry.config(fg=self.entry_fg)

            self.type_combobox.set(first_record_dict["type"])
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, first_record_dict["date"])
            if first_record_dict["date"]: self.date_entry.config(fg=self.entry_fg)
            self.status_combobox.set(first_record_dict["status"])
        else:
            self.display_message(f"Nenhum ticket encontrado com o código '{name_query}'.")
            self.output_label.config(text=f"Nenhum ticket encontrado com '{name_query}':") # Atualiza o label superior
            self.clear_entries()
            
    def filter_records_by_date(self):
        """Filtra e exibe tickets com base na data inserida no campo 'Data:'."""
        date_filter = self.date_entry.get().strip()

        if date_filter == "dd/mm/aaaa" or not date_filter:
            messagebox.showerror("Erro de Filtro", "Por favor, insira uma data no campo 'Data:' para filtrar.")
            return

        if not re.match(r"^\d{2}/\d{2}/\d{4}$", date_filter):
            messagebox.showerror("Erro nos Dados", "Formato de data inválido. Use dd/mm/aaaa.")
            return
        if not self._validate_date(date_filter):
            messagebox.showerror("Erro nos Dados", "Data inválida. Por favor, insira uma data real no formato dd/mm/aaaa.")
            return

        columns, records = self.db.select_records_by_date(self.table_name, date_filter)
        if records:
            self._display_records_in_output(columns, records, f"Tickets na data: {date_filter}")
            self.output_label.config(text=f"Tickets na data: {date_filter}:") # Atualiza o label superior
        else:
            self.display_message(f"Nenhum ticket encontrado para a data {date_filter}.")
            self.output_label.config(text=f"Nenhum ticket encontrado na data: {date_filter}:") # Atualiza o label superior

    def filter_records_by_status(self):
        """Filtra e exibe tickets com base no status selecionado no combobox, ordenados pela data mais recente."""
        status_filter = self.status_combobox.get().strip()

        if not status_filter or status_filter not in self.status_options:
            messagebox.showerror("Erro de Filtro", "Por favor, selecione um status válido para filtrar.")
            return

        # Chamada ao método do banco de dados
        columns, records = self.db.select_records_by_status(self.table_name, status_filter, order_by="date", ascending=False)
        if records:
            self._display_records_in_output(columns, records, f"Tickets com Status: {status_filter}")
            self.output_label.config(text=f"Tickets com Status: {status_filter}:") # Atualiza o label superior
        else:
            self.display_message(f"Nenhum ticket encontrado com o status '{status_filter}'.")
            self.output_label.config(text=f"Nenhum ticket encontrado com status: {status_filter}:") # Atualiza o label superior

    def filter_records_by_type(self):
        """Filtra e exibe tickets com base no tipo selecionado no combobox, ordenados pela data mais recente."""
        type_filter = self.type_combobox.get().strip()

        if not type_filter or type_filter not in self.type_options:
            messagebox.showerror("Erro de Filtro", "Por favor, selecione um tipo válido para filtrar.")
            return

        columns, records = self.db.select_records_by_type(self.table_name, type_filter, order_by="date", ascending=False)
        if records:
            self._display_records_in_output(columns, records, f"Tickets com Tipo: {type_filter}")
            self.output_label.config(text=f"Tickets com Tipo: {type_filter}:")
        else:
            self.display_message(f"Nenhum ticket encontrado com o tipo '{type_filter}'.")
            self.output_label.config(text=f"Nenhum ticket encontrado com tipo: {type_filter}:")


    def _display_records_in_output(self, columns, records, title):
        """Função auxiliar para formatar e exibir registros na área de saída."""
        self.output_text.delete(1.0, tk.END)
        print(f"DEBUG (_display_records_in_output): Received {len(records)} records for display under title: '{title}'")
        
        self.output_text.insert(tk.END, f"{title}\n\n")

        if not records:
            self.output_text.insert(tk.END, "Nenhum registro encontrado.\n")
            self.output_text.insert(tk.END, f"\n--- Exibindo {len(records)} registro(s) ---\n")
            self.output_text.see(tk.END)
            return
        
        display_name_map = {"id": "ID", "name": "Ticket", "type": "Tipo", "date": "Data", "status": "Status"}
        
        display_columns_for_width = [len(display_name_map.get(col, col)) for col in columns]

        for record in records:
            for i, item in enumerate(record):
                display_columns_for_width[i] = max(display_columns_for_width[i], len(str(item)))

        col_widths = [w + 2 for w in display_columns_for_width]

        #tag "bold" para usar a mesma fonte monoespaçada
        self.output_text.tag_configure("bold", font=(self.monospace_font[0], self.monospace_font[1], "bold"))

        for i, col_name_raw in enumerate(columns):
            display_col_name = display_name_map.get(col_name_raw, col_name_raw)
            formatted_part = f"{display_col_name:<{col_widths[i]}}"
            self.output_text.insert(tk.END, formatted_part, "bold")

        self.output_text.insert(tk.END, "\n")
        total_header_len = sum(col_widths) 
        self.output_text.insert(tk.END, "-" * total_header_len + "\n")

        for record in records:
            record_parts = []
            for i, item in enumerate(record):
                record_parts.append(f"{str(item):<{col_widths[i]}}")
            self.output_text.insert(tk.END, "".join(record_parts) + "\n")

        self.output_text.insert(tk.END, f"\n--- Exibindo {len(records)} registro(s) ---\n")
        self.output_text.see(tk.END)

    def clear_all_records_prompt(self):
        """Solicita confirmação e deleta todos os registros do banco de dados."""
        if messagebox.askyesno("Confirmar Exclusão", "Você tem certeza que deseja excluir TODOS os tickets? Esta ação é irreversível!"):
            if self.db.delete_all_records(self.table_name):
                self.display_message("Todos os tickets foram excluídos com sucesso.")
                self.clear_entries()
                self.update_ticket_count()
                self.show_all_records_entry() 

    def show_help_message(self):
        """Exibe uma mensagem de ajuda descrevendo os campos e tipos."""
        # A lista de tipos é gerada dinamicamente para o help
        type_options_str = ', '.join(self.type_options)
        
        help_text = (
            "--- GUIA DE USO ---\n\n"
            "• Ticket: Código de identificação do ticket (deve ser único).\n"
            "  Ex: INC123456, INC654321\n\n"
            "• Tipo: Categoria do serviço ou problema. Escolha da lista.\n"
            f"  Valores: {type_options_str}\n\n"
            "• Data: Data do registro ou ocorrência. Formato dd/mm/aaaa.\n"
            "  Ex: 25/10/2025\n\n"
            "• Status: Situação atual do ticket. Escolha da lista.\n"
            f"  Valores: {', '.join(self.status_options)}\n\n"
            "• ID: Usado para Atualizar ou Deletar um registro existente.\n"
            "  Ex: 1, 5, 10\n\n"
            "--- OPERAÇÕES ---\n"
            "• Adicionar: Salva um novo ticket. O código do ticket deve ser ÚNICO.\n"
            "• Atualizar: Modifica um ticket existente pelo ID.\n"
            "• Deletar: Remove um ticket pelo ID.\n"
            "• Mostrar Todos: Exibe todos os tickets ordenados pela data mais recente.\n"
            "• Mostrar por Ticket: Busca tickets que contenham o texto digitado no campo 'Ticket'.\n"
            "• Filtrar por Data: Exibe apenas os tickets que correspondem à data inserida no campo 'Data:'.\n"
            "• Filtrar por Tipo: Exibe apenas os tickets que correspondem ao tipo selecionado no campo 'Tipo:', ordenados pela data mais recente.\n"
            "• Filtrar por Status: Exibe apenas os tickets que correspondem ao status selecionado no campo 'Status:', ordenados pela data mais recente.\n"
            "• Limpar Campos: Limpa todos os campos de entrada.\n"
            "• Limpar Registros: Exclui permanentemente TODOS os tickets do banco de dados.\n"
        )
        messagebox.showinfo("Ajuda Mahnrattan Control", help_text)


#Início do Aplicativo Principal
if __name__ == "__main__":
    root = tk.Tk()
    app = DatabasePanel(root, db_name="records_gui.db")
    root.mainloop()

