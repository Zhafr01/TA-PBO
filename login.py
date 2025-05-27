from tkinter import *
from tkinter import messagebox
from tkcalendar import Calendar
from PIL import Image, ImageTk, ImageFilter
import mysql.connector
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="ManajemenKegiatanDTEI"
)


def login_window():
    window = Tk()
    window.title("Login")
    window.geometry("1080x720")
    try:
        bg = Image.open("img/LOGIN.png").filter(ImageFilter.GaussianBlur(10))  # Ganti ke LOGIN.png sesuai file Anda
        bg = bg.resize((1080, 720))
        bg = ImageTk.PhotoImage(bg)
        bg_label = Label(window, image=bg)
        bg_label.image = bg  # Prevent garbage collection
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    except Exception as e:
        messagebox.showerror("Error", f"Gagal memuat gambar: {e}")

    Label(window, text="Username").place(x=500, y=300, anchor="center")
    username_entry = Entry(window)
    username_entry.place(x=500, y=330, anchor="center")
    Label(window, text="Password").place(x=500, y=370, anchor="center")
    password_entry = Entry(window, show="*")
    password_entry.place(x=500, y=400, anchor="center")

    def login():
        username = username_entry.get()
        password = password_entry.get()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Pengguna WHERE Username = %s AND Password = %s", (username, password))
        result = cursor.fetchone()
        if result:
            messagebox.showinfo("Login", "Login berhasil!")
            window.destroy()
            # main_app()
        else:
            messagebox.showerror("Login", "Username atau password salah")

    Button(window, text="Login", command=login).place(x=500, y=440, anchor="center")
    window.mainloop()