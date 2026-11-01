
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import numpy as np
from pathlib import Path

app = Flask(__name__)
app.secret_key = "smart_library_secret"

# CSV file location
DATA_FILE = Path(__file__).with_name("books.csv")


# Load books from CSV
def load_books():
    df = pd.read_csv(DATA_FILE)

    # Clean column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # Rename CSV columns to match the application
    df.rename(columns={
        "book_id": "id",
        "total_copies": "total",
        "available_copies": "available"
    }, inplace=True)

    # Check required columns
    if "id" not in df.columns:
        df.insert(0, "id", range(1, len(df) + 1))

    if "title" not in df.columns:
        df["title"] = ""

    if "author" not in df.columns:
        df["author"] = ""

    if "category" not in df.columns:
        df["category"] = ""

    if "total" not in df.columns:
        df["total"] = 0

    if "available" not in df.columns:
        df["available"] = df["total"]

    if "publication_year" not in df.columns:
        df["publication_year"] = ""

    # Convert numeric columns
    for col in ["id", "total", "available"]:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    # Clean text columns
    for col in ["title", "author", "category"]:
        df[col] = df[col].fillna("").astype(str)

    return df


# Save books to CSV
def save_books(df):
    df.to_csv(DATA_FILE, index=False)


# Home page
@app.route("/")
def index():
    df = load_books()

    search = request.args.get("q", "").strip()
    category = request.args.get("cat", "").strip()

    # Search books by title or author
    if search:
        df = df[
            df["title"].str.contains(search, case=False, na=False)
            | df["author"].str.contains(search, case=False, na=False)
        ]

    # Filter books by category
    if category:
        df = df[df["category"] == category]

    all_books = load_books()

    # Dashboard statistics using NumPy
    stats = {
        "total": int(np.sum(all_books["total"])),
        "available": int(np.sum(all_books["available"])),
        "issued": int(np.sum(
            all_books["total"] - all_books["available"]
        )),
        "titles": len(all_books)
    }

    # Get book categories
    categories = sorted(
        all_books["category"].dropna().unique().tolist()
    )

    # Convert DataFrame into list of dictionaries
    books = df.to_dict(orient="records")

    return render_template(
        "index.html",
        stats=stats,
        books=books,
        categories=categories,
        q=search,
        cat=category
    )


# Issue a book
@app.route("/issue/<int:book_id>", methods=["POST"])
def issue_book(book_id):
    df = load_books()

    match = df.index[df["id"] == book_id]

    if len(match) > 0:
        index = match[0]

        if df.loc[index, "available"] > 0:
            df.loc[index, "available"] -= 1
            save_books(df)
            flash("Book issued successfully!", "success")
        else:
            flash("Book is not available!", "error")

    return redirect(url_for("index"))


# Return a book
@app.route("/return/<int:book_id>", methods=["POST"])
def return_book(book_id):
    df = load_books()

    match = df.index[df["id"] == book_id]

    if len(match) > 0:
        index = match[0]

        if df.loc[index, "available"] < df.loc[index, "total"]:
            df.loc[index, "available"] += 1
            save_books(df)
            flash("Book returned successfully!", "success")
        else:
            flash("All copies are already available!", "error")

    return redirect(url_for("index"))


# Add a new book
@app.route("/add", methods=["POST"])
def add_book():
    df = load_books()

    try:
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not author or not category:
            raise ValueError("All fields are required")

        total = int(request.form.get("total", 1))

        if total < 1:
            raise ValueError("Total copies must be at least 1")

        new_id = int(df["id"].max()) + 1 if not df.empty else 1

        new_book = {
            "id": new_id,
            "title": title,
            "author": author,
            "category": category,
            "publication_year": request.form.get(
                "publication_year", ""
            ).strip(),
            "total": total,
            "available": total
        }

        df = pd.concat(
            [df, pd.DataFrame([new_book])],
            ignore_index=True
        )

        save_books(df)
        flash("New book added successfully!", "success")

    except (ValueError, KeyError):
        flash("Please enter valid book details!", "error")

    return redirect(url_for("index"))


# Run application
if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=5000,
        use_reloader=False
    )
