from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, String, select, DateTime, func
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
import datetime

# ==========================================
# 1. DATABASE SETUP
# ==========================================
engine = create_engine("sqlite:///final_app.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(50), unique=True)


class Blog(Base):
    __tablename__ = "blogs"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(String(2000))
    author: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

Base.metadata.create_all(bind=engine)

# Ensure new columns exist in existing SQLite table (safe ALTER TABLE add column)
def ensure_blog_columns():
    inspector = sa.inspect(engine)
    if "blogs" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("blogs")}
    with engine.begin() as conn:
        if "author" not in cols:
            conn.execute(sa.text("ALTER TABLE blogs ADD COLUMN author VARCHAR(100)"))
        if "created_at" not in cols:
            conn.execute(sa.text("ALTER TABLE blogs ADD COLUMN created_at DATETIME"))
        if "updated_at" not in cols:
            conn.execute(sa.text("ALTER TABLE blogs ADD COLUMN updated_at DATETIME"))

ensure_blog_columns()

# ==========================================
# 2. FASTAPI & JINJA2 SETUP
# ==========================================
app = FastAPI()
templates = Jinja2Templates(directory="Frontend")
# serve static files from Frontend/static at /static
app.mount("/static", StaticFiles(directory="Frontend/static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 3. ROUTES (Returning HTML Pages)
# ==========================================

# --- READ (Homepage) ---
@app.get("/", response_class=HTMLResponse)
def home_page(request: Request, db: Session = Depends(get_db)):
    users = db.scalars(select(User)).all()
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"users": users}
    )

# --- CREATE ---
@app.get("/create", response_class=HTMLResponse)
def create_page(request: Request):
    return templates.TemplateResponse(request=request, name="create.html")

@app.post("/create")
def create_user(name: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    new_user = User(name=name, email=email)
    db.add(new_user)
    db.commit()
    # 303 status code tells the browser to redirect back to the homepage
    return RedirectResponse(url="/", status_code=303)

# --- UPDATE ---
@app.get("/update/{user_id}", response_class=HTMLResponse)
def update_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    return templates.TemplateResponse(
        request=request, 
        name="update.html", 
        context={"user": user}
    )

@app.post("/update/{user_id}")
def update_user(user_id: int, name: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user:
        user.name = name
        user.email = email
        db.commit()
    return RedirectResponse(url="/", status_code=303)

# --- DELETE ---
@app.get("/delete/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/", status_code=303)


# ==========================================
# Blog routes
# ==========================================


@app.get("/blog", response_class=HTMLResponse)
def blog_index(request: Request, db: Session = Depends(get_db)):
    posts = db.scalars(select(Blog)).all()
    return templates.TemplateResponse(
        request=request,
        name="blog_index.html",
        context={"posts": posts}
    )


@app.get("/blog/create", response_class=HTMLResponse)
def blog_create_page(request: Request):
    return templates.TemplateResponse(request=request, name="blog_create.html")


@app.post("/blog/create")
def create_post(title: str = Form(...), content: str = Form(...), author: str = Form(""), db: Session = Depends(get_db)):
    new_post = Blog(title=title, content=content, author=author)
    db.add(new_post)
    db.commit()
    return RedirectResponse(url="/blog", status_code=303)


@app.get("/blog/update/{post_id}", response_class=HTMLResponse)
def blog_update_page(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = db.get(Blog, post_id)
    return templates.TemplateResponse(
        request=request,
        name="blog_update.html",
        context={"post": post}
    )


@app.post("/blog/update/{post_id}")
def update_post(post_id: int, title: str = Form(...), content: str = Form(...), author: str = Form(""), db: Session = Depends(get_db)):
    post = db.get(Blog, post_id)
    if post:
        post.title = title
        post.content = content
        post.author = author
        post.updated_at = func.now()
        db.commit()
    return RedirectResponse(url="/blog", status_code=303)


@app.get("/blog/delete/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(Blog, post_id)
    if post:
        db.delete(post)
        db.commit()
    return RedirectResponse(url="/blog", status_code=303)


@app.get("/blog/{post_id}", response_class=HTMLResponse)
def blog_detail(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = db.get(Blog, post_id)
    return templates.TemplateResponse(
        request=request,
        name="blog_detail.html",
        context={"post": post}
    )