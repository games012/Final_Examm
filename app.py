import os
from contextlib import contextmanager

import pymysql
import pymysql.cursors
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

DB_NAME = os.getenv("DB_NAME", "bookdb")
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


@contextmanager
def db_cursor(use_db=True):
    """เปิดการเชื่อมต่อ ให้ cursor, commit เมื่อสำเร็จ, rollback เมื่อผิดพลาด, แล้วปิดเสมอ"""
    cfg = dict(DB_CONFIG)
    if use_db:
        cfg["database"] = DB_NAME
    conn = pymysql.connect(**cfg)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """สร้างฐานข้อมูลและตาราง book (ถ้ายังไม่มี) และใส่ข้อมูลตัวอย่างถ้าตารางว่าง"""
    with db_cursor(use_db=False) as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    with db_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS book (
                id     INT AUTO_INCREMENT PRIMARY KEY,
                name   VARCHAR(255) NOT NULL,
                author VARCHAR(255) NOT NULL,
                price  DECIMAL(10, 2) NOT NULL DEFAULT 0
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """
        )
        cur.execute("SELECT COUNT(*) AS n FROM book")
        if cur.fetchone()["n"] == 0:
            cur.execute(
                "INSERT INTO book (name, author, price) VALUES (%s, %s, %s)",
                ("Oen", "ดรใวิสุท แช่ตั้ง", 250),
            )


def parse_form():
    name = request.form.get("name", "").strip()
    author = request.form.get("author", "").strip()
    price_raw = request.form.get("price", "").strip()
    try:
        price = float(price_raw)
        if price < 0:
            raise ValueError
    except ValueError:
        return None, "ราคาต้องเป็นตัวเลขที่ไม่ติดลบ"
    if not name or not author:
        return None, "กรุณากรอกชื่อหนังสือและผู้แต่ง"
    return (name, author, price), None


@app.route("/")
def index():
    with db_cursor() as cur:
        cur.execute("SELECT id, name, author, price FROM book ORDER BY id")
        books = cur.fetchall()
    return render_template("index.html", books=books)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        data, error = parse_form()
        if error:
            flash(error, "danger")
            return render_template("form.html", title="เพิ่มหนังสือ", book=request.form)
        with db_cursor() as cur:
            cur.execute(
                "INSERT INTO book (name, author, price) VALUES (%s, %s, %s)", data
            )
        flash("เพิ่มหนังสือเรียบร้อยแล้ว", "success")
        return redirect(url_for("index"))
    return render_template("form.html", title="เพิ่มหนังสือ", book={})


@app.route("/edit/<int:book_id>", methods=["GET", "POST"])
def edit(book_id):
    with db_cursor() as cur:
        cur.execute("SELECT id, name, author, price FROM book WHERE id = %s", (book_id,))
        book = cur.fetchone()
    if book is None:
        flash("ไม่พบหนังสือที่ต้องการแก้ไข", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        data, error = parse_form()
        if error:
            flash(error, "danger")
            return render_template("form.html", title="แก้ไขหนังสือ", book=request.form)
        with db_cursor() as cur:
            cur.execute(
                "UPDATE book SET name = %s, author = %s, price = %s WHERE id = %s",
                (*data, book_id),
            )
        flash("แก้ไขข้อมูลเรียบร้อยแล้ว", "success")
        return redirect(url_for("index"))
    return render_template("form.html", title="แก้ไขหนังสือ", book=book)


@app.route("/delete/<int:book_id>", methods=["POST"])
def delete(book_id):
    with db_cursor() as cur:
        cur.execute("DELETE FROM book WHERE id = %s", (book_id,))
    flash("ลบหนังสือเรียบร้อยแล้ว", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
