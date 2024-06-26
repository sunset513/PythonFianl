from flask import Flask, request, render_template, url_for, redirect, g, session, jsonify
from flask_wtf import FlaskForm

# 資料庫及表單
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError, Regexp

import sqlite3

# 大型語言模型
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 資料庫處理
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

# 判斷使用者相關資訊
def validate_username(form, field):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (field.data,)).fetchone()
    if user:
        raise ValidationError('This name has already been taken')

def validate_password(form, field):
    password = field.data
    if (len(password) < 8 or not any(c.isupper() for c in password)
            or not any(c.islower() for c in password)
            or not any(c.isdigit() for c in password)
            or not any(c in '@$!%*?&' for c in password)):
        raise ValidationError('Password must be at least 8 characters long and contain uppercase and lowercase letters, digits, and special characters')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), validate_username])
    password = PasswordField('Password', validators=[DataRequired(), validate_password])
    email = StringField('Email', validators=[DataRequired(), Email(), Regexp(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', message="Email must be in the format XXX@gmail.com")])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@app.route('/')
def index():
    return redirect(url_for('login'))

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
            return render_template('login.html', form=form, error='Incorrect username or password')
    form.password.data = ''
    return render_template('login.html', form=form)


# 登出
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


# 聊天室
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    return render_template('chat.html')

# 聊天室訊息
@app.route('/get', methods=['POST'])
def get_message():
    message = request.form['msg']
    response = get_response(message)
    return jsonify(response=response)

def get_response(inputText):
    for step in range(15):

        # encode the new user input, add the eos_token and return a tensor in Pytorch
        new_user_input_ids = tokenizer.encode(str(inputText) + tokenizer.eos_token, return_tensors='pt')

        # append the new user input tokens to the chat history
        bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids], dim=-1) if step > 0 else new_user_input_ids

        # generated a response
        chat_history_ids = model.generate(bot_input_ids, max_length=1000, pad_token_id=tokenizer.eos_token_id)

        # pretty print last ouput tokens from bot
        return format(tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True))

if __name__ == '__main__':
    app.run(debug=True)
