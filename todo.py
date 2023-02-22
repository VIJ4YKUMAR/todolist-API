from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# create database connection
SQLALCHEMY_DATABASE_URL = "mysql://vijay:*******@Localhost/TodoList"  # replace with your own database URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# create password hashing object
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# create models for db tables

#for User table
class User(Base):
    tablename = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(100))

#for TodoItem table
class TodoItem(Base):
    tablename = "todo_items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50))
    description = Column(String(100))
    is_completed = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="todo_items")

User.todo_items = relationship("TodoItem", back_populates="user")

# create database tables
Base.metadata.create_all(bind=engine)

# create an instance of FastAPI app
app = FastAPI()

# authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#function to create a session in the database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#function to verify the user entered password with hashed user password in the db
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

#function to get the username
def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

#function to authenticate the user
def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

#route to generate a token for the user to authenticate with the application
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = next(get_db())
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": user.username, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_user(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid authentication token")
    return user

# CRUD operations

#pydantic models
class TodoItemBase(BaseModel):
    title: str
    description: str

class TodoItemCreate(TodoItemBase):
    pass

class TodoItem(TodoItemBase):
    id: int
    is_completed: bool
    user_id: int

    class Config:
        orm_mode = True

#route to create a todo_item
@app.post("/todo_items/", response_model=TodoItem)
async def create_todo_item(todo_item: TodoItemCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_todo_item = TodoItem(title=todo_item.title, description=todo_item.description, user_id=current_user.id)
    db.add(db_todo_item)
    db.commit()
    db.refresh(db_todo_item)
    return db_todo_item

#route to read the todo_items
@app.get("/todo_items/", response_model=List[TodoItem])
async def read_todo_items(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo_items = db.query(TodoItem).filter(TodoItem.user_id == current_user.id).offset(skip).limit(limit).all()
    return todo_items
