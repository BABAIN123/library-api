from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
import bcrypt

app = FastAPI(title="Library API")


# ---------- DATABASE ----------

def get_db():
    conn = sqlite3.connect("library.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------- MODELS ----------

class UserCreate(BaseModel):
    username: str
    password: str


class LoginData(BaseModel):
    username: str
    password: str


class BookCreate(BaseModel):
    title: str
    author: str


class ReviewCreate(BaseModel):
    book_id: int
    user_id: int
    text: str


# ---------- HTML ----------

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Library API</title>
        </head>
        <body>
            <h1>📚 Library API</h1>
            <p>Мой учебный проект библиотеки на FastAPI.</p>
            <p><a href="/docs">Открыть Swagger</a></p>
        </body>
    </html>
    """


# ---------- USERS ----------

@app.post("/register")
def register(user: UserCreate):
    conn = get_db()

    password_hash = bcrypt.hashpw(
        user.password.encode(),
        bcrypt.gensalt()
    ).decode()

    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (user.username, password_hash)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    conn.close()

    return {"message": "User registered"}


@app.post("/login")
def login(data: LoginData):
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (data.username,)
    ).fetchone()

    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not bcrypt.checkpw(
        data.password.encode(),
        user["password_hash"].encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "message": "Login successful",
        "user_id": user["id"]
    }


# ---------- BOOKS CRUD ----------

@app.post("/books")
def create_book(book: BookCreate):
    conn = get_db()

    cursor = conn.execute(
        "INSERT INTO books (title, author) VALUES (?, ?)",
        (book.title, book.author)
    )

    conn.commit()
    book_id = cursor.lastrowid
    conn.close()

    return {
        "id": book_id,
        "title": book.title,
        "author": book.author
    }


@app.get("/books")
def get_books():
    conn = get_db()

    books = conn.execute(
        "SELECT * FROM books"
    ).fetchall()

    conn.close()

    return [dict(book) for book in books]


@app.get("/books/{book_id}")
def get_book(book_id: int):
    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    conn.close()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return dict(book)


@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookCreate):
    conn = get_db()

    existing = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")

    conn.execute(
        "UPDATE books SET title = ?, author = ? WHERE id = ?",
        (book.title, book.author, book_id)
    )

    conn.commit()
    conn.close()

    return {"message": "Book updated"}


@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    conn = get_db()

    existing = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")

    conn.execute(
        "DELETE FROM books WHERE id = ?",
        (book_id,)
    )

    conn.commit()
    conn.close()

    return {"message": "Book deleted"}


# ---------- REVIEWS CRUD ----------

@app.post("/reviews")
def create_review(review: ReviewCreate):
    conn = get_db()

    book = conn.execute(
        "SELECT id FROM books WHERE id = ?",
        (review.book_id,)
    ).fetchone()

    user = conn.execute(
        "SELECT id FROM users WHERE id = ?",
        (review.user_id,)
    ).fetchone()

    if not book:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")

    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    cursor = conn.execute(
        """
        INSERT INTO reviews (book_id, user_id, text)
        VALUES (?, ?, ?)
        """,
        (review.book_id, review.user_id, review.text)
    )

    conn.commit()
    review_id = cursor.lastrowid
    conn.close()

    return {
        "id": review_id,
        "book_id": review.book_id,
        "user_id": review.user_id,
        "text": review.text
    }


@app.get("/reviews")
def get_reviews():
    conn = get_db()

    reviews = conn.execute("""
        SELECT
            reviews.id,
            reviews.text,
            books.title AS book,
            users.username AS user
        FROM reviews
        JOIN books ON reviews.book_id = books.id
        JOIN users ON reviews.user_id = users.id
    """).fetchall()

    conn.close()

    return [dict(review) for review in reviews]


@app.delete("/reviews/{review_id}")
def delete_review(review_id: int):
    conn = get_db()

    existing = conn.execute(
        "SELECT * FROM reviews WHERE id = ?",
        (review_id,)
    ).fetchone()

    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Review not found")

    conn.execute(
        "DELETE FROM reviews WHERE id = ?",
        (review_id,)
    )

    conn.commit()
    conn.close()

    return {"message": "Review deleted"}


# ---------- PROTECTED ENDPOINT ----------

@app.get("/protected")
def protected(username: str):
    conn = get_db()

    user = conn.execute(
        "SELECT username FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {
        "message": "Protected data",
        "username": username
    }