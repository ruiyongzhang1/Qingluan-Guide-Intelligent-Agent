# gui_tool.py
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from database_self import db

class DatabaseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite 数据库管理工具")
        self.root.geometry("1000x600")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.setup_tables_tab()
        self.setup_users_tab()
        self.setup_conversations_tab()
        self.setup_messages_tab()
        self.setup_stats_tab()

    def setup_tables_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text='表结构')

        btn = ttk.Button(frame, text='刷新表列表', command=self.show_tables)
        btn.pack(pady=5)

        self.table_list = scrolledtext.ScrolledText(frame, height=15, font=("Courier", 11))
        self.table_list.pack(fill='both', expand=True)

    def show_tables(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        self.table_list.delete(1.0, tk.END)
        for tbl in tables:
            self.table_list.insert(tk.END, f"- {tbl['name']}\n")
        conn.close()

    def setup_users_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text='用户')

        self.user_tree = ttk.Treeview(frame, columns=('id', 'email', 'created'), show='headings', height=20)
        self.user_tree.heading('id', text='ID')
        self.user_tree.heading('email', text='邮箱')
        self.user_tree.heading('created', text='创建时间')
        self.user_tree.column('email', width=300)
        self.user_tree.pack(fill='both', expand=True)

        control = ttk.Frame(frame)
        control.pack(pady=5)

        refresh_btn = ttk.Button(control, text='刷新用户列表', command=self.show_users)
        refresh_btn.pack(side='left', padx=5)

        self.email_entry = ttk.Entry(control, width=40)
        self.email_entry.pack(side='left', padx=5)
        del_btn = ttk.Button(control, text='删除用户', command=self.delete_user)
        del_btn.pack(side='left', padx=5)

    def show_users(self):
        for i in self.user_tree.get_children():
            self.user_tree.delete(i)
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email, created_at FROM users ORDER BY created_at DESC")
        users = cur.fetchall()
        for u in users:
            self.user_tree.insert('', 'end', values=(u['id'], u['email'], u['created_at']))
        conn.close()

    def delete_user(self):
        email = self.email_entry.get()
        if not email:
            return
        if not messagebox.askyesno("确认删除", f"确定要删除用户 {email} 吗？"):
            return
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        conn.close()
        self.show_users()

    def setup_conversations_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text='对话')

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill='x', pady=5)

        self.conv_email_entry = ttk.Entry(top_frame, width=40)
        self.conv_email_entry.pack(side='left', padx=5)
        search_btn = ttk.Button(top_frame, text='搜索对话', command=self.show_conversations)
        search_btn.pack(side='left', padx=5)

        self.conv_tree = ttk.Treeview(frame, columns=('id', 'email', 'date', 'count', 'created'), show='headings', height=15)
        for col, name, width in zip(
            ('id', 'email', 'date', 'count', 'created'),
            ('对话ID', '用户', '日期', '消息数', '创建时间'),
            (300, 250, 100, 60, 150)):
            self.conv_tree.heading(col, text=name)
            self.conv_tree.column(col, width=width)
        self.conv_tree.pack(fill='both', expand=True)

        btns = ttk.Frame(frame)
        btns.pack(pady=5)
        ttk.Button(btns, text='查看消息', command=self.select_conversation).pack(side='left', padx=5)
        ttk.Button(btns, text='删除对话', command=self.delete_conversation).pack(side='left', padx=5)

    def show_conversations(self):
        for i in self.conv_tree.get_children():
            self.conv_tree.delete(i)
        email = self.conv_email_entry.get()
        conn = db.get_connection()
        cur = conn.cursor()
        if email:
            cur.execute("""
                SELECT c.id, c.user_email, c.date, c.created_at, COUNT(m.id) as msg_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_email = ?
                GROUP BY c.id ORDER BY c.created_at DESC
            """, (email,))
        else:
            cur.execute("""
                SELECT c.id, c.user_email, c.date, c.created_at, COUNT(m.id) as msg_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY c.id ORDER BY c.created_at DESC
            """)
        rows = cur.fetchall()
        for r in rows:
            self.conv_tree.insert('', 'end', values=(r['id'], r['user_email'], r['date'], r['msg_count'], r['created_at']))
        conn.close()

    def select_conversation(self):
        selected = self.conv_tree.focus()
        if not selected:
            return
        conv_id = self.conv_tree.item(selected)['values'][0]
        self.show_messages(conv_id)

    def delete_conversation(self):
        selected = self.conv_tree.focus()
        if not selected:
            return
        conv_id = self.conv_tree.item(selected)['values'][0]
        if not messagebox.askyesno("确认删除", f"删除对话 {conv_id}？"):
            return
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
        conn.close()
        self.show_conversations()

    def setup_messages_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text='消息')
        self.msg_text = scrolledtext.ScrolledText(frame, wrap='word', font=("Courier", 11))
        self.msg_text.pack(fill='both', expand=True)

    def show_messages(self, conv_id):
        self.notebook.select(3)
        self.msg_text.delete(1.0, tk.END)
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT text, is_user, agent_type, created_at
            FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
        """, (conv_id,))
        messages = cur.fetchall()
        for i, msg in enumerate(messages, 1):
            sender = "用户" if msg['is_user'] else "AI"
            self.msg_text.insert(tk.END, f"[{i}] {sender} ({msg['agent_type']}) - {msg['created_at']}\n")
            self.msg_text.insert(tk.END, f"     {msg['text']}\n\n")
        conn.close()

    def setup_stats_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text='统计')

        self.stats_label = tk.Label(frame, justify='left', anchor='nw', font=("Courier", 12))
        self.stats_label.pack(fill='both', expand=True, padx=10, pady=10)

        btn = ttk.Button(frame, text='刷新统计', command=self.show_stats)
        btn.pack(pady=5)

    def show_stats(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM users")
        users = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) as count FROM conversations")
        convs = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) as count FROM messages")
        msgs = cur.fetchone()['count']
        cur.execute("""
            SELECT COUNT(DISTINCT user_email) as count FROM conversations
            WHERE created_at >= datetime('now', '-7 days')
        """)
        actives = cur.fetchone()['count']
        conn.close()

        stats = f"""
总用户数:        {users}
总对话数:        {convs}
总消息数:        {msgs}
最近7天活跃用户: {actives}
"""
        self.stats_label.config(text=stats)

if __name__ == '__main__':
    root = tk.Tk()
    app = DatabaseGUI(root)
    root.mainloop()
