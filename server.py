import os
from datetime import datetime

from flask import Flask, url_for, redirect, request
from flask_admin import helpers, expose
from flask_admin.contrib import sqla
from flask_sqlalchemy import SQLAlchemy
from flask_admin import base
from sqlalchemy import UniqueConstraint
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
import flask_admin as admin
import flask_login as login

from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import form, fields, validators

from server import *

app = Flask(__name__)

app.config['SECRET_KEY'] = 'utopianio'


app.config['DATABASE_FILE'] = 'utopianio.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = False
db = SQLAlchemy(app)

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)


class Telegram_User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, unique=True)
    steem_name = db.Column(db.String(200))
    activite  = db.Column(db.Boolean, default=False)

    def __str__(self):
        return str(self.client_id)

    def __repr__(self):
        return '<Telegram_User %r>' % (self.client_id)

    def get_users(self, user_id):
        return self.query.filter_by(client_id=user_id).first() or False


class Control(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post =  db.Column(db.String(400))
    telegram_user_id = db.Column(db.Integer(), db.ForeignKey(Telegram_User.id))
    telegram_user = db.relationship(Telegram_User)
    is_comment = db.Column(db.Boolean, default=False)
    is_vote = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("id", "post"),
    )


    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return '<Telegram_User bot %r>' % (self.id)

    def get_blog(self, blog):
        return self.query.filter_by(post=blog).first() or False


class Price_task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.Integer(), db.ForeignKey(Telegram_User.id))
    telegram_user = db.relationship(Telegram_User)
    price_task = db.Column(db.Integer)

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return '<Price task  %r>' % (self.price_task)

    def get_task(self, user):
        return self.query.filter_by(telegram_user=user).first() or False

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password = db.Column(db.String(64))

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        if not check_password_hash(user.password, self.password.data):
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(login=self.login.data).first()


class RegistrationForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    email = fields.StringField()
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(login=self.login.data).count() > 0:
            raise validators.ValidationError('Duplicate username')


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated


# Create customized index view class that handles login & registration
class MyAdminIndexView(base.AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        link = ''
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))
    
# Flask views
@app.route('/')
def index():
    return redirect(url_for('admin.login_view'))


# Initialize flask-login
init_login()

# Create admin
admin = base.Admin(app, 'Bot', index_view=MyAdminIndexView(), base_template='my_master.html')

# Add view
admin.add_view(MyModelView(Telegram_User, db.session))
admin.add_view(MyModelView(Control, db.session))
admin.add_view(MyModelView(Price_task, db.session))
admin.add_view(MyModelView(User, db.session))

def build_sample_db():
    db.drop_all()
    db.create_all()

    test_user = User(login="test", password=generate_password_hash("test"))
    db.session.add(test_user)
    db.session.commit()
    return
if __name__ == '__main__':
    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()
    port = int(os.environ.get('PORT', 5000))
    manager.run()
