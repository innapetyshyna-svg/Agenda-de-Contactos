from flask import Flask, request, jsonify, session, render_template, send_file, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
from datetime import datetime

from charts import generate_overview_chart, generate_birthdays_chart

app = Flask(__name__)
app.secret_key = '4f3d2a1b8e7c6d5e4f3d2a1b8e7c6d5e'

CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Admin@localhost/contact_agenda'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    contacts = db.relationship('Contact', backref='user', lazy=True)


class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255))
    birthday = db.Column(db.Date, nullable=True)


@app.route('/')
def main_page():
    return render_template('index.html')


@app.route('/register')
def register_page():
    return render_template('register_step1.html')


@app.route('/register/password')
def register_password_page():
    return render_template('register_step2.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout_page():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login_page'))


@app.route('/contacts')
@login_required
def contacts_main_page():
    return render_template('contacts_main.html')


@app.route('/charts/overview.png')
@login_required
def chart_overview():
    contacts = Contact.query.filter_by(user_id=current_user.id).all()
    img = generate_overview_chart(contacts)
    return send_file(img, mimetype='image/png')


@app.route('/charts/birthdays.png')
@login_required
def chart_birthdays():
    contacts = Contact.query.filter_by(user_id=current_user.id).all()
    img = generate_birthdays_chart(contacts)
    return send_file(img, mimetype='image/png')


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'erro': 'Username, email and password are required'}), 400

    try:
        if User.query.filter_by(username=username).first():
            return jsonify({'erro': 'Username already exists'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'erro': 'Email already exists'}), 400

        new_user = User(
            username=username,
            email=email,
            password=password
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({'mensagem': 'User successfully registered'}), 201

    except SQLAlchemyError as err:
        db.session.rollback()
        return jsonify({'erro': str(err)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'erro': 'Username e password são obrigatórios'}), 400

    try:
        user = User.query.filter_by(username=username, password=password).first()
    except SQLAlchemyError as err:
        return jsonify({'erro': str(err)}), 500

    if user:
        login_user(user)
        return jsonify({'mensagem': 'Login efetuado com sucesso!'})

    return jsonify({'erro': 'Credenciais inválidas'}), 401


@app.route('/api/contacts', methods=['GET'])
@login_required
def get_contacts():
    try:
        contacts = Contact.query.filter_by(user_id=current_user.id).all()
        contacts_list = []

        for contact in contacts:
            contacts_list.append({
                'id': contact.id,
                'name': contact.name,
                'phone': contact.phone,
                'email': contact.email,
                'birthday': contact.birthday.isoformat() if contact.birthday else ''
            })

        return jsonify(contacts_list)
    except SQLAlchemyError as err:
        return jsonify({'erro': str(err)}), 500


@app.route('/api/contacts', methods=['POST'])
@login_required
def add_contact():
    data = request.get_json(silent=True) or {}

    if not data.get('name') or not data.get('phone'):
        return jsonify({'erro': 'Nome e telefone são obrigatórios'}), 400

    birthday = None
    if data.get('birthday'):
        try:
            birthday = datetime.strptime(data['birthday'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'erro': 'Formato de birthday inválido. Use YYYY-MM-DD'}), 400

    try:
        new_contact = Contact(
            user_id=current_user.id,
            name=data['name'],
            phone=data['phone'],
            email=data.get('email', ''),
            birthday=birthday
        )

        db.session.add(new_contact)
        db.session.commit()

        return jsonify({
            'mensagem': 'Contacto adicionado com sucesso!',
            'id': new_contact.id
        })
    except SQLAlchemyError as err:
        db.session.rollback()
        return jsonify({'erro': str(err)}), 500


@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
@login_required
def update_contact(contact_id):
    data = request.get_json(silent=True) or {}

    try:
        contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()

        if not contact:
            return jsonify({'erro': 'Contacto não encontrado ou não autorizado'}), 404

        if data.get('name'):
            contact.name = data['name']
        if data.get('phone'):
            contact.phone = data['phone']
        if data.get('email') is not None:
            contact.email = data['email']

        if data.get('birthday') is not None:
            if data['birthday'] == '':
                contact.birthday = None
            else:
                try:
                    contact.birthday = datetime.strptime(data['birthday'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'erro': 'Formato de birthday inválido. Use YYYY-MM-DD'}), 400

        db.session.commit()
        return jsonify({'mensagem': 'Contacto atualizado com sucesso!'})
    except SQLAlchemyError as err:
        db.session.rollback()
        return jsonify({'erro': str(err)}), 500


@app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
@login_required
def delete_contact(contact_id):
    try:
        contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()

        if not contact:
            return jsonify({'erro': 'Contacto não encontrado ou não autorizado'}), 404

        db.session.delete(contact)
        db.session.commit()
        return jsonify({'mensagem': 'Contacto eliminado com sucesso!'})
    except SQLAlchemyError as err:
        db.session.rollback()
        return jsonify({'erro': str(err)}), 500


@app.route('/api/contacts/search', methods=['GET'])
@login_required
def search_contacts():
    query = request.args.get('q', '').strip()

    if not query:
        return get_contacts()

    try:
        contacts = Contact.query.filter(
            Contact.user_id == current_user.id,
            or_(
                Contact.name.like(f'%{query}%'),
                Contact.phone.like(f'%{query}%'),
                Contact.email.like(f'%{query}%')
            )
        ).all()

        contacts_list = []
        for contact in contacts:
            contacts_list.append({
                'id': contact.id,
                'name': contact.name,
                'phone': contact.phone,
                'email': contact.email,
                'birthday': contact.birthday.isoformat() if contact.birthday else ''
            })

        return jsonify(contacts_list)
    except SQLAlchemyError as err:
        return jsonify({'erro': str(err)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)