# init_db.py (первая версия — без регистрации)
import sqlite3
import os

print("=" * 50)
print("СОЗДАНИЕ БАЗЫ ДАННЫХ")
print("=" * 50)

if os.path.exists('database.db'):
    os.remove('database.db')
    print("Старая база удалена")

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('PRAGMA foreign_keys = ON;')

print("Создаю таблицы...")

# ============= ТАБЛИЦЫ (упрощенные) =============

# Пользователи (без phone и position)
cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    full_name TEXT,
    department TEXT,
    created_at TEXT,
    is_active INTEGER DEFAULT 1
)
''')
print("  + users")

# Единицы измерения
cursor.execute('''
CREATE TABLE units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    short_name TEXT NOT NULL
)
''')
print("  + units")

# Категории
cursor.execute('''
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
)
''')
print("  + categories")

# Места хранения
cursor.execute('''
CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    address TEXT
)
''')
print("  + locations")

# Поставщики (без расширенных полей)
cursor.execute('''
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    contact_person TEXT,
    phone TEXT,
    email TEXT,
    rating INTEGER DEFAULT 3
)
''')
print("  + suppliers")

# Проекты
cursor.execute('''
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'active'
)
''')
print("  + projects")

# Материалы (упрощенные)
cursor.execute('''
CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER,
    unit_id INTEGER,
    description TEXT,
    min_quantity REAL DEFAULT 0,
    current_quantity REAL DEFAULT 0,
    price_per_unit REAL DEFAULT 0,
    location_id INTEGER,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (unit_id) REFERENCES units(id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
)
''')
print("  + materials")

# Транзакции
cursor.execute('''
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    type TEXT CHECK(type IN ('receipt', 'expense')) NOT NULL,
    quantity REAL NOT NULL,
    date TEXT NOT NULL,
    supplier_id INTEGER,
    project_id INTEGER,
    price_per_unit REAL,
    comment TEXT,
    created_by INTEGER,
    created_at TEXT,
    FOREIGN KEY (material_id) REFERENCES materials(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
)
''')
print("  + transactions")

print("\nЗаполняю тестовыми данными...")

current_time = "2024-01-15 10:00:00"

# Единицы измерения
cursor.executemany("INSERT INTO units (name, short_name) VALUES (?, ?)", [
    ('штука', 'шт'), ('килограмм', 'кг'), ('литр', 'л')
])

# Категории
cursor.executemany("INSERT INTO categories (name) VALUES (?)", [
    ('Сырье',), ('Топливо',), ('Запчасти',)
])

# Места
cursor.executemany("INSERT INTO locations (name) VALUES (?)", [
    ('Основной склад',), ('Склад ГСМ',)
])

# Поставщики
cursor.executemany("INSERT INTO suppliers (name, contact_person, phone, rating) VALUES (?, ?, ?, ?)", [
    ('ООО НефтьСнаб', 'Иван Петрович', '111-111', 5),
    ('ИП Метизы', 'Сергей', '222-222', 4)
])

# Проекты
cursor.executemany("INSERT INTO projects (name, status) VALUES (?, ?)", [
    ('Производство', 'active'), ('Ремонт', 'active')
])

# Пользователи (только тестовые, регистрация отсутствует)
users = [
    ('admin', 'admin@example.com', 'admin123', 'admin', 'Администратор', 'IT', current_time),
    ('moderator', 'mod@example.com', 'mod123', 'moderator', 'Модератор', 'Склад', current_time),
    ('user', 'user@example.com', 'user123', 'user', 'Пользователь', 'Производство', current_time)
]
cursor.executemany('''
    INSERT INTO users (username, email, password, role, full_name, department, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', users)

# Материалы
cursor.executemany('''
    INSERT INTO materials (name, category_id, unit_id, current_quantity, min_quantity, price_per_unit, location_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', [
    ('Бензин АИ-92', 2, 3, 150, 50, 55.5, 2),
    ('Масло моторное', 3, 3, 20, 10, 450, 1),
    ('Болт М8', 1, 1, 1000, 200, 5, 1)
])

# Транзакции
cursor.executemany('''
    INSERT INTO transactions (material_id, type, quantity, date, supplier_id, project_id, price_per_unit, comment, created_by, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', [
    (1, 'receipt', 200, current_time, 1, None, 55, 'Основная поставка', 1, current_time),
    (2, 'receipt', 30, current_time, 2, None, 440, 'Поставка масла', 1, current_time),
    (1, 'expense', 30, current_time, None, 1, 55.5, 'Заправка техники', 2, current_time)
])

conn.commit()
conn.close()

print("=" * 50)
print("БАЗА ДАННЫХ УСПЕШНО СОЗДАНА!")
print("=" * 50)
print("\nТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ (регистрация отсутствует):")
print("  Администратор: admin     / admin123")
print("  Модератор:     moderator / mod123")
print("  Пользователь:  user      / user123")
print("=" * 50)