import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv

# Carga las variables de entorno que tengo en .env
load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Querys de creacion de las tablas
query_create_books = "CREATE TABLE books(id SERIAL PRIMARY KEY NOT NULL, isbn VARCHAR(10) NOT NULL, title VARCHAR NOT NULL, author VARCHAR, year VARCHAR(4))"
query_create_users = "CREATE TABLE users(id SERIAL PRIMARY KEY NOT NULL, username VARCHAR NOT NULL, hash VARCHAR NOT NULL)"
query_create_reseñas = "CREATE TABLE reseñas(id SERIAL PRIMARY KEY NOT NULL, comentario VARCHAR, puntuacion INTEGER, user_id INTEGER REFERENCES users, book_id INTEGER REFERENCES books)"
# Crea las tablas usando las querys
db.execute(query_create_books)
db.execute(query_create_users)
db.execute(query_create_reseñas)

# Lee el csv
f = open("books.csv")
reader = csv.reader(f)

# Itera dentro del csv y almacena en base de datos
for isbn, title, author, year in reader:
    if isbn == "isbn":
        # No hacer nada xd, es la linea de cabeceras
        print("Linea de cabeceras omitida")
    else:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                   {"isbn": isbn, "title": title, "author": author, "year": year})

print("Todo añadido a la base de datos...")

db.commit()
