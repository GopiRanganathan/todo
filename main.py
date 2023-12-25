from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, relationship
import sqlalchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from datetime import datetime, timedelta
from pywebpush import webpush, WebPushException
# from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler

browser_endpoint = ''

# load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQL_URI')


login_manager = LoginManager()
login_manager.init_app(app)

# DATABASE SCHEMA
class Base(DeclarativeBase):
  pass

db = SQLAlchemy(app, model_class=Base)

class User(db.Model, UserMixin):
    __tablename__ = "Users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=False, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, unique=True, nullable=False)
    endpoint = db.Column(db.String, unique=False, nullable=True)
    key1 = db.Column(db.String, unique=False, nullable=True)
    key2 = db.Column(db.String, unique=False, nullable=True)
    tasks = relationship('Todo', back_populates='user')

class Todo(db.Model):
    __tablename__ = 'todos'
    user = relationship('User', back_populates='tasks')
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'))
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=False, nullable=False)
    duedate = db.Column(db.DateTime, nullable=True)
    createdate = db.Column(db.DateTime, nullable=False)
    alert = db.Column(db.Boolean, nullable=False)
    completed = db.Column(db.Boolean, nullable=False)



with app.app_context():
    db.create_all()


# FUNCTION TO SEND NOTIFICATION
def send_notification(id, todo):
    user = db.get_or_404(User, id)
    subscription_data = {
        "endpoint": user.endpoint,
        "keys":{
            "p256dh": user.key1,
            "auth": user.key2
        }
    }  
    payload = f'Hey {user.name}! {todo.title} due tomorrow! Take action!'
    vapid_private_key = os.environ.get('PRIVATE_KEY') 
    vapid_claims = {
        'sub': 'mailto:gopiranga9@email.com'  
    }
    try:
        webpush(
            subscription_info=subscription_data,
            data=payload,
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims
        )
        return jsonify({'success': True, 'message': 'Notification sent successfully'})
    except WebPushException as e:
        return jsonify({'success': False, 'message': f'Failed to send notification: {str(e)}'})

# CHECK DUE DATE
def check_due_date():
    with app.app_context():
        # print('scheduler start')
        tomorrow = datetime.now().date() + timedelta(days=1)
        due_dates = Todo.query.filter(Todo.duedate == tomorrow, Todo.alert == True, Todo.completed == False).all()
        # print(due_dates)
        for todo in due_dates:
            send_notification(id=todo.user_id, todo=todo)


# SCHEDULER
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(check_due_date, 'cron', day_of_week='*', hour=22, minute=0) 
scheduler.start()


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


@app.route('/')
def home():
    if current_user.is_authenticated:
        todos = db.session.execute(db.select(Todo).where(Todo.user_id == current_user.id) ).scalars()
        
        return render_template('todo.html', todos = todos, today = datetime.now().date(), timedelta=timedelta)
    return render_template('index.html', is_logged=current_user.is_authenticated)


@app.route('/signup', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        try:
            password = request.form.get('password')
            generated_password = generate_password_hash(password=password, method="scrypt", salt_length=12)
            new_user = User(
                name= request.form.get('username'),
                email = request.form.get('email'),
                password = generated_password,
                endpoint = browser_endpoint['endpoint'],
                key1 = browser_endpoint['keys']['p256dh'],
                key2 = browser_endpoint['keys']['auth']
            )
            db.session.add(new_user)
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash("You already signed up. Please log in", 'warning')
            return redirect(url_for('log_in'))
        login_user(new_user)
        flash("Success! You're now signed up. Ready to tackle your to-dos?", "success")
        return redirect(url_for('home'))
    return render_template('signup.html', is_logged=current_user.is_authenticated)

@app.route('/login', methods=['GET', 'POST'])
def log_in():
    if request.method == 'POST':
        user = db.session.execute(db.select(User).where(User.email == request.form.get('email'))).scalar()
        if user:
            if check_password_hash(user.password, request.form.get('password')):
                flash("Success! You're now logged in.", "success")
                login_user(user)
                return redirect(url_for('home'))
            else:
                flash("Invalid Password!", "danger")
                return redirect(url_for('log_in'))
        else:
            flash('No account found. Please sign up.', "danger")
            return redirect(url_for('sign_up'))
    return render_template('login.html', is_logged=current_user.is_authenticated)


@app.route('/add', methods=['POST', 'GET'])
@login_required
def add_todo():
    if request.method == 'POST':
        new_todo = Todo(
            user_id = current_user.id,
            title = request.form.get('title'),
            duedate = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date(),
            createdate = datetime.now().date(),
            alert = False if request.form.get('alert') == None else True,
            completed = False
        )
        db.session.add(new_todo)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_todo.html')


@app.route('/updatetodo/<int:id>', methods=['GET', 'POST'])
@login_required
def update_todo_status(id):
    if request.method == 'POST':
        todo = db.session.execute(db.select(Todo).where(Todo.id==id)).scalar()
        todo.completed = request.json['completed']
        db.session.commit()
        return {'message': f'Todo ID {id} status updated successfully'}, 200
    

@app.route('/delete/<int:id>')
@login_required
def delete_todo(id):
    todo = db.session.execute(db.select(Todo).where(Todo.id==id)).scalar()
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/edit_todo/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_todo(id):
    todo = db.session.execute(db.select(Todo).where(Todo.id==id)).scalar()
    if request.method == 'POST':
        todo.title = request.form.get('title')
        todo.duedate = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        todo.alert = False if request.form.get('alert') == None else True
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_todo.html', todo=todo)


@app.route('/save-token', methods=['POST'])
def save_token():
    global browser_endpoint
    data = request.get_json() 
    browser_endpoint = data
    return 'Subscription received successfully'
    

    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=False)