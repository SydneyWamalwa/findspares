from flask import Flask, render_template, request, redirect, session,jsonify,url_for
from flask_session import Session
from flask_mail import Mail, Message
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
import sqlite3
import os
import logging
import requests

secret_key = os.urandom(24)
app = Flask(__name__, template_folder='templates')
app.secret_key = secret_key
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
bcrypt = Bcrypt(app)

app.logger.setLevel(logging.DEBUG)

try:
    # Create the users table if it doesn't exist
    with sqlite3.connect('spares.db') as connection:
        cursor = connection.cursor()
        app.logger.debug('Executing SQL statements...')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_name TEXT NOT NULL,
                part_number TEXT NOT NULL,
                part_image BLOB NOT NULL,
                description TEXT NOT NULL,
                thumbnail BLOB NOT NULL,
                img1 BLOB NOT NULL,
                img2 BLOB NOT NULL,
                Price INTEGER NOT NULL
            )
        ''')


        cursor.execute('''
    CREATE TABLE IF NOT EXISTS Orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT DEFAULT 'Open',
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        payment_reference TEXT,
        payment_amount INTEGER,
        FOREIGN KEY (part_id) REFERENCES Parts(id)
    )
''')


    connection.commit()
except Exception as e:
    print(f"Error connecting to the database: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/Login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        with sqlite3.connect('spares.db') as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            # If the user exists, store user information in the session
            session['user_id'] = user[0]
            session['user_name'] = user[1]

            # Redirect to the original requested page or the home page
            return redirect('/SuccessLogin')

        else:
            # If login fails, you can display an error message or redirect to the login page
            return render_template('Login.html', error='Invalid credentials')

    return render_template('Login.html')

@app.route('/logout')
def logout():
    # Clear session variables
    session.clear()
    return render_template('index.html')

@app.route('/Signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Process the form data here (save to database, perform validation, etc.)
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Hash the password before storing it in the database
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            # Insert the user into the users table
            with sqlite3.connect('spares.db') as connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_password))
                connection.commit()

            # Store the user's name in the session
            session['name'] = name
            session['email'] = email

            # Redirect to the index page with the user's name as a parameter
            return redirect('/Success')

        except sqlite3.IntegrityError:
            # Handle the case where the email is not unique (already exists in the database)
            return render_template('signup.html', error='Email already exists. Please use a different email.')

    return render_template('Signup.html')

@app.route('/Success')
def success():
    # Get the user's name from the session
    user_name = session.get('name')
    return render_template('Success.html', user_name=user_name)

@app.route('/SuccessLogin')
def successlogin():
    # Get the user's name from the session
    user_name = session.get('user_name')
    return render_template('Loginsuccess.html', user_name=user_name)

@app.route('/adminsignup', methods=['GET', 'POST'])
def adminsignup():
    if request.method == 'POST':
        # Process the form data here (save to database, perform validation, etc.)
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Hash the password before storing it in the database
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            # Insert the user into the users table
            with sqlite3.connect('spares.db') as connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO admins (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_password))
                connection.commit()

            # Store the user's name in the session
            session['name'] = name
            session['email'] = email

            # Redirect to the index page with the user's name as a parameter
            return render_template('dashboard.html')

        except sqlite3.IntegrityError:
            # Handle the case where the email is not unique (already exists in the database)
            return render_template('Signup.html', error='Email already exists. Please use a different email.')

    return render_template('Admin_signup.html')

@app.route('/LoginAdmin', methods=['GET', 'POST'])
def loginAdmin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        with sqlite3.connect('spares.db') as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM admins WHERE email=?", (email,))
            user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user[3], password):
            # If the user exists and the password is correct, store user information in the session
            session['user_id'] = user[0]
            session['user_name'] = user[1]

            # Pass the admin_name to the template
            return render_template('dashboard.html', admin_name=user[1])

        else:
            # If login fails, you can display an error message or redirect to the login page
            return render_template('Login.html', error='Invalid credentials')

    return render_template('AdminLogin.html')

@app.route('/track-order')
def Tracking():
    return render_template('track-order.html')

@app.route('/get-orders')
def get_orders():
    with sqlite3.connect('spares.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT Orders.id, Parts.part_name, Parts.part_number, Parts.part_image, Orders.quantity, Orders.status,
                   Orders.customer_name, Orders.customer_email, Orders.order_date,
                   Orders.payment_reference, Orders.payment_amount
            FROM Orders
            JOIN Parts ON Orders.part_id = Parts.id
            ORDER BY Orders.order_date DESC
        ''')
        orders = cursor.fetchall()
    return jsonify(orders)


@app.route('/close-order/<int:order_id>', methods=['POST'])
def close_order(order_id):
    with sqlite3.connect('spares.db') as connection:
        cursor = connection.cursor()
        cursor.execute('UPDATE Orders SET status = "Closed" WHERE id = ?', (order_id,))
        connection.commit()
    return jsonify({"success": True})

@app.route('/upload-part', methods=['GET', 'POST'])
def upload_part():
    if request.method == 'POST':
        part_name = request.form.get('part_name')
        part_number = request.form.get('part_number')
        description = request.form.get('description')
        price = request.form.get('price')

        # Retrieve file data
        part_image = request.files['part_image']
        thumbnail = request.files['thumbnail']
        img1 = request.files['img1']
        img2 = request.files['img2']

        # Your code to save the files and other form data into the database...
        # Make sure to handle file uploads and save them to an appropriate folder.

        # Sample code (modify based on your requirements):
        # Save the files to a folder named 'uploads' within the static folder
        part_image.save('static/uploads/' + part_image.filename)
        thumbnail.save('static/uploads/' + thumbnail.filename)
        img1.save('static/uploads/' + img1.filename)
        img2.save('static/uploads/' + img2.filename)

        # Your code to insert the form data into the database...
        # Sample code (modify based on your database schema):
        with sqlite3.connect('spares.db') as connection:
            cursor = connection.cursor()
            cursor.execute('''
                INSERT INTO Parts (part_name, part_number, part_image, description, thumbnail, img1, img2, Price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (part_name, part_number, part_image.filename, description, thumbnail.filename, img1.filename, img2.filename, price))
            connection.commit()

        # Redirect to a success page or any other page as needed
        return redirect(url_for('success_upload'))

    return render_template('upload-part.html')

@app.route('/success-upload')
def success_upload():
    return render_template('success-upload.html')

@app.route('/Models')
def Models():
    return render_template('Models.html')

@app.route('/toyota.html')
def Toyota():
    return render_template('toyota.html')

@app.route('/nissan.html')
def Nissan():
    return render_template('nissan.html')

@app.route('/merc.html')
def Merc():
    return render_template('merc.html')

@app.route('/Peaugot.html')
def Peaugot():
    return render_template('Peaugot.html')

@app.route('/Audi.html')
def Audi():
    return render_template('Audi.html')

@app.route('/VW.html')
def VW():
    return render_template('VW.html')

@app.route('/BMW.html')
def BMW():
    return render_template('BMW.html')

@app.route('/Porsche.html')
def Porsche():
    return render_template('Porsche.html')

@app.route('/Subaru.html')
def Subaru():
    return render_template('Subaru.html')

@app.route('/Honda.html')
def Honda():
    return render_template('Honda.html')

@app.route('/Suzuki.html')
def Suzuki():
    return render_template('Suzuki.html')

@app.route('/Mazda.html')
def Mazda():
    return render_template('Mazda.html')

@app.route('/Mitsubishi.html')
def Mitsubishi():
    return render_template('Mitsubishi.html')


@app.route('/Search_Model', methods=['GET', 'POST'])
def search_model():
    if request.method == 'POST':
        search_query = request.form.get('search_query')

        # Your code to query the database based on the search_query
        # Modify this query based on your database schema and search requirements
        with sqlite3.connect('spares.db') as connection:
            cursor = connection.cursor()
            cursor.execute('''
                SELECT * FROM Parts
                WHERE part_number = ? OR vehicle_model_id = ?
            ''', (search_query, search_query))
            parts = cursor.fetchall()
            print(parts)

        return render_template('results.html', parts=parts, search_query=search_query)

    return render_template('results.html')

@app.route('/part-details/<int:part_id>')
def part_details(part_id):
    if 'user_id' not in session:
        return redirect(url_for('login', next=request.url))
    # Retrieve part details based on part_id
    with sqlite3.connect('spares.db') as connection:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM Parts WHERE id = ?', (part_id,))
        part = cursor.fetchone()

    if part:
        return render_template('part-details.html', part=part)
    else:
        return redirect(url_for('search_model'))


@app.route('/store_data', methods=['POST'])
def store_data():
    try:
        if request.method == 'POST':
            # Retrieve data from the request form
            email = request.form.get('email')
            name = request.form.get('name')
            quantity = request.form.get('quantity')
            amount = request.form.get('totalAmount')
            payment_reference = request.form.get('payment_reference')



# Proceed with Paystack payment

            # Fetch the corresponding part details based on your logic
            with sqlite3.connect('spares.db') as connection:
                cursor = connection.cursor()

                # Modify this query based on your database schema and requirements
                # Here, I'm assuming you want to fetch the part with the highest ID (latest part)
                cursor.execute('SELECT * FROM Parts ORDER BY id DESC LIMIT 1')
                part = cursor.fetchone()

                if part:
                    # Insert the order details into the Orders table
                    cursor.execute('''
                        INSERT INTO Orders (part_id, quantity, customer_email, customer_name, payment_amount, payment_reference)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (part[0], quantity, email, name, amount, payment_reference))
                    connection.commit()

                    # Return a success response
                    return jsonify({'status': 'success'})
                else:
                    # Return an error response if no part is found
                    return jsonify({'status': 'error', 'message': 'No part found'})
    except Exception as e:
        # Return an error response if an exception occurs
        return jsonify({'status': 'error', 'message': f'Error: {e}'})

    # Return a generic error response if the request method is not POST
    return jsonify({'status': 'error', 'message': 'Invalid request'})




if __name__ == '__main__':
    app.run(debug=True)