from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.secret_key = '4f3d2a1b8e7c6d5e4f3d2a1b8e7c6d5e'
CORS(app)

# Configuração da base de dados (MySQL via SQLAlchemy)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Admin@localhost/contact_agenda'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Autenticação - инициализация только один раз
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'  # Redirect unauthorized requests to the login page

# Модель User
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    # Связь с контактами
    #contacts = db.relationship('Contact', backref='user', lazy=True)

# Модель Contact
class Contact(db.Model):
    __tablename__ = 'contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255))
    address = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None

# HTML страницы
@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/')
@app.route('/index.html')
@login_required
def index():
    return render_template('index.html')

# API маршруты аутентификации
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    
    # Проверка наличия данных
    if not username or not password:
        return jsonify({'erro': 'Username e password são obrigatórios'}), 400
    
    # Поиск пользователя в БД
    try:
        user = User.query.filter_by(username=username, password=password).first()
    except SQLAlchemyError as err:
        return jsonify({'erro': str(err)}), 500
    
    # Проверка результата
    if user:
        login_user(user)
        return jsonify({'mensagem': 'Login efetuado com sucesso!'})
    
    return jsonify({'erro': 'Credenciais inválidas'}), 401

@app.route('/api/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'mensagem': 'Logout efetuado.'})

# API маршруты для контактов

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
                'address': contact.address
            })
        return jsonify(contacts_list)
    except SQLAlchemyError as err:
        return jsonify({'erro': str(err)}), 500

@app.route('/api/contacts', methods=['POST'])
@login_required
def add_contact():
    data = request.get_json(silent=True) or {}
    
    # Проверка обязательных полей
    if not data.get('name') or not data.get('phone'):
        return jsonify({'erro': 'Nome e telefone são obrigatórios'}), 400
    
    try:
        new_contact = Contact(
            user_id=current_user.id,
            name=data['name'],
            phone=data['phone'],
            email=data.get('email', ''),
            address=data.get('address', '')
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
        
        # Обновление полей
        if data.get('name'):
            contact.name = data['name']
        if data.get('phone'):
            contact.phone = data['phone']
        if data.get('email') is not None:
            contact.email = data['email']
        if data.get('address') is not None:
            contact.address = data['address']
        
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
    query = request.args.get('q', '')
    
    if not query:
        return get_contacts()
    
    try:
        contacts = Contact.query.filter(
            Contact.user_id == current_user.id,
            db.or_(
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
                'address': contact.address
            })
        return jsonify(contacts_list)
    except SQLAlchemyError as err:
        return jsonify({'erro': str(err)}), 500

if __name__ == '__main__':
    # Создание таблиц в базе данных (если их нет)
    """with app.app_context():
        db.create_all()"""
    app.run(debug=True)