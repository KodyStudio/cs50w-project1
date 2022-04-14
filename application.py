import os
from django.shortcuts import render

from flask import Flask, redirect, render_template, request, session, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.sql.elements import Null
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
# from helpers import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", "POST"])
# @login_required
def index():
    request.method == "POST"
    busqueda = request.form.get('busqueda')
    print(busqueda)

    resultado = db.execute(
        f"SELECT isbn, title, author, year, id from books where upper(author)='{request.form.get('busqueda')}' or upper(author) LIKE upper('%{request.form.get('busqueda')}%') or upper(title)='{request.form.get('busqueda')}' or upper(title) LIKE upper('{request.form.get('busqueda')}') or upper(year)='{request.form.get('busqueda')}' or upper(year) LIKE upper('{request.form.get('busqueda')}') GROUP BY title, isbn, author, year, id ")
    print(resultado)

    return render_template("index.html", resultado=resultado)


@app.route("/review/<id>", methods=["GET", "POST"])
def review(id):

    books = db.execute(
        "SELECT * FROM books WHERE id = :id", {"id": id}).fetchone()

    print(books)

    return render_template("review.html", books=books)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        # sustituir los apology por flash cuando hay un error y rederizar a registro.html
        if not username:
            flash("Username es requerido")
            return render_template("register.html")
        elif not password:
            flash("Password es requerido")
            return render_template("register.html")
        elif not confirmation:
            flash("Confirmation es requerido")
            return render_template("register.html")

        if password != confirmation:
            flash("Password no coinciden bro")
            return render_template("register.html")

        userid = db.execute(
            f"SELECT * FROM users WHERE username = '{request.form.get('username')}'").rowcount

        if userid > 0:
            flash("hay un usuario con ese name UnU")
            return render_template("register.html")

        hash = generate_password_hash(password)

        db.execute(
            "INSERT INTO users (username, hash) VALUES (:username, :hash)", {"username": username, "hash": hash})
        db.commit()
        id_user = db.execute("SELECT id FROM users WHERE username=:username",
                             {"username": username, "hash": hash}).fetchone()["id"]
        session["user_id"] = id_user
        flash("registrado")
        return redirect('/')

    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Username es requerido")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Password es requerido")
            return render_template("login.html")

        # Query database for username

        count = 0
        hash = Null
        id = 0

        for rows in db.execute("SELECT count(username), hash, id FROM users WHERE username = :username GROUP BY username, id, hash",
                               {"username": request.form.get("username")}):
            count = rows[0]
            hash = rows['hash']
            id = rows['id']

        print(count)

        # Ensure username exists and password is correct
        if count == 0 or not check_password_hash(hash, request.form.get("password")):
            flash("invalid username and/or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
