from flask import Flask, request, render_template, url_for, redirect, g, session, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError, Regexp, Length
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('users.db')
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def validate_username(form, field):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (field.data,)).fetchone()
    if user:
        raise ValidationError('此名稱已被使用')

def validate_password(form, field):
    password = field.data
    if (len(password) < 8 or not any(c.isupper() for c in password)
            or not any(c.islower() for c in password)
            or not any(c.isdigit() for c in password)
            or not any(c in '@$!%*?&' for c in password)):
        raise ValidationError('密碼必須超過8個字元且包含英文大小寫和特殊字元')

class RegistrationForm(FlaskForm):
    username = StringField('使用者名稱', validators=[DataRequired(), validate_username])
    password = StringField('密碼', validators=[DataRequired(), validate_password])
    email = StringField('電子郵件', validators=[DataRequired(), Email(), Regexp(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', message="電子郵件必須是XXX@gmail.com")])
    submit = SubmitField('註冊')

class LoginForm(FlaskForm):
    username = StringField('使用者名稱', validators=[DataRequired()])
    password = StringField('密碼', validators=[DataRequired()])
    submit = SubmitField('登入')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data

        db = get_db()
        db.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', (username, password, email))
        db.commit()

        return redirect(url_for('login'))
    form.password.data = ''
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():

        username = form.username.data
        password = form.password.data

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()

        if user:
            session['username'] = user['username']
            return redirect(url_for('chat'))
        else:
            form.password.data = ''
            return render_template('login.html', form=form, error='使用者名稱或密碼錯誤')
    form.password.data = ''
    return render_template('login.html', form=form)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    
    return render_template('chat.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
