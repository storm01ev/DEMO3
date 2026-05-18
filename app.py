from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_exam' # Нужно для работы сессий (хранения роли пользователя)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'DE') # Имя твоего файла базы данных SQLite

# Функция для удобного подключения к базе данных
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Позволяет обращаться к полям по именам, например row['name']
    return conn

# 1. СТРАНИЦА ВХОДА (АВТОРИЗАЦИЯ)
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Если нажата кнопка "Войти как гость"
        if 'guest' in request.form:
            session['role'] = 'Гость'
            session['user_name'] = 'Уважаемый гость'
            return redirect(url_for('catalog'))
            
        # Если ввели логин и пароль
        login_input = request.form.get('login')
        password_input = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE login = ? AND password = ?', 
                            (login_input, password_input)).fetchone()
        conn.close()
        
        if user:
            # Сохраняем роль и ФИО в сессию, чтобы сайт "помнил" нас
            session['role'] = user['role']
            session['user_name'] = user['full_name']
            return redirect(url_for('catalog'))
        else:
            error = "Неверный логин или пароль!"
            
    return render_template('login.html', error=error)

# 2. СТРАНИЦА КАТАЛОГА ТОВАРОВ
@app.route('/catalog')
def catalog():
    # Если пользователь зашел в обход страницы входа, отправляем его обратно
    if 'role' not in session:
        return redirect(url_for('login'))
        
    role = session['role']
    
    # Сбор параметров фильтрации (нужны для Менеджера и Админа)
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    sort_by = request.args.get('sort', '')

    conn = get_db_connection()
    
    # Базовый SQL-запрос для всех
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    # По ТЗ: Фильтрация, сортировка и поиск доступны ТОЛЬКО Менеджеру и Админу
    if role in ['Менеджер', 'Администратор']:
        if search_query:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        if category_filter:
            query += " AND category = ?"
            params.append(category_filter)
        if sort_by == 'price_asc':
            query += " ORDER BY price ASC"
        elif sort_by == 'price_desc':
            query += " ORDER BY price DESC"

    products = conn.execute(query, params).fetchall()
    
    # Вытаскиваем уникальные категории для выпадающего списка фильтра
    categories = conn.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL").fetchall()
    conn.close()
    
    return render_template('catalog.html', products=products, categories=categories, role=role, user_name=session['user_name'])

# 3. СТРАНИЦА ЗАКАЗОВ (Для Менеджера и Админа)
@app.route('/orders')
def orders_list():
    if 'role' not in session or session['role'] not in ['Менеджер', 'Администратор']:
        return "Доступ запрещен!", 403
        
    conn = get_db_connection()
    # Берем все заказы
    orders = conn.execute("SELECT * FROM orders").fetchall()
    conn.close()
    return render_template('orders.html', orders=orders, role=session['role'])

# 4. ДЕЙСТВИЯ АДМИНИСТРАТОРА: Удаление товара
@app.route('/product/delete/<article>')
def delete_product(article):
    if session.get('role') != 'Администратор':
        return "Доступ запрещен!", 403
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE article = ?", (article,))
    conn.commit()
    conn.close()
    return redirect(url_for('catalog'))

# 5. ДЕЙСТВИЯ АДМИНИСТРАТОРА: Добавление товара
@app.route('/product/add', methods=['GET', 'POST'])
def add_product():
    if session.get('role') != 'Администратор':
        return "Доступ запрещен!", 403
        
    if request.method == 'POST':
        # Собираем данные из формы
        article = request.form['article']
        name = request.form['name']
        unit = request.form['unit']
        price = float(request.form['price'])
        category = request.form['category']
        stock = int(request.form['stock_quantity'])
        
        conn = get_db_connection()
        conn.execute("""INSERT INTO products (article, name, unit, price, category, stock_quantity) 
                        VALUES (?, ?, ?, ?, ?, ?)""", (article, name, unit, price, category, stock))
        conn.commit()
        conn.close()
        return redirect(url_for('catalog'))
        
    return render_template('add_product.html')

# ВЫХОД ИЗ СИСТЕМЫ
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)