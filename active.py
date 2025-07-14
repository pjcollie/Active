import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

# Initialize the main application
class RetirementTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Retirement Contribution Tracker")
        self.conn = sqlite3.connect("retirement.db")
        self.cursor = self.conn.cursor()
        self.setup_database()
        self.contribution_percentage = self.get_contribution_percentage()
        self.fiscal_year_start = "2025-01-01"
        self.fiscal_year_end = "2025-12-31"
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
            CREATE TABLE IF NOT EXISTS settings (
                setting_id INTEGER PRIMARY KEY,
                contribution_percentage REAL,
                fiscal_year_start TEXT,
                fiscal_year_end TEXT
            )
        """)
        # Insert default settings if not present
        self.cursor.execute("SELECT COUNT(*) FROM settings")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute(
                "INSERT INTO settings (setting_id, contribution_percentage, fiscal_year_start, fiscal_year_end) VALUES (?, ?, ?, ?)",
                (1, 5.0, "2025-01-01", "2025-12-31")
            )
        self.conn.commit()

    def get_contribution_percentage(self):
        # Fetch contribution percentage from settings
        self.cursor.execute("SELECT contribution_percentage FROM settings WHERE setting_id = 1")
        result = self.cursor.fetchone()
        return result[0] if result else 5.0

    def create_gui(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True, fill='both')

        # Employee Management Tab
        self.employee_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.employee_frame, text="Manage Employees")
        ttk.Label(self.employee_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = ttk.Entry(self.employee_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.employee_frame, text="Department:").grid(row=1, column=0, padx=5, pady=5)
        self.dept_combobox = ttk.Combobox(self.employee_frame, values=["Officer", "Office", "Warehouse"])
        self.dept_combobox.grid(row=1, column=1, padx=5, pady=5)
        self.dept_combobox.set("")  # Default to empty selection
        ttk.Button(self.employee_frame, text="Add Employee", command=self.add_employee).grid(row=2, column=0, columnspan=2, pady=10)

        # Income Entry Tab
        self.income_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.income_frame, text="Log Income")
        ttk.Label(self.income_frame, text="Employee:").grid(row=0, column=0, padx=5, pady=5)
        self.employee_combobox = ttk.Combobox(self.income_frame)
        self.employee_combobox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.income_frame, text="Amount:").grid(row=1, column=0, padx=5, pady=5)
        self.amount_entry = ttk.Entry(self.income_frame)
        self.amount_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(self.income_frame, text="Date (MM-DD-YYYY or MMDDYYYY):").grid(row=2, column=0, padx=5, pady=5)
        self.date_entry = ttk.Entry(self.income_frame)
        self.date_entry.grid(row=2, column=1, padx=5, pady=5)
        self.date_entry.bind("<KeyRelease>", self.auto_format_date)  # Bind key release to auto-format
        ttk.Label(self.income_frame, text="Type:").grid(row=3, column=0, padx=5, pady=5)
        self.type_combobox = ttk.Combobox(self.income_frame, values=["Salary", "Bonus"])
        self.type_combobox.grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(self.income_frame, text="Add Income", command=self.add_income).grid(row=4, column=0, columnspan=2, pady=10)
        self.update_employee_combobox()

        # Summary Tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Summary")
        self.tree = ttk.Treeview(self.summary_frame, columns=("ID", "Name", "Department", "Total Income", "Contribution"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Department", text="Department")
        self.tree.heading("Total Income", text="Total Income")
        self.tree.heading("Contribution", text="Contribution")
        self.tree.pack(pady=10, fill='both', expand=True)
        ttk.Button(self.summary_frame, text="Refresh Summary", command=self.refresh_summary).pack(pady=5)
        ttk.Button(self.summary_frame, text="Delete Employee", command=self.delete_employee).pack(pady=5)
        ttk.Button(self.summary_frame, text="View Income", command=self.view_employee_income).pack(pady=5)
        # Labels for totals
        self.total_income_label = ttk.Label(self.summary_frame, text="Total Income: $0.00")
        self.total_income_label.pack(pady=5)
        self.total_contribution_label = ttk.Label(self.summary_frame, text="Total Contribution: $0.00")
        self.total_contribution_label.pack(pady=5)
        self.total_spend_label = ttk.Label(self.summary_frame, text="Total Spend: $0.00")
        self.total_spend_label.pack(pady=5)

        # Settings Tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        ttk.Label(self.settings_frame, text="Contribution Percentage:").grid(row=0, column=0, padx=5, pady=5)
        self.percentage_entry = ttk.Entry(self.settings_frame)
        self.percentage_entry.insert(0, str(self.contribution_percentage))
        self.percentage_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.settings_frame, text="Update Percentage", command=self.update_percentage).grid(row=1, column=0, columnspan=2, pady=10)

    def auto_format_date(self, event):
        # Auto-format date to MM-DD-YYYY when 8 digits are entered
        text = self.date_entry.get().replace("-", "")  # Remove existing hyphens
        if len(text) == 8 and text.isdigit():
            formatted = f"{text[:2]}-{text[2:4]}-{text[4:]}"
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, formatted)

    def update_employee_combobox(self):
        # Populate employee combobox
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        self.employee_combobox["values"] = [f"{id}: {name}" for id, name in employees]
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

    def refresh_summary(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
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
            self.tree.insert("", tk.END, values=(row[0], row[1], row[2], f"${row[3]:.2f}", f"${contribution:.2f}"))
            total_income += row[3]
        # Calculate and update totals
        total_contribution = total_income * (self.contribution_percentage / 100)
        total_spend = total_income + total_contribution
        self.total_income_label.config(text=f"Total Income: ${total_income:.2f}")
        self.total_contribution_label.config(text=f"Total Contribution: ${total_contribution:.2f}")
        self.total_spend_label.config(text=f"Total Spend: ${total_spend:.2f}")

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

    def update_percentage(self):
        try:
            new_percentage = float(self.percentage_entry.get())
            if new_percentage < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid percentage")
            return
        self.cursor.execute(
            "UPDATE settings SET contribution_percentage = ? WHERE setting_id = 1",
            (new_percentage,)
        )
        self.conn.commit()
        self.contribution_percentage = new_percentage
        self.refresh_summary()
        messagebox.showinfo("Success", "Percentage updated")

    def view_employee_income(self):
        # Create a new window for viewing income
        income_window = tk.Toplevel(self.root)
        income_window.title("Employee Income Records")
        income_window.geometry("600x400")  # Set a reasonable size for the window

        # Employee selection dropdown
        ttk.Label(income_window, text="Select Employee:").pack(pady=5)
        income_employee_combobox = ttk.Combobox(income_window)
        income_employee_combobox.pack(pady=5)
        self.cursor.execute("SELECT employee_id, name FROM employees")
        employees = [(row[0], row[1]) for row in self.cursor.fetchall()]
        income_employee_combobox["values"] = [f"{id}: {name}" for id, name in employees]
        if employees:
            # Pre-select the employee from the summary table if one is selected
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
        income_tree = ttk.Treeview(income_window, columns=("Income ID", "Date", "Amount", "Type"), show="headings")
        income_tree.heading("Income ID", text="ID")
        income_tree.heading("Date", text="Date")
        income_tree.heading("Amount", text="Amount")
        income_tree.heading("Type", text="Type")
        income_tree.pack(pady=10, fill='both', expand=True)

        def update_income_table(event=None):
            # Clear existing items
            for item in income_tree.get_children():
                income_tree.delete(item)
            # Get selected employee
            employee_str = income_employee_combobox.get()
            if not employee_str:
                return
            employee_id = int(employee_str.split(":")[0])
            # Fetch income records, sorted by date (oldest to newest)
            self.cursor.execute(
                "SELECT income_id, date, amount, type FROM income WHERE employee_id = ? ORDER BY date ASC",
                (employee_id,)
            )
            for row in self.cursor.fetchall():
                # Convert date from YYYY-MM-DD to MM-DD-YYYY for display
                db_date = row[1]
                display_date = datetime.strptime(db_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                income_tree.insert("", tk.END, values=(row[0], display_date, f"${row[2]:.2f}", row[3]))

        # Button to edit selected income record
        ttk.Button(income_window, text="Edit Selected Income", command=lambda: self.edit_income(income_tree, income_employee_combobox, update_income_table)).pack(pady=5)

        # Bind combobox change to update table
        income_employee_combobox.bind("<<ComboboxSelected>>", update_income_table)
        # Initial table update
        update_income_table()

    def edit_income(self, income_tree, income_employee_combobox, update_income_table):
        # Get selected income record
        selected_item = income_tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Select an income record to edit")
            return
        values = income_tree.item(selected_item)["values"]
        income_id = values[0]
        current_date = values[1]
        current_amount = float(values[2].replace("$", ""))
        current_type = values[3]

        # Create edit window
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Income Record")
        edit_window.geometry("300x200")

        # Fields for editing
        ttk.Label(edit_window, text="Amount:").grid(row=0, column=0, padx=5, pady=5)
        amount_entry = ttk.Entry(edit_window)
        amount_entry.insert(0, str(current_amount))
        amount_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(edit_window, text="Date (MM-DD-YYYY):").grid(row=1, column=0, padx=5, pady=5)
        date_entry = ttk.Entry(edit_window)
        date_entry.insert(0, current_date)
        date_entry.grid(row=1, column=1, padx=5, pady=5)
        date_entry.bind("<KeyRelease>", self.auto_format_date)  # Reuse auto-format for date

        ttk.Label(edit_window, text="Type:").grid(row=2, column=0, padx=5, pady=5)
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
                # Validate date format MM-DD-YYYY and convert to YYYY-MM-DD
                parsed_date = datetime.strptime(new_date, "%m-%d-%Y")
                db_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Invalid amount or date format (use MM-DD-YYYY)")
                return
            # Update database
            self.cursor.execute(
                "UPDATE income SET amount = ?, date = ?, type = ? WHERE income_id = ?",
                (new_amount, db_date, new_type, income_id)
            )
            self.conn.commit()
            update_income_table()  # Refresh the income table
            self.refresh_summary()  # Refresh the summary to update totals
            edit_window.destroy()
            messagebox.showinfo("Success", "Income record updated")

        ttk.Button(edit_window, text="Save Changes", command=save_changes).grid(row=3, column=0, columnspan=2, pady=10)

    def __del__(self):
        # Close database connection
        self.conn.close()

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    root.state('zoomed')  # Maximize the window to full screen
    app = RetirementTrackerApp(root)
    root.mainloop()
