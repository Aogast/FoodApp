from datetime import datetime, timedelta
import hashlib

from flask import Flask, url_for, request, render_template, redirect, session

import sqlite3

app = Flask(__name__)

app.secret_key = 'your_secret_key'


def get_db_connection():
    conn = sqlite3.connect('data/users.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS dishes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        dish_name TEXT NOT NULL,
                        calories REAL NOT NULL,
                        proteins REAL NOT NULL,
                        fats REAL NOT NULL,
                        carbs REAL NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    );''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS food_consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            dish_id INTEGER,
            grams INTEGER NOT NULL,
            consumption_date DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (dish_id) REFERENCES dishes(id)
        );
        ''')
    conn.commit()
    conn.close()


@app.route('/')
def home():
    """main page"""

    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    return render_template('main.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        password = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            error = 'Неправильный email или пароль'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()

        existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if existing_user:
            error = 'Человек с данным Email уже зарегистрирован.'
            conn.close()
            return render_template('register.html', error=error)
        else:

            conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                         (username, email, password))
            conn.commit()
            conn.close()

            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = session.get('username')
    return render_template('main_screen.html', username=username)


@app.route('/add_dish', methods=['GET', 'POST'])
def add_dish():
    conn = get_db_connection()
    message = ""  
    if request.method == 'POST':
        dish_name = request.form['dish_name']
        calories = request.form['calories']
        proteins = request.form['proteins']
        fats = request.form['fats']
        carbs = request.form['carbs']

        existing_dish = conn.execute('SELECT * FROM dishes WHERE dish_name = ? AND user_id = ?',
                                     (dish_name, session['user_id'])).fetchone()

        if existing_dish:
            message = "Блюдо с таким именем уже есть"
        else:
            conn.execute(
                'INSERT INTO dishes (dish_name, calories, proteins, fats, carbs, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                (dish_name, calories, proteins, fats, carbs, session['user_id']))
            conn.commit()
            message = "Блюдо добавлено успешно!"

    dishes = conn.execute('SELECT * FROM dishes WHERE user_id = ? LIMIT 10', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('add_dish.html', dishes=dishes, message=message)


@app.route('/edit_dish/<int:dish_id>', methods=['GET', 'POST'])
def edit_dish(dish_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        dish_name = request.form['dish_name']
        calories = request.form['calories']
        proteins = request.form['proteins']
        fats = request.form['fats']
        carbs = request.form['carbs']

        conn.execute('UPDATE dishes SET dish_name = ?, calories = ?, proteins = ?, fats = ?, carbs = ? WHERE id = ?',
                     (dish_name, calories, proteins, fats, carbs, dish_id))
        conn.commit()
        conn.close()

        return redirect(url_for('add_dish'))

    dish = conn.execute('SELECT * FROM dishes WHERE id = ?', (dish_id,)).fetchone()
    conn.close()

    return render_template('edit_dish.html', dish=dish)


@app.route('/track_consumption', methods=['GET', 'POST'])
def track_consumption():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        consumption_date = request.form['consumption_date']
        user_id = session['user_id']

        conn = get_db_connection()

        for dish in request.form:
            if dish.startswith('grams_'):
                dish_id = dish.split('_')[1]
                grams = request.form[dish]
                if grams:
                    conn.execute(
                        'INSERT INTO food_consumption (user_id, dish_id, grams, consumption_date) VALUES (?, ?, ?, ?)',
                        (user_id, dish_id, grams, consumption_date))

        conn.commit()
        conn.close()
        return redirect(url_for('track_consumption', message="Meal added successfully!"))

    conn = get_db_connection()
    user_id = session['user_id']
    dishes = conn.execute('SELECT * FROM dishes WHERE user_id = ? ORDER BY dish_name ASC', (user_id,)).fetchall()
    conn.close()
    return render_template('track_consumption.html', dishes=dishes)


@app.route('/statistics', methods=['GET', 'POST'])
def statistics():
    if request.method == 'POST':
        user_id = session['user_id']
        if 'range' in request.form:
            if request.form['range'] == 'last_week':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
            elif request.form['range'] == 'last_month':
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
            else:
                start_date = request.form['start_date']
                end_date = request.form['end_date']
        else:
            start_date = request.form['start_date']
            end_date = request.form['end_date']

        conn = get_db_connection()
        consumption_data = conn.execute('''
            SELECT 
                DATE(consumption_date) AS date,
                SUM(grams * (SELECT fats FROM dishes WHERE id = dish_id)) / 100 AS total_fats,
                SUM(grams * (SELECT proteins FROM dishes WHERE id = dish_id)) / 100 AS total_proteins,
                SUM(grams * (SELECT carbs FROM dishes WHERE id = dish_id)) / 100 AS total_carbs,
                SUM(grams) AS total_grams
            FROM food_consumption
            WHERE user_id = ? AND consumption_date BETWEEN ? AND ?
            GROUP BY date
        ''', (user_id, start_date, end_date)).fetchall()

        dates = [row['date'] for row in consumption_data]
        total_fats = [row['total_fats'] for row in consumption_data]
        total_proteins = [row['total_proteins'] for row in consumption_data]
        total_carbs = [row['total_carbs'] for row in consumption_data]
        total_calories = [(row['total_fats'] * 9 + row['total_proteins'] * 4 + row['total_carbs'] * 4) for row in
                          consumption_data]

        conn.close()

        return render_template('statistics.html', dates=dates, total_fats=total_fats,
                               total_proteins=total_proteins, total_carbs=total_carbs,
                               total_calories=total_calories)

    return render_template('statistics.html', dates=[], total_fats=[], total_proteins=[], total_carbs=[],
                           total_calories=[])


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    init_db()
    app.run(port=8080, host='127.0.0.1')
