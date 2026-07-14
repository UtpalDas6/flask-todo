import os
from datetime import date, timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, g
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

db_url = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

TASK_COINS = 5
HABIT_COINS = 10
MILESTONE_EVERY = 7      # days
MILESTONE_BONUS = 50     # coins


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coins = db.Column(db.Integer, default=0)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100))
    complete = db.Column(db.Boolean, default=False)


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100))
    streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    last_done = db.Column(db.Date)


def next_streak(current_streak, last_done, today):
    """Pure streak transition: (new_streak, coins_awarded)."""
    if last_done == today:
        return current_streak, False
    if last_done == today - timedelta(days=1):
        return current_streak + 1, True
    return 1, True


@app.before_request
def load_user():
    user = User.query.first()
    if user is None:
        user = User(coins=0)
        db.session.add(user)
        db.session.commit()
    g.user = user


@app.route("/")
def home():
    todo_list = Todo.query.filter_by(user_id=g.user.id).all()
    habits = Habit.query.filter_by(user_id=g.user.id).all()
    return render_template(
        "base.html",
        todo_list=todo_list,
        habits=habits,
        today=date.today(),
        user=g.user,
    )


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title")
    db.session.add(Todo(title=title, complete=False, user_id=g.user.id))
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/update/<int:todo_id>")
def update(todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=g.user.id).first_or_404()
    todo.complete = not todo.complete
    if todo.complete:
        g.user.coins += TASK_COINS
    else:
        g.user.coins = max(0, g.user.coins - TASK_COINS)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/delete/<int:todo_id>")
def delete(todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=g.user.id).first_or_404()
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/habit/add", methods=["POST"])
def habit_add():
    name = request.form.get("name")
    db.session.add(Habit(name=name, streak=0, best_streak=0, last_done=None, user_id=g.user.id))
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/habit/checkin/<int:habit_id>")
def habit_checkin(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=g.user.id).first_or_404()
    today = date.today()
    habit.streak, awarded = next_streak(habit.streak, habit.last_done, today)
    habit.best_streak = max(habit.best_streak, habit.streak)
    habit.last_done = today
    if awarded:
        g.user.coins += HABIT_COINS
        if habit.streak % MILESTONE_EVERY == 0:
            g.user.coins += MILESTONE_BONUS
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/habit/delete/<int:habit_id>")
def habit_delete(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=g.user.id).first_or_404()
    db.session.delete(habit)
    db.session.commit()
    return redirect(url_for("home"))


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
