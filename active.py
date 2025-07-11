import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
from datetime import datetime
import sqlite3

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
        self.total_label_font = tkfont.Font(family="Helvetica", size=14, weight="bold")  # Larger and bold for totals
        self.tree_font = tkfont.Font(family="Helvetica", size=11)
        self.create_gui()

    def setup_database(self):
        # Create tables if they don't exist
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT
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
        # Check if selected_year and privacy_mode columns exist and add them if not
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
        # Fetch contribution percentage from settings
        self.cursor.execute("SELECT contribution_percentage FROM settings WHERE setting_id = 1")
        result = self.cursor.fetchone()
        return result[0] if result else 5.0

    def get_selected_year(self):
        # Fetch selected year from settings
        self.cursor.execute("SELECT selected_year FROM settings WHERE setting_id = 1")
        result = self.cursor.fetchone()
        return result[0] if result else datetime.now().year

    def get_privacy_mode(self):
        # Fetch privacy mode from settings
        self.cursor.execute("SELECT privacy_mode FROM settings WHERE setting_id = 1")
        result = self.cursor.fetchone()
        return result[0] if result is not None else 0

    def get_total_profit(self):
        # Fetch total profit for the selected year
        self.cursor.execute("SELECT total_profit FROM taxable_income WHERE year = ?", (self.selected_year,))
        result = self.cursor.fetchone()
        return result[0] if result else 0.0

    def set_fiscal_year(self, year):
        # Set fiscal year start as March 1st of the selected year and end as the last day of February of the next year
        self.fiscal_year_start = f"{year}-03-01"
        self.fiscal_year_end = f"{year + 1}-02-28"

    def blur_name(self, name):
        # Blur name by replacing each part with asterisks of the same length
        if not self.privacy_mode:
            return name
        parts = name.split()
        blurred_parts = [''.join('*' for _ in part) for part in parts]
        return ' '.join(blurred_parts)

    def create_gui(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True, fill='both')

        # Employee Management Tab
        self.employee_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.employee_frame, text="Manage Employees")
        ttk.Label(self.employee_frame, text="Name:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = ttk.Entry(self.employee_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.employee_frame, text="Department:", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        self.dept_combobox = ttk.Combobox(self.employee_frame, values=["Officer", "Office", "Warehouse"])
        self.dept_combobox.grid(row=1, column=1, padx=5, pady=5)
        self.dept_combobox.set("")  # Default to empty selection
        ttk.Button(self.employee_frame, text="Add Employee", command=self.add_employee, style="Big.TButton").grid(row=2, column=0, columnspan=2, pady=10)

        # Income Entry Tab
        self.income_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.income_frame, text="Log Income")
        ttk.Label(self.income_frame, text="Employee:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.employee_combobox = ttk.Combobox(self.income_frame)
        self.employee_combobox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.income_frame, text="Amount:", font=self.label_font).grid(row=1, column=0, padx=5, pady=5)
        self.amount_entry = ttk.Entry(self.income_frame)
        self.amount_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(self.income_frame, text="Date (MM-DD-YYYY or MMDDYYYY):", font=self.label_font).grid(row=2, column=0, padx=5, pady=5)
        self.date_entry = ttk.Entry(self.income_frame)
        self.date_entry.grid(row=2, column=1, padx=5, pady=5)
        self.date_entry.bind("<KeyRelease>", self.auto_format_date)  # Bind key release to auto-format
        # Add Today button
        ttk.Button(self.income_frame, text="Today", command=self.set_today_date, style="Big.TButton").grid(row=2, column=2, padx=5, pady=5)
        ttk.Label(self.income_frame, text="Type:", font=self.label_font).grid(row=3, column=0, padx=5, pady=5)
        self.type_combobox = ttk.Combobox(self.income_frame, values=["Salary", "Bonus"])
        self.type_combobox.grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(self.income_frame, text="Add Income", command=self.add_income, style="Big.TButton").grid(row=4, column=0, columnspan=2, pady=10)
        self.update_employee_combobox()

        # Taxable Income Tab
        self.taxable_income_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.taxable_income_frame, text="Taxable Income")
        ttk.Label(self.taxable_income_frame, text=f"Total Profit for {self.selected_year}:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.total_profit_entry = ttk.Entry(self.taxable_income_frame)
        self.total_profit_entry.insert(0, str(self.get_total_profit()))
        self.total_profit_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.taxable_income_frame, text="Update Total Profit", command=self.update_total_profit, style="Big.TButton").grid(row=1, column=0, columnspan=2, pady=10)

        # Summary Tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Summary")
        # Create left and right frames for layout
        self.left_frame = ttk.Frame(self.summary_frame)
        self.left_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        self.right_frame = ttk.Frame(self.summary_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        # Configure grid weights to make right frame expand
        self.summary_frame.grid_columnconfigure(1, weight=1)
        self.summary_frame.grid_rowconfigure(0, weight=1)
        # Buttons on the left
        ttk.Button(self.left_frame, text="Refresh Summary", command=self.refresh_summary, style="Big.TButton").pack(pady=5, fill='x')
        ttk.Button(self.left_frame, text="Delete Employee", command=self.delete_employee, style="Big.TButton").pack(pady=5, fill='x')
        ttk.Button(self.left_frame, text="View Income", command=self.view_employee_income, style="Big.TButton").pack(pady=5, fill='x')
        # Treeview and labels on the right
        self.tree = ttk.Treeview(self.right_frame, columns=("ID", "Name", "Department", "Total Income", "Contribution"), show="headings", style="Big.Treeview")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Department", text="Department")
        self.tree.heading("Total Income", text="Total Income")
        self.tree.heading("Contribution", text="Contribution")
        self.tree.pack(pady=10, fill='both', expand=True)
        # Labels for totals with larger, bold font and fiscal year prefix
        self.total_income_label = ttk.Label(self.right_frame, text=f"Fiscal Year {self.selected_year} Total Income: $0.00", font=self.total_label_font, anchor="w")
        self.total_income_label.pack(pady=10, fill='x')
        self.total_contribution_label = ttk.Label(self.right_frame, text=f"Fiscal Year {self.selected_year} Total Contribution: $0.00", font=self.total_label_font, anchor="w")
        self.total_contribution_label.pack(pady=10, fill='x')
        self.total_taxable_income_label = ttk.Label(self.right_frame, text=f"Fiscal Year {self.selected_year} Total Taxable Income: $0.00", font=self.total_label_font, anchor="w")
        self.total_taxable_income_label.pack(pady=10, fill='x')
        self.total_spend_label = ttk.Label(self.right_frame, text=f"Fiscal Year {self.selected_year} Total Spend: $0.00", font=self.total_label_font, anchor="w")
        self.total_spend_label.pack(pady=10, fill='x')
        # Configure styles for larger fonts
        style = ttk.Style()
        style.configure("Big.TButton", font=self.button_font)
        style.configure("Big.Treeview", font=self.tree_font)
        style.configure("Big.Treeview.Heading", font=self.label_font)

        # Settings Tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        ttk.Label(self.settings_frame, text="Contribution Percentage:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        self.percentage_entry = ttk.Entry(self.settings_frame)
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

    def set_today_date(self):
        # Set the date entry to today's date in MM-DD-YYYY format
        today = datetime.now().strftime("%m-%d-%Y")
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, today)

    def auto_format_date(self, event):
        # Auto-format date to MM-DD-YYYY when 8 digits are entered
        text = event.widget.get().replace("-", "")  # Use event.widget to support multiple date entries
        if len(text) == 8 and text.isdigit():
            formatted = f"{text[:2]}-{text[2:4]}-{text[4:]}"
            event.widget.delete(0, tk.END)
            event.widget.insert(0, formatted)

    def update_employee_combobox(self):
        # Populate employee combobox for income tab with blurred names if privacy mode is on
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        self.employee_combobox["values"] = [f"{id}: {self.blur_name(name)}" for id, name in employees]
        if employees:
            self.employee_combobox.current(0)

    def add_employee(self):
        name = self.name_entry.get()
        department = self.dept_combobox.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        self.cursor.execute("INSERT INTO employees (name, department) VALUES (?, ?)", (name, department))
        self.conn.commit()
        self.name_entry.delete(0, tk.END)
        self.dept_combobox.set("")  # Clear combobox selection
        self.update_employee_combobox()
        messagebox.showinfo("Success", "Employee added")

    def add_income(self):
        employee_str = self.employee_combobox.get()
        if not employee_str:
            messagebox.showerror("Error", "Select an employee")
            return
        employee_id = int(employee_str.split(":")[0])
        try:
            amount = float(self.amount_entry.get())
            date = self.date_entry.get()
            type_ = self.type_combobox.get()
            if not amount or not date or not type_:
                messagebox.showerror("Error", "All fields are required")
                return
            # Validate date format MM-DD-YYYY and convert to YYYY-MM-DD for storage
            parsed_date = datetime.strptime(date, "%m-%d-%Y")
            db_date = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid amount or date format (use MM-DD-YYYY)")
            return
        self.cursor.execute(
            "INSERT INTO income (employee_id, amount, date, type) VALUES (?, ?, ?, ?)",
            (employee_id, amount, db_date, type_)
        )
        self.conn.commit()
        self.amount_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self.type_combobox.set("")
        messagebox.showinfo("Success", "Income added")

    def update_total_profit(self):
        try:
            total_profit = float(self.total_profit_entry.get())
            if total_profit < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid profit amount (must be a non-negative number)")
            return
        # Check if a record exists for the selected year
        self.cursor.execute("SELECT COUNT(*) FROM taxable_income WHERE year = ?", (self.selected_year,))
        if self.cursor.fetchone()[0] > 0:
            self.cursor.execute("UPDATE taxable_income SET total_profit = ? WHERE year = ?", (total_profit, self.selected_year))
        else:
            self.cursor.execute("INSERT INTO taxable_income (year, total_profit) VALUES (?, ?)", (self.selected_year, total_profit))
        self.conn.commit()
        self.refresh_summary()
        messagebox.showinfo("Success", "Total profit updated")

    def refresh_summary(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Fetch total profit for the selected year
        total_profit = self.get_total_profit()
        # Fetch and display summary
        self.cursor.execute("""
            SELECT e.employee_id, e.name, e.department, COALESCE(SUM(i.amount), 0) as total_income
            FROM employees e
            LEFT JOIN income i ON e.employee_id = i.employee_id
            WHERE i.date BETWEEN ? AND ? OR i.date IS NULL
            GROUP BY e.employee_id
        """, (self.fiscal_year_start, self.fiscal_year_end))
        total_income = 0
        rows = self.cursor.fetchall()
        for row in rows:
            contribution = row[3] * (self.contribution_percentage / 100)
            blurred_name = self.blur_name(row[1])
            self.tree.insert("", tk.END, values=(row[0], blurred_name, row[2], f"${row[3]:.2f}", f"${contribution:.2f}"))
            total_income += row[3]
        # Calculate and update totals with fiscal year prefix
        total_contribution = total_income * (self.contribution_percentage / 100)
        total_spend = total_income + total_contribution - total_profit
        self.total_income_label.config(text=f"Fiscal Year {self.selected_year} Total Income: ${total_income:.2f}")
        self.total_contribution_label.config(text=f"Fiscal Year {self.selected_year} Total Contribution: ${total_contribution:.2f}")
        self.total_taxable_income_label.config(text=f"Fiscal Year {self.selected_year} Total Taxable Income: ${total_profit:.2f}")
        self.total_spend_label.config(text=f"Fiscal Year {self.selected_year} Total Spend: ${total_spend:.2f}")

    def delete_employee(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        employee_id = self.tree.item(selected_item)["values"][0]
        if messagebox.askyesno("Confirm", "Delete this employee and their income records?"):
            self.cursor.execute("DELETE FROM income WHERE employee_id = ?", (employee_id,))
            self.cursor.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
            self.conn.commit()
            self.refresh_summary()
            self.update_employee_combobox()
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
        # Update total profit entry for the new year
        self.total_profit_entry.delete(0, tk.END)
        self.total_profit_entry.insert(0, str(self.get_total_profit()))
        self.refresh_summary()
        self.update_employee_combobox()
        messagebox.showinfo("Success", "Settings updated")

    def view_employee_income(self):
        # Create a new window for viewing income
        income_window = tk.Toplevel(self.root)
        income_window.title("Employee Income Records")
        income_window.geometry("600x400")

        # Employee selection dropdown
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

        # Income table
        income_tree = ttk.Treeview(income_window, columns=("Income ID", "Date", "Amount", "Type"), show="headings", style="Big.Treeview")
        income_tree.heading("Income ID", text="ID")
        income_tree.heading("Date", text="Date")
        income_tree.heading("Amount", text="Amount")
        income_tree.heading("Type", text="Type")
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
                income_tree.insert("", tk.END, values=(row[0], display_date, f"${row[2]:.2f}", row[3]))

        # Button to edit selected income record
        ttk.Button(income_window, text="Edit Selected Income", command=lambda: self.edit_income(income_tree, income_employee_combobox, update_income_table), style="Big.TButton").pack(pady=5)

        income_employee_combobox.bind("<<ComboboxSelected>>", update_income_table)
        update_income_table()

    def edit_income(self, income_tree, income_employee_combobox, update_income_table):
        selected_item = income_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an income record to edit")
            return
        values = income_tree.item(selected_item)["values"]
        income_id = values[0]
        current_date = values[1]
        current_amount = float(values[2].replace("$", ""))
        current_type = values[3]

        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Income Record")
        edit_window.geometry("300x200")

        ttk.Label(edit_window, text="Amount:", font=self.label_font).grid(row=0, column=0, padx=5, pady=5)
        amount_entry = ttk.Entry(edit_window)
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
                new_date = date_entry.get()
                new_type = type_combobox.get()
                if not new_amount or not new_date or not new_type:
                    messagebox.showerror("Error", "All fields are required")
                    return
                parsed_date = datetime.strptime(new_date, "%m-%d-%Y")
                db_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Invalid amount or date format (use MM-DD-YYYY)")
                return
            self.cursor.execute(
                "UPDATE income SET amount = ?, date = ?, type = ? WHERE income_id = ?",
                (new_amount, db_date, new_type, income_id)
            )
            self.conn.commit()
            update_income_table()
            self.refresh_summary()
            edit_window.destroy()
            messagebox.showinfo("Success", "Income record updated")

        ttk.Button(edit_window, text="Save Changes", command=save_changes, style="Big.TButton").grid(row=3, column=0, columnspan=2, pady=10)

    def __del__(self):
        # Close database connection
        self.conn.close()

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    root.state('zoomed')  # Maximize the window to full screen
    app = RetirementTrackerApp(root)
    root.mainloop()
