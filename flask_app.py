from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Configuração do Banco de Dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'users.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # IMPORTANTE: Permite acessar colunas pelo nome
    return conn

def init_db():
    try:
        conn = get_db_connection()

        # 1. Tabela de Usuários
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                     (email TEXT PRIMARY KEY, password TEXT, name TEXT,
                      birth_year TEXT, gender TEXT, contact TEXT, image_uri TEXT,
                      notif_water INTEGER, notif_meds INTEGER, notif_practice INTEGER,
                      notif_news INTEGER, notif_sound INTEGER)''')

        # 2. Tabela de Dor
        conn.execute('''CREATE TABLE IF NOT EXISTS pain_records
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      email TEXT, level INTEGER, date TEXT, full_date TEXT, location_count TEXT)''')

        # 3. Tabela de Práticas
        conn.execute('''CREATE TABLE IF NOT EXISTS practice_records
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      email TEXT, name TEXT, date TEXT, duration TEXT)''')

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao iniciar banco: {e}")

# Inicia o banco
with app.app_context():
    init_db()

@app.route('/')
def home():
    return "Servidor CuidArtrite - Lógica de Dia Único Ativa!"

# --- REGISTRO E LOGIN ---

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                  (data.get('email'), data.get('password'), data.get('name')))
        conn.commit()
        conn.close()
        return jsonify({"message": "Criado", "status": "ok"}), 201
    except Exception as e:
        return jsonify({"message": str(e), "status": "error"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    try:
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()

        if user:
            # Busca Históricos
            pain_rows = conn.execute("SELECT level, date, full_date, location_count FROM pain_records WHERE email=?", (email,)).fetchall()
            pain_list = [dict(row) for row in pain_rows]

            prac_rows = conn.execute("SELECT name, date, duration FROM practice_records WHERE email=?", (email,)).fetchall()
            prac_list = [dict(row) for row in prac_rows]

            conn.close()

            return jsonify({
                "status": "ok",
                "userName": user['name'],
                "birthYear": user['birth_year'] or "",
                "gender": user['gender'] or "",
                "contact": user['contact'] or "",
                "imageUri": user['image_uri'] or "",
                "notifWater": bool(user['notif_water']),
                "notifMeds": bool(user['notif_meds']),
                "notifPractice": bool(user['notif_practice']),
                "notifNews": bool(user['notif_news']),
                "notifSound": bool(user['notif_sound']),
                "painHistory": pain_list,
                "practicesHistory": prac_list
            }), 200
        else:
            conn.close()
            return jsonify({"status": "error", "message": "Login falhou"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update_user', methods=['POST'])
def update_user():
    data = request.get_json()
    try:
        conn = get_db_connection()
        conn.execute('''UPDATE users SET name=?, birth_year=?, gender=?, contact=?, image_uri=?, notif_water=?, notif_meds=?, notif_practice=?, notif_news=?, notif_sound=? WHERE email=?''',
                     (data.get('userName'), data.get('userBirthYear'), data.get('userGender'), data.get('userContact'), data.get('profileImageUriString'), data.get('notifWater'), data.get('notifMeds'), data.get('notifPractice'), data.get('notifNews'), data.get('notifSound'), data.get('email')))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

# --- SALVAR PROGRESSO (LÓGICA AJUSTADA) ---

@app.route('/add_pain', methods=['POST'])
def add_pain():
    data = request.get_json()
    email = data.get('email')
    date_short = data.get('date') # Ex: "02/12" (Usado para verificar duplicidade no dia)

    try:
        conn = get_db_connection()

        # 1. VERIFICA SE JÁ EXISTE REGISTRO HOJE
        cursor = conn.execute("SELECT id FROM pain_records WHERE email=? AND date=?", (email, date_short))
        existing_record = cursor.fetchone()

        if existing_record:
            # --- ATUALIZA (UPDATE) ---
            conn.execute("UPDATE pain_records SET level=?, full_date=?, location_count=? WHERE id=?",
                         (data.get('level'), data.get('fullDate'), data.get('locationCount'), existing_record['id']))
            message = "Registro atualizado"
        else:
            # --- CRIA NOVO (INSERT) ---
            conn.execute("INSERT INTO pain_records (email, level, date, full_date, location_count) VALUES (?, ?, ?, ?, ?)",
                         (email, data.get('level'), date_short, data.get('fullDate'), data.get('locationCount')))
            message = "Registro criado"

        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "message": message}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/add_practice', methods=['POST'])
def add_practice():
    data = request.get_json()
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO practice_records (email, name, date, duration) VALUES (?, ?, ?, ?)",
                     (data.get('email'), data.get('name'), data.get('date'), data.get('duration')))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"}), 201
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run()