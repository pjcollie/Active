import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
from datetime import datetime
import sqlite3
import re

try:
    import PyPDF2
except ImportError:
    # Note: User needs to install PyPDF2 via pip install PyPDF2
    pass

# Initialize the main application
class RetirementTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Retirement Contribution Tracker")
        self.conn = sqlite3.connect("retirement.db")
        self.cursor = self.conn.cursor()
        self.setup_database()
        self.contribution_percentage = self.get_contribution_percentage()
        self.selected_year = self.get_selected_year()
        self.privacy_mode = self.get_privacy_mode()
        self.set_fiscal_year(self.selected_year)
        # Define fonts
        self.button_font = tkfont.Font(family="Helvetica", size=12)
        self.label_font = tkfont.Font(family="Helvetica", size=12)
        self.compare_label_font = tkfont.Font(family="Helvetica", size=14)
        self.total_label_font = tkfont.Font(family="Helvetica", size=14, weight="bold")
        self.tree_font = tkfont.Font(family="Helvetica", size=11)
        # Hypothetical data storage
        self.hypothetical_data = {}  # Dictionary to store hypothetical values {employee_id: (income, contribution, eligible)}
        self.summary_rows = []  # To store summary rows for filtering
        self.actual_rows = []
        self.hypothetical_rows = []
        self.create_gui()

    def setup_database(self):
        # Create tables if they don't exist
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT,
                eligible_for_retirement INTEGER DEFAULT 0
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS income (
                income_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                amount REAL,
                date TEXT,
                type TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS taxable_income (
                year INTEGER PRIMARY KEY,
                total_profit REAL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_id INTEGER PRIMARY KEY,
                contribution_percentage REAL,
                selected_year INTEGER,
                fiscal_year_start TEXT,
                fiscal_year_end TEXT,
                privacy_mode INTEGER
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                note_text TEXT,
                date TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                date TEXT,
                status TEXT,  -- 'Absent' or 'Tardy'
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        """)
        # Check if columns exist and add them if not
        self.cursor.execute("PRAGMA table_info(employees)")
        columns = [col[1] for col in self.cursor.fetchall()]
        if 'eligible_for_retirement' not in columns:
            self.cursor.execute("ALTER TABLE employees ADD COLUMN eligible_for_retirement INTEGER DEFAULT 0")
        
        self.cursor.execute("PRAGMA table_info(settings)")
        columns = [col[1] for col in self.cursor.fetchall()]
        if 'selected_year' not in columns:
            self.cursor.execute("ALTER TABLE settings ADD COLUMN selected_year INTEGER")
            self.cursor.execute("UPDATE settings SET selected_year = ? WHERE setting_id = 1", (datetime.now().year,))
        if 'privacy_mode' not in columns:
            self.cursor.execute("ALTER TABLE settings ADD COLUMN privacy_mode INTEGER")
            self.cursor.execute("UPDATE settings SET privacy_mode = 0 WHERE setting_id = 1")
        # Insert default settings if not present
        self.cursor.execute("SELECT COUNT(*) FROM settings")
        if self.cursor.fetchone()[0] == 0:
            default_year = datetime.now().year
            self.cursor.execute(
                "INSERT INTO settings (setting_id, contribution_percentage, selected_year, fiscal_year_start, fiscal_year_end, privacy_mode) VALUES (?, ?, ?, ?, ?, ?)",
                (1, 5.0, default_year, f"{default_year}-03-01", f"{default_year + 1}-02-28", 0)
            )
        # Remove deductions table if it exists
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deductions'")
        if self.cursor.fetchone():
            self.cursor.execute("DROP TABLE deductions")
        self.conn.commit()

    def get_contribution_percentage(self):
        self.cursor.execute("SELECT contribution_percentage FROM settings WHERE setting_id = 1")
        result = self.cursor.fetchone()
        return result[0] if result else 5.0

    def get_selected_year(self):
        self.cursor.execute("SELECT selected_year FROM settings WHERE setting_id = 1")
        result = self.cursor.fetchone()
        return result[0] if result else datetime.now().year

    def get_privacy_mode(self):
        self.cursor.execute("SELECT privacy_mode FROM settings WHERE setting_id = 1")
        result = self.cursor.fetchone()
        return result[0] if result is not None else 0

    def get_total_profit(self):
        self.cursor.execute("SELECT total_profit FROM taxable_income WHERE year = ?", (self.selected_year,))
        result = self.cursor.fetchone()
        return result[0] if result else 0.0

    def set_fiscal_year(self, year):
        self.fiscal_year_start = f"{year}-03-01"
        self.fiscal_year_end = f"{year + 1}-02-28"

    def blur_name(self, name):
        if not self.privacy_mode:
            return name
        parts = name.split()
        blurred_parts = [''.join('*' for _ in part) for part in parts]
        return ' '.join(blurred_parts)

    def validate_date_range(self, start_date, end_date):
        try:
            start = datetime.strptime(start_date, "%m-%d-%Y")
            end = datetime.strptime(end_date, "%m-%d-%Y")
            if start > end:
                return False, "Start date must be before end date"
            return True, (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        except ValueError:
            return False, "Invalid date format (use MM-DD-YYYY)"

    def add_placeholder(self, entry, placeholder):
        entry.insert(0, placeholder)
        entry.config(foreground="grey")
        def on_focusin(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(foreground="black")
        def on_focusout(event):
            if entry.get() == "":
                entry.insert(0, placeholder)
                entry.config(foreground="grey")
        entry.bind("<FocusIn>", on_focusin)
        entry.bind("<FocusOut>", on_focusout)

    def format_currency(self, value):
        if value < 0:
            return f"(${abs(value):,.2f})"
        else:
            return f"${value:,.2f}"

    def create_gui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True, fill='both')

        # Employee Management Tab
        self.employee_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.employee_frame, text="Manage Employees")
        ttk.Label(self.employee_frame, text="Name:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = ttk.Entry(self.employee_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        self.add_placeholder(self.name_entry, "John Doe")
        ttk.Label(self.employee_frame, text="Department:", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        self.dept_combobox = ttk.Combobox(self.employee_frame, values=["Officer", "Office", "Warehouse"])
        self.dept_combobox.grid(row=1, column=1, padx=5, pady=5)
        self.dept_combobox.set("")
        ttk.Label(self.employee_frame, text="Retirement Eligible:", font=self.label_font).grid(row=2, column=0, padx=5, pady=5)
        self.eligible_var = tk.IntVar(value=0)
        self.eligible_check = ttk.Checkbutton(self.employee_frame, text="Eligible", variable=self.eligible_var)
        self.eligible_check.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(self.employee_frame, text="Add Employee", command=self.add_employee, style="Big.TButton").grid(row=3, column=0, columnspan=2, pady=10)

        # Income Entry Tab
        self.income_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.income_frame, text="Log Income")
        ttk.Label(self.income_frame, text="Employee:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.employee_combobox = ttk.Combobox(self.income_frame)
        self.employee_combobox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.income_frame, text="Amount:", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        self.amount_entry = ttk.Entry(self.income_frame, justify='right')
        self.amount_entry.grid(row=1, column=1, padx=5, pady=5)
        self.add_placeholder(self.amount_entry, "0.00")
        ttk.Label(self.income_frame, text="Date (MM-DD-YYYY or MMDDYYYY):", font=self.label_font).grid(row=2, column=0, padx=5, pady=5)
        self.date_entry = ttk.Entry(self.income_frame)
        self.date_entry.grid(row=2, column=1, padx=5, pady=5)
        self.date_entry.bind("<KeyRelease>", self.auto_format_date)
        self.add_placeholder(self.date_entry, "MM-DD-YYYY")
        ttk.Button(self.income_frame, text="Today", command=self.set_today_date, style="Big.TButton").grid(row=2, column=2, padx=5, pady=5)
        ttk.Label(self.income_frame, text="Type:", font=self.label_font).grid(row=3, column=0, padx=5, pady=5)
        self.type_combobox = ttk.Combobox(self.income_frame, values=["Salary", "Bonus"])
        self.type_combobox.grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(self.income_frame, text="Add Income", command=self.add_income, style="Big.TButton").grid(row=4, column=0, columnspan=2, pady=10)

        # Notes Entry Tab
        self.notes_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.notes_frame, text="Log Notes")
        ttk.Label(self.notes_frame, text="Employee:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.notes_employee_combobox = ttk.Combobox(self.notes_frame)
        self.notes_employee_combobox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.notes_frame, text="Note:", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        self.note_entry = ttk.Entry(self.notes_frame, width=40)
        self.note_entry.grid(row=1, column=1, padx=5, pady=5)
        self.add_placeholder(self.note_entry, "Enter note here")
        ttk.Label(self.notes_frame, text="Date (MM-DD-YYYY or MMDDYYYY):", font=self.label_font).grid(row=2, column=0, padx=5, pady=5)
        self.note_date_entry = ttk.Entry(self.notes_frame)
        self.note_date_entry.grid(row=2, column=1, padx=5, pady=5)
        self.note_date_entry.bind("<KeyRelease>", self.auto_format_date)
        self.add_placeholder(self.note_date_entry, "MM-DD-YYYY")
        ttk.Button(self.notes_frame, text="Today", command=self.set_note_today_date, style="Big.TButton").grid(row=2, column=2, padx=5, pady=5)
        ttk.Button(self.notes_frame, text="Add Note", command=self.add_note, style="Big.TButton").grid(row=3, column=0, columnspan=2, pady=10)

        # Attendance Entry Tab
        self.attendance_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.attendance_frame, text="Log Attendance")
        ttk.Label(self.attendance_frame, text="Employee:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.attendance_employee_combobox = ttk.Combobox(self.attendance_frame)
        self.attendance_employee_combobox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.attendance_frame, text="Date (MM-DD-YYYY or MMDDYYYY):", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        self.attendance_date_entry = ttk.Entry(self.attendance_frame)
        self.attendance_date_entry.grid(row=1, column=1, padx=5, pady=5)
        self.attendance_date_entry.bind("<KeyRelease>", self.auto_format_date)
        self.add_placeholder(self.attendance_date_entry, "MM-DD-YYYY")
        ttk.Button(self.attendance_frame, text="Today", command=self.set_attendance_today_date, style="Big.TButton").grid(row=1, column=2, padx=5, pady=5)
        ttk.Label(self.attendance_frame, text="Status:", font=self.label_font).grid(row=2, column=0, padx=5, pady=5)
        self.status_combobox = ttk.Combobox(self.attendance_frame, values=["Absent", "Tardy"])
        self.status_combobox.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(self.attendance_frame, text="Add Attendance", command=self.add_attendance, style="Big.TButton").grid(row=3, column=0, columnspan=2, pady=10)

        # Taxable Income Tab
        self.taxable_income_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.taxable_income_frame, text="Taxable Income")
        self.income_statement_frame = ttk.Frame(self.taxable_income_frame)
        self.income_statement_frame.pack(pady=10, fill='both', expand=True)
        self.revenue_entry = self.create_income_statement_entry("Revenue", 0)
        self.cost_of_sales_entry = self.create_income_statement_entry("Cost of Sales", 1)
        self.gross_profit_label = ttk.Label(self.income_statement_frame, text="Gross Profit: $0.00", font=self.label_font, anchor="e")
        self.gross_profit_label.grid(row=2, column=0, columnspan=2, pady=5, sticky="e")
        self.admin_expenses_entry = self.create_income_statement_entry("Administrative Expenses", 3)
        self.other_operating_expenses_entry = self.create_income_statement_entry("Other Operating Expenses", 4)
        self.operating_profit_label = ttk.Label(self.income_statement_frame, text="Operating Profit: $0.00", font=self.label_font, anchor="e")
        self.operating_profit_label.grid(row=5, column=0, columnspan=2, pady=5, sticky="e")
        self.finance_costs_entry = self.create_income_statement_entry("Finance Costs", 6)
        self.other_income_entry = self.create_income_statement_entry("Other Income", 7)
        self.profit_before_tax_label = ttk.Label(self.income_statement_frame, text="Profit Before Tax: $0.00", font=self.label_font, anchor="e")
        self.profit_before_tax_label.grid(row=8, column=0, columnspan=2, pady=5, sticky="e")
        self.tax_entry = self.create_income_statement_entry("Tax", 9)
        self.profit_after_tax_label = ttk.Label(self.income_statement_frame, text="Profit After Tax: $0.00", font=self.label_font, anchor="e")
        self.profit_after_tax_label.grid(row=10, column=0, columnspan=2, pady=5, sticky="e")
        ttk.Button(self.taxable_income_frame, text="Calculate", command=self.calculate_income_statement, style="Big.TButton").pack(pady=5)
        ttk.Button(self.taxable_income_frame, text="Import PDF", command=self.import_pdf, style="Big.TButton").pack(pady=5)
        self.analysis_text = tk.Text(self.taxable_income_frame, height=10, font=self.label_font)
        self.analysis_text.pack(pady=10, fill='both', expand=True)
        self.analysis_text.config(state='disabled')
        ttk.Label(self.taxable_income_frame, text="Total Taxable Income:", font=self.label_font).pack(pady=5)
        self.total_profit_entry = ttk.Entry(self.taxable_income_frame, justify='right')
        self.total_profit_entry.pack(pady=5)
        self.add_placeholder(self.total_profit_entry, "0.00")
        ttk.Button(self.taxable_income_frame, text="Update Total Profit", command=self.update_total_profit, style="Big.TButton").pack(pady=5)

        # Summary Tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Summary")
        self.left_frame = ttk.Frame(self.summary_frame)
        self.left_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        self.right_frame = ttk.Frame(self.summary_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.notes_display_frame = ttk.Frame(self.summary_frame)
        self.notes_display_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        # Date range selection for Summary
        self.date_range_frame = ttk.Frame(self.summary_frame)
        self.date_range_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(self.date_range_frame, text="Start Date (MM-DD-YYYY):", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.summary_start_date = ttk.Entry(self.date_range_frame)
        self.summary_start_date.grid(row=0, column=1, padx=5, pady=5)
        self.summary_start_date.bind("<KeyRelease>", self.auto_format_date)
        self.add_placeholder(self.summary_start_date, "MM-DD-YYYY")
        ttk.Label(self.date_range_frame, text="End Date (MM-DD-YYYY):", font=self.label_font).grid(row=0, column=2, padx=5, pady=5)
        self.summary_end_date = ttk.Entry(self.date_range_frame)
        self.summary_end_date.grid(row=0, column=3, padx=5, pady=5)
        self.summary_end_date.bind("<KeyRelease>", self.auto_format_date)
        self.add_placeholder(self.summary_end_date, "MM-DD-YYYY")
        ttk.Button(self.date_range_frame, text="Apply Date Range", command=self.refresh_summary, style="Big.TButton").grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(self.date_range_frame, text="Clear Date Range", command=self.clear_summary_date_range, style="Big.TButton").grid(row=0, column=5, padx=5, pady=5)
        self.summary_frame.grid_columnconfigure(1, weight=1)
        self.summary_frame.grid_rowconfigure(0, weight=1)
        self.summary_frame.grid_rowconfigure(2, weight=1)
        ttk.Button(self.left_frame, text="Refresh Summary", command=self.refresh_summary, style="Big.TButton").pack(pady=5, fill='x')
        ttk.Button(self.left_frame, text="Delete Employee", command=self.delete_employee, style="Big.TButton").pack(pady=5, fill='x')
        ttk.Button(self.left_frame, text="View Income", command=self.view_employee_income, style="Big.TButton").pack(pady=5, fill='x')
        ttk.Button(self.left_frame, text="View Notes", command=self.view_employee_notes, style="Big.TButton").pack(pady=5, fill='x')
        ttk.Button(self.left_frame, text="View Attendance", command=self.view_employee_attendance, style="Big.TButton").pack(pady=5, fill='x')
        ttk.Button(self.left_frame, text="Toggle Retirement Eligibility", command=self.toggle_eligibility, style="Big.TButton").pack(pady=5, fill='x')
        # Search in Summary
        search_frame = ttk.Frame(self.right_frame)
        search_frame.pack(pady=5, fill='x')
        ttk.Label(search_frame, text="Search:", font=self.label_font).pack(side="left", padx=5)
        self.summary_search_entry = ttk.Entry(search_frame)
        self.summary_search_entry.pack(side="left", fill='x', expand=True)
        self.summary_search_entry.bind("<KeyRelease>", self.filter_summary)
        self.tree = ttk.Treeview(self.right_frame, columns=("ID", "Name", "Department", "Total Income", "Contribution", "Eligible"), show="headings", style="Big.Treeview")
        self.tree.heading("ID", text="ID", command=lambda: self.sort_summary("ID", False))
        self.tree.heading("Name", text="Name", command=lambda: self.sort_summary("Name", False))
        self.tree.heading("Department", text="Department", command=lambda: self.sort_summary("Department", False))
        self.tree.heading("Total Income", text="Total Income", command=lambda: self.sort_summary("Total Income", False))
        self.tree.heading("Contribution", text="Contribution", command=lambda: self.sort_summary("Contribution", False))
        self.tree.heading("Eligible", text="Retirement Eligible", command=lambda: self.sort_summary("Eligible", False))
        self.tree.column("Total Income", anchor='e')
        self.tree.column("Contribution", anchor='e')
        self.tree.pack(pady=10, fill='both', expand=True)
        self.total_income_label = ttk.Label(self.right_frame, text=f"Fiscal Year {self.selected_year} Total Income: $0.00", font=self.total_label_font, anchor="w")
        self.total_income_label.pack(pady=10, fill='x')
        self.total_contribution_label = ttk.Label(self.right_frame, text=f"Fiscal Year {self.selected_year} Total Contribution: $0.00", font=self.total_label_font, anchor="w")
        self.total_contribution_label.pack(pady=10, fill='x')
        self.total_taxable_income_label = ttk.Label(self.right_frame, text=f"Fiscal Year {self.selected_year} Total Taxable Income: $0.00", font=self.total_label_font, anchor="w")
        self.total_taxable_income_label.pack(pady=10, fill='x')
        self.total_spend_label = ttk.Label(self.right_frame, text=f"Fiscal Year {self.selected_year} Total Spend: $0.00", font=self.total_label_font, anchor="w")
        self.total_spend_label.pack(pady=10, fill='x')
        # Notes section in Summary Tab
        ttk.Label(self.notes_display_frame, text="Employee Notes:", font=self.total_label_font).pack(pady=5)
        self.notes_text = tk.Text(self.notes_display_frame, height=10, font=self.label_font)
        self.notes_text.pack(pady=10, fill='both', expand=True)
        self.notes_text.config(state='disabled')

        # Scenarios Tab
        self.scenarios_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.scenarios_frame, text="Scenarios")
        self.scenarios_left_frame = ttk.Frame(self.scenarios_frame)
        self.scenarios_left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.scenarios_right_frame = ttk.Frame(self.scenarios_frame)
        self.scenarios_right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        # Date range selection for Scenarios
        self.scenarios_date_range_frame = ttk.Frame(self.scenarios_frame)
        self.scenarios_date_range_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ttk.Label(self.scenarios_date_range_frame, text="Start Date (MM-DD-YYYY):", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.scenarios_start_date = ttk.Entry(self.scenarios_date_range_frame)
        self.scenarios_start_date.grid(row=0, column=1, padx=5, pady=5)
        self.scenarios_start_date.bind("<KeyRelease>", self.auto_format_date)
        self.add_placeholder(self.scenarios_start_date, "MM-DD-YYYY")
        ttk.Label(self.scenarios_date_range_frame, text="End Date (MM-DD-YYYY):", font=self.label_font).grid(row=0, column=2, padx=5, pady=5)
        self.scenarios_end_date = ttk.Entry(self.scenarios_date_range_frame)
        self.scenarios_end_date.grid(row=0, column=3, padx=5, pady=5)
        self.scenarios_end_date.bind("<KeyRelease>", self.auto_format_date)
        self.add_placeholder(self.scenarios_end_date, "MM-DD-YYYY")
        ttk.Button(self.scenarios_date_range_frame, text="Apply Date Range", command=self.refresh_scenarios, style="Big.TButton").grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(self.scenarios_date_range_frame, text="Clear Date Range", command=self.clear_scenarios_date_range, style="Big.TButton").grid(row=0, column=5, padx=5, pady=5)
        self.scenarios_frame.grid_columnconfigure(0, weight=1)
        self.scenarios_frame.grid_columnconfigure(1, weight=1)
        self.scenarios_frame.grid_rowconfigure(0, weight=1)
        # Actual Summary Table
        ttk.Label(self.scenarios_left_frame, text="Actual Summary", font=self.total_label_font).pack(pady=5)
        actual_search_frame = ttk.Frame(self.scenarios_left_frame)
        actual_search_frame.pack(pady=5, fill='x')
        ttk.Label(actual_search_frame, text="Search:", font=self.label_font).pack(side="left", padx=5)
        self.actual_search_entry = ttk.Entry(actual_search_frame)
        self.actual_search_entry.pack(side="left", fill='x', expand=True)
        self.actual_search_entry.bind("<KeyRelease>", self.filter_actual)
        self.actual_tree = ttk.Treeview(self.scenarios_left_frame, columns=("ID", "Name", "Department", "Total Income", "Contribution", "Eligible"), show="headings", style="Big.Treeview")
        self.actual_tree.heading("ID", text="ID", command=lambda: self.sort_actual("ID", False))
        self.actual_tree.heading("Name", text="Name", command=lambda: self.sort_actual("Name", False))
        self.actual_tree.heading("Department", text="Department", command=lambda: self.sort_actual("Department", False))
        self.actual_tree.heading("Total Income", text="Total Income", command=lambda: self.sort_actual("Total Income", False))
        self.actual_tree.heading("Contribution", text="Contribution", command=lambda: self.sort_actual("Contribution", False))
        self.actual_tree.heading("Eligible", text="Eligible", command=lambda: self.sort_actual("Eligible", False))
        self.actual_tree.column("Total Income", anchor='e')
        self.actual_tree.column("Contribution", anchor='e')
        self.actual_tree.pack(pady=10, fill='both', expand=True)
        # Hypothetical Summary Table
        ttk.Label(self.scenarios_right_frame, text="Hypothetical Summary", font=self.total_label_font).pack(pady=5)
        hypothetical_search_frame = ttk.Frame(self.scenarios_right_frame)
        hypothetical_search_frame.pack(pady=5, fill='x')
        ttk.Label(hypothetical_search_frame, text="Search:", font=self.label_font).pack(side="left", padx=5)
        self.hypothetical_search_entry = ttk.Entry(hypothetical_search_frame)
        self.hypothetical_search_entry.pack(side="left", fill='x', expand=True)
        self.hypothetical_search_entry.bind("<KeyRelease>", self.filter_hypothetical)
        self.hypothetical_tree = ttk.Treeview(self.scenarios_right_frame, columns=("ID", "Name", "Department", "Total Income", "Contribution", "Eligible"), show="headings", style="Big.Treeview")
        self.hypothetical_tree.heading("ID", text="ID", command=lambda: self.sort_hypothetical("ID", False))
        self.hypothetical_tree.heading("Name", text="Name", command=lambda: self.sort_hypothetical("Name", False))
        self.hypothetical_tree.heading("Department", text="Department", command=lambda: self.sort_hypothetical("Department", False))
        self.hypothetical_tree.heading("Total Income", text="Total Income", command=lambda: self.sort_hypothetical("Total Income", False))
        self.hypothetical_tree.heading("Contribution", text="Contribution", command=lambda: self.sort_hypothetical("Contribution", False))
        self.hypothetical_tree.heading("Eligible", text="Eligible", command=lambda: self.sort_hypothetical("Eligible", False))
        self.hypothetical_tree.column("Total Income", anchor='e')
        self.hypothetical_tree.column("Contribution", anchor='e')
        self.hypothetical_tree.pack(pady=10, fill='both', expand=True)
        # Differences Text
        self.differences_text = tk.Text(self.scenarios_frame, height=10, font=self.label_font)
        self.differences_text.grid(row=2, column=0, columnspan=2, pady=10, padx=10, sticky="nsew")
        self.scenarios_frame.grid_rowconfigure(2, weight=0)
        # Refresh Button
        ttk.Button(self.scenarios_frame, text="Refresh Comparison", command=self.refresh_scenarios, style="Big.TButton").grid(row=3, column=0, columnspan=2, pady=10)
        # Bind double-click for editing hypothetical table
        self.hypothetical_tree.bind("<Double-1>", self.edit_hypothetical)

        # Compare Tab
        self.compare_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.compare_frame, text="Compare")
        self.compare_left_frame = ttk.Frame(self.compare_frame)
        self.compare_left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.compare_right_frame = ttk.Frame(self.compare_frame)
        self.compare_right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.compare_frame.grid_columnconfigure(0, weight=1)
        self.compare_frame.grid_columnconfigure(1, weight=1)
        self.compare_frame.grid_rowconfigure(0, weight=1)
        # Employee 1 selection
        ttk.Label(self.compare_left_frame, text="Employee 1:", font=self.label_font).pack(pady=5)
        self.employee1_combobox = ttk.Combobox(self.compare_left_frame)
        self.employee1_combobox.pack(pady=5, fill='x')
        # Employee 2 selection
        ttk.Label(self.compare_right_frame, text="Employee 2:", font=self.label_font).pack(pady=5)
        self.employee2_combobox = ttk.Combobox(self.compare_right_frame)
        self.employee2_combobox.pack(pady=5, fill='x')
        # Labels for comparison
        self.employee1_info = ttk.Label(self.compare_left_frame, text="Select an employee", font=self.compare_label_font, anchor="center")
        self.employee1_info.pack(pady=10, fill='x')
        self.employee2_info = ttk.Label(self.compare_right_frame, text="Select an employee", font=self.compare_label_font, anchor="center")
        self.employee2_info.pack(pady=10, fill='x')
        # Refresh button
        ttk.Button(self.compare_frame, text="Refresh Comparison", command=self.refresh_compare, style="Big.TButton").grid(row=1, column=0, columnspan=2, pady=10)

        # Settings Tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        ttk.Label(self.settings_frame, text="Contribution Percentage:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.percentage_entry = ttk.Entry(self.settings_frame, justify='right')
        self.percentage_entry.insert(0, str(self.contribution_percentage))
        self.percentage_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.settings_frame, text="Select Year:", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        self.year_combobox = ttk.Combobox(self.settings_frame, values=[str(y) for y in range(2020, 2031)])
        self.year_combobox.set(str(self.selected_year))
        self.year_combobox.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(self.settings_frame, text="Privacy Mode:", font=self.label_font).grid(row=2, column=0, padx=5, pady=5)
        self.privacy_var = tk.IntVar(value=self.privacy_mode)
        self.privacy_check = ttk.Checkbutton(self.settings_frame, text="Blur Employee Names", variable=self.privacy_var)
        self.privacy_check.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(self.settings_frame, text="Update Settings", command=self.update_settings, style="Big.TButton").grid(row=3, column=0, columnspan=2, pady=10)

        # Configure styles
        style = ttk.Style()
        style.configure("Big.TButton", font=self.button_font)
        style.configure("Big.Treeview", font=self.tree_font)
        style.configure("Big.Treeview.Heading", font=self.label_font)

        # Initialize comboboxes after all tabs are created
        self.update_employee_combobox()
        self.update_notes_combobox()
        self.update_attendance_combobox()
        self.update_compare_comboboxes()
        self.refresh_summary()

    def set_today_date(self):
        today = datetime.now().strftime("%m-%d-%Y")
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, today)
        self.date_entry.config(foreground="black")

    def set_note_today_date(self):
        today = datetime.now().strftime("%m-%d-%Y")
        self.note_date_entry.delete(0, tk.END)
        self.note_date_entry.insert(0, today)
        self.note_date_entry.config(foreground="black")

    def set_attendance_today_date(self):
        today = datetime.now().strftime("%m-%d-%Y")
        self.attendance_date_entry.delete(0, tk.END)
        self.attendance_date_entry.insert(0, today)
        self.attendance_date_entry.config(foreground="black")

    def auto_format_date(self, event):
        text = event.widget.get().replace("-", "")
        if len(text) == 8 and text.isdigit():
            formatted = f"{text[:2]}-{text[2:4]}-{text[4:]}"
            event.widget.delete(0, tk.END)
            event.widget.insert(0, formatted)
            event.widget.config(foreground="black")

    def clear_summary_date_range(self):
        self.summary_start_date.delete(0, tk.END)
        self.summary_end_date.delete(0, tk.END)
        self.add_placeholder(self.summary_start_date, "MM-DD-YYYY")
        self.add_placeholder(self.summary_end_date, "MM-DD-YYYY")
        self.refresh_summary()

    def clear_scenarios_date_range(self):
        self.scenarios_start_date.delete(0, tk.END)
        self.scenarios_end_date.delete(0, tk.END)
        self.add_placeholder(self.scenarios_start_date, "MM-DD-YYYY")
        self.add_placeholder(self.scenarios_end_date, "MM-DD-YYYY")
        self.refresh_scenarios()

    def update_employee_combobox(self):
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        self.employee_combobox["values"] = [f"{id}: {self.blur_name(name)}" for id, name in employees]
        if employees:
            self.employee_combobox.current(0)

    def update_notes_combobox(self):
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        self.notes_employee_combobox["values"] = [f"{id}: {self.blur_name(name)}" for id, name in employees]
        if employees:
            self.notes_employee_combobox.current(0)

    def update_attendance_combobox(self):
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        self.attendance_employee_combobox["values"] = [f"{id}: {self.blur_name(name)}" for id, name in employees]
        if employees:
            self.attendance_employee_combobox.current(0)

    def update_compare_comboboxes(self):
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        employee_values = [f"{id}: {self.blur_name(name)}" for id, name in employees]
        self.employee1_combobox["values"] = employee_values
        self.employee2_combobox["values"] = employee_values
        if employees:
            self.employee1_combobox.current(0) if len(employees) > 0 else None
            self.employee2_combobox.current(1 if len(employees) > 1 else 0) if employee_values else None
        self.refresh_compare()

    def add_employee(self):
        name = self.name_entry.get()
        if name == "John Doe":
            name = ""
        department = self.dept_combobox.get()
        eligible = self.eligible_var.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        self.cursor.execute("INSERT INTO employees (name, department, eligible_for_retirement) VALUES (?, ?, ?)", 
                          (name, department, eligible))
        self.conn.commit()
        self.name_entry.delete(0, tk.END)
        self.add_placeholder(self.name_entry, "John Doe")
        self.dept_combobox.set("")
        self.eligible_var.set(0)
        self.update_employee_combobox()
        self.update_notes_combobox()
        self.update_attendance_combobox()
        self.update_compare_comboboxes()
        self.refresh_summary()
        self.refresh_scenarios()
        messagebox.showinfo("Success", "Employee added")

    def add_income(self):
        employee_str = self.employee_combobox.get()
        if not employee_str:
            messagebox.showerror("Error", "Select an employee")
            return
        employee_id = int(employee_str.split(":")[0])
        try:
            amount_str = self.amount_entry.get()
            if amount_str == "0.00":
                raise ValueError("Amount must be positive")
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            date = self.date_entry.get()
            if date == "MM-DD-YYYY":
                date = ""
            type_ = self.type_combobox.get()
            if not amount or not date or not type_:
                messagebox.showerror("Error", "All fields are required")
                return
            parsed_date = datetime.strptime(date, "%m-%d-%Y")
            db_date = parsed_date.strftime("%Y-%m-%d")
        except ValueError as e:
            messagebox.showerror("Error", str(e) or "Invalid amount or date format (use MM-DD-YYYY)")
            return
        self.cursor.execute(
            "INSERT INTO income (employee_id, amount, date, type) VALUES (?, ?, ?, ?)",
            (employee_id, amount, db_date, type_)
        )
        self.conn.commit()
        self.amount_entry.delete(0, tk.END)
        self.add_placeholder(self.amount_entry, "0.00")
        self.date_entry.delete(0, tk.END)
        self.add_placeholder(self.date_entry, "MM-DD-YYYY")
        self.type_combobox.set("")
        self.refresh_summary()
        self.refresh_scenarios()
        self.refresh_compare()
        messagebox.showinfo("Success", "Income added")

    def add_note(self):
        employee_str = self.notes_employee_combobox.get()
        if not employee_str:
            messagebox.showerror("Error", "Select an employee")
            return
        employee_id = int(employee_str.split(":")[0])
        note_text = self.note_entry.get()
        if note_text == "Enter note here":
            note_text = ""
        date = self.note_date_entry.get()
        if date == "MM-DD-YYYY":
            date = ""
        if not note_text or not date:
            messagebox.showerror("Error", "Note and date are required")
            return
        try:
            parsed_date = datetime.strptime(date, "%m-%d-%Y")
            db_date = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format (use MM-DD-YYYY)")
            return
        self.cursor.execute(
            "INSERT INTO notes (employee_id, note_text, date) VALUES (?, ?, ?)",
            (employee_id, note_text, db_date)
        )
        self.conn.commit()
        self.note_entry.delete(0, tk.END)
        self.add_placeholder(self.note_entry, "Enter note here")
        self.note_date_entry.delete(0, tk.END)
        self.add_placeholder(self.note_date_entry, "MM-DD-YYYY")
        self.update_notes_display()
        self.refresh_summary()
        messagebox.showinfo("Success", "Note added")

    def add_attendance(self):
        employee_str = self.attendance_employee_combobox.get()
        if not employee_str:
            messagebox.showerror("Error", "Select an employee")
            return
        employee_id = int(employee_str.split(":")[0])
        date = self.attendance_date_entry.get()
        if date == "MM-DD-YYYY":
            date = ""
        status = self.status_combobox.get()
        if not date or not status:
            messagebox.showerror("Error", "Date and status are required")
            return
        try:
            parsed_date = datetime.strptime(date, "%m-%d-%Y")
            db_date = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid date format (use MM-DD-YYYY)")
            return
        self.cursor.execute(
            "INSERT INTO attendance (employee_id, date, status) VALUES (?, ?, ?)",
            (employee_id, db_date, status)
        )
        self.conn.commit()
        self.attendance_date_entry.delete(0, tk.END)
        self.add_placeholder(self.attendance_date_entry, "MM-DD-YYYY")
        self.status_combobox.set("")
        self.refresh_compare()
        messagebox.showinfo("Success", "Attendance record added")

    def update_total_profit(self):
        try:
            total_profit_str = self.total_profit_entry.get()
            if total_profit_str == "0.00":
                total_profit = 0.0
            else:
                total_profit = float(total_profit_str)
            if total_profit < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid profit amount (must be a non-negative number)")
            return
        self.cursor.execute("SELECT COUNT(*) FROM taxable_income WHERE year = ?", (self.selected_year,))
        if self.cursor.fetchone()[0] > 0:
            self.cursor.execute("UPDATE taxable_income SET total_profit = ? WHERE year = ?", (total_profit, self.selected_year))
        else:
            self.cursor.execute("INSERT INTO taxable_income (year, total_profit) VALUES (?, ?)", (self.selected_year, total_profit))
        self.conn.commit()
        self.refresh_summary()
        messagebox.showinfo("Success", "Total profit updated")

    def toggle_eligibility(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an employee to toggle eligibility")
            return
        employee_id = self.tree.item(selected_item)["values"][0]
        self.cursor.execute("SELECT eligible_for_retirement FROM employees WHERE employee_id = ?", (employee_id,))
        current_status = self.cursor.fetchone()[0]
        new_status = 1 if current_status == 0 else 0
        self.cursor.execute("UPDATE employees SET eligible_for_retirement = ? WHERE employee_id = ?", (new_status, employee_id))
        self.conn.commit()
        self.refresh_summary()
        self.refresh_scenarios()
        self.refresh_compare()
        messagebox.showinfo("Success", f"Retirement eligibility {'enabled' if new_status else 'disabled'}")

    def sort_summary(self, col, descending):
        # Sort the summary_rows
        def get_key(row):
            val = row[self.tree['columns'].index(col)]
            if col in ["Total Income", "Contribution"]:
                val = val.replace(",", "").replace("$", "").replace("(", "-").replace(")", "")
                return float(val)
            elif col == "ID":
                return int(val)
            else:
                return val.lower()
        self.summary_rows.sort(key=get_key, reverse=descending)
        self.display_summary_rows()
        # Update heading command to reverse sort
        self.tree.heading(col, command=lambda: self.sort_summary(col, not descending))

    def filter_summary(self, event=None):
        self.display_summary_rows()

    def display_summary_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        query = self.summary_search_entry.get().lower()
        for row in self.summary_rows:
            if query in row[1].lower() or query in row[2].lower():
                self.tree.insert("", tk.END, values=row)

    def refresh_summary(self):
        total_profit = self.get_total_profit()
        start_date = self.summary_start_date.get()
        if start_date == "MM-DD-YYYY":
            start_date = ""
        end_date = self.summary_end_date.get()
        if end_date == "MM-DD-YYYY":
            end_date = ""
        if start_date and end_date:
            valid, result = self.validate_date_range(start_date, end_date)
            if not valid:
                messagebox.showerror("Error", result)
                return
            start_db, end_db = result
            period_label = f"{start_date} to {end_date}"
        else:
            start_db, end_db = self.fiscal_year_start, self.fiscal_year_end
            period_label = f"Fiscal Year {self.selected_year}"
        self.cursor.execute("""
            SELECT e.employee_id, e.name, e.department, COALESCE(SUM(i.amount), 0) as total_income, e.eligible_for_retirement
            FROM employees e
            LEFT JOIN income i ON e.employee_id = i.employee_id
            WHERE i.date BETWEEN ? AND ? OR i.date IS NULL
            GROUP BY e.employee_id
        """, (start_db, end_db))
        total_income = 0
        total_contribution = 0
        rows = self.cursor.fetchall()
        self.summary_rows = []
        for row in rows:
            contribution = row[3] * (self.contribution_percentage / 100) if row[4] else 0
            blurred_name = self.blur_name(row[1])
            eligible_status = "Yes" if row[4] else "No"
            self.summary_rows.append((row[0], blurred_name, row[2], self.format_currency(row[3]), self.format_currency(contribution), eligible_status))
            total_income += row[3]
            if row[4]:
                total_contribution += contribution
        total_spend = total_income + total_contribution - total_profit
        self.total_income_label.config(text=f"{period_label} Total Income: {self.format_currency(total_income)}")
        self.total_contribution_label.config(text=f"{period_label} Total Contribution: {self.format_currency(total_contribution)}")
        self.total_taxable_income_label.config(text=f"{period_label} Total Taxable Income: {self.format_currency(total_profit)}")
        self.total_spend_label.config(text=f"{period_label} Total Spend: {self.format_currency(total_spend)}")
        self.display_summary_rows()
        # Update notes display when an employee is selected
        self.tree.bind('<<TreeviewSelect>>', self.update_notes_display)

    def update_notes_display(self, event=None):
        self.notes_text.config(state='normal')
        self.notes_text.delete(1.0, tk.END)
        selected_item = self.tree.selection()
        if selected_item:
            employee_id = self.tree.item(selected_item)["values"][0]
            self.cursor.execute("SELECT date, note_text FROM notes WHERE employee_id = ? ORDER BY date DESC", (employee_id,))
            notes = self.cursor.fetchall()
            if notes:
                for date, note_text in notes:
                    display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%m-%d-%Y")
                    self.notes_text.insert(tk.END, f"{display_date}: {note_text}\n\n")
            else:
                self.notes_text.insert(tk.END, "No notes available for this employee.")
        else:
            self.notes_text.insert(tk.END, "Select an employee to view notes.")
        self.notes_text.config(state='disabled')

    def sort_actual(self, col, descending):
        def get_key(row):
            val = row[self.actual_tree['columns'].index(col)]
            if col in ["Total Income", "Contribution"]:
                val = val.replace(",", "").replace("$", "").replace("(", "-").replace(")", "")
                return float(val)
            elif col == "ID":
                return int(val)
            else:
                return val.lower()
        self.actual_rows.sort(key=get_key, reverse=descending)
        self.display_actual_rows()
        self.actual_tree.heading(col, command=lambda: self.sort_actual(col, not descending))

    def filter_actual(self, event=None):
        self.display_actual_rows()

    def display_actual_rows(self):
        for item in self.actual_tree.get_children():
            self.actual_tree.delete(item)
        query = self.actual_search_entry.get().lower()
        for row in self.actual_rows:
            if query in row[1].lower() or query in row[2].lower():
                self.actual_tree.insert("", tk.END, values=row)

    def sort_hypothetical(self, col, descending):
        def get_key(row):
            val = row[self.hypothetical_tree['columns'].index(col)]
            if col in ["Total Income", "Contribution"]:
                val = val.replace(",", "").replace("$", "").replace("(", "-").replace(")", "")
                return float(val)
            elif col == "ID":
                return int(val)
            else:
                return val.lower()
        self.hypothetical_rows.sort(key=get_key, reverse=descending)
        self.display_hypothetical_rows()
        self.hypothetical_tree.heading(col, command=lambda: self.sort_hypothetical(col, not descending))

    def filter_hypothetical(self, event=None):
        self.display_hypothetical_rows()

    def display_hypothetical_rows(self):
        for item in self.hypothetical_tree.get_children():
            self.hypothetical_tree.delete(item)
        query = self.hypothetical_search_entry.get().lower()
        for row in self.hypothetical_rows:
            if query in row[1].lower() or query in row[2].lower():
                self.hypothetical_tree.insert("", tk.END, values=row)

    def edit_hypothetical(self, event):
        selected_item = self.hypothetical_tree.selection()
        if not selected_item:
            return
        item = self.hypothetical_tree.item(selected_item)
        employee_id = item["values"][0]
        column = self.hypothetical_tree.identify_column(event.x)
        col_index = int(column.replace("#", "")) - 1
        if col_index not in [3, 4, 5]:  # Only allow editing Total Income, Contribution, Eligible
            return
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Hypothetical Data")
        edit_window.geometry("300x150")
        ttk.Label(edit_window, text="New Value:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        if col_index == 5:  # Eligible column
            eligible_var = tk.StringVar(value=item["values"][col_index])
            ttk.Radiobutton(edit_window, text="Yes", value="Yes", variable=eligible_var).grid(row=0, column=1, padx=5, pady=5)
            ttk.Radiobutton(edit_window, text="No", value="No", variable=eligible_var).grid(row=1, column=1, padx=5, pady=5)
        else:
            entry = ttk.Entry(edit_window, justify='right')
            entry.grid(row=0, column=1, padx=5, pady=5)
            entry.insert(0, item["values"][col_index].replace("$", "").replace(",", "").replace("(", "").replace(")", ""))
        def save_edit():
            try:
                if col_index == 3:  # Total Income
                    new_value = float(entry.get())
                    if new_value < 0:
                        raise ValueError
                    eligible = self.hypothetical_data.get(employee_id, (0, 0, False))[2]
                    contribution = new_value * (self.contribution_percentage / 100) if eligible else self.hypothetical_data.get(employee_id, (0, 0, False))[1]
                    self.hypothetical_data[employee_id] = (new_value, contribution, eligible)
                elif col_index == 4:  # Contribution
                    new_value = float(entry.get())
                    if new_value < 0:
                        raise ValueError
                    eligible = self.hypothetical_data.get(employee_id, (0, 0, False))[2]
                    income = new_value / (self.contribution_percentage / 100) if eligible and self.contribution_percentage != 0 else self.hypothetical_data.get(employee_id, (0, 0, False))[0]
                    self.hypothetical_data[employee_id] = (income, new_value, eligible)
                elif col_index == 5:  # Eligible
                    new_value = eligible_var.get() == "Yes"
                    income = self.hypothetical_data.get(employee_id, (0, 0, False))[0]
                    contribution = income * (self.contribution_percentage / 100) if new_value else 0
                    self.hypothetical_data[employee_id] = (income, contribution, new_value)
                self.refresh_scenarios()
                edit_window.destroy()
            except ValueError:
                messagebox.showerror("Error", "Invalid input (must be a non-negative number for income/contribution)")
        ttk.Button(edit_window, text="Save", command=save_edit, style="Big.TButton").grid(row=2, column=0, columnspan=2, pady=10)

    def refresh_scenarios(self):
        # Clear tables
        for item in self.actual_tree.get_children():
            self.actual_tree.delete(item)
        for item in self.hypothetical_tree.get_children():
            self.hypothetical_tree.delete(item)
        self.differences_text.delete(1.0, tk.END)
        # Determine date range
        start_date = self.scenarios_start_date.get()
        if start_date == "MM-DD-YYYY":
            start_date = ""
        end_date = self.scenarios_end_date.get()
        if end_date == "MM-DD-YYYY":
            end_date = ""
        if start_date and end_date:
            valid, result = self.validate_date_range(start_date, end_date)
            if not valid:
                messagebox.showerror("Error", result)
                return
            start_db, end_db = result
            period_label = f"{start_date} to {end_date}"
        else:
            start_db, end_db = self.fiscal_year_start, self.fiscal_year_end
            period_label = f"Fiscal Year {self.selected_year}"
        # Populate actual table
        self.cursor.execute("""
            SELECT e.employee_id, e.name, e.department, COALESCE(SUM(i.amount), 0) as total_income, e.eligible_for_retirement
            FROM employees e
            LEFT JOIN income i ON e.employee_id = i.employee_id
            WHERE i.date BETWEEN ? AND ? OR i.date IS NULL
            GROUP BY e.employee_id
        """, (start_db, end_db))
        actual_data = {}
        differences = []
        self.actual_rows = []
        for row in self.cursor.fetchall():
            employee_id, name, department, total_income, eligible = row
            contribution = total_income * (self.contribution_percentage / 100) if eligible else 0
            actual_data[employee_id] = (total_income, contribution, eligible)
            blurred_name = self.blur_name(name)
            eligible_status = "Yes" if eligible else "No"
            self.actual_rows.append((employee_id, blurred_name, department, self.format_currency(total_income), self.format_currency(contribution), eligible_status))
            # Initialize hypothetical data if not already set
            if employee_id not in self.hypothetical_data:
                self.hypothetical_data[employee_id] = (total_income, contribution, bool(eligible))
        self.display_actual_rows()
        # Populate hypothetical table
        self.hypothetical_rows = []
        for employee_id, (total_income, contribution, eligible) in self.hypothetical_data.items():
            self.cursor.execute("SELECT name, department FROM employees WHERE employee_id = ?", (employee_id,))
            result = self.cursor.fetchone()
            if result:
                name, department = result
                blurred_name = self.blur_name(name)
                eligible_status = "Yes" if eligible else "No"
                self.hypothetical_rows.append((employee_id, blurred_name, department, self.format_currency(total_income), self.format_currency(contribution), eligible_status))
        self.display_hypothetical_rows()
        # Calculate differences
        for employee_id, (hyp_income, hyp_contribution, hyp_eligible) in self.hypothetical_data.items():
            if employee_id in actual_data:
                act_income, act_contribution, act_eligible = actual_data[employee_id]
                self.cursor.execute("SELECT name FROM employees WHERE employee_id = ?", (employee_id,))
                name = self.cursor.fetchone()[0]
                blurred_name = self.blur_name(name)
                if hyp_income != act_income:
                    differences.append(f"{blurred_name}: Change Total Income from {self.format_currency(act_income)} to {self.format_currency(hyp_income)}")
                if hyp_contribution != act_contribution:
                    differences.append(f"{blurred_name}: Change Contribution from {self.format_currency(act_contribution)} to {self.format_currency(hyp_contribution)}")
                if hyp_eligible != act_eligible:
                    differences.append(f"{blurred_name}: Change Retirement Eligibility from {'Yes' if act_eligible else 'No'} to {'Yes' if hyp_eligible else 'No'}")
        # Display differences
        if differences:
            self.differences_text.insert(tk.END, f"Changes needed to achieve hypothetical scenario for {period_label}:\n" + "\n".join(differences))
        else:
            self.differences_text.insert(tk.END, f"No differences between actual and hypothetical scenarios for {period_label}.")

    def refresh_compare(self):
        employee1_str = self.employee1_combobox.get()
        employee2_str = self.employee2_combobox.get()
        
        def get_employee_info(employee_str):
            if not employee_str:
                return "Select an employee", 0, 0, False, "", 0, 0
            try:
                employee_id = int(employee_str.split(":")[0])
                self.cursor.execute("""
                    SELECT e.name, COALESCE(SUM(i.amount), 0), e.eligible_for_retirement, e.department
                    FROM employees e
                    LEFT JOIN income i ON e.employee_id = i.employee_id
                    WHERE e.employee_id = ? AND (i.date BETWEEN ? AND ? OR i.date IS NULL)
                    GROUP BY e.employee_id
                """, (employee_id, self.fiscal_year_start, self.fiscal_year_end))
                result = self.cursor.fetchone()
                # Count absences and tardies
                self.cursor.execute("""
                    SELECT COUNT(*) FROM attendance 
                    WHERE employee_id = ? AND status = 'Absent' AND date BETWEEN ? AND ?
                """, (employee_id, self.fiscal_year_start, self.fiscal_year_end))
                absences = self.cursor.fetchone()[0]
                self.cursor.execute("""
                    SELECT COUNT(*) FROM attendance 
                    WHERE employee_id = ? AND status = 'Tardy' AND date BETWEEN ? AND ?
                """, (employee_id, self.fiscal_year_start, self.fiscal_year_end))
                tardies = self.cursor.fetchone()[0]
                if result:
                    name, total_income, eligible, department = result
                    contribution = total_income * (self.contribution_percentage / 100) if eligible else 0
                    return name, total_income, contribution, eligible, department, absences, tardies
                return "Employee not found", 0, 0, False, "", 0, 0
            except:
                return "Select an employee", 0, 0, False, "", 0, 0

        name1, income1, contrib1, eligible1, dept1, absences1, tardies1 = get_employee_info(employee1_str)
        name2, income2, contrib2, eligible2, dept2, absences2, tardies2 = get_employee_info(employee2_str)
        
        self.employee1_info.config(text=f"Name: {self.blur_name(name1)}\n"
                                      f"Department: {dept1}\n"
                                      f"Total Income: {self.format_currency(income1)}\n"
                                      f"Contribution: {self.format_currency(contrib1)}\n"
                                      f"Eligible: {'Yes' if eligible1 else 'No'}\n"
                                      f"Absences: {absences1}\n"
                                      f"Tardies: {tardies1}",
                                 font=self.compare_label_font)
        self.employee2_info.config(text=f"Name: {self.blur_name(name2)}\n"
                                      f"Department: {dept2}\n"
                                      f"Total Income: {self.format_currency(income2)}\n"
                                      f"Contribution: {self.format_currency(contrib2)}\n"
                                      f"Eligible: {'Yes' if eligible2 else 'No'}\n"
                                      f"Absences: {absences2}\n"
                                      f"Tardies: {tardies2}",
                                 font=self.compare_label_font)

    def delete_employee(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        employee_id = self.tree.item(selected_item)["values"][0]
        if messagebox.askyesno("Confirm", "Delete this employee, their income records, notes, and attendance records?"):
            self.cursor.execute("DELETE FROM income WHERE employee_id = ?", (employee_id,))
            self.cursor.execute("DELETE FROM notes WHERE employee_id = ?", (employee_id,))
            self.cursor.execute("DELETE FROM attendance WHERE employee_id = ?", (employee_id,))
            self.cursor.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
            self.hypothetical_data.pop(employee_id, None)
            self.conn.commit()
            self.refresh_summary()
            self.update_employee_combobox()
            self.update_notes_combobox()
            self.update_attendance_combobox()
            self.update_compare_comboboxes()
            self.refresh_scenarios()
            messagebox.showinfo("Success", "Employee deleted")

    def update_settings(self):
        try:
            new_percentage = float(self.percentage_entry.get())
            new_year = int(self.year_combobox.get())
            if new_percentage < 0 or new_year < 1900 or new_year > 2100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid percentage or year")
            return
        new_privacy_mode = self.privacy_var.get()
        self.set_fiscal_year(new_year)
        self.cursor.execute(
            "UPDATE settings SET contribution_percentage = ?, selected_year = ?, fiscal_year_start = ?, fiscal_year_end = ?, privacy_mode = ? WHERE setting_id = 1",
            (new_percentage, new_year, self.fiscal_year_start, self.fiscal_year_end, new_privacy_mode)
        )
        self.conn.commit()
        self.contribution_percentage = new_percentage
        self.selected_year = new_year
        self.privacy_mode = new_privacy_mode
        self.hypothetical_data.clear()  # Reset hypothetical data on settings change
        self.total_profit_entry.delete(0, tk.END)
        self.total_profit_entry.insert(0, str(self.get_total_profit()))
        self.refresh_summary()
        self.update_employee_combobox()
        self.update_notes_combobox()
        self.update_attendance_combobox()
        self.update_compare_comboboxes()
        self.refresh_scenarios()
        messagebox.showinfo("Success", "Settings updated")

    def view_employee_income(self):
        income_window = tk.Toplevel(self.root)
        income_window.title("Employee Income Records")
        income_window.geometry("600x400")
        ttk.Label(income_window, text="Select Employee:", font=self.label_font).pack(pady=5)
        income_employee_combobox = ttk.Combobox(income_window)
        income_employee_combobox.pack(pady=5)
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        income_employee_combobox["values"] = [f"{id}: {self.blur_name(name)}" for id, name in employees]
        if employees:
            selected_item = self.tree.selection()
            if selected_item:
                employee_id = self.tree.item(selected_item)["values"][0]
                for i, (id, name) in enumerate(employees):
                    if id == employee_id:
                        income_employee_combobox.current(i)
                        break
            else:
                income_employee_combobox.current(0)
        income_tree = ttk.Treeview(income_window, columns=("Income ID", "Date", "Amount", "Type"), show="headings", style="Big.Treeview")
        income_tree.heading("Income ID", text="ID")
        income_tree.heading("Date", text="Date")
        income_tree.heading("Amount", text="Amount")
        income_tree.heading("Type", text="Type")
        income_tree.column("Amount", anchor='e')
        income_tree.pack(pady=10, fill='both', expand=True)
        def update_income_table(event=None):
            for item in income_tree.get_children():
                income_tree.delete(item)
            employee_str = income_employee_combobox.get()
            if not employee_str:
                return
            employee_id = int(employee_str.split(":")[0])
            self.cursor.execute(
                "SELECT income_id, date, amount, type FROM income WHERE employee_id = ? ORDER BY date ASC",
                (employee_id,)
            )
            for row in self.cursor.fetchall():
                db_date = row[1]
                display_date = datetime.strptime(db_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                income_tree.insert("", tk.END, values=(row[0], display_date, self.format_currency(row[2]), row[3]))
        ttk.Button(income_window, text="Edit Selected Income", command=lambda: self.edit_income(income_tree, income_employee_combobox, update_income_table), style="Big.TButton").pack(pady=5)
        ttk.Button(income_window, text="Delete Selected Income", command=lambda: self.delete_income(income_tree, update_income_table), style="Big.TButton").pack(pady=5)
        income_employee_combobox.bind("<<ComboboxSelected>>", update_income_table)
        update_income_table()

    def delete_income(self, tree, update_func):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an income record to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete this income record?"):
            return
        income_id = tree.item(selected_item)["values"][0]
        self.cursor.execute("DELETE FROM income WHERE income_id = ?", (income_id,))
        self.conn.commit()
        update_func()
        self.refresh_summary()
        self.refresh_scenarios()
        self.refresh_compare()
        messagebox.showinfo("Success", "Income record deleted")

    def view_employee_notes(self):
        notes_window = tk.Toplevel(self.root)
        notes_window.title("Employee Notes")
        notes_window.geometry("600x400")
        ttk.Label(notes_window, text="Select Employee:", font=self.label_font).pack(pady=5)
        notes_employee_combobox = ttk.Combobox(notes_window)
        notes_employee_combobox.pack(pady=5)
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        notes_employee_combobox["values"] = [f"{id}: {self.blur_name(name)}" for id, name in employees]
        if employees:
            selected_item = self.tree.selection()
            if selected_item:
                employee_id = self.tree.item(selected_item)["values"][0]
                for i, (id, name) in enumerate(employees):
                    if id == employee_id:
                        notes_employee_combobox.current(i)
                        break
            else:
                notes_employee_combobox.current(0)
        notes_tree = ttk.Treeview(notes_window, columns=("Note ID", "Date", "Note"), show="headings", style="Big.Treeview")
        notes_tree.heading("Note ID", text="ID")
        notes_tree.heading("Date", text="Date")
        notes_tree.heading("Note", text="Note")
        notes_tree.column("Note", width=300)
        notes_tree.pack(pady=10, fill='both', expand=True)
        def update_notes_table(event=None):
            for item in notes_tree.get_children():
                notes_tree.delete(item)
            employee_str = notes_employee_combobox.get()
            if not employee_str:
                return
            employee_id = int(employee_str.split(":")[0])
            self.cursor.execute(
                "SELECT note_id, date, note_text FROM notes WHERE employee_id = ? ORDER BY date DESC",
                (employee_id,)
            )
            for row in self.cursor.fetchall():
                db_date = row[1]
                display_date = datetime.strptime(db_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                notes_tree.insert("", tk.END, values=(row[0], display_date, row[2]))
        ttk.Button(notes_window, text="Edit Selected Note", command=lambda: self.edit_note(notes_tree, notes_employee_combobox, update_notes_table), style="Big.TButton").pack(pady=5)
        ttk.Button(notes_window, text="Delete Selected Note", command=lambda: self.delete_note(notes_tree, update_notes_table), style="Big.TButton").pack(pady=5)
        notes_employee_combobox.bind("<<ComboboxSelected>>", update_notes_table)
        update_notes_table()

    def delete_note(self, tree, update_func):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select a note to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete this note?"):
            return
        note_id = tree.item(selected_item)["values"][0]
        self.cursor.execute("DELETE FROM notes WHERE note_id = ?", (note_id,))
        self.conn.commit()
        update_func()
        self.update_notes_display()
        messagebox.showinfo("Success", "Note deleted")

    def view_employee_attendance(self):
        attendance_window = tk.Toplevel(self.root)
        attendance_window.title("Employee Attendance Records")
        attendance_window.geometry("600x400")
        ttk.Label(attendance_window, text="Select Employee:", font=self.label_font).pack(pady=5)
        attendance_employee_combobox = ttk.Combobox(attendance_window)
        attendance_employee_combobox.pack(pady=5)
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        attendance_employee_combobox["values"] = [f"{id}: {self.blur_name(name)}" for id, name in employees]
        if employees:
            selected_item = self.tree.selection()
            if selected_item:
                employee_id = self.tree.item(selected_item)["values"][0]
                for i, (id, name) in enumerate(employees):
                    if id == employee_id:
                        attendance_employee_combobox.current(i)
                        break
            else:
                attendance_employee_combobox.current(0)
        attendance_tree = ttk.Treeview(attendance_window, columns=("Attendance ID", "Date", "Status"), show="headings", style="Big.Treeview")
        attendance_tree.heading("Attendance ID", text="ID")
        attendance_tree.heading("Date", text="Date")
        attendance_tree.heading("Status", text="Status")
        attendance_tree.pack(pady=10, fill='both', expand=True)
        def update_attendance_table(event=None):
            for item in attendance_tree.get_children():
                attendance_tree.delete(item)
            employee_str = attendance_employee_combobox.get()
            if not employee_str:
                return
            employee_id = int(employee_str.split(":")[0])
            self.cursor.execute(
                "SELECT attendance_id, date, status FROM attendance WHERE employee_id = ? ORDER BY date DESC",
                (employee_id,)
            )
            for row in self.cursor.fetchall():
                db_date = row[1]
                display_date = datetime.strptime(db_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                attendance_tree.insert("", tk.END, values=(row[0], display_date, row[2]))
        ttk.Button(attendance_window, text="Edit Selected Attendance", command=lambda: self.edit_attendance(attendance_tree, attendance_employee_combobox, update_attendance_table), style="Big.TButton").pack(pady=5)
        ttk.Button(attendance_window, text="Delete Selected Attendance", command=lambda: self.delete_attendance(attendance_tree, update_attendance_table), style="Big.TButton").pack(pady=5)
        attendance_employee_combobox.bind("<<ComboboxSelected>>", update_attendance_table)
        update_attendance_table()

    def delete_attendance(self, tree, update_func):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an attendance record to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete this attendance record?"):
            return
        attendance_id = tree.item(selected_item)["values"][0]
        self.cursor.execute("DELETE FROM attendance WHERE attendance_id = ?", (attendance_id,))
        self.conn.commit()
        update_func()
        self.refresh_compare()
        messagebox.showinfo("Success", "Attendance record deleted")

    def edit_note(self, notes_tree, notes_employee_combobox, update_notes_table):
        selected_item = notes_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select a note to edit")
            return
        values = notes_tree.item(selected_item)["values"]
        note_id = values[0]
        current_date = values[1]
        current_note = values[2]
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Note")
        edit_window.geometry("400x200")
        ttk.Label(edit_window, text="Note:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        note_entry = ttk.Entry(edit_window, width=40)
        note_entry.insert(0, current_note)
        note_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(edit_window, text="Date (MM-DD-YYYY):", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        date_entry = ttk.Entry(edit_window)
        date_entry.insert(0, current_date)
        date_entry.grid(row=1, column=1, padx=5, pady=5)
        date_entry.bind("<KeyRelease>", self.auto_format_date)
        def save_changes():
            new_note = note_entry.get()
            new_date = date_entry.get()
            if not new_note or not new_date:
                messagebox.showerror("Error", "Note and date are required")
                return
            try:
                parsed_date = datetime.strptime(new_date, "%m-%d-%Y")
                db_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Invalid date format (use MM-DD-YYYY)")
                return
            self.cursor.execute(
                "UPDATE notes SET note_text = ?, date = ? WHERE note_id = ?",
                (new_note, db_date, note_id)
            )
            self.conn.commit()
            update_notes_table()
            self.update_notes_display()
            edit_window.destroy()
            messagebox.showinfo("Success", "Note updated")
        ttk.Button(edit_window, text="Save Changes", command=save_changes, style="Big.TButton").grid(row=2, column=0, columnspan=2, pady=10)

    def edit_attendance(self, attendance_tree, attendance_employee_combobox, update_attendance_table):
        selected_item = attendance_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an attendance record to edit")
            return
        values = attendance_tree.item(selected_item)["values"]
        attendance_id = values[0]
        current_date = values[1]
        current_status = values[2]
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Attendance Record")
        edit_window.geometry("300x200")
        ttk.Label(edit_window, text="Date (MM-DD-YYYY):", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        date_entry = ttk.Entry(edit_window)
        date_entry.insert(0, current_date)
        date_entry.grid(row=0, column=1, padx=5, pady=5)
        date_entry.bind("<KeyRelease>", self.auto_format_date)
        ttk.Label(edit_window, text="Status:", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        status_combobox = ttk.Combobox(edit_window, values=["Absent", "Tardy"])
        status_combobox.set(current_status)
        status_combobox.grid(row=1, column=1, padx=5, pady=5)
        def save_changes():
            new_date = date_entry.get()
            new_status = status_combobox.get()
            if not new_date or not new_status:
                messagebox.showerror("Error", "Date and status are required")
                return
            try:
                parsed_date = datetime.strptime(new_date, "%m-%d-%Y")
                db_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Invalid date format (use MM-DD-YYYY)")
                return
            self.cursor.execute(
                "UPDATE attendance SET date = ?, status = ? WHERE attendance_id = ?",
                (db_date, new_status, attendance_id)
            )
            self.conn.commit()
            update_attendance_table()
            self.refresh_compare()
            edit_window.destroy()
            messagebox.showinfo("Success", "Attendance record updated")
        ttk.Button(edit_window, text="Save Changes", command=save_changes, style="Big.TButton").grid(row=2, column=0, columnspan=2, pady=10)

    def edit_income(self, income_tree, income_employee_combobox, update_income_table):
        selected_item = income_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an income record to edit")
            return
        values = income_tree.item(selected_item)["values"]
        income_id = values[0]
        current_date = values[1]
        current_amount_str = values[2].replace("$", "").replace(",", "").replace("(", "").replace(")", "")
        current_amount = float(current_amount_str)
        current_type = values[3]
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Income Record")
        edit_window.geometry("300x200")
        ttk.Label(edit_window, text="Amount:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        amount_entry = ttk.Entry(edit_window, justify='right')
        amount_entry.insert(0, str(current_amount))
        amount_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(edit_window, text="Date (MM-DD-YYYY):", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        date_entry = ttk.Entry(edit_window)
        date_entry.insert(0, current_date)
        date_entry.grid(row=1, column=1, padx=5, pady=5)
        date_entry.bind("<KeyRelease>", self.auto_format_date)
        ttk.Label(edit_window, text="Type:", font=self.label_font).grid(row=2, column=0, padx=5, pady=5)
        type_combobox = ttk.Combobox(edit_window, values=["Salary", "Bonus"])
        type_combobox.set(current_type)
        type_combobox.grid(row=2, column=1, padx=5, pady=5)
        def save_changes():
            try:
                new_amount = float(amount_entry.get())
                if new_amount <= 0:
                    raise ValueError("Amount must be positive")
                new_date = date_entry.get()
                new_type = type_combobox.get()
                if not new_amount or not new_date or not new_type:
                    messagebox.showerror("Error", "All fields are required")
                    return
                parsed_date = datetime.strptime(new_date, "%m-%d-%Y")
                db_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError as e:
                messagebox.showerror("Error", str(e) or "Invalid amount or date format (use MM-DD-YYYY)")
                return
            self.cursor.execute(
                "UPDATE income SET amount = ?, date = ?, type = ? WHERE income_id = ?",
                (new_amount, db_date, new_type, income_id)
            )
            self.conn.commit()
            update_income_table()
            self.refresh_summary()
            self.refresh_scenarios()
            self.refresh_compare()
            edit_window.destroy()
            messagebox.showinfo("Success", "Income record updated")
        ttk.Button(edit_window, text="Save Changes", command=save_changes, style="Big.TButton").grid(row=3, column=0, columnspan=2, pady=10)

    def create_income_statement_entry(self, label_text, row):
        ttk.Label(self.income_statement_frame, text=label_text + ":", font=self.label_font).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        entry = ttk.Entry(self.income_statement_frame, justify='right')
        entry.grid(row=row, column=1, padx=5, pady=5, sticky="e")
        self.add_placeholder(entry, "0.00")
        return entry

    def calculate_income_statement(self):
        try:
            revenue = float(self.revenue_entry.get() if self.revenue_entry.get() != "0.00" else 0)
            cost_of_sales = float(self.cost_of_sales_entry.get() if self.cost_of_sales_entry.get() != "0.00" else 0)
            gross_profit = revenue - cost_of_sales
            self.gross_profit_label.config(text=f"Gross Profit: {self.format_currency(gross_profit)}")
            admin_expenses = float(self.admin_expenses_entry.get() if self.admin_expenses_entry.get() != "0.00" else 0)
            other_operating_expenses = float(self.other_operating_expenses_entry.get() if self.other_operating_expenses_entry.get() != "0.00" else 0)
            operating_profit = gross_profit - admin_expenses - other_operating_expenses
            self.operating_profit_label.config(text=f"Operating Profit: {self.format_currency(operating_profit)}")
            finance_costs = float(self.finance_costs_entry.get() if self.finance_costs_entry.get() != "0.00" else 0)
            other_income = float(self.other_income_entry.get() if self.other_income_entry.get() != "0.00" else 0)
            profit_before_tax = operating_profit - finance_costs + other_income
            self.profit_before_tax_label.config(text=f"Profit Before Tax: {self.format_currency(profit_before_tax)}")
            tax = float(self.tax_entry.get() if self.tax_entry.get() != "0.00" else 0)
            profit_after_tax = profit_before_tax - tax
            self.profit_after_tax_label.config(text=f"Profit After Tax: {self.format_currency(profit_after_tax)}")
            self.total_profit_entry.delete(0, tk.END)
            self.total_profit_entry.insert(0, str(profit_before_tax))
            self.analysis_text.config(state='normal')
            self.analysis_text.delete(1.0, tk.END)
            analysis = []
            if revenue > 0:
                gross_margin = (gross_profit / revenue) * 100
                analysis.append(f"Gross Profit Margin: {gross_margin:.2f}%")
                op_exp_ratio = ((admin_expenses + other_operating_expenses) / revenue) * 100
                analysis.append(f"Operating Expenses to Revenue: {op_exp_ratio:.2f}%")
            if profit_before_tax > 0:
                tax_rate = (tax / profit_before_tax) * 100
                analysis.append(f"Effective Tax Rate: {tax_rate:.2f}%")
            else:
                analysis.append("The company is reporting a loss before tax.")
            if profit_after_tax < 0:
                analysis.append("The company is loss-making after tax.")
            self.analysis_text.insert(tk.END, "\n".join(analysis))
            self.analysis_text.config(state='disabled')
        except ValueError:
            messagebox.showerror("Error", "Invalid input in income statement fields")

    def import_pdf(self):
        if 'PyPDF2' not in globals():
            messagebox.showerror("Error", "PyPDF2 library not found. Please install it using 'pip install PyPDF2'")
            return
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return
        try:
            with open(file_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            # Analyze text with rule-based "AI"
            self.analysis_text.config(state='normal')
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(tk.END, "Extracted Text:\n" + text + "\n\nAnalysis:\n")
            def extract_value(labels, text):
                for label in labels:
                    pattern = r'' + re.escape(label) + r'\s*:\s*[\$]?([-0-9,]+\.[0-9]{2})'
                    match = re.search(pattern, text, re.I)
                    if match:
                        return float(match.group(1).replace(",", ""))
                return 0.0
            revenue_labels = ["Revenue", "Sales", "Net Sales", "Total Revenue"]
            cost_of_sales_labels = ["Cost of Sales", "Cost of Goods Sold", "COGS"]
            admin_expenses_labels = ["Administrative Expenses", "Selling, General and Administrative Expenses", "SG&A"]
            other_operating_expenses_labels = ["Other Operating Expenses", "Operating Expenses"]
            finance_costs_labels = ["Finance Costs", "Interest Expense"]
            other_income_labels = ["Other Income", "Non-Operating Income"]
            tax_labels = ["Tax", "Income Tax Expense"]
            revenue = extract_value(revenue_labels, text)
            cost_of_sales = extract_value(cost_of_sales_labels, text)
            admin_expenses = extract_value(admin_expenses_labels, text)
            other_operating_expenses = extract_value(other_operating_expenses_labels, text)
            finance_costs = extract_value(finance_costs_labels, text)
            other_income = extract_value(other_income_labels, text)
            tax = extract_value(tax_labels, text)
            # Autofill entries
            self.revenue_entry.delete(0, tk.END)
            self.revenue_entry.insert(0, str(revenue) if revenue != 0 else "0.00")
            self.revenue_entry.config(foreground="black")
            self.cost_of_sales_entry.delete(0, tk.END)
            self.cost_of_sales_entry.insert(0, str(cost_of_sales) if cost_of_sales != 0 else "0.00")
            self.cost_of_sales_entry.config(foreground="black")
            self.admin_expenses_entry.delete(0, tk.END)
            self.admin_expenses_entry.insert(0, str(admin_expenses) if admin_expenses != 0 else "0.00")
            self.admin_expenses_entry.config(foreground="black")
            self.other_operating_expenses_entry.delete(0, tk.END)
            self.other_operating_expenses_entry.insert(0, str(other_operating_expenses) if other_operating_expenses != 0 else "0.00")
            self.other_operating_expenses_entry.config(foreground="black")
            self.finance_costs_entry.delete(0, tk.END)
            self.finance_costs_entry.insert(0, str(finance_costs) if finance_costs != 0 else "0.00")
            self.finance_costs_entry.config(foreground="black")
            self.other_income_entry.delete(0, tk.END)
            self.other_income_entry.insert(0, str(other_income) if other_income != 0 else "0.00")
            self.other_income_entry.config(foreground="black")
            self.tax_entry.delete(0, tk.END)
            self.tax_entry.insert(0, str(tax) if tax != 0 else "0.00")
            self.tax_entry.config(foreground="black")
            # Calculate and update labels
            self.calculate_income_statement()
            self.analysis_text.config(state='disabled')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process PDF: {str(e)}")

    def __del__(self):
        self.conn.close()

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    root.state('zoomed')
    app = RetirementTrackerApp(root)
    root.mainloop()
