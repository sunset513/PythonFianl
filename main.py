from flask import Flask, request, render_template, url_for, redirect, g, session, send_file,jsonify
from flask_wtf import FlaskForm

# 資料庫及表單
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError, Regexp, Length
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
@app.route('/get', methods=['GET', 'POST'])
def chat():
    message =request.form['message']
    input = message
    return get_response(input)

def get_response(inputText):
    for step in range(5):

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
