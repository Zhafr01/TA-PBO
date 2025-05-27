import mysql.connector
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
import datetime
from PIL import Image, ImageTk # Dihapus ImageFilter karena tidak digunakan

# --- Warna & Gaya Global ---
BG_COLOR = "#f0f8ff"
FONT_STYLE = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
BTN_COLOR = "#4a90e2"
BTN_HOVER = "#357ABD"

# --- Kelas Entitas ---
class Entitas:
    """Kelas dasar untuk semua entitas data (Pengguna, Kegiatan)."""
    def __init__(self, id_entitas):
        self._id_entitas = id_entitas # Enkapsulasi: _id_entitas bersifat protected

    @property
    def id_entitas(self):
        return self._id_entitas

    # Metode ini akan di-override oleh subclass (Polimorfisme)
    def get_details_string(self):
        """Mengembalikan representasi string dari detail entitas."""
        return f"ID: {self._id_entitas}"

class Pengguna(Entitas):
    """Merepresentasikan entitas Pengguna."""
    def __init__(self, id_pengguna, nama, role_id=None, nim_nip=None, username=None, password=None):
        super().__init__(id_pengguna) # Pewarisan: memanggil constructor kelas induk
        self._nama = nama
        self._role_id = role_id
        self._nim_nip = nim_nip
        self._username = username
        self._password = password # Dalam aplikasi nyata, ini harus di-hash

    # Enkapsulasi melalui properties
    @property
    def nama(self):
        return self._nama

    @property
    def role_id(self):
        return self._role_id

    @property
    def nim_nip(self):
        return self._nim_nip

    @property
    def username(self):
        return self._username
    
    # Contoh metode untuk enkapsulasi data
    def get_display_name(self):
        return f"{self._nama} (ID: {self.id_entitas})"

    # Polimorfisme: Override metode dari kelas Entitas
    def get_details_string(self):
        return f"ID Pengguna: {self.id_entitas}, Nama: {self._nama}, Username: {self._username}, Role ID: {self._role_id}"

class Kegiatan(Entitas):
    """Merepresentasikan entitas Kegiatan."""
    def __init__(self, id_kegiatan, nama_kegiatan, tanggal, tempat, jenis_kegiatan, id_penanggung_jawab=None):
        super().__init__(id_kegiatan) # Pewarisan
        self._nama_kegiatan = nama_kegiatan
        self._tanggal = tanggal # Bisa berupa string atau objek date
        self._tempat = tempat
        self._jenis_kegiatan = jenis_kegiatan
        self._id_penanggung_jawab = id_penanggung_jawab

    # Enkapsulasi melalui properties
    @property
    def nama_kegiatan(self):
        return self._nama_kegiatan

    @property
    def tanggal(self):
        return self._tanggal
    
    @tanggal.setter
    def tanggal(self, value):
        self._tanggal = value

    @property
    def tempat(self):
        return self._tempat

    @property
    def jenis_kegiatan(self):
        return self._jenis_kegiatan

    @property
    def id_penanggung_jawab(self):
        return self._id_penanggung_jawab

    # Polimorfisme: Override metode dari kelas Entitas
    def get_details_string(self):
        return (f"ID Kegiatan: {self.id_entitas}, Nama: {self._nama_kegiatan}, "
                f"Tanggal: {self._tanggal}, Tempat: {self._tempat}, "
                f"Jenis: {self._jenis_kegiatan}, PJ ID: {self._id_penanggung_jawab}")

    def to_tuple_for_display(self, nama_pj="N/A"):
        """Mengembalikan tuple data kegiatan untuk ditampilkan di Treeview."""
        return (
            self.id_entitas,
            self._nama_kegiatan,
            self._tanggal, # Asumsikan sudah dalam format string yang benar
            self._tempat,
            self._jenis_kegiatan,
            nama_pj,
            self._id_penanggung_jawab
        )

# --- Kelas untuk Manajemen Database ---
# --- Kelas untuk Manajemen Database ---
class DatabaseManager:
    def __init__(self, host, user, password, database_name):
        # Enkapsulasi: Atribut instance bersifat private-like
        self._host = host
        self._user = user
        self._password = password
        self._database_name = database_name

    def _get_connection(self):
        """Membuat dan mengembalikan koneksi database."""
        try:
            return mysql.connector.connect(
                host=self._host,
                user=self._user,
                password=self._password,
                database=self._database_name
            )
        except mysql.connector.Error as err:
            if err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
                try:
                    temp_conn = mysql.connector.connect(host=self._host, user=self._user, password=self._password)
                    temp_cursor = temp_conn.cursor()
                    temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self._database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    temp_conn.commit()
                    temp_cursor.close()
                    temp_conn.close()
                    return mysql.connector.connect(
                        host=self._host, user=self._user, password=self._password, database=self._database_name
                    )
                except mysql.connector.Error as create_err:
                    raise mysql.connector.Error(f"Gagal membuat atau terhubung ke database '{self._database_name}': {create_err}") from create_err
            else:
                raise mysql.connector.Error(f"Koneksi database gagal: {err}") from err

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False, is_many=False, is_ddl=False): # Mengganti is_ddl_multi menjadi is_ddl
        """Mengeksekusi query SQL dan mengelola koneksi."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor() # Buat cursor di awal

            if is_ddl: # Jika ini adalah query DDL tunggal (seperti CREATE TABLE, TRIGGER, SP)
                # Ekstensi C MySQL Connector mungkin tidak suka 'multi=True' untuk DDL tunggal.
                # Kita akan mencoba mengeksekusinya sebagai statement tunggal.
                # Konektor biasanya dapat menangani blok BEGIN...END dalam SP/Trigger.
                try:
                    cursor.execute(query, params) # Tanpa multi=True
                except mysql.connector.Error as e:
                    # Jika errornya karena query mengandung multiple statements yang *tidak bisa*
                    # ditangani sebagai satu blok oleh execute() biasa (jarang untuk DDL standar),
                    # maka kita bisa coba dengan 'multi=True' sebagai fallback,
                    # atau memecah query jika memungkinkan (di luar scope fungsi ini).
                    # Untuk sekarang, kita re-raise errornya.
                    # print(f"Info: Mencoba eksekusi DDL dengan multi=True karena error awal: {e}")
                    # for _ in cursor.execute(query, params, multi=True): # Loop untuk consume semua hasil
                    #     pass
                    # Untuk DDL, loop di atas tidak diperlukan jika multi=True berhasil
                    # cursor.execute(query, params, multi=True) # Coba jika versi mendukung
                    # Namun, karena error aslinya adalah `unexpected keyword argument 'multi'`,
                    # kita hindari penggunaan `multi=True` di sini.
                    raise e # Re-raise error jika eksekusi DDL tunggal gagal
            elif is_many and params: # Untuk executemany
                cursor.executemany(query, params)
            else: # Untuk query DML standar (SELECT, INSERT, UPDATE, DELETE non-batch)
                cursor.execute(query, params)

            # Commit jika query adalah DML yang mengubah data atau DDL
            if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")) or is_ddl:
                conn.commit()

            # Fetch results jika diperlukan (biasanya bukan untuk DDL)
            if fetch_one:
                result = cursor.fetchone()
                cursor.close()
                return result
            if fetch_all:
                result = cursor.fetchall()
                cursor.close()
                return result
            
            # Return lastrowid untuk INSERT atau rowcount untuk operasi lain
            if cursor.lastrowid and query.strip().upper().startswith("INSERT"):
                last_id = cursor.lastrowid
                cursor.close()
                return last_id
            
            rowcount = cursor.rowcount
            cursor.close()
            return rowcount

        except mysql.connector.Error as err:
            if conn:
                conn.rollback()
            raise err # Re-raise error untuk ditangani di level lebih tinggi
        finally:
            if conn and conn.is_connected():
                conn.close()


    def call_stored_procedure(self, proc_name, args=()):
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.callproc(proc_name, args)
            conn.commit()
            
            # Mengambil hasil jika SP mengembalikan sesuatu (opsional, tergantung SP)
            # results = []
            # for result in cursor.stored_results():
            #     results.extend(result.fetchall())
            # if results:
            #     return results

            rowcount = cursor.rowcount # Berguna untuk SP non-SELECT atau untuk mengetahui status
            return rowcount
        except mysql.connector.Error as err:
            if conn:
                conn.rollback()
            raise err
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def _execute_ddl_block(self, ddl_string):
        """Mengeksekusi satu blok DDL string."""
        try:
            ddl_string = ddl_string.strip()
            if ddl_string: # Pastikan string tidak kosong
                 # Tandai sebagai DDL agar execute_query menanganinya dengan tepat
                self.execute_query(ddl_string, is_ddl=True)
        except mysql.connector.Error as e:
            # Daftar error number yang umum untuk objek yang sudah ada
            existing_object_errors = [
                mysql.connector.errorcode.ER_TABLE_EXISTS_ERROR,
                mysql.connector.errorcode.ER_VIEW_EXISTS,
                mysql.connector.errorcode.ER_SP_ALREADY_EXISTS, # Stored Procedure
                mysql.connector.errorcode.ER_TRG_ALREADY_EXISTS, # Trigger
                mysql.connector.errorcode.ER_DB_CREATE_EXISTS, # Database
                mysql.connector.errorcode.ER_INDEX_EXISTS # Jika ada CREATE INDEX eksplisit
                # Mungkin ada error lain terkait "already exists"
            ]
            if e.errno in existing_object_errors or "already exists" in e.msg.lower(): # Periksa juga pesan error
                print(f"Info: Objek DDL sudah ada atau operasi serupa sudah dilakukan, dilewati. Detail: {str(e)[:150]}")
            else:
                # Cetak query yang bermasalah untuk debugging
                print(f"Error saat eksekusi DDL block: {e}\nQuery Bermasalah:\n{ddl_string[:500]}{'...' if len(ddl_string) > 500 else ''}")
                raise # Re-raise error jika bukan karena objek sudah ada

    # ... sisa kelas DatabaseManager (initialize_database, dll.) tetap sama ...
    # Pastikan metode initialize_database memanggil _execute_ddl_block untuk setiap DDL
    def initialize_database(self):
        """Membuat tabel, view, trigger, dan stored procedure."""
        # DDL untuk Tabel
        base_tables_ddl = [
            """CREATE TABLE IF NOT EXISTS Role (
                Role_ID INT PRIMARY KEY,
                Nama_Role VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            """CREATE TABLE IF NOT EXISTS Pengguna (
                ID_Pengguna INT PRIMARY KEY,
                Nama VARCHAR(100) NOT NULL,
                Role_ID INT,
                NIM_NIP VARCHAR(50) UNIQUE,
                Username VARCHAR(50) UNIQUE NOT NULL,
                Password VARCHAR(255) NOT NULL,
                FOREIGN KEY (Role_ID) REFERENCES Role(Role_ID) ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            """CREATE TABLE IF NOT EXISTS Kegiatan (
                ID_Kegiatan VARCHAR(10) PRIMARY KEY,
                Nama_Kegiatan VARCHAR(100) NOT NULL,
                Tanggal VARCHAR(20),
                Tempat VARCHAR(100),
                Jenis_Kegiatan VARCHAR(50),
                ID_Penanggung_Jawab INT,
                FOREIGN KEY (ID_Penanggung_Jawab) REFERENCES Pengguna(ID_Pengguna) ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
        ]
        for ddl in base_tables_ddl:
            self._execute_ddl_block(ddl)

        # DDL untuk Log Table
        log_table_ddl = """
        CREATE TABLE IF NOT EXISTS Log_Perubahan_Kegiatan (
            ID_Log INT AUTO_INCREMENT PRIMARY KEY,
            ID_Kegiatan_Ref VARCHAR(10),
            Aksi VARCHAR(50) NOT NULL,
            Timestamp_Aksi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            Detail_Lama TEXT,
            Detail_Baru TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
        self._execute_ddl_block(log_table_ddl)

        # DDL untuk View
        view_ddl = """
        CREATE OR REPLACE VIEW View_Detail_Kegiatan AS
        SELECT
            K.ID_Kegiatan, K.Nama_Kegiatan, K.Tanggal, K.Tempat, K.Jenis_Kegiatan,
            P.Nama AS Nama_Penanggung_Jawab, R.Nama_Role AS Role_Penanggung_Jawab,
            K.ID_Penanggung_Jawab
        FROM Kegiatan K
        LEFT JOIN Pengguna P ON K.ID_Penanggung_Jawab = P.ID_Pengguna
        LEFT JOIN Role R ON P.Role_ID = R.Role_ID
        """
        self._execute_ddl_block(view_ddl)

        # DDL untuk Triggers dan Stored Procedures
        # Setiap DDL ini akan dieksekusi sebagai satu blok/perintah
        trigger_insert_ddl = """
        CREATE TRIGGER IF NOT EXISTS TRG_Kegiatan_After_Insert
        AFTER INSERT ON Kegiatan
        FOR EACH ROW
        BEGIN
            INSERT INTO Log_Perubahan_Kegiatan (ID_Kegiatan_Ref, Aksi, Detail_Baru)
            VALUES (NEW.ID_Kegiatan, 'INSERT',
                    CONCAT('ID: ', NEW.ID_Kegiatan,
                           ', Nama: ', NEW.Nama_Kegiatan,
                           ', Tanggal: ', NEW.Tanggal,
                           ', Tempat: ', NEW.Tempat,
                           ', Jenis: ', NEW.Jenis_Kegiatan,
                           ', PJ_ID: ', IFNULL(NEW.ID_Penanggung_Jawab, 'NULL'))
                   );
        END
        """
        self._execute_ddl_block(trigger_insert_ddl)

        trigger_update_ddl = """
        CREATE TRIGGER IF NOT EXISTS TRG_Kegiatan_After_Update
        AFTER UPDATE ON Kegiatan
        FOR EACH ROW
        BEGIN
            DECLARE detail_lama_str TEXT;
            DECLARE detail_baru_str TEXT;
            SET detail_lama_str = CONCAT('ID: ', OLD.ID_Kegiatan, ', Nama: ', OLD.Nama_Kegiatan, ', Tanggal: ', OLD.Tanggal, ', Tempat: ', OLD.Tempat, ', Jenis: ', OLD.Jenis_Kegiatan, ', PJ_ID: ', IFNULL(OLD.ID_Penanggung_Jawab, 'NULL'));
            SET detail_baru_str = CONCAT('ID: ', NEW.ID_Kegiatan, ', Nama: ', NEW.Nama_Kegiatan, ', Tanggal: ', NEW.Tanggal, ', Tempat: ', NEW.Tempat, ', Jenis: ', NEW.Jenis_Kegiatan, ', PJ_ID: ', IFNULL(NEW.ID_Penanggung_Jawab, 'NULL'));
            IF detail_lama_str <> detail_baru_str THEN
                INSERT INTO Log_Perubahan_Kegiatan (ID_Kegiatan_Ref, Aksi, Detail_Lama, Detail_Baru)
                VALUES (NEW.ID_Kegiatan, 'UPDATE', detail_lama_str, detail_baru_str);
            END IF;
        END
        """
        self._execute_ddl_block(trigger_update_ddl)

        trigger_delete_ddl = """
        CREATE TRIGGER IF NOT EXISTS TRG_Kegiatan_Before_Delete
        BEFORE DELETE ON Kegiatan
        FOR EACH ROW
        BEGIN
            INSERT INTO Log_Perubahan_Kegiatan (ID_Kegiatan_Ref, Aksi, Detail_Lama)
            VALUES (OLD.ID_Kegiatan, 'DELETE',
                    CONCAT('ID: ', OLD.ID_Kegiatan,
                           ', Nama: ', OLD.Nama_Kegiatan,
                           ', Tanggal: ', OLD.Tanggal,
                           ', Tempat: ', OLD.Tempat,
                           ', Jenis: ', OLD.Jenis_Kegiatan,
                           ', PJ_ID: ', IFNULL(OLD.ID_Penanggung_Jawab, 'NULL'))
                   );
        END
        """
        self._execute_ddl_block(trigger_delete_ddl)

        sp_tambah_ddl = """
        CREATE PROCEDURE IF NOT EXISTS SP_TambahKegiatan (
            IN p_ID_Kegiatan VARCHAR(10), IN p_Nama_Kegiatan VARCHAR(100), IN p_Tanggal VARCHAR(20),
            IN p_Tempat VARCHAR(100), IN p_Jenis_Kegiatan VARCHAR(50), IN p_ID_Penanggung_Jawab INT
        )
        BEGIN
            IF EXISTS (SELECT 1 FROM Kegiatan WHERE ID_Kegiatan = p_ID_Kegiatan) THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: ID Kegiatan sudah ada.';
            ELSE
                INSERT INTO Kegiatan (ID_Kegiatan, Nama_Kegiatan, Tanggal, Tempat, Jenis_Kegiatan, ID_Penanggung_Jawab)
                VALUES (p_ID_Kegiatan, p_Nama_Kegiatan, p_Tanggal, p_Tempat, p_Jenis_Kegiatan, p_ID_Penanggung_Jawab);
            END IF;
        END
        """
        self._execute_ddl_block(sp_tambah_ddl)

        sp_update_ddl = """
        CREATE PROCEDURE IF NOT EXISTS SP_UpdateKegiatan (
            IN p_ID_Kegiatan_Target VARCHAR(10), IN p_Nama_Kegiatan_Baru VARCHAR(100), IN p_Tanggal_Baru VARCHAR(20),
            IN p_Tempat_Baru VARCHAR(100), IN p_Jenis_Kegiatan_Baru VARCHAR(50), IN p_ID_Penanggung_Jawab_Baru INT
        )
        BEGIN
            UPDATE Kegiatan
            SET Nama_Kegiatan = p_Nama_Kegiatan_Baru, Tanggal = p_Tanggal_Baru, Tempat = p_Tempat_Baru,
                Jenis_Kegiatan = p_Jenis_Kegiatan_Baru, ID_Penanggung_Jawab = p_ID_Penanggung_Jawab_Baru
            WHERE ID_Kegiatan = p_ID_Kegiatan_Target;
        END
        """
        self._execute_ddl_block(sp_update_ddl)

        sp_hapus_ddl = """
        CREATE PROCEDURE IF NOT EXISTS SP_HapusKegiatan (
            IN p_ID_Kegiatan VARCHAR(10)
        )
        BEGIN
            DELETE FROM Kegiatan WHERE ID_Kegiatan = p_ID_Kegiatan;
        END
        """
        self._execute_ddl_block(sp_hapus_ddl)
        
        # Inisialisasi data awal
        self._initialize_data_if_empty()

    def _initialize_data_if_empty(self):
        """Mengisi data awal jika tabel kosong."""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM Role")
            if cursor.fetchone()[0] == 0:
                roles = [(1, 'Mahasiswa'), (2, 'Dosen'), (3, 'Staff')]
                # Untuk INSERT banyak baris, is_many=True digunakan
                self.execute_query("INSERT INTO Role (Role_ID, Nama_Role) VALUES (%s, %s)", params=roles, is_many=True)

            cursor.execute("SELECT COUNT(*) FROM Pengguna")
            if cursor.fetchone()[0] == 0:
                pengguna_data = [
                    Pengguna(101, "Paul Fajar", 1, "2025", "Paul_mhs", "PAULPASS"),
                    Pengguna(102, "Dr. Zhafier", 2, "705", "Zhafier_dsn", "ZHAFPASS"),
                    Pengguna(103, "Vijaypal Singh", 3, "2252", "Jay_staff", "JAYPASS")
                ]
                pengguna_tuples = [(p.id_entitas, p.nama, p.role_id, p.nim_nip, p.username, p._password) for p in pengguna_data]
                self.execute_query("INSERT INTO Pengguna (ID_Pengguna, Nama, Role_ID, NIM_NIP, Username, Password) VALUES (%s, %s, %s, %s, %s, %s)", params=pengguna_tuples, is_many=True)

            cursor.execute("SELECT COUNT(*) FROM Kegiatan")
            if cursor.fetchone()[0] == 0:
                kegiatan_awal = [
                    Kegiatan("K001", "Seminar AI", "10-05-2025", "Aula FT", "Seminar", 101),
                    Kegiatan("K002", "Praktikum IoT", "15-05-2025", "Lab Jaringan Komputer", "Praktikum", 102),
                    Kegiatan("K003", "Rapat Dosen Bulanan", "20-05-2025", "Ruang Dosen", "Rapat Dosen", 103),
                ]
                for keg in kegiatan_awal:
                    # Memanggil Stored Procedure untuk menambah kegiatan, bukan INSERT langsung
                    self.call_stored_procedure("SP_TambahKegiatan",
                                                (keg.id_entitas, keg.nama_kegiatan,
                                                 keg.tanggal, keg.tempat,
                                                 keg.jenis_kegiatan, keg.id_penanggung_jawab))
            
            conn.commit() # Commit setelah semua data awal dimasukkan
            print("Data awal berhasil diinisialisasi jika diperlukan.")
        except mysql.connector.Error as err_init_data:
            print(f"Error saat mengisi data awal: {err_init_data}")
            if conn: conn.rollback()
        finally:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()

    # ... (metode lain seperti tambah_kegiatan_obj_db, dll. tetap sama)
    # ... (pastikan semua pemanggilan ke execute_query dari metode lain sudah sesuai,
    #      misalnya tidak menggunakan is_ddl_multi lagi jika tidak perlu)

    def tambah_kegiatan_obj_db(self, kegiatan_obj: 'Kegiatan'): # Tambahkan type hint jika Kegiatan belum didefinisikan
        """Menambah kegiatan ke DB menggunakan objek Kegiatan via Stored Procedure."""
        try:
            self.call_stored_procedure("SP_TambahKegiatan",
                                   (kegiatan_obj.id_entitas, kegiatan_obj.nama_kegiatan,
                                    kegiatan_obj.tanggal, kegiatan_obj.tempat,
                                    kegiatan_obj.jenis_kegiatan, kegiatan_obj.id_penanggung_jawab))
        except mysql.connector.Error as e:
            # Tangani error spesifik dari SP, misal duplikasi ID
            if e.sqlstate == '45000': # SQLSTATE yang kita set di SP untuk error custom
                raise mysql.connector.Error(msg=e.msg, errno=e.errno, sqlstate=e.sqlstate) # Re-raise dengan pesan dari SP
            else:
                raise # Re-raise error lain

    def update_kegiatan_obj_db(self, kegiatan_obj: 'Kegiatan'):
        """Mengupdate kegiatan di DB menggunakan objek Kegiatan via Stored Procedure."""
        return self.call_stored_procedure("SP_UpdateKegiatan",
                                   (kegiatan_obj.id_entitas, kegiatan_obj.nama_kegiatan,
                                    kegiatan_obj.tanggal, kegiatan_obj.tempat,
                                    kegiatan_obj.jenis_kegiatan, kegiatan_obj.id_penanggung_jawab))

    def hapus_kegiatan_db(self, id_keg: str):
        return self.call_stored_procedure("SP_HapusKegiatan", (id_keg,))

    def get_semua_kegiatan_obj_db(self):
        query = """
            SELECT ID_Kegiatan, Nama_Kegiatan, Tanggal, Tempat, Jenis_Kegiatan,
                   ID_Penanggung_Jawab, Nama_Penanggung_Jawab 
            FROM View_Detail_Kegiatan
            ORDER BY STR_TO_DATE(Tanggal, '%d-%m-%Y') DESC, Nama_Kegiatan ASC
        """
        rows = self.execute_query(query, fetch_all=True)
        kegiatan_list = []
        if rows:
            for row in rows:
                # Pastikan urutan indeks sesuai dengan kolom yang di-SELECT dari view
                # ID_Kegiatan=row[0], Nama_Kegiatan=row[1], Tanggal=row[2], Tempat=row[3], Jenis_Kegiatan=row[4],
                # ID_Penanggung_Jawab=row[5], Nama_Penanggung_Jawab=row[6]
                keg = Kegiatan(id_kegiatan=row[0], nama_kegiatan=row[1], tanggal=row[2],
                               tempat=row[3], jenis_kegiatan=row[4], id_penanggung_jawab=row[5])
                kegiatan_list.append({'objek': keg, 'nama_pj': row[6]})
        return kegiatan_list


    def get_semua_pengguna_obj_db(self):
        query = "SELECT ID_Pengguna, Nama, Role_ID, NIM_NIP, Username FROM Pengguna ORDER BY Nama"
        rows = self.execute_query(query, fetch_all=True)
        if rows:
            # Pastikan kelas Pengguna sudah didefinisikan
            return [Pengguna(id_pengguna=row[0], nama=row[1], role_id=row[2], nim_nip=row[3], username=row[4]) for row in rows]
        return []

    def verify_user_credentials(self, username, password):
        query = "SELECT ID_Pengguna, Nama, Role_ID, NIM_NIP, Username FROM Pengguna WHERE Username = %s AND Password = %s"
        user_data = self.execute_query(query, (username, password), fetch_one=True)
        if user_data:
            # Pastikan kelas Pengguna sudah didefinisikan
            return Pengguna(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4])
        return None


    def get_roles_db(self):
        query = "SELECT Role_ID, Nama_Role FROM Role ORDER BY Nama_Role"
        return self.execute_query(query, fetch_all=True)

    def check_username_exists(self, username):
        query = "SELECT 1 FROM Pengguna WHERE Username = %s"
        return self.execute_query(query, (username,), fetch_one=True) is not None

    def check_nimid_exists(self, nim_nip):
        query = "SELECT 1 FROM Pengguna WHERE NIM_NIP = %s"
        return self.execute_query(query, (nim_nip,), fetch_one=True) is not None

    def get_max_pengguna_id(self):
        query = "SELECT MAX(ID_Pengguna) FROM Pengguna"
        result = self.execute_query(query, fetch_one=True)
        return result[0] if result and result[0] is not None else 0

    def add_user_obj_db(self, pengguna_obj: 'Pengguna'): # Tambahkan type hint
        query = """
            INSERT INTO Pengguna (ID_Pengguna, Nama, Role_ID, NIM_NIP, Username, Password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        self.execute_query(query, (pengguna_obj.id_entitas, pengguna_obj.nama, pengguna_obj.role_id,
                                   pengguna_obj.nim_nip, pengguna_obj.username, pengguna_obj._password))


    def get_activity_log_db(self):
        query = """
            SELECT ID_Log, Timestamp_Aksi, Aksi, ID_Kegiatan_Ref, Detail_Lama, Detail_Baru
            FROM Log_Perubahan_Kegiatan
            ORDER BY Timestamp_Aksi DESC
        """
        return self.execute_query(query, fetch_all=True)

# --- Kelas Dasar untuk Dialog UI ---
class BaseDialog:
    """Kelas dasar untuk semua dialog Toplevel."""
    def __init__(self, parent_root, title, geometry="400x300"):
        self.parent_root = parent_root
        self.top = tk.Toplevel(parent_root)
        self.top.title(title)
        self.top.geometry(geometry)
        self.top.resizable(False, False)
        self.top.grab_set() # Membuat dialog modal
        self.top.configure(bg=BG_COLOR)
        self.result = None # Untuk menyimpan hasil dialog jika perlu

        self._setup_styles()
        self._build_ui() # Metode ini akan di-override oleh subclass (Polimorfisme)
        
        self.top.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        """Konfigurasi style umum untuk dialog."""
        s = ttk.Style()
        s.configure(f"{self.__class__.__name__}.TLabel", background=BG_COLOR, font=FONT_STYLE)
        s.configure(f"{self.__class__.__name__}.TEntry", font=FONT_STYLE)
        s.configure(f"{self.__class__.__name__}.TButton", font=FONT_BOLD) # FONT_STYLE diganti FONT_BOLD
        s.configure(f"{self.__class__.__name__}.TCombobox", font=FONT_STYLE)

    def _build_ui(self):
        """Metode placeholder untuk dibangun oleh subclass."""
        raise NotImplementedError("Subclass harus mengimplementasikan _build_ui")

    def _on_close(self):
        """Handler saat dialog ditutup."""
        self.top.destroy()

    def show(self):
        """Menampilkan dialog dan menunggu hingga ditutup."""
        self.parent_root.wait_window(self.top)
        return self.result

# --- Kelas untuk Jendela Login (Mewarisi BaseDialog) ---
class LoginDialog(BaseDialog):
    def __init__(self, parent_root, db_manager: DatabaseManager, open_signup_callback):
        self.db_manager = db_manager
        self.open_signup_callback = open_signup_callback
        self.login_successful = False # Tetap ada untuk kompatibilitas logika di main
        super().__init__(parent_root, "Login Aplikasi Manajemen Kegiatan", "1080x720")

    def _setup_styles(self): # Override untuk style khusus Login
        super()._setup_styles() # Panggil setup style dasar
        s = ttk.Style()
        s.configure("Login.TLabel", background="#FFFFFF", font=(FONT_STYLE[0], 12), padding=5)
        s.configure("Login.TEntry", font=(FONT_STYLE[0], 12), padding=5)
        s.configure("Login.TButton", font=(FONT_STYLE[0], 12, "bold"), padding=10)
        s.configure("Link.TLabel", foreground="blue", font=(FONT_STYLE[0], 10, "underline"), background="#FFFFFF")


    def _build_ui(self): # Polimorfisme: Implementasi spesifik untuk LoginDialog
        try:
            # Pastikan path ke aset benar
            img = Image.open("./assets/LOGIN (1).png")
            img = img.resize((1080, 720), Image.LANCZOS)
            self.bg_image = ImageTk.PhotoImage(img)
            bg_label = ttk.Label(self.top, image=self.bg_image)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except FileNotFoundError:
            print("Peringatan: Gambar latar login './assets/LOGIN (1).png' tidak ditemukan.")
            # self.top.configure(bg="lightgray") # Sudah dihandle oleh BaseDialog
        except Exception as e:
            print(f"Error memuat gambar latar: {e}")
            # self.top.configure(bg="lightgray")

        # Frame dibuat transparan agar gambar latar terlihat
        center_frame = ttk.Frame(self.top, style="TFrame") # Style default TFrame biasanya transparan
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        # Jika TFrame tidak transparan, coba:
        # center_frame = tk.Frame(self.top, bg_color_gambar_atau_transparan)

        ttk.Label(center_frame, text="Username", style="Login.TLabel").grid(row=0, column=0, pady=(0,5), sticky="w")
        self.username_entry = ttk.Entry(center_frame, style="Login.TEntry", width=30)
        self.username_entry.grid(row=1, column=0, pady=(0,10))

        ttk.Label(center_frame, text="Password", style="Login.TLabel").grid(row=2, column=0, pady=(0,5), sticky="w")
        self.password_entry = ttk.Entry(center_frame, show="*", style="Login.TEntry", width=30)
        self.password_entry.grid(row=3, column=0, pady=(0,20))

        self.password_entry.bind("<Return>", self._attempt_login)

        login_button = ttk.Button(center_frame, text="Login", command=self._attempt_login, style="Login.TButton")
        login_button.grid(row=4, column=0, pady=10, sticky="ew")

        signup_label = ttk.Label(center_frame, text="Belum punya akun? Daftar di sini", style="Link.TLabel", cursor="hand2")
        signup_label.grid(row=5, column=0, pady=(10,0))
        signup_label.bind("<Button-1>", lambda e: self.open_signup_callback())

        self.username_entry.focus_set()

    def _on_close(self): # Override jika ada perilaku khusus saat menutup
        print("Jendela login ditutup oleh pengguna.")
        self.login_successful = False
        self.top.destroy()
        # Logika untuk menutup parent_root jika login tidak berhasil dipindahkan ke blok main
        # if not self.login_successful:
        #     self.parent_root.destroy()

    def _attempt_login(self, event=None):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Login Gagal", "Username dan Password harus diisi.", parent=self.top)
            return

        try:
            user_obj = self.db_manager.verify_user_credentials(username, password)
            if user_obj: # Jika objek Pengguna dikembalikan, login berhasil
                messagebox.showinfo("Login Berhasil", f"Login berhasil! Selamat datang {user_obj.nama}.", parent=self.top)
                self.login_successful = True
                self.result = user_obj # Simpan objek pengguna jika perlu diakses setelah dialog
                self.top.destroy()
            else:
                messagebox.showerror("Login Gagal", "Username atau password salah.", parent=self.top)
        except mysql.connector.Error as db_err:
            messagebox.showerror("Error Database", f"Tidak dapat terhubung ke database: {db_err}", parent=self.top)
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan: {e}", parent=self.top)


# --- Kelas untuk Jendela Signup (Mewarisi BaseDialog) ---
class SignupDialog(BaseDialog):
    def __init__(self, parent_root, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.signup_successful = False
        super().__init__(parent_root, "Pendaftaran Pengguna Baru", "500x500") # Geometri disesuaikan

    def _setup_styles(self):
        super()._setup_styles()
        s = ttk.Style()
        s.configure("Signup.TLabel", background=BG_COLOR, font=(FONT_STYLE[0], 11))
        s.configure("Signup.TEntry", font=(FONT_STYLE[0], 11))
        s.configure("Signup.TButton", font=(FONT_STYLE[0], 11, "bold"))
        s.configure("Signup.TCombobox", font=(FONT_STYLE[0], 11))

    def _build_ui(self):
        form_frame = ttk.Frame(self.top, padding="20 20 20 20", style="TFrame") # Pastikan TFrame ada
        form_frame.pack(expand=True, fill=tk.BOTH)

        fields = {
            "Nama Lengkap:": "_nama_entry",
            "NIM/NIP:": "_nimid_entry",
            "Username:": "_username_entry",
            "Password:": "_password_entry",
            "Konfirmasi Password:": "_confirm_password_entry"
        }
        
        row_idx = 0
        for label_text, entry_attr_name in fields.items():
            ttk.Label(form_frame, text=label_text, style="Signup.TLabel").grid(row=row_idx, column=0, sticky="w", pady=5)
            entry = ttk.Entry(form_frame, width=40, style="Signup.TEntry")
            if "Password" in label_text:
                entry.config(show="*")
            entry.grid(row=row_idx, column=1, pady=5, sticky="ew")
            setattr(self, entry_attr_name, entry) # Menyimpan referensi entry
            row_idx += 1
            if entry_attr_name == "_password_entry":
                self._password_entry_ref = entry # Simpan ref khusus untuk bind
            elif entry_attr_name == "_confirm_password_entry":
                 self._confirm_password_entry_ref = entry # Simpan ref khusus untuk bind


        ttk.Label(form_frame, text="Role:", style="Signup.TLabel").grid(row=row_idx, column=0, sticky="w", pady=5)
        self.role_combo = ttk.Combobox(form_frame, state="readonly", width=38, style="Signup.TCombobox")
        self.role_combo.grid(row=row_idx, column=1, pady=5, sticky="ew")
        self._load_roles()
        row_idx +=1
        
        # Binding Return key
        if hasattr(self, '_confirm_password_entry_ref'):
             self._confirm_password_entry_ref.bind("<Return>", self._attempt_signup)


        button_frame = ttk.Frame(form_frame, style="TFrame") # Pastikan TFrame ada
        button_frame.grid(row=row_idx, column=0, columnspan=2, pady=20)

        signup_button = ttk.Button(button_frame, text="Daftar", command=self._attempt_signup, style="Signup.TButton")
        signup_button.pack(side=tk.LEFT, padx=10)

        cancel_button = ttk.Button(button_frame, text="Batal", command=self._on_close, style="Signup.TButton")
        cancel_button.pack(side=tk.LEFT, padx=10)

        if hasattr(self, '_nama_entry'): # Pastikan atribut sudah ada
            self._nama_entry.focus_set()


    def _load_roles(self):
        try:
            roles_data = self.db_manager.get_roles_db()
            if roles_data:
                self.role_map = {nama_role: role_id for role_id, nama_role in roles_data}
                self.role_combo["values"] = list(self.role_map.keys())
                if self.role_combo["values"]:
                    self.role_combo.current(0) # Pilih item pertama jika ada
            else:
                self.role_combo["values"] = []
                self.role_map = {}
        except mysql.connector.Error as db_err:
            messagebox.showerror("Error Database", f"Gagal memuat role: {db_err}", parent=self.top)
            self.role_combo["values"] = []
            self.role_map = {}

    def _attempt_signup(self, event=None):
        nama = self._nama_entry.get().strip()
        nim_nip = self._nimid_entry.get().strip()
        username = self._username_entry.get().strip()
        password = self._password_entry.get()
        confirm_password = self._confirm_password_entry.get()
        role_nama = self.role_combo.get()

        if not all([nama, nim_nip, username, password, confirm_password, role_nama]):
            messagebox.showerror("Pendaftaran Gagal", "Semua field harus diisi.", parent=self.top)
            return

        if password != confirm_password:
            messagebox.showerror("Pendaftaran Gagal", "Password dan Konfirmasi Password tidak cocok.", parent=self.top)
            return

        if len(password) < 6:
            messagebox.showerror("Pendaftaran Gagal", "Password minimal harus 6 karakter.", parent=self.top)
            return

        role_id = self.role_map.get(role_nama)
        if role_id is None:
            messagebox.showerror("Pendaftaran Gagal", "Role tidak valid.", parent=self.top)
            return

        try:
            if self.db_manager.check_username_exists(username):
                messagebox.showerror("Pendaftaran Gagal", f"Username '{username}' sudah digunakan.", parent=self.top)
                return
            if self.db_manager.check_nimid_exists(nim_nip):
                messagebox.showerror("Pendaftaran Gagal", f"NIM/NIP '{nim_nip}' sudah terdaftar.", parent=self.top)
                return

            max_id = self.db_manager.get_max_pengguna_id()
            new_id_pengguna = max_id + 1
            
            # Membuat objek Pengguna baru
            new_user = Pengguna(new_id_pengguna, nama, role_id, nim_nip, username, password)
            self.db_manager.add_user_obj_db(new_user) # Menggunakan metode baru dengan objek

            messagebox.showinfo("Pendaftaran Berhasil", "Pengguna baru berhasil didaftarkan! Silakan login.", parent=self.top)
            self.signup_successful = True
            self.result = new_user # Simpan objek pengguna jika perlu
            self._on_close()

        except mysql.connector.Error as db_err:
            messagebox.showerror("Error Database", f"Gagal mendaftarkan pengguna: {db_err}", parent=self.top)
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan: {e}", parent=self.top)


# --- Kelas untuk Jendela Riwayat Aktivitas (Mewarisi BaseDialog) ---
class ActivityLogDialog(BaseDialog):
    def __init__(self, parent, db_manager: DatabaseManager):
        self.db_manager = db_manager
        super().__init__(parent, "📜 Riwayat Aktivitas Kegiatan", "950x500")

    def _build_ui(self):
        log_frame = ttk.LabelFrame(self.top, text="Log Perubahan Data Kegiatan", padding="10")
        log_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        columns = ("id_log", "timestamp", "aksi", "id_keg_ref", "detail_lama", "detail_baru")
        self.log_tree = ttk.Treeview(log_frame, columns=columns, show="headings")

        col_configs = {
            "id_log": {"text": "ID Log", "width": 60, "anchor": "center"},
            "timestamp": {"text": "Waktu", "width": 150, "anchor": "w"},
            "aksi": {"text": "Aksi", "width": 80, "anchor": "w"},
            "id_keg_ref": {"text": "ID Kegiatan", "width": 100, "anchor": "center"},
            "detail_lama": {"text": "Data Lama", "width": 250, "anchor": "w"},
            "detail_baru": {"text": "Data Baru", "width": 250, "anchor": "w"}
        }
        for col, config in col_configs.items():
            self.log_tree.heading(col, text=config["text"])
            self.log_tree.column(col, width=config["width"], anchor=config["anchor"])


        scrollbar_y = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_tree.yview)
        scrollbar_x = ttk.Scrollbar(log_frame, orient="horizontal", command=self.log_tree.xview)
        self.log_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.log_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        button_frame = ttk.Frame(self.top, style="TFrame") # Pastikan TFrame ada
        button_frame.pack(pady=10)

        refresh_button = ttk.Button(button_frame, text="🔄 Muat Ulang", command=self._load_log_data, style=f"{self.__class__.__name__}.TButton")
        refresh_button.pack(side=tk.LEFT, padx=5)

        close_button = ttk.Button(button_frame, text="Tutup", command=self._on_close, style=f"{self.__class__.__name__}.TButton")
        close_button.pack(side=tk.LEFT, padx=5)

        self._load_log_data()

    def _load_log_data(self):
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        try:
            log_data = self.db_manager.get_activity_log_db()
            if log_data:
                for row in log_data:
                    formatted_row = list(row)
                    if isinstance(row[1], datetime.datetime):
                        formatted_row[1] = row[1].strftime("%Y-%m-%d %H:%M:%S")
                    self.log_tree.insert("", tk.END, values=formatted_row)
            else:
                self.log_tree.insert("", tk.END, values=("", "Tidak ada data log.", "", "", "", ""))
        except mysql.connector.Error as db_err:
            messagebox.showerror("Error Database", f"Gagal memuat riwayat aktivitas: {db_err}", parent=self.top)
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan saat memuat log: {e}", parent=self.top)


# --- Kelas Aplikasi Utama ---
class KegiatanApp:
    def __init__(self, root, db_manager: DatabaseManager):
        self.root = root
        self.db_manager = db_manager
        self.current_user: Pengguna = None # Akan diisi setelah login
        self.selected_kegiatan_obj_for_update: Kegiatan = None # Menyimpan objek Kegiatan yang dipilih
        
        self.root.title("🗂️ Aplikasi Manajemen Kegiatan DTEI (VTS)")
        self.root.configure(bg=BG_COLOR)
        self.root.geometry("1050x850")

        self._setup_styles()
        
        self.pengguna_obj_map = {} # Map: display_name -> objek Pengguna
        self.pengguna_id_to_display_map = {} # Map: id_pengguna -> display_name

        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=FONT_BOLD)
        style.configure("Treeview", font=FONT_STYLE, rowheight=25)
        style.configure("TLabel", background=BG_COLOR, font=FONT_STYLE)
        style.configure("TEntry", font=FONT_STYLE)
        style.configure("TCombobox", font=FONT_STYLE)
        style.map("TCombobox", fieldbackground=[("readonly", "white")])
        style.configure("TButton", font=FONT_STYLE, padding=5)
        style.configure("TLabelframe.Label", font=FONT_BOLD, background=BG_COLOR)

    def _styled_button(self, parent, text, command, style_name="TButton"):
        btn = ttk.Button(parent, text=text, command=command, style=style_name)
        return btn

    def _build_ui(self):
        self._create_input_frame()
        self._create_action_buttons()
        self._create_table_frame()

        self._load_pengguna_ui() # Memuat data pengguna untuk combobox
        self._tampilkan_semua_kegiatan_ui() # Menampilkan data kegiatan awal

    def _create_input_frame(self):
        input_frame = ttk.LabelFrame(self.root, text="Formulir Kegiatan")
        input_frame.pack(fill='x', padx=15, pady=10)
        form_fields_frame = ttk.Frame(input_frame) # style="TFrame"
        form_fields_frame.pack(padx=10, pady=10)

        self.labels_texts_map = {
            "id_kegiatan": "ID Kegiatan:", "nama_kegiatan": "Nama Kegiatan:",
            "tanggal": "Tanggal:", "tempat": "Tempat:",
            "jenis_kegiatan": "Jenis Kegiatan:", "pj": "Penanggung Jawab:"
        }
        self.entries = {}
        self.tempat_options = ["Aula B11", "Auditorium B12", "Labkom1-B11", "Kelas1", "Kelas2",
                               "Kelas3", "Kelas4", "Kelas5", "Kelas6", "Kelas7", "Kelas8",
                               "Kelas9", "Kelas10", "Ruang Rapat A", "Ruang Dosen"]

        tanggal_idx = list(self.labels_texts_map.keys()).index("tanggal")
        
        col_idx_label = 0
        col_idx_widget = 1
        # Layout Grid
        current_row_idx = 0

        # ID Kegiatan
        ttk.Label(form_fields_frame, text=self.labels_texts_map["id_kegiatan"]).grid(row=current_row_idx, column=col_idx_label, sticky="w", padx=5, pady=5)
        self.entries["id_kegiatan"] = ttk.Entry(form_fields_frame, font=FONT_STYLE, width=40)
        self.entries["id_kegiatan"].grid(row=current_row_idx, column=col_idx_widget, sticky="ew", padx=5, pady=5)
        current_row_idx += 1

        # Nama Kegiatan
        ttk.Label(form_fields_frame, text=self.labels_texts_map["nama_kegiatan"]).grid(row=current_row_idx, column=col_idx_label, sticky="w", padx=5, pady=5)
        self.entries["nama_kegiatan"] = ttk.Entry(form_fields_frame, font=FONT_STYLE, width=40)
        self.entries["nama_kegiatan"].grid(row=current_row_idx, column=col_idx_widget, sticky="ew", padx=5, pady=5)
        current_row_idx += 1
        
        # Tanggal (Kalender)
        ttk.Label(form_fields_frame, text=self.labels_texts_map["tanggal"]).grid(row=current_row_idx, column=col_idx_label, sticky="nw", padx=5, pady=5) # sticky nw
        self.cal_tanggal = Calendar(form_fields_frame, selectmode='day', date_pattern='dd-mm-yyyy',
                                    font=FONT_STYLE, showweeknumbers=False, locale='id_ID',
                                    background=BTN_COLOR, foreground='white', bordercolor=BTN_COLOR,
                                    headersbackground=BTN_COLOR, headersforeground='white',
                                    selectbackground=BTN_HOVER, selectforeground='white',
                                    normalbackground='white', normalforeground='black',
                                    weekendbackground='white', weekendforeground='black',
                                    othermonthbackground='lightgray', othermonthforeground='darkgray',
                                    othermonthwebackground='lightgray', othermonthweforeground='darkgray')
        self.cal_tanggal.grid(row=current_row_idx, column=col_idx_widget, sticky="ew", padx=5, pady=5, rowspan=3)
        self.entries["tanggal"] = self.cal_tanggal
        # self.cal_tanggal.bind("<<CalendarSelected>>", self._on_calendar_selected_debug) # Jika perlu debug
        current_row_idx += 3 # Kalender memakan 3 baris efektif

        # Tempat (Combobox)
        ttk.Label(form_fields_frame, text=self.labels_texts_map["tempat"]).grid(row=current_row_idx, column=col_idx_label, sticky="w", padx=5, pady=5)
        self.combo_tempat = ttk.Combobox(form_fields_frame, values=self.tempat_options, state="readonly", width=37, font=FONT_STYLE)
        self.combo_tempat.grid(row=current_row_idx, column=col_idx_widget, sticky="ew", padx=5, pady=5)
        self.entries["tempat"] = self.combo_tempat
        current_row_idx += 1

        # Jenis Kegiatan
        ttk.Label(form_fields_frame, text=self.labels_texts_map["jenis_kegiatan"]).grid(row=current_row_idx, column=col_idx_label, sticky="w", padx=5, pady=5)
        self.entries["jenis_kegiatan"] = ttk.Entry(form_fields_frame, font=FONT_STYLE, width=40)
        self.entries["jenis_kegiatan"].grid(row=current_row_idx, column=col_idx_widget, sticky="ew", padx=5, pady=5)
        current_row_idx += 1

        # Penanggung Jawab (Combobox)
        ttk.Label(form_fields_frame, text=self.labels_texts_map["pj"]).grid(row=current_row_idx, column=col_idx_label, sticky="w", padx=5, pady=5)
        self.combo_pj = ttk.Combobox(form_fields_frame, state="readonly", width=37, font=FONT_STYLE)
        self.combo_pj.grid(row=current_row_idx, column=col_idx_widget, sticky="ew", padx=5, pady=5)
        self.entries["pj"] = self.combo_pj
        current_row_idx += 1

        form_fields_frame.columnconfigure(col_idx_widget, weight=1) # Agar widget input bisa expand


    def _create_action_buttons(self):
        # Frame untuk tombol diletakkan di dalam input_frame agar ikut ter-pack dengan baik
        input_frame_children = self.root.winfo_children()
        # Cari input_frame (biasanya yang terakhir dari jenis LabelFrame)
        target_input_frame = None
        for child in reversed(input_frame_children):
            if isinstance(child, ttk.LabelFrame) and child.cget("text") == "Formulir Kegiatan":
                target_input_frame = child
                break
        
        if not target_input_frame:
            # Fallback jika tidak ditemukan, buat di root (kurang ideal secara layout)
            target_input_frame = self.root 
            print("Peringatan: Frame input_frame tidak ditemukan, tombol diletakkan di root.")

        action_buttons_frame = ttk.Frame(target_input_frame) # style="TFrame"
        action_buttons_frame.pack(pady=20)

        self.btn_simpan = self._styled_button(action_buttons_frame, "➕ Tambah", self._tambah_kegiatan)
        self.btn_simpan.pack(side=tk.LEFT, padx=5)

        self.btn_update = self._styled_button(action_buttons_frame, "✏️ Update", self._update_kegiatan)
        self.btn_update.pack(side=tk.LEFT, padx=5)
        self.btn_update.config(state="disabled")

        self.btn_hapus = self._styled_button(action_buttons_frame, "❌ Hapus", self._hapus_kegiatan)
        self.btn_hapus.pack(side=tk.LEFT, padx=5)

        self.btn_clear_form = self._styled_button(action_buttons_frame, "🧹 Bersihkan Form", self._clear_form_action)
        self.btn_clear_form.pack(side=tk.LEFT, padx=5)

        self.btn_refresh_data = self._styled_button(action_buttons_frame, "🔄 Muat Ulang Data", self._tampilkan_semua_kegiatan_ui)
        self.btn_refresh_data.pack(side=tk.LEFT, padx=5)

        self.btn_activity_log = self._styled_button(action_buttons_frame, "📜 Riwayat Aktivitas", self._open_activity_log_dialog)
        self.btn_activity_log.pack(side=tk.LEFT, padx=5)


    def _create_table_frame(self):
        tabel_frame = ttk.LabelFrame(self.root, text="📋 Daftar Kegiatan (dari View)")
        tabel_frame.pack(fill='both', expand=True, padx=15, pady=10)

        columns_info = {
            "id": {"text": "ID Keg.", "width": 80, "anchor": "w"},
            "nama": {"text": "Nama Kegiatan", "width": 250, "anchor": "w"},
            "tanggal": {"text": "Tanggal", "width": 100, "anchor": "center"},
            "tempat": {"text": "Tempat", "width": 180, "anchor": "w"},
            "jenis": {"text": "Jenis Keg.", "width": 120, "anchor": "w"},
            "pj_nama": {"text": "P. Jawab", "width": 150, "anchor": "w"},
            "pj_id": {"text": "ID PJ", "width": 0, "anchor": "w"} # Kolom tersembunyi
        }
        self.tree = ttk.Treeview(tabel_frame, columns=list(columns_info.keys()), show="headings")

        for col_id, info in columns_info.items():
            self.tree.heading(col_id, text=info["text"])
            self.tree.column(col_id, anchor=info["anchor"], width=info["width"],
                             minwidth=info["width"] if info["width"] > 50 else 50,
                             stretch=tk.NO if info["width"] == 0 else tk.YES)


        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        scrollbar = ttk.Scrollbar(tabel_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill="y")

    def _clear_form_fields(self):
        self.entries["id_kegiatan"].config(state="normal")
        self.entries["id_kegiatan"].delete(0, tk.END)
        self.entries["nama_kegiatan"].delete(0, tk.END)
        self.cal_tanggal.selection_set(datetime.date.today()) # Reset tanggal ke hari ini
        self.combo_tempat.set('')
        self.entries["jenis_kegiatan"].delete(0, tk.END)
        self.combo_pj.set('')
        self.selected_kegiatan_obj_for_update = None # Reset objek yang dipilih

    def _clear_form_action(self):
        self._clear_form_fields()
        self.entries["id_kegiatan"].config(state="normal")
        self.btn_simpan.config(state="normal")
        self.btn_update.config(state="disabled")
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection()[0])

    def _on_tree_select(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            self._clear_form_action()
            return

        item_id = selected_items[0] # ID internal treeview, bukan ID kegiatan
        item_values = self.tree.item(item_id, "values")

        if not item_values or len(item_values) < 7:
            print("Error: Data item tidak lengkap dari treeview.")
            self._clear_form_action()
            return

        self._clear_form_fields()

        id_keg_val, nama_keg_val, tgl_val, tempat_val, jenis_val, _, pj_id_val_hidden = item_values
        
        # Cari objek Kegiatan yang sesuai dari data yang sudah dimuat
        # Ini asumsi bahwa ID kegiatan (id_keg_val) unik dan ada di self.kegiatan_data_cache
        # Jika tidak ada cache, Anda perlu query lagi ke DB atau simpan objek saat memuat tree
        self.selected_kegiatan_obj_for_update = Kegiatan(id_keg_val, nama_keg_val, tgl_val, tempat_val, jenis_val, int(pj_id_val_hidden) if pj_id_val_hidden and pj_id_val_hidden != 'None' else None)


        self.entries["id_kegiatan"].insert(0, id_keg_val)
        self.entries["id_kegiatan"].config(state="readonly")
        self.entries["nama_kegiatan"].insert(0, nama_keg_val)

        try:
            if tgl_val:
                date_obj = datetime.datetime.strptime(tgl_val, "%d-%m-%Y").date()
                self.cal_tanggal.selection_set(date_obj)
            else: # Jika tgl_val kosong atau None
                self.cal_tanggal.selection_set(datetime.date.today())
        except ValueError:
            print(f"Format tanggal salah dari tree: {tgl_val}")
            self.cal_tanggal.selection_set(datetime.date.today()) # Default ke hari ini

        if tempat_val in self.tempat_options:
            self.combo_tempat.set(tempat_val)
        else:
            self.combo_tempat.set('') # Kosongkan jika tidak ada di opsi

        self.entries["jenis_kegiatan"].insert(0, jenis_val)

        if pj_id_val_hidden and pj_id_val_hidden != 'None' and pj_id_val_hidden.strip():
            try:
                pj_id_int = int(pj_id_val_hidden)
                pj_display_text = self.pengguna_id_to_display_map.get(pj_id_int)
                if pj_display_text:
                    self.combo_pj.set(pj_display_text)
                else:
                    self.combo_pj.set('') # PJ tidak ditemukan
            except ValueError:
                self.combo_pj.set('')
                print(f"ID PJ tidak valid: {pj_id_val_hidden}")
        else:
            self.combo_pj.set('') # Tidak ada PJ

        self.btn_simpan.config(state="disabled")
        self.btn_update.config(state="normal")

    def _load_pengguna_ui(self):
        try:
            pengguna_list_obj = self.db_manager.get_semua_pengguna_obj_db() # Dapat list objek Pengguna
            if pengguna_list_obj:
                self.pengguna_obj_map = {p_obj.get_display_name(): p_obj for p_obj in pengguna_list_obj}
                self.pengguna_id_to_display_map = {p_obj.id_entitas: p_obj.get_display_name() for p_obj in pengguna_list_obj}
                self.combo_pj["values"] = list(self.pengguna_obj_map.keys())
            else:
                self.combo_pj["values"] = []
                self.pengguna_obj_map = {}
                self.pengguna_id_to_display_map = {}
        except mysql.connector.Error as err:
            messagebox.showerror("Error Database", f"Gagal memuat data pengguna: {err}", parent=self.root)


    def _get_form_data_as_kegiatan_object(self, for_update=False):
        """Mengambil data dari form dan mengembalikannya sebagai objek Kegiatan."""
        id_keg = self.entries["id_kegiatan"].get().strip()
        if for_update and self.selected_kegiatan_obj_for_update:
            id_keg = self.selected_kegiatan_obj_for_update.id_entitas # Gunakan ID dari objek yang dipilih untuk update

        nama = self.entries["nama_kegiatan"].get().strip()
        
        tanggal_obj_from_cal = self.cal_tanggal.get_date() # Ini adalah objek datetime.date
        tanggal_str = ""
        if isinstance(tanggal_obj_from_cal, datetime.date):
            tanggal_str = tanggal_obj_from_cal.strftime("%d-%m-%Y")
        elif isinstance(tanggal_obj_from_cal, str) and tanggal_obj_from_cal: # Jika get_date() mengembalikan string
             try:
                parsed_date = datetime.datetime.strptime(tanggal_obj_from_cal, "%d-%m-%Y").date()
                tanggal_str = parsed_date.strftime("%d-%m-%Y")
             except ValueError:
                messagebox.showerror("Error Tanggal", f"Format tanggal dari kalender ('{tanggal_obj_from_cal}') tidak valid.", parent=self.root)
                return None # Indikasi error
        else: # tanggal_obj_from_cal adalah None atau tipe tidak dikenal
            messagebox.showwarning("Validasi Gagal", "Tanggal harus dipilih.", parent=self.root)
            return None # Indikasi error


        tempat = self.combo_tempat.get().strip()
        jenis = self.entries["jenis_kegiatan"].get().strip()
        pj_display_name = self.combo_pj.get()

        if not all([id_keg, nama, tanggal_str, tempat, jenis, pj_display_name]):
            messagebox.showwarning("⚠️ Validasi Gagal", "Semua kolom formulir harus diisi.", parent=self.root)
            return None

        selected_pengguna_obj = self.pengguna_obj_map.get(pj_display_name)
        if not selected_pengguna_obj:
            messagebox.showerror("Error Internal", "Penanggung jawab tidak valid.", parent=self.root)
            return None
        id_pj = selected_pengguna_obj.id_entitas

        return Kegiatan(id_keg, nama, tanggal_str, tempat, jenis, id_pj)


    def _tambah_kegiatan(self):
        kegiatan_baru = self._get_form_data_as_kegiatan_object()
        if not kegiatan_baru:
            return # Validasi gagal atau error saat ambil data form

        try:
            self.db_manager.tambah_kegiatan_obj_db(kegiatan_baru)
            messagebox.showinfo("✅ Sukses", f"Kegiatan '{kegiatan_baru.nama_kegiatan}' berhasil ditambahkan.", parent=self.root)
            self._tampilkan_semua_kegiatan_ui()
            self._clear_form_action()
        except mysql.connector.Error as db_err:
            if db_err.errno == 1062 or (hasattr(db_err, 'msg') and 'ID Kegiatan sudah ada.' in db_err.msg) :
                 messagebox.showerror("❌ Error Duplikasi", f"ID Kegiatan '{kegiatan_baru.id_entitas}' sudah terdaftar atau ada error SP terkait duplikasi.", parent=self.root)
            else:
                 messagebox.showerror("❌ Error Database", f"Gagal menambah kegiatan: {db_err}", parent=self.root)
        except Exception as e:
            messagebox.showerror("❌ Kesalahan Umum", f"Terjadi kesalahan tak terduga: {e}", parent=self.root)


    def _update_kegiatan(self):
        if not self.selected_kegiatan_obj_for_update:
            messagebox.showwarning("⚠️ Peringatan", "Tidak ada kegiatan yang dipilih untuk diupdate.", parent=self.root)
            return

        kegiatan_update = self._get_form_data_as_kegiatan_object(for_update=True)
        if not kegiatan_update:
            return # Validasi gagal

        try:
            self.db_manager.update_kegiatan_obj_db(kegiatan_update)
            messagebox.showinfo("✅ Sukses", f"Kegiatan (ID: {kegiatan_update.id_entitas}) berhasil diperbarui.", parent=self.root)
            self._tampilkan_semua_kegiatan_ui()
            self._clear_form_action()
        except mysql.connector.Error as db_err:
             messagebox.showerror("❌ Error Database", f"Gagal memperbarui kegiatan: {db_err}", parent=self.root)
        except Exception as e:
            messagebox.showerror("❌ Kesalahan Umum", f"Terjadi kesalahan tak terduga saat update: {e}", parent=self.root)

    def _hapus_kegiatan(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("⚠️ Peringatan", "Pilih satu kegiatan yang ingin dihapus.", parent=self.root)
            return
        if len(selected_items) > 1: # Seharusnya tidak terjadi karena treeview single select
            messagebox.showwarning("⚠️ Peringatan", "Hanya bisa menghapus satu kegiatan dalam satu waktu.", parent=self.root)
            return

        id_keg_to_delete = self.tree.item(selected_items[0], "values")[0]
        nama_keg_to_delete = self.tree.item(selected_items[0], "values")[1]


        if not messagebox.askyesno("❓ Konfirmasi Hapus", f"Anda yakin ingin menghapus kegiatan '{nama_keg_to_delete}' (ID: {id_keg_to_delete})?", parent=self.root):
            return

        try:
            self.db_manager.hapus_kegiatan_db(id_keg_to_delete)
            messagebox.showinfo("🗑️ Sukses", f"Kegiatan ID: {id_keg_to_delete} berhasil dihapus.", parent=self.root)
            self._tampilkan_semua_kegiatan_ui()
            self._clear_form_action()
        except mysql.connector.Error as err:
            messagebox.showerror("❌ Error Database", f"Gagal menghapus ID {id_keg_to_delete}: {err}", parent=self.root)


    def _tampilkan_semua_kegiatan_ui(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            # get_semua_kegiatan_obj_db mengembalikan list dict {'objek':Kegiatan, 'nama_pj':str}
            kegiatan_data_list = self.db_manager.get_semua_kegiatan_obj_db()
            if kegiatan_data_list:
                self.kegiatan_data_cache = {} # Untuk menyimpan objek kegiatan jika perlu diakses nanti
                for data_item in kegiatan_data_list:
                    keg_obj = data_item['objek']
                    nama_pj = data_item['nama_pj']
                    self.kegiatan_data_cache[keg_obj.id_entitas] = keg_obj # Cache objeknya
                    
                    # Pastikan tanggal adalah string yang diformat
                    tanggal_display = keg_obj.tanggal
                    if isinstance(keg_obj.tanggal, datetime.date):
                        tanggal_display = keg_obj.tanggal.strftime("%d-%m-%Y")
                    
                    display_values = keg_obj.to_tuple_for_display(nama_pj=nama_pj)
                    self.tree.insert("", "end", values=display_values) # iid tidak di-set, akan otomatis
            else:
                 self.kegiatan_data_cache = {}
        except mysql.connector.Error as err:
            messagebox.showerror("Error Database", f"Gagal memuat daftar kegiatan: {err}", parent=self.root)

    def _open_activity_log_dialog(self):
        log_dialog = ActivityLogDialog(self.root, self.db_manager)
        log_dialog.show() # Menggunakan metode show dari BaseDialog

# --- Titik Masuk Aplikasi ---
def main():
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASS = "" # Isi password database Anda jika ada
    DB_NAME = "ManajemenKegiatanDTEI_VTS_OOP" # Nama DB bisa disesuaikan

    main_root = tk.Tk()
    main_root.withdraw() # Sembunyikan jendela utama awal

    db_manager = DatabaseManager(DB_HOST, DB_USER, DB_PASS, DB_NAME)

    try:
        print(f"Menginisialisasi database '{DB_NAME}'...")
        db_manager.initialize_database()
        print("Inisialisasi database selesai.")
    except Exception as e:
        messagebox.showerror("Kritikal: Inisialisasi Database Gagal", f"Aplikasi tidak dapat dimulai.\nError: {e}")
        print(f"Kritikal: Inisialisasi Database Gagal - {e}")
        main_root.destroy()
        return # Keluar dari fungsi main

    def do_open_signup():
        signup_dialog = SignupDialog(main_root, db_manager)
        signup_dialog.show() # Tampilkan dialog signup

    # Proses Login
    login_dialog = LoginDialog(main_root, db_manager, do_open_signup)
    # login_dialog.show() # Tidak perlu karena kita cek login_successful secara manual

    # Modifikasi loop login agar parent_root tidak hancur prematur
    main_root.wait_window(login_dialog.top) # Tunggu dialog login selesai

    if hasattr(login_dialog, 'login_successful') and login_dialog.login_successful:
        current_user_obj = login_dialog.result # Ambil objek Pengguna dari hasil dialog
        main_root.deiconify() # Tampilkan jendela utama
        app = KegiatanApp(main_root, db_manager)
        app.current_user = current_user_obj # Set pengguna yang login di aplikasi utama
        print(f"Pengguna login: {current_user_obj.get_details_string()}") # Polimorfisme contoh
        
        # Contoh penggunaan polimorfisme dengan objek Kegiatan
        # if app.kegiatan_data_cache:
        #    first_keg_id = list(app.kegiatan_data_cache.keys())[0]
        #    first_keg_obj = app.kegiatan_data_cache[first_keg_id]
        #    print(f"Detail kegiatan pertama: {first_keg_obj.get_details_string()}")

        main_root.mainloop()
    else:
        print("Login gagal atau jendela login ditutup. Aplikasi keluar.")
        main_root.destroy() # Hancurkan root jika login tidak berhasil


if __name__ == "__main__":
    main()