from asyncio.windows_events import NULL
import os
import requests
from django.shortcuts import render

from flask import Flask, flash, redirect, render_template, request, session, jsonify
from helpers import login_required
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.sql.elements import Null
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash


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
@login_required
def index():

    resultado = db.execute(
        f"SELECT isbn, title, author, year, id from books where upper(author)='{request.form.get('busqueda')}' or upper(author) LIKE upper('%{request.form.get('busqueda')}%') or upper(isbn)='{request.form.get('busqueda')}' or upper(isbn) LIKE upper('%{request.form.get('busqueda')}%') or upper(title)='{request.form.get('busqueda')}' or upper(title) LIKE upper('{request.form.get('busqueda')}') or upper(year)='{request.form.get('busqueda')}' or upper(year) LIKE upper('{request.form.get('busqueda')}') GROUP BY title, isbn, author, year, id ")

    return render_template("index.html", resultado=resultado)


@app.route("/review/<id>", methods=["GET", "POST"])
@login_required
def review(id):
    if request.method == "POST":
        puntuacion = request.form.get('puntuacion')
        comentario = request.form.get('comentario')

        db.execute(
            "INSERT INTO reviews (book_id, comentario, puntuacion, user_id) VALUES (:id, :comentario, :puntuacion, :user_id)", {
                "id": id, "comentario": comentario, "puntuacion": puntuacion, "user_id": session['user_id']})

        db.commit()

    isbn = db.execute("SELECT isbn as isbn from books where id=:id",
                      {"id": id}).fetchone()["isbn"]

    response = requests.get(
        "https://www.googleapis.com/books/v1/volumes?q=isbn:"+isbn).json()

    # la imagen desde la api

    if(response.get('totalItems') != 0):
        data = response.get('items')[0]
        volumeInfo = data.get("volumeInfo")
        imagen = volumeInfo.get("imageLinks")

        if not imagen:
            imagen = ("https://media.istockphoto.com/vectors/error-page-or-file-not-found-icon-vector-id924949200?k=20&m=924949200&s=170667a&w=0&h=-g01ME1udkojlHCZeoa1UnMkWZZppdIFHEKk6wMvxrs=")
        else:
            imagen = imagen.get("thumbnail")
    else:
        imagen = (
            "https://media.istockphoto.com/vectors/error-page-or-file-not-found-icon-vector-id924949200?k=20&m=924949200&s=170667a&w=0&h=-g01ME1udkojlHCZeoa1UnMkWZZppdIFHEKk6wMvxrs=")

    # puntaje promedio desde la api

    if(response.get('totalItems') != 0):
        data = response.get('items')[0]
        volumeInfo = data.get("volumeInfo")
        averageRating = volumeInfo.get("averageRating")
        ratingsCount = volumeInfo.get("ratingsCount")

        print("averageRating:", averageRating)
        print("ratingsCount:", ratingsCount)
    else:
        averageRating = -1
        ratingsCount = -1

    books = db.execute(
        "SELECT * FROM books WHERE id = :id", {"id": id}).fetchone()

    reviews = db.execute(
        "SELECT * FROM reviews as r inner join users as u on r.user_id = u.id  WHERE book_id = :id", {"id": id})

    user_id = session["user_id"]

    count_comment = db.execute(
        "SELECT count(*)as conteo from reviews where user_id = :user_id and book_id = :id", {"user_id": user_id, "id": id}).fetchone()["conteo"]

    return render_template("review.html", books=books, reviews=reviews, count_comment=count_comment, imagen=imagen, averageRating=averageRating, ratingsCount=ratingsCount)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        if not username:
            flash("Username es requerido", "error")
            return render_template("register.html")
        elif not password:
            flash("Password es requerido", "error")
            return render_template("register.html")
        elif not confirmation:
            flash("Confirmation es requerido")
            return render_template("register.html")

        if password != confirmation:
            flash("Las contraseñas no coinciden", "error")
            return render_template("register.html")

        userid = db.execute(
            f"SELECT * FROM users WHERE username = '{request.form.get('username')}'").rowcount

        if userid > 0:
            flash("hay un usuario con ese nombre UnU", "error")
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
            flash("Username es requerido", "error")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Contraseña es requerido", "error")
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
            flash("nombre de usuario o contraseña inválido", "error")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/error")
@login_required
def error():

    return render_template("404.html")


@app.route("/api/<code>")
@login_required
def get_book_by_code(code):

    response = requests.get(
        "https://www.googleapis.com/books/v1/volumes?q=isbn:"+code).json()

    if(response.get('totalItems') != 0):
        data = response.get('items')[0]
        volumeInfo = data.get("volumeInfo")
        averageRating = volumeInfo.get("averageRating")
        ratingsCount = volumeInfo.get("ratingsCount")
    else:
        return redirect("/error")

    book = db.execute("SELECT * FROM books WHERE isbn = :code",
                      {"code": code}).fetchone()

    review_count = db.execute(
        "SELECT count(*)as conteo from reviews where book_id = :code", {"code": book["id"]}).fetchone()["conteo"]

    return jsonify(
        tile=book.title,
        author=book.author,
        year=book.year,
        isbn=book.isbn,
        review_count=review_count,
        averageRating=averageRating,
        ratingsCount=ratingsCount
    )
