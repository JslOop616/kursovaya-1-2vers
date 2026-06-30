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

            # Обновляем время последнего входа
            execute_db('UPDATE users SET last_login = ? WHERE id = ?',
                       [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user['id']])

            flash(f'Добро пожаловать, {user["full_name"] or user["username"]}!', 'success')

            if user['role'] in ['admin', 'moderator']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form.get('full_name', '')
        department = request.form.get('department', '')
        phone = request.form.get('phone', '')
        position = request.form.get('position', '')
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        existing = query_db('SELECT id FROM users WHERE username = ? OR email = ?',
                            [username, email], one=True)

        if existing:
            flash('Пользователь с таким логином или email уже существует', 'error')
        else:
            execute_db('''
                INSERT INTO users (username, email, password, role, full_name, department, phone, position, created_at)
                VALUES (?, ?, ?, 'user', ?, ?, ?, ?, ?)
            ''', (username, email, password, full_name, department, phone, position, created_at))
            flash('Регистрация успешна! Теперь вы можете войти', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


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
            (SELECT COUNT(*) FROM v_materials_full WHERE status = 'Требуется закупка') as low_stock_count
    ''', one=True)

    materials = query_db('SELECT * FROM v_materials_full ORDER BY material_name')
    low_stock = query_db('SELECT * FROM v_materials_full WHERE status = "Требуется закупка"')

    # Последние 5 уведомлений для пользователя
    notifications = query_db('''
        SELECT * FROM notifications WHERE user_id = ? OR user_id = 0
        ORDER BY created_at DESC LIMIT 5
    ''', [session['user_id']])

    return render_template('dashboard.html', stats=stats, materials=materials,
                           low_stock=low_stock, notifications=notifications)


@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = query_db('''
        SELECT 
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM materials WHERE is_active = 1) as total_materials,
            (SELECT COUNT(*) FROM transactions) as total_transactions,
            (SELECT COUNT(*) FROM suppliers WHERE is_active = 1) as total_suppliers,
            (SELECT SUM(current_quantity * price_per_unit) FROM materials) as total_value,
            (SELECT COUNT(*) FROM supplier_contracts WHERE status = 'active') as active_contracts
    ''', one=True)

    recent_transactions = query_db('''
        SELECT t.*, m.name as material_name, u.short_name as unit, us.username
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        JOIN units u ON m.unit_id = u.id
        LEFT JOIN users us ON t.created_by = us.id
        ORDER BY t.date DESC LIMIT 20
    ''')

    low_stock_materials = query_db('''
        SELECT * FROM v_materials_full WHERE status = 'Требуется закупка' LIMIT 10
    ''')

    return render_template('admin_dashboard.html', stats=stats, transactions=recent_transactions,
                           low_stock_materials=low_stock_materials)


# ============= УПРАВЛЕНИЕ ПОСТАВЩИКАМИ =============
@app.route('/suppliers')
@operator_required
def suppliers_list():
    suppliers = query_db('SELECT * FROM v_suppliers_full ORDER BY rating DESC, name')
    return render_template('suppliers_list.html', suppliers=suppliers)


@app.route('/supplier/<int:supplier_id>')
@operator_required
def supplier_detail(supplier_id):
    supplier = query_db('SELECT * FROM v_suppliers_full WHERE id = ?', [supplier_id], one=True)
    if not supplier:
        flash('Поставщик не найден', 'error')
        return redirect(url_for('suppliers_list'))

    bank_accounts = query_db('''
        SELECT * FROM supplier_bank_accounts WHERE supplier_id = ? AND is_active = 1
    ''', [supplier_id])

    contracts = query_db('''
        SELECT * FROM supplier_contracts WHERE supplier_id = ? ORDER BY contract_date DESC
    ''', [supplier_id])

    purchases = query_db('''
        SELECT ph.*, m.name as material_name, u.short_name as unit
        FROM purchase_history ph
        JOIN materials m ON ph.material_id = m.id
        JOIN units u ON m.unit_id = u.id
        WHERE ph.supplier_id = ?
        ORDER BY ph.purchase_date DESC LIMIT 20
    ''', [supplier_id])

    materials_from_supplier = query_db('''
        SELECT DISTINCT m.id, m.name, u.short_name as unit,
               (SELECT AVG(price) FROM purchase_history WHERE supplier_id = ? AND material_id = m.id) as avg_price
        FROM purchase_history ph
        JOIN materials m ON ph.material_id = m.id
        JOIN units u ON m.unit_id = u.id
        WHERE ph.supplier_id = ?
        GROUP BY m.id
    ''', [supplier_id, supplier_id])

    return render_template('supplier_detail.html', supplier=supplier, bank_accounts=bank_accounts,
                           contracts=contracts, purchases=purchases, materials_from_supplier=materials_from_supplier)


@app.route('/supplier/add', methods=['GET', 'POST'])
@admin_required
def supplier_add():
    if request.method == 'POST':
        try:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            supplier_id = execute_db('''
                INSERT INTO suppliers (
                    name, full_name, short_name, inn, kpp, ogrn,
                    legal_address, actual_address, phone, fax, email, website,
                    contact_person, contact_phone, contact_email, rating,
                    work_start_date, payment_delay_days, tax_system, created_at, comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request.form['name'], request.form.get('full_name', ''),
                request.form.get('short_name', ''), request.form.get('inn', ''),
                request.form.get('kpp', ''), request.form.get('ogrn', ''),
                request.form.get('legal_address', ''), request.form.get('actual_address', ''),
                request.form.get('phone', ''), request.form.get('fax', ''),
                request.form.get('email', ''), request.form.get('website', ''),
                request.form.get('contact_person', ''), request.form.get('contact_phone', ''),
                request.form.get('contact_email', ''), int(request.form.get('rating', 3)),
                request.form.get('work_start_date', ''), int(request.form.get('payment_delay_days', 0)),
                request.form.get('tax_system', ''), current_time, request.form.get('comment', '')
            ))
            flash('Поставщик успешно добавлен', 'success')
            return redirect(url_for('supplier_detail', supplier_id=supplier_id))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')

    return render_template('supplier_form.html')


@app.route('/supplier/<int:supplier_id>/edit', methods=['GET', 'POST'])
@admin_required
def supplier_edit(supplier_id):
    supplier = query_db('SELECT * FROM suppliers WHERE id = ?', [supplier_id], one=True)
    if not supplier:
        flash('Поставщик не найден', 'error')
        return redirect(url_for('suppliers_list'))

    if request.method == 'POST':
        try:
            execute_db('''
                UPDATE suppliers SET
                    name = ?, full_name = ?, short_name = ?, inn = ?, kpp = ?, ogrn = ?,
                    legal_address = ?, actual_address = ?, phone = ?, fax = ?, email = ?, website = ?,
                    contact_person = ?, contact_phone = ?, contact_email = ?, rating = ?,
                    work_start_date = ?, payment_delay_days = ?, tax_system = ?, updated_at = ?, comment = ?
                WHERE id = ?
            ''', (
                request.form['name'], request.form.get('full_name', ''),
                request.form.get('short_name', ''), request.form.get('inn', ''),
                request.form.get('kpp', ''), request.form.get('ogrn', ''),
                request.form.get('legal_address', ''), request.form.get('actual_address', ''),
                request.form.get('phone', ''), request.form.get('fax', ''),
                request.form.get('email', ''), request.form.get('website', ''),
                request.form.get('contact_person', ''), request.form.get('contact_phone', ''),
                request.form.get('contact_email', ''), int(request.form.get('rating', 3)),
                request.form.get('work_start_date', ''), int(request.form.get('payment_delay_days', 0)),
                request.form.get('tax_system', ''), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                request.form.get('comment', ''), supplier_id
            ))
            flash('Данные поставщика обновлены', 'success')
            return redirect(url_for('supplier_detail', supplier_id=supplier_id))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')

    return render_template('supplier_form.html', supplier=supplier, is_edit=True)


@app.route('/supplier/<int:supplier_id>/bank/add', methods=['POST'])
@admin_required
def supplier_add_bank(supplier_id):
    try:
        execute_db('''
            INSERT INTO supplier_bank_accounts (supplier_id, bank_name, bik, correspondent_account, checking_account, is_main)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            supplier_id, request.form['bank_name'], request.form.get('bik', ''),
            request.form.get('correspondent_account', ''), request.form['checking_account'],
            int(request.form.get('is_main', 0))
        ))
        flash('Банковский счет добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')

    return redirect(url_for('supplier_detail', supplier_id=supplier_id))


@app.route('/supplier/<int:supplier_id>/contract/add', methods=['POST'])
@admin_required
def supplier_add_contract(supplier_id):
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_db('''
            INSERT INTO supplier_contracts (supplier_id, contract_number, contract_date, start_date, end_date, 
                                           contract_type, subject, total_amount, status, created_at, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            supplier_id, request.form['contract_number'], request.form['contract_date'],
            request.form.get('start_date', ''), request.form.get('end_date', ''),
            request.form.get('contract_type', ''), request.form.get('subject', ''),
            float(request.form.get('total_amount', 0)) if request.form.get('total_amount') else None,
            request.form.get('status', 'active'), current_time, request.form.get('comment', '')
        ))
        flash('Договор добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')

    return redirect(url_for('supplier_detail', supplier_id=supplier_id))


@app.route('/supplier/<int:supplier_id>/bank/<int:bank_id>/delete', methods=['POST'])
@admin_required
def supplier_delete_bank(supplier_id, bank_id):
    try:
        execute_db('UPDATE supplier_bank_accounts SET is_active = 0 WHERE id = ?', [bank_id])
        flash('Банковский счет удален', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('supplier_detail', supplier_id=supplier_id))


@app.route('/supplier/<int:supplier_id>/contract/<int:contract_id>/delete', methods=['POST'])
@admin_required
def supplier_delete_contract(supplier_id, contract_id):
    try:
        execute_db('DELETE FROM supplier_contracts WHERE id = ?', [contract_id])
        flash('Договор удален', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'error')
    return redirect(url_for('supplier_detail', supplier_id=supplier_id))


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
            total_amount = quantity * price

            db = get_db()
            cursor = db.cursor()

            # Добавляем транзакцию
            cursor.execute('''
                INSERT INTO transactions (material_id, supplier_id, type, quantity, date, price_per_unit, 
                                         total_amount, comment, created_by, created_at)
                VALUES (?, ?, 'receipt', ?, ?, ?, ?, ?, ?, ?)
            ''', (material_id, supplier_id if supplier_id else None, quantity, date, price,
                  total_amount, comment, session['user_id'], date))

            # Обновляем остаток и цену материала
            cursor.execute('''
                UPDATE materials 
                SET current_quantity = current_quantity + ?,
                    last_price = ?,
                    price_per_unit = ((price_per_unit * current_quantity) + (? * ?)) / (current_quantity + ?),
                    updated_at = ?
                WHERE id = ?
            ''', (quantity, price, price, quantity, quantity, date, material_id))

            # Добавляем запись в историю закупок
            cursor.execute('''
                INSERT INTO purchase_history (supplier_id, material_id, purchase_date, quantity, price, 
                                             total_amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (supplier_id, material_id, date, quantity, price, total_amount, date))

            db.commit()
            flash('Приход успешно добавлен', 'success')
            return redirect(
                url_for('admin_dashboard' if session.get('role') in ['admin', 'moderator'] else 'dashboard'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')

    materials = query_db('SELECT id, name, current_quantity FROM materials WHERE is_active = 1 ORDER BY name')
    suppliers = query_db('SELECT id, name FROM suppliers WHERE is_active = 1 ORDER BY name')
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

            material = query_db('SELECT current_quantity, price_per_unit FROM materials WHERE id = ?', [material_id],
                                one=True)
            if material and material['current_quantity'] >= quantity:
                total_amount = quantity * material['price_per_unit']

                cursor.execute('''
                    INSERT INTO transactions (material_id, type, quantity, date, project_id, price_per_unit,
                                             total_amount, comment, created_by, created_at)
                    VALUES (?, 'expense', ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (material_id, quantity, date, project_id if project_id else None,
                      material['price_per_unit'], total_amount, comment, session['user_id'], date))

                cursor.execute('''
                    UPDATE materials SET current_quantity = current_quantity - ?, updated_at = ? WHERE id = ?
                ''', (quantity, date, material_id))

                # Обновляем потраченную сумму по проекту
                if project_id:
                    cursor.execute('''
                        UPDATE projects SET spent = spent + ? WHERE id = ?
                    ''', (total_amount, project_id))

                db.commit()
                flash('Расход успешно добавлен', 'success')
            else:
                flash(f'Недостаточно материалов! Доступно: {material["current_quantity"]}', 'error')

            return redirect(
                url_for('admin_dashboard' if session.get('role') in ['admin', 'moderator'] else 'dashboard'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'error')

    materials = query_db('SELECT id, name, current_quantity FROM materials WHERE is_active = 1 ORDER BY name')
    projects = query_db('SELECT id, name FROM projects WHERE status = "active" ORDER BY name')
    return render_template('add_expense.html', materials=materials, projects=projects)


# ============= ОТЧЕТЫ (доступны всем авторизованным) =============
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


# ============= НОВЫЙ ОТЧЕТ: СТАТИСТИКА ПО ПОСТАВЩИКАМ =============
@app.route('/supplier_statistics')
@operator_required
def supplier_statistics():
    stats = query_db('SELECT * FROM v_supplier_statistics ORDER BY total_amount DESC')
    return render_template('supplier_statistics.html', stats=stats)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("СЕРВЕР ЗАПУЩЕН")
    print("=" * 60)
    print("Адрес: http://127.0.0.1:5010")
    print("=" * 60)
    print("\nТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ:")
    print("  Администратор: admin     / admin123")
    print("  Модератор:     moderator / mod123")
    print("  Пользователь:  user      / user123")
    print("=" * 60)
    print("\nДОСТУПНЫЕ РАЗДЕЛЫ:")
    print("  /                 - Главная")
    print("  /admin            - Админ-панель")
    print("  /suppliers        - Список поставщиков")
    print("  /supplier/<id>    - Карточка поставщика")
    print("  /add_receipt      - Добавить приход")
    print("  /add_expense      - Добавить расход")
    print("  /reports          - Отчеты")
    print("  /task1, /task2, /task3 - Аналитические отчеты")
    print("=" * 60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5010)