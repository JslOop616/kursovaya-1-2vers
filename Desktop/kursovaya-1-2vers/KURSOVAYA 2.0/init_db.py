# init_db.py
import sqlite3
import datetime
import os

print("=" * 60)
print("РАСШИРЕННАЯ БАЗА ДАННЫХ УЧЕТА МАТЕРИАЛОВ")
print("=" * 60)

if os.path.exists('database.db'):
    os.remove('database.db')
    print("Старая база удалена\n")

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('PRAGMA foreign_keys = ON;')

print("1. Создание таблиц...")
print("-" * 40)

# ============= СПРАВОЧНИКИ =============

# Пользователи (расширенные)
cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    full_name TEXT,
    department TEXT,
    phone TEXT,
    position TEXT,
    created_at TEXT,
    last_login TEXT,
    is_active INTEGER DEFAULT 1
)
''')
print("  + users")

# Единицы измерения
cursor.execute('''
CREATE TABLE units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    short_name TEXT NOT NULL,
    description TEXT
)
''')
print("  + units")

# Категории материалов (иерархические)
cursor.execute('''
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    parent_id INTEGER,
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
)
''')
print("  + categories")

# Места хранения
cursor.execute('''
CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    address TEXT,
    responsible_person TEXT,
    phone TEXT,
    is_active INTEGER DEFAULT 1
)
''')
print("  + locations")

# ============= ПОСТАВЩИКИ (РАСШИРЕННЫЕ) =============

# Основная информация о поставщиках
cursor.execute('''
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    full_name TEXT,
    short_name TEXT UNIQUE,
    inn TEXT UNIQUE,
    kpp TEXT,
    ogrn TEXT,
    legal_address TEXT,
    actual_address TEXT,
    phone TEXT,
    fax TEXT,
    email TEXT,
    website TEXT,
    contact_person TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    rating INTEGER DEFAULT 3,
    work_start_date TEXT,
    payment_delay_days INTEGER DEFAULT 0,
    tax_system TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT,
    comment TEXT
)
''')
print("  + suppliers")

# Банковские счета поставщиков
cursor.execute('''
CREATE TABLE supplier_bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    bank_name TEXT NOT NULL,
    bik TEXT,
    correspondent_account TEXT,
    checking_account TEXT NOT NULL,
    is_main INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
)
''')
print("  + supplier_bank_accounts")

# Контракты/договоры с поставщиками
cursor.execute('''
CREATE TABLE supplier_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    contract_number TEXT NOT NULL,
    contract_date TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    contract_type TEXT,
    subject TEXT,
    total_amount REAL,
    file_path TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT,
    comment TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
)
''')
print("  + supplier_contracts")

# ============= ОСНОВНЫЕ ТАБЛИЦЫ =============

# Материалы (расширенные)
cursor.execute('''
CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    article TEXT,
    barcode TEXT,
    category_id INTEGER,
    unit_id INTEGER,
    description TEXT,
    min_quantity REAL DEFAULT 0,
    max_quantity REAL DEFAULT 0,
    current_quantity REAL DEFAULT 0,
    reserved_quantity REAL DEFAULT 0,
    price_per_unit REAL DEFAULT 0,
    last_price REAL DEFAULT 0,
    location_id INTEGER,
    weight REAL,
    weight_unit TEXT DEFAULT 'кг',
    is_active INTEGER DEFAULT 1,
    created_by INTEGER,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (unit_id) REFERENCES units(id),
    FOREIGN KEY (location_id) REFERENCES locations(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
)
''')
print("  + materials")

# Проекты
cursor.execute('''
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE,
    description TEXT,
    manager_id INTEGER,
    budget REAL,
    spent REAL DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT,
    FOREIGN KEY (manager_id) REFERENCES users(id)
)
''')
print("  + projects")

# Документы
cursor.execute('''
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL,
    date TEXT NOT NULL,
    type TEXT CHECK(type IN ('invoice', 'waybill', 'act', 'contract', 'other')) NOT NULL,
    supplier_id INTEGER,
    material_id INTEGER,
    quantity REAL,
    price REAL,
    total_amount REAL,
    file_path TEXT,
    created_at TEXT,
    comment TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (material_id) REFERENCES materials(id)
)
''')
print("  + documents")

# Транзакции (движение материалов)
cursor.execute('''
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    type TEXT CHECK(type IN ('receipt', 'expense', 'write_off', 'return', 'move')) NOT NULL,
    quantity REAL NOT NULL,
    date TEXT NOT NULL,
    supplier_id INTEGER,
    project_id INTEGER,
    from_location_id INTEGER,
    to_location_id INTEGER,
    price_per_unit REAL,
    total_amount REAL,
    document_id INTEGER,
    comment TEXT,
    created_by INTEGER,
    created_at TEXT,
    FOREIGN KEY (material_id) REFERENCES materials(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
)
''')
print("  + transactions")

# ============= ДОПОЛНИТЕЛЬНЫЕ ТАБЛИЦЫ =============

# История закупок
cursor.execute('''
CREATE TABLE purchase_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    purchase_date TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    total_amount REAL,
    delivery_days INTEGER,
    invoice_number TEXT,
    quality_rating INTEGER DEFAULT 3,
    created_at TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (material_id) REFERENCES materials(id)
)
''')
print("  + purchase_history")

# Инвентаризация
cursor.execute('''
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    fact_quantity REAL NOT NULL,
    system_quantity REAL NOT NULL,
    difference REAL,
    date TEXT NOT NULL,
    employee_id INTEGER,
    comment TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (material_id) REFERENCES materials(id),
    FOREIGN KEY (employee_id) REFERENCES users(id)
)
''')
print("  + inventory")

# Уведомления
cursor.execute('''
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
''')
print("  + notifications")

print("\n2. Заполнение справочных данных...")
print("-" * 40)

current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
today = datetime.datetime.now().strftime("%Y-%m-%d")

# ============= ЕДИНИЦЫ ИЗМЕРЕНИЯ =============
units = [
    ('штука', 'шт', 'штучный товар'),
    ('килограмм', 'кг', 'весовой товар'),
    ('литр', 'л', 'жидкость'),
    ('метр', 'м', 'длина'),
    ('упаковка', 'уп', 'упакованный товар'),
    ('комплект', 'компл', 'набор деталей'),
    ('пачка', 'пач', 'пачка бумаги/документов'),
    ('рулон', 'рул', 'рулонный материал')
]
cursor.executemany("INSERT INTO units (name, short_name, description) VALUES (?, ?, ?)", units)
print("  + добавлены единицы измерения (%d шт)" % len(units))

# ============= КАТЕГОРИИ (иерархические) =============
categories = [
    ('Сырье и материалы', 'Основные материалы для производства', None, 1),
    ('Топливо и ГСМ', 'Горюче-смазочные материалы', None, 2),
    ('Запчасти и комплектующие', 'Детали для ремонта оборудования', None, 3),
    ('Канцелярия и офис', 'Офисные расходные материалы', None, 4),
    ('Инструмент', 'Ручной и электрический инструмент', None, 5),
    ('Бензин', 'Разные виды бензина', 2, 1),
    ('Дизельное топливо', 'Солярка', 2, 2),
    ('Метизы', 'Болты, гайки, шайбы', 1, 1),
    ('Краски и ЛКМ', 'Лакокрасочные материалы', 1, 2),
]
cursor.executemany("INSERT INTO categories (name, description, parent_id, sort_order) VALUES (?, ?, ?, ?)", categories)
print("  + добавлены категории (%d шт)" % len(categories))

# ============= МЕСТА ХРАНЕНИЯ =============
locations = [
    ('Основной склад', 'ул. Ленина, 10, складской комплекс', 'Петров П.П.', '+7 (999) 111-11-11'),
    ('Склад ГСМ', 'промзона, территория завода, корпус 5', 'Сидоров А.А.', '+7 (999) 222-22-22'),
    ('Цех №1 (расходный склад)', 'территория завода, цех 1', 'Иванов И.И.', '+7 (999) 333-33-33'),
    ('Офис (канцелярия)', 'ул. Ленина, 10, офис 301', 'Петрова Е.С.', '+7 (999) 444-44-44'),
    ('Склад готовой продукции', 'ул. Ленина, 10, склад 2', 'Смирнов Д.Д.', '+7 (999) 555-55-55')
]
cursor.executemany("INSERT INTO locations (name, address, responsible_person, phone) VALUES (?, ?, ?, ?)", locations)
print("  + добавлены места хранения (%d шт)" % len(locations))

# ============= ПОСТАВЩИКИ (расширенные) =============
suppliers = [
    (
        'ООО "НефтьСнаб"', 'Общество с ограниченной ответственностью "НефтьСнаб"', 'НефтьСнаб',
        '7712345678', '771201001', '1027700123456',
        'г. Москва, ул. Нефтяников, д. 15, стр. 1',
        'г. Москва, ул. Нефтяников, д. 15, стр. 1',
        '+7 (495) 111-11-11', '+7 (495) 111-11-12',
        'info@neftsnab.ru', 'www.neftsnab.ru',
        'Игорь Викторович Смирнов', '+7 (999) 111-11-11', 'i.smirnov@neftsnab.ru',
        5, '2010-01-15', 14, 'ОСН', current_time, None,
        'Крупный поставщик нефтепродуктов, доставка в течение 3 дней'
    ),
    (
        'ООО "МеталлТорг"', 'Общество с ограниченной ответственностью "МеталлТорг"', 'МеталлТорг',
        '7723456789', '772201002', '1037700234567',
        'г. Москва, ул. Металлургов, д. 8',
        'г. Москва, ул. Металлургов, д. 8',
        '+7 (495) 222-22-22', '+7 (495) 222-22-23',
        'sales@metalltorg.ru', 'www.metalltorg.ru',
        'Алексей Петрович Иванов', '+7 (999) 222-22-22', 'a.ivanov@metalltorg.ru',
        4, '2012-03-20', 21, 'ОСН', current_time, None,
        'Поставка металлопроката и метизов, высокое качество продукции'
    ),
    (
        'ИП "КанцТрейд"', 'Индивидуальный предприниматель "КанцТрейд"', 'КанцТрейд',
        '7734567890', None, '312773456789012',
        'г. Москва, ул. Канцелярская, д. 3',
        'г. Москва, ул. Канцелярская, д. 3',
        '+7 (495) 333-33-33', None,
        'order@kanctrade.ru', 'www.kanctrade.ru',
        'Елена Сергеевна Соколова', '+7 (999) 333-33-33', 'e.sokolova@kanctrade.ru',
        5, '2015-06-10', 0, 'УСН', current_time, None,
        'Офисные и канцелярские товары, бесплатная доставка по Москве'
    ),
    (
        'ООО "АвтоЗапчасть"', 'ООО "АвтоЗапчасть"', 'АвтоЗапчасть',
        '7745678901', '774501003', '1047700345678',
        'г. Москва, ул. Автозаводская, д. 20',
        'г. Москва, ул. Автозаводская, д. 20',
        '+7 (495) 444-44-44', '+7 (495) 444-44-45',
        'zakaz@avtozap.ru', 'www.avtozap.ru',
        'Дмитрий Николаевич Кузнецов', '+7 (999) 444-44-44', 'd.kuznetsov@avtozap.ru',
        3, '2018-09-05', 7, 'ОСН', current_time, None,
        'Запчасти для спецтехники и грузовых автомобилей'
    ),
    (
        'ООО "СтройКомплект"', 'ООО "СтройКомплект"', 'СтройКомплект',
        '7756789012', '775601004', '1057800456789',
        'г. Москва, ул. Строителей, д. 12',
        'г. Москва, ул. Строителей, д. 12',
        '+7 (495) 555-55-55', '+7 (495) 555-55-56',
        'info@stroykomplekt.ru', 'www.stroykomplekt.ru',
        'Сергей Викторович Морозов', '+7 (999) 555-55-55', 's.morozov@stroykomplekt.ru',
        4, '2016-08-15', 14, 'ОСН', current_time, None,
        'Строительные материалы и инструменты'
    )
]
cursor.executemany('''
    INSERT INTO suppliers (
        name, full_name, short_name, inn, kpp, ogrn,
        legal_address, actual_address, phone, fax, email, website,
        contact_person, contact_phone, contact_email, rating,
        work_start_date, payment_delay_days, tax_system, created_at, updated_at, comment
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', suppliers)
print("  + добавлены поставщики (%d шт)" % len(suppliers))

# ============= БАНКОВСКИЕ СЧЕТА ПОСТАВЩИКОВ =============
bank_accounts = [
    (1, 'ПАО Сбербанк', '044525225', '30101810400000000225', '40702810900000012345', 1),
    (1, 'АО Альфа-Банк', '044525593', '30101810200000000593', '40702810500000067890', 0),
    (2, 'ПАО ВТБ', '044525187', '30101810700000000187', '40702810900000023456', 1),
    (2, 'АО Тинькофф Банк', '044525974', '30101810100000000974', '40702810300000034567', 0),
    (3, 'ПАО Сбербанк', '044525225', '30101810400000000225', '40802810200000045678', 1),
    (4, 'АО Альфа-Банк', '044525593', '30101810200000000593', '40702810300000056789', 1),
    (5, 'ПАО ВТБ', '044525187', '30101810700000000187', '40702810900000067890', 1)
]
cursor.executemany('''
    INSERT INTO supplier_bank_accounts (supplier_id, bank_name, bik, correspondent_account, checking_account, is_main)
    VALUES (?, ?, ?, ?, ?, ?)
''', bank_accounts)
print("  + добавлены банковские счета (%d шт)" % len(bank_accounts))

# ============= КОНТРАКТЫ С ПОСТАВЩИКАМИ =============
contracts = [
    (1, 'НС-2024-01', today, '2024-01-01', '2024-12-31', 'general', 'Поставка нефтепродуктов', 5000000.00, None, 'active', current_time, 'Генеральный договор поставки'),
    (1, 'НС-2024-02', today, '2024-02-01', '2024-06-30', 'additional', 'Дополнительная поставка бензина', 1000000.00, None, 'active', current_time, 'Дополнительное соглашение'),
    (2, 'МТ-2024-01', today, '2024-01-01', '2024-12-31', 'general', 'Поставка метизов и крепежа', 2000000.00, None, 'active', current_time, 'Рамочный договор поставки'),
    (3, 'КТ-2024-01', today, '2024-01-01', '2024-12-31', 'general', 'Поставка канцтоваров', 500000.00, None, 'active', current_time, 'Договор поставки'),
    (4, 'АЗ-2024-01', today, '2024-03-01', '2024-12-31', 'general', 'Поставка запчастей', 1000000.00, None, 'active', current_time, 'Контракт на запчасти'),
    (5, 'СК-2024-01', today, '2024-01-15', '2024-12-31', 'general', 'Поставка стройматериалов', 1500000.00, None, 'active', current_time, 'Договор поставки')
]
cursor.executemany('''
    INSERT INTO supplier_contracts (supplier_id, contract_number, contract_date, start_date, end_date, 
                                   contract_type, subject, total_amount, file_path, status, created_at, comment)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', contracts)
print("  + добавлены контракты (%d шт)" % len(contracts))

# ============= ПОЛЬЗОВАТЕЛИ =============
users = [
    ('admin', 'admin@example.com', 'admin123', 'admin', 'Администратор Системы', 'IT', '+7 (999) 000-00-01', 'Директор', current_time, None, 1),
    ('moderator', 'mod@example.com', 'mod123', 'moderator', 'Модератор Склада', 'Склад', '+7 (999) 000-00-02', 'Начальник склада', current_time, None, 1),
    ('user', 'user@example.com', 'user123', 'user', 'Иванов Иван Иванович', 'Производство', '+7 (999) 000-00-03', 'Инженер', current_time, None, 1),
    ('petrov', 'petrov@example.com', 'petrov123', 'user', 'Петров Петр Петрович', 'Склад', '+7 (999) 000-00-04', 'Кладовщик', current_time, None, 1),
    ('sidorova', 'sidorova@example.com', 'sidorova123', 'user', 'Сидорова Анна Сергеевна', 'Бухгалтерия', '+7 (999) 000-00-05', 'Бухгалтер', current_time, None, 1)
]
cursor.executemany('''
    INSERT INTO users (username, email, password, role, full_name, department, phone, position, created_at, last_login, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', users)
print("  + добавлены пользователи (%d шт)" % len(users))

# ============= ПРОЕКТЫ =============
projects = [
    ('Производство продукции А', 'PR-A-001', 'Основное производство', 3, 1000000, 250000, '2024-01-01', '2024-12-31', 'active', current_time),
    ('Ремонт оборудования', 'PR-R-002', 'Плановый ремонт станков в цехе №1', 3, 200000, 50000, '2024-02-01', '2024-03-15', 'active', current_time),
    ('Офисные нужды', 'PR-O-003', 'Канцелярия и хозяйственные товары', 1, 50000, 15000, '2024-01-01', '2024-12-31', 'active', current_time),
    ('Складская логистика', 'PR-L-004', 'Организация складского учета', 2, 300000, 0, '2024-03-01', '2024-06-01', 'planning', current_time),
    ('Капитальный ремонт', 'PR-K-005', 'Капитальный ремонт здания склада', 1, 500000, 0, '2024-04-01', '2024-08-01', 'planning', current_time)
]
cursor.executemany('''
    INSERT INTO projects (name, code, description, manager_id, budget, spent, start_date, end_date, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', projects)
print("  + добавлены проекты (%d шт)" % len(projects))

# ============= МАТЕРИАЛЫ (расширенные) =============
materials = [
    # id, name, article, barcode, category_id, unit_id, description, min, max, current, reserved, price, last_price, location_id, weight, weight_unit, created_by
    (1, 'Бензин АИ-92', 'GAS-92', '4601234567890', 6, 3, 'Бензин неэтилированный АИ-92', 50, 500, 150, 10, 55.50, 55.50, 2, 0.75, 'кг', 1),
    (2, 'Бензин АИ-95', 'GAS-95', '4601234567891', 6, 3, 'Бензин премиум АИ-95', 40, 400, 80, 5, 60.30, 60.30, 2, 0.75, 'кг', 1),
    (3, 'Масло моторное 10W-40', 'OIL-10W40', '4601234567892', 3, 3, 'Полусинтетическое моторное масло 10W-40', 10, 100, 25, 2, 450.00, 450.00, 1, 1.00, 'л', 1),
    (4, 'Болт М8х20', 'BLT-M8-20', '4601234567893', 8, 1, 'Оцинкованный болт М8х20 мм', 200, 2000, 1500, 100, 5.00, 5.00, 1, 0.01, 'кг', 1),
    (5, 'Болт М10х30', 'BLT-M10-30', '4601234567894', 8, 1, 'Оцинкованный болт М10х30 мм', 150, 1500, 800, 50, 8.50, 8.50, 1, 0.02, 'кг', 1),
    (6, 'Гайка М8', 'NUT-M8', '4601234567895', 8, 1, 'Оцинкованная гайка М8', 200, 2000, 2000, 100, 3.00, 3.00, 1, 0.005, 'кг', 1),
    (7, 'Бумага А4 Снегурочка', 'PAP-A4', '4601234567896', 4, 7, 'Бумага офисная А4 80г/м2, 500 листов', 10, 100, 45, 5, 300.00, 300.00, 4, 2.50, 'кг', 1),
    (8, 'Ручка шариковая синяя', 'PEN-BALL', '4601234567897', 4, 1, 'Ручка шариковая синяя, автоматическая', 20, 500, 100, 10, 15.00, 15.00, 4, 0.01, 'кг', 1),
    (9, 'Краска масляная белая', 'PNT-WH', '4601234567898', 9, 3, 'Краска масляная белая, 1л', 5, 30, 12, 3, 280.00, 280.00, 3, 1.20, 'кг', 1),
    (10, 'Шуруповерт аккумуляторный', 'TOOL-SCR', '4601234567899', 5, 1, 'Аккумуляторный шуруповерт 12V', 2, 10, 5, 1, 3500.00, 3500.00, 3, 1.50, 'кг', 1),
]
cursor.executemany('''
    INSERT INTO materials (
        id, name, article, barcode, category_id, unit_id, description,
        min_quantity, max_quantity, current_quantity, reserved_quantity,
        price_per_unit, last_price, location_id, weight, weight_unit, created_by
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', materials)
print("  + добавлены материалы (%d шт)" % len(materials))

# ============= ТРАНЗАКЦИИ =============
transactions = [
    # Приходы
    (1, 'receipt', 200, current_time, 1, None, None, None, 55.00, 11000.00, None, 'Основная поставка бензина АИ-92', 1, current_time),
    (2, 'receipt', 30, current_time, 1, None, None, None, 60.00, 1800.00, None, 'Поставка бензина АИ-95', 1, current_time),
    (3, 'receipt', 30, current_time, 1, None, None, None, 440.00, 13200.00, None, 'Поставка моторного масла', 1, current_time),
    (4, 'receipt', 500, current_time, 2, None, None, None, 5.00, 2500.00, None, 'Поставка болтов М8', 1, current_time),
    (5, 'receipt', 300, current_time, 2, None, None, None, 8.50, 2550.00, None, 'Поставка болтов М10', 1, current_time),
    (6, 'receipt', 1000, current_time, 2, None, None, None, 3.00, 3000.00, None, 'Поставка гаек М8', 1, current_time),
    (7, 'receipt', 50, current_time, 3, None, None, None, 290.00, 14500.00, None, 'Поставка канцелярии', 1, current_time),
    (8, 'receipt', 100, current_time, 3, None, None, None, 15.00, 1500.00, None, 'Поставка ручек', 1, current_time),
    (9, 'receipt', 20, current_time, 5, None, None, None, 280.00, 5600.00, None, 'Поставка краски', 1, current_time),
    # Расходы
    (1, 'expense', 30, current_time, None, 1, None, None, 55.50, 1665.00, None, 'Заправка техники в цехе', 2, current_time),
    (4, 'expense', 200, current_time, None, 2, None, None, 5.00, 1000.00, None, 'Ремонт станка в цехе №1', 2, current_time),
    (7, 'expense', 5, current_time, None, 3, None, None, 300.00, 1500.00, None, 'Печать документов для отдела кадров', 2, current_time),
    (3, 'expense', 5, current_time, None, 1, None, None, 450.00, 2250.00, None, 'Замена масла в оборудовании', 2, current_time),
    (8, 'expense', 30, current_time, None, 3, None, None, 15.00, 450.00, None, 'Выдача ручек сотрудникам', 2, current_time),
]
cursor.executemany('''
    INSERT INTO transactions (
        material_id, type, quantity, date, supplier_id, project_id,
        from_location_id, to_location_id, price_per_unit, total_amount,
        document_id, comment, created_by, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', transactions)
print("  + добавлены транзакции (%d шт)" % len(transactions))

# ============= ИСТОРИЯ ЗАКУПОК =============
purchase_history = [
    (1, 1, '2024-01-15', 200, 55.00, 11000.00, 3, 'СЧ-001', 5, current_time),
    (1, 2, '2024-01-15', 30, 60.00, 1800.00, 3, 'СЧ-001', 5, current_time),
    (1, 3, '2024-01-20', 30, 440.00, 13200.00, 5, 'СЧ-002', 4, current_time),
    (2, 4, '2024-01-25', 500, 5.00, 2500.00, 2, 'СЧ-003', 5, current_time),
    (2, 5, '2024-02-01', 300, 8.50, 2550.00, 3, 'СЧ-004', 5, current_time),
    (2, 6, '2024-02-01', 1000, 3.00, 3000.00, 2, 'СЧ-004', 5, current_time),
    (3, 7, '2024-02-05', 50, 290.00, 14500.00, 1, 'СЧ-005', 5, current_time),
    (3, 8, '2024-02-05', 100, 15.00, 1500.00, 1, 'СЧ-005', 5, current_time),
    (5, 9, '2024-02-10', 20, 280.00, 5600.00, 2, 'СЧ-006', 4, current_time),
]
cursor.executemany('''
    INSERT INTO purchase_history (
        supplier_id, material_id, purchase_date, quantity, price, total_amount,
        delivery_days, invoice_number, quality_rating, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', purchase_history)
print("  + добавлена история закупок (%d шт)" % len(purchase_history))

# ============= ИНВЕНТАРИЗАЦИЯ =============
inventory = [
    (1, 148, 150, -2, '2024-02-01 10:00:00', 2, 'Небольшая недостача после инвентаризации', 'completed'),
    (4, 1480, 1500, -20, '2024-02-01 10:30:00', 2, 'Обнаружена недостача болтов', 'completed'),
    (7, 44, 45, -1, '2024-02-01 11:00:00', 2, 'Одна пачка бумаги списана без оформления', 'completed'),
    (3, 24, 25, -1, '2024-02-15 14:00:00', 2, 'Плановая инвентаризация ГСМ', 'pending'),
]
cursor.executemany('''
    INSERT INTO inventory (material_id, fact_quantity, system_quantity, difference, date, employee_id, comment, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', inventory)
print("  + добавлены записи инвентаризации (%d шт)" % len(inventory))

# ============= УВЕДОМЛЕНИЯ =============
notifications = [
    (3, 'Новый материал добавлен', 'В системе зарегистрирован новый материал "Шуруповерт аккумуляторный"', 'info', 0, current_time),
    (3, 'Низкий остаток', 'Остаток материала "Бензин АИ-92" ниже минимального (150 < 200)', 'warning', 0, current_time),
    (2, 'Поставка ожидается', 'Ожидается поставка от ООО "НефтьСнаб" завтра в 10:00', 'info', 0, current_time),
    (1, 'Инвентаризация', 'Запланирована инвентаризация склада на 01.03.2024', 'info', 0, current_time),
    (4, 'Срочная закупка', 'Требуется срочная закупка болтов М8, остаток критический', 'warning', 0, current_time),
]
cursor.executemany('''
    INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
''', notifications)
print("  + добавлены уведомления (%d шт)" % len(notifications))

# ============= ПРЕДСТАВЛЕНИЯ ДЛЯ ОТЧЕТОВ =============

print("\n3. Создание представлений...")
print("-" * 40)

# Полная информация о материалах
cursor.execute('''
CREATE VIEW IF NOT EXISTS v_materials_full AS
SELECT 
    m.id,
    m.name AS material_name,
    m.article,
    c.name AS category,
    u.short_name AS unit,
    m.current_quantity,
    m.min_quantity,
    m.max_quantity,
    m.reserved_quantity,
    (m.current_quantity - m.reserved_quantity) AS available_quantity,
    CASE 
        WHEN m.current_quantity - m.reserved_quantity < m.min_quantity THEN 'Требуется закупка'
        WHEN m.current_quantity - m.reserved_quantity < m.min_quantity * 1.5 THEN 'Мало'
        ELSE 'Норма'
    END AS status,
    l.name AS location,
    m.price_per_unit,
    m.current_quantity * m.price_per_unit AS total_value,
    m.weight,
    m.weight_unit
FROM materials m
LEFT JOIN categories c ON m.category_id = c.id
LEFT JOIN units u ON m.unit_id = u.id
LEFT JOIN locations l ON m.location_id = l.id
WHERE m.is_active = 1
''')
print("  + v_materials_full")

# Информация о поставщиках с банковскими счетами
cursor.execute('''
CREATE VIEW IF NOT EXISTS v_suppliers_full AS
SELECT 
    s.*,
    (SELECT COUNT(*) FROM supplier_contracts sc WHERE sc.supplier_id = s.id AND sc.status = 'active') AS active_contracts,
    (SELECT SUM(sc.total_amount) FROM supplier_contracts sc WHERE sc.supplier_id = s.id) AS total_contracts_sum,
    (SELECT COUNT(*) FROM purchase_history ph WHERE ph.supplier_id = s.id) AS total_purchases,
    (SELECT AVG(ph.quality_rating) FROM purchase_history ph WHERE ph.supplier_id = s.id) AS avg_quality,
    (SELECT SUM(ph.total_amount) FROM purchase_history ph WHERE ph.supplier_id = s.id) AS total_purchases_sum
FROM suppliers s
WHERE s.is_active = 1
''')
print("  + v_suppliers_full")

# Банковские счета поставщиков
cursor.execute('''
CREATE VIEW IF NOT EXISTS v_supplier_bank_accounts AS
SELECT 
    s.name AS supplier_name,
    s.inn,
    sba.bank_name,
    sba.bik,
    sba.correspondent_account,
    sba.checking_account,
    CASE WHEN sba.is_main = 1 THEN 'Основной' ELSE 'Дополнительный' END AS account_type
FROM supplier_bank_accounts sba
JOIN suppliers s ON sba.supplier_id = s.id
WHERE sba.is_active = 1
''')
print("  + v_supplier_bank_accounts")

# Транзакции с деталями
cursor.execute('''
CREATE VIEW IF NOT EXISTS v_transactions_full AS
SELECT 
    t.id,
    t.date,
    t.type,
    CASE WHEN t.type = 'receipt' THEN 'Приход' ELSE 'Расход' END AS type_name,
    m.name AS material_name,
    u.short_name AS unit,
    t.quantity,
    t.price_per_unit,
    t.total_amount,
    s.name AS supplier_name,
    p.name AS project_name,
    u2.username AS created_by_name,
    t.comment
FROM transactions t
JOIN materials m ON t.material_id = m.id
JOIN units u ON m.unit_id = u.id
LEFT JOIN suppliers s ON t.supplier_id = s.id
LEFT JOIN projects p ON t.project_id = p.id
LEFT JOIN users u2 ON t.created_by = u2.id
ORDER BY t.date DESC
''')
print("  + v_transactions_full")

# Статистика по поставщикам
cursor.execute('''
CREATE VIEW IF NOT EXISTS v_supplier_statistics AS
SELECT 
    s.id,
    s.name,
    s.rating,
    s.contact_person,
    s.phone,
    COUNT(DISTINCT t.id) AS total_deliveries,
    SUM(t.quantity) AS total_quantity,
    SUM(t.total_amount) AS total_amount,
    AVG(t.price_per_unit) AS avg_price,
    COUNT(DISTINCT t.material_id) AS distinct_materials,
    MAX(t.date) AS last_delivery_date,
    s.payment_delay_days
FROM suppliers s
LEFT JOIN transactions t ON s.id = t.supplier_id AND t.type = 'receipt'
WHERE s.is_active = 1
GROUP BY s.id
ORDER BY total_amount DESC
''')
print("  + v_supplier_statistics")

# Материалы с низким остатком для быстрого доступа
cursor.execute('''
CREATE VIEW IF NOT EXISTS v_low_stock AS
SELECT * FROM v_materials_full 
WHERE status IN ('Требуется закупка', 'Мало')
ORDER BY (current_quantity / min_quantity) ASC
''')
print("  + v_low_stock")

# Сводка по проектам
cursor.execute('''
CREATE VIEW IF NOT EXISTS v_project_summary AS
SELECT 
    p.id,
    p.name,
    p.code,
    p.status,
    p.budget,
    p.spent,
    (p.budget - p.spent) AS remaining,
    ROUND((p.spent / p.budget) * 100, 2) AS spent_percent,
    u.full_name AS manager_name
FROM projects p
LEFT JOIN users u ON p.manager_id = u.id
WHERE p.status != 'completed'
''')
print("  + v_project_summary")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("БАЗА ДАННЫХ УСПЕШНО СОЗДАНА")
print("=" * 60)
print("\nНОВАЯ СТРУКТУРА ВКЛЮЧАЕТ:")
print("  - 12 основных таблиц")
print("  - 6 представлений для отчетов")
print("  - Полные реквизиты поставщиков (ИНН, КПП, ОГРН, банковские счета)")
print("  - Контракты и договоры")
print("  - Историю закупок с рейтингом качества")
print("  - Инвентаризацию")
print("  - Уведомления")
print("\nКОЛИЧЕСТВО ДАННЫХ:")
print(f"  - Пользователей: {len(users)}")
print(f"  - Поставщиков: {len(suppliers)}")
print(f"  - Материалов: {len(materials)}")
print(f"  - Транзакций: {len(transactions)}")
print(f"  - Контрактов: {len(contracts)}")
print(f"  - Банковских счетов: {len(bank_accounts)}")
print("\nТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ:")
print("  Администратор: admin     / admin123")
print("  Модератор:     moderator / mod123")
print("  Пользователь:  user      / user123")
print("  Дополнительные: petrov   / petrov123")
print("                 sidorova / sidorova123")
print("\n" + "=" * 60)
print("Для запуска приложения выполните:")
print("  python app.py")
print("=" * 60)