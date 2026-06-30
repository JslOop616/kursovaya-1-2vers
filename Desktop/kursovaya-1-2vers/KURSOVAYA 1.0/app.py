from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import datetime
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
DATABASE = 'database.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        if not os.path.exists(DATABASE):
            return None
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    db = get_db()
    if db is None:
        return [] if not one else None
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=()):
    db = get_db()
    if db is None:
        return None
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def operator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        if session.get('role') not in ['admin', 'moderator']:
            flash('Доступ запрещен. Только для администраторов и модераторов', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Доступ запрещен. Только для администраторов', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============= АВТОРИЗАЦИЯ =============
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = query_db('SELECT * FROM users WHERE username = ? AND password = ? AND is_active = 1',
                        [username, password], one=True)

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']

            flash(f'Добро пожаловать, {user["full_name"] or user["username"]}!', 'success')

            if user['role'] in ['admin', 'moderator']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль', 'error')

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('login'))


# ============= ДАШБОРДЫ =============
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') in ['admin', 'moderator']:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    stats = query_db('''
        SELECT 
            (SELECT COUNT(*) FROM materials WHERE is_active = 1) as total_materials,
            (SELECT SUM(current_quantity * price_per_unit) FROM materials) as total_value,
            (SELECT COUNT(*) FROM materials WHERE current_quantity < min_quantity) as low_stock_count
    ''', one=True)

    materials = query_db('''
        SELECT 
            m.id,
            m.name AS material_name,
            c.name AS category,
            u.short_name AS unit,
            m.current_quantity,
            m.min_quantity,
            CASE 
                WHEN m.current_quantity < m.min_quantity THEN 'Требуется закупка'
                ELSE 'Норма'
            END AS status,
            l.name AS location,
            m.price_per_unit,
            m.current_quantity * m.price_per_unit AS total_value
        FROM materials m
        LEFT JOIN categories c ON m.category_id = c.id
        LEFT JOIN units u ON m.unit_id = u.id
        LEFT JOIN locations l ON m.location_id = l.id
        WHERE m.is_active = 1
        ORDER BY m.name
    ''')

    low_stock = query_db('''
        SELECT 
            m.id,
            m.name AS material_name,
            u.short_name AS unit,
            m.current_quantity,
            m.min_quantity
        FROM materials m
        LEFT JOIN units u ON m.unit_id = u.id
        WHERE m.current_quantity < m.min_quantity AND m.is_active = 1
    ''')

    return render_template('dashboard.html', stats=stats, materials=materials, low_stock=low_stock)


@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = query_db('''
        SELECT 
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM materials WHERE is_active = 1) as total_materials,
            (SELECT COUNT(*) FROM transactions) as total_transactions,
            (SELECT COUNT(*) FROM suppliers) as total_suppliers,
            (SELECT SUM(current_quantity * price_per_unit) FROM materials) as total_value
    ''', one=True)

    recent_transactions = query_db('''
        SELECT t.*, m.name as material_name, u.short_name as unit, us.username
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        JOIN units u ON m.unit_id = u.id
        LEFT JOIN users us ON t.created_by = us.id
        ORDER BY t.date DESC LIMIT 20
    ''')

    return render_template('admin_dashboard.html', stats=stats, transactions=recent_transactions)


# ============= ОПЕРАЦИИ (только для админов и модераторов) =============
@app.route('/add_receipt', methods=['GET', 'POST'])
@operator_required
def add_receipt():
    if request.method == 'POST':
        try:
            material_id = request.form['material_id']
            supplier_id = request.form['supplier_id']
            quantity = float(request.form['quantity'])
            price = float(request.form['price'])
            comment = request.form['comment']
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            db = get_db()
            cursor = db.cursor()

            cursor.execute('''
                INSERT INTO transactions (material_id, supplier_id, type, quantity, date, price_per_unit, comment, created_by, created_at)
                VALUES (?, ?, 'receipt', ?, ?, ?, ?, ?, ?)
            ''', (material_id, supplier_id if supplier_id else None, quantity, date, price, comment, session['user_id'], date))

            cursor.execute('''
                UPDATE materials 
                SET current_quantity = current_quantity + ?,
                    price_per_unit = ((price_per_unit * current_quantity) + (? * ?)) / (current_quantity + ?)
                WHERE id = ?
            ''', (quantity, price, quantity, quantity, material_id))

            db.commit()
            flash('Приход успешно добавлен', 'success')
            return redirect(url_for('admin_dashboard' if session.get('role') in ['admin', 'moderator'] else 'dashboard'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')

    materials = query_db('SELECT id, name, current_quantity FROM materials WHERE is_active = 1 ORDER BY name')
    suppliers = query_db('SELECT id, name FROM suppliers ORDER BY name')
    return render_template('add_receipt.html', materials=materials, suppliers=suppliers)


@app.route('/add_expense', methods=['GET', 'POST'])
@operator_required
def add_expense():
    if request.method == 'POST':
        try:
            material_id = request.form['material_id']
            quantity = float(request.form['quantity'])
            project_id = request.form.get('project_id')
            comment = request.form['comment']
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            db = get_db()
            cursor = db.cursor()

            material = query_db('SELECT current_quantity, price_per_unit FROM materials WHERE id = ?', [material_id], one=True)
            if material and material['current_quantity'] >= quantity:
                cursor.execute('''
                    INSERT INTO transactions (material_id, type, quantity, date, project_id, price_per_unit, comment, created_by, created_at)
                    VALUES (?, 'expense', ?, ?, ?, ?, ?, ?, ?)
                ''', (material_id, quantity, date, project_id if project_id else None, material['price_per_unit'], comment, session['user_id'], date))

                cursor.execute('''
                    UPDATE materials SET current_quantity = current_quantity - ? WHERE id = ?
                ''', (quantity, material_id))

                db.commit()
                flash('Расход успешно добавлен', 'success')
            else:
                flash(f'Недостаточно материалов! Доступно: {material["current_quantity"]}', 'error')

            return redirect(url_for('admin_dashboard' if session.get('role') in ['admin', 'moderator'] else 'dashboard'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')

    materials = query_db('SELECT id, name, current_quantity FROM materials WHERE is_active = 1 ORDER BY name')
    projects = query_db('SELECT id, name FROM projects WHERE status = "active" ORDER BY name')
    return render_template('add_expense.html', materials=materials, projects=projects)


# ============= ОТЧЕТЫ =============
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')


@app.route('/task1')
@login_required
def task1():
    try:
        current_month = datetime.datetime.now().strftime("%Y-%m")

        query = '''
        SELECT 
            s.id, s.name AS supplier_name, s.contact_person, s.phone, s.email, s.rating,
            COUNT(t.id) AS deliveries_count,
            SUM(t.quantity * t.price_per_unit) AS total_sum,
            SUM(t.quantity) AS total_quantity
        FROM transactions t
        JOIN suppliers s ON t.supplier_id = s.id
        WHERE t.type = 'receipt' AND strftime('%Y-%m', t.date) = ?
        GROUP BY s.id
        ORDER BY total_sum DESC
        LIMIT 1
        '''

        top_supplier = query_db(query, [current_month], one=True)

        if top_supplier:
            details_query = '''
            SELECT t.date, m.name AS material_name, u.short_name AS unit, t.quantity, t.price_per_unit,
                   (t.quantity * t.price_per_unit) AS total
            FROM transactions t
            JOIN materials m ON t.material_id = m.id
            JOIN units u ON m.unit_id = u.id
            WHERE t.supplier_id = ? AND t.type = 'receipt' AND strftime('%Y-%m', t.date) = ?
            ORDER BY t.date DESC
            '''
            deliveries = query_db(details_query, [top_supplier['id'], current_month])
        else:
            deliveries = []

        return render_template('task1.html', supplier=top_supplier, deliveries=deliveries, current_month=current_month)
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
        return redirect(url_for('reports'))


@app.route('/task2')
@login_required
def task2():
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        query = '''
        SELECT t.id, t.date, t.type, m.name AS material_name, u.short_name AS unit, t.quantity,
               CASE WHEN t.type = 'receipt' THEN 'Приход' ELSE 'Расход' END AS type_ru,
               s.name AS supplier_name, p.name AS project_name, t.comment
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        JOIN units u ON m.unit_id = u.id
        LEFT JOIN suppliers s ON t.supplier_id = s.id
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE date(t.date) = ?
        ORDER BY t.date DESC
        '''

        transactions = query_db(query, [today])

        stats_query = '''
        SELECT COUNT(*) as total_count,
               SUM(CASE WHEN type = 'receipt' THEN 1 ELSE 0 END) as receipt_count,
               SUM(CASE WHEN type = 'expense' THEN 1 ELSE 0 END) as expense_count,
               SUM(CASE WHEN type = 'receipt' THEN quantity ELSE 0 END) as total_receipt,
               SUM(CASE WHEN type = 'expense' THEN quantity ELSE 0 END) as total_expense
        FROM transactions WHERE date(date) = ?
        '''

        stats = query_db(stats_query, [today], one=True)

        return render_template('task2.html', transactions=transactions, stats=stats, today=today)
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
        return redirect(url_for('reports'))


@app.route('/task3')
@login_required
def task3():
    try:
        current_year = datetime.datetime.now().strftime("%Y")

        query = '''
        SELECT m.id, m.name AS material_name, IFNULL(c.name, 'Без категории') AS category,
               u.short_name AS unit,
               SUM(IFNULL(t.quantity, 0)) AS total_quantity,
               COUNT(t.id) AS delivery_count,
               AVG(IFNULL(t.price_per_unit, 0)) AS avg_price,
               SUM(IFNULL(t.quantity, 0) * IFNULL(t.price_per_unit, 0)) AS total_cost,
               (SELECT SUM(IFNULL(t2.quantity, 0)) FROM transactions t2 
                WHERE t2.material_id = m.id AND t2.type = 'expense' AND strftime('%Y', t2.date) = ?) AS used_quantity
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        JOIN units u ON m.unit_id = u.id
        LEFT JOIN categories c ON m.category_id = c.id
        WHERE t.type = 'receipt' AND strftime('%Y', t.date) = ?
        GROUP BY m.id HAVING total_quantity > 0
        ORDER BY total_quantity DESC LIMIT 1
        '''

        top_material = query_db(query, [current_year, current_year], one=True)

        if not top_material:
            return render_template('task3.html', material=None, monthly_data=[], suppliers=[],
                                   current_year=current_year, error="В этом году еще не было поставок")

        top_material_dict = dict(top_material)
        for key in ['total_quantity', 'avg_price', 'total_cost', 'used_quantity']:
            if top_material_dict[key] is None:
                top_material_dict[key] = 0

        monthly_query = '''
        SELECT strftime('%m', date) as month, SUM(IFNULL(quantity, 0)) as monthly_quantity
        FROM transactions
        WHERE material_id = ? AND type = 'receipt' AND strftime('%Y', date) = ?
        GROUP BY strftime('%m', date) ORDER BY month
        '''
        monthly_data = query_db(monthly_query, [top_material_dict['id'], current_year])

        monthly_data_clean = []
        for item in monthly_data:
            item_dict = dict(item)
            if item_dict['monthly_quantity'] is None:
                item_dict['monthly_quantity'] = 0
            monthly_data_clean.append(item_dict)

        suppliers_query = '''
        SELECT s.name, COUNT(t.id) as deliveries, SUM(IFNULL(t.quantity, 0)) as total
        FROM transactions t
        JOIN suppliers s ON t.supplier_id = s.id
        WHERE t.material_id = ? AND t.type = 'receipt' AND strftime('%Y', t.date) = ?
        GROUP BY s.id ORDER BY total DESC
        '''
        suppliers = query_db(suppliers_query, [top_material_dict['id'], current_year])

        suppliers_clean = []
        for s in suppliers:
            s_dict = dict(s)
            if s_dict['total'] is None:
                s_dict['total'] = 0
            suppliers_clean.append(s_dict)

        return render_template('task3.html', material=top_material_dict, monthly_data=monthly_data_clean,
                               suppliers=suppliers_clean, current_year=current_year, error=None)
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
        return redirect(url_for('reports'))


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("СЕРВЕР ЗАПУЩЕН")
    print("=" * 60)
    print("Адрес: http://127.0.0.1:5000")
    print("=" * 60)
    print("\nТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ:")
    print("  Администратор: admin     / admin123")
    print("  Модератор:     moderator / mod123")
    print("  Пользователь:  user      / user123")
    print("=" * 60)
    print("\nРЕГИСТРАЦИЯ ОТСУТСТВУЕТ (только тестовые пользователи)")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)