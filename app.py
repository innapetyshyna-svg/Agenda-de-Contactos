from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

# Initialize Flask application
app = Flask(__name__)
# Secret key for session encryption and security
app.secret_key = '4f3d2a1b8e7c6d5e4f3d2a1b8e7c6d5e'
# Enable CORS (Cross-Origin Resource Sharing) for all routes
CORS(app)

# Database configuration (MySQL via SQLAlchemy ORM)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Admin@localhost/contact_agenda'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking to save resources
db = SQLAlchemy(app)  # Create SQLAlchemy database instance

# Authentication setup - initialize LoginManager only once
login_manager = LoginManager()
login_manager.init_app(app)  # Bind LoginManager to the Flask app
login_manager.login_view = 'login_page'  # Redirect unauthorized users to the login page


# User model for database table 'users'
class User(db.Model, UserMixin):
    __tablename__ = 'users'  # Explicitly define table name

    # User table columns
    id = db.Column(db.Integer, primary_key=True)  # Primary key, auto-incremented
    username = db.Column(db.String(255), unique=True, nullable=False)  # Unique username, required
    password = db.Column(db.String(255), nullable=False)  # User password, required
    
    # Relationship with contacts (commented out but can be used for ORM relationships)
    contacts = db.relationship('Contact', backref='user', lazy=True)

# Contact model for database table 'contacts'
class Contact(db.Model):
    __tablename__ = 'contacts'  # Explicitly define table name
    
    # Contact table columns
    id = db.Column(db.Integer, primary_key=True)  # Primary key, auto-incremented
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Foreign key to users table
    name = db.Column(db.String(255), nullable=False)  # Contact name, required
    phone = db.Column(db.String(50), nullable=False)  # Phone number, required
    email = db.Column(db.String(255))  # Email address, optional
    address = db.Column(db.Text)  # Physical address, optional (Text type for longer content)

@login_manager.user_loader
def load_user(user_id):
    """
    Load user by ID for Flask-Login.
    This function is required to reload the user object from the user ID stored in the session.
    """
    try:
        # Retrieve user from database by ID
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        # Return None if user_id is invalid
        return None

# HTML page routes
@app.route('/login')
def login_page():
    """Serve the login page HTML"""
    return render_template('login.html')

@app.route('/')
@app.route('/index.html')
@login_required  # Require authentication to access this page
def index():
    """Serve the main application page (contact list)"""
    return render_template('index.html')

# Authentication API routes
@app.route('/api/login', methods=['POST'])
def login():
    """
    Handle user login requests.
    Expects JSON with username and password.
    Returns success message if credentials are valid, error otherwise.
    """
    # Get JSON data from request, return empty dict if no JSON
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    
    # Validate required fields
    if not username or not password:
        return jsonify({'erro': 'Username e password são obrigatórios'}), 400
    
    # Search for user in database
    try:
        # Simple authentication (in production, use password hashing)
        user = User.query.filter_by(username=username, password=password).first()
    except SQLAlchemyError as err:
        # Handle database errors
        return jsonify({'erro': str(err)}), 500
    
    # Check if user was found
    if user:
        login_user(user)  # Log the user in (creates session)
        return jsonify({'mensagem': 'Login efetuado com sucesso!'})
    
    # Return error for invalid credentials
    return jsonify({'erro': 'Credenciais inválidas'}), 401

@app.route('/api/logout')
@login_required  # User must be logged in to logout
def logout():
    """Handle user logout requests"""
    logout_user()  # Log the user out (clears session)
    return jsonify({'mensagem': 'Logout efetuado.'})

# Contact management API routes
@app.route('/api/contacts', methods=['GET'])
@login_required  # User must be logged in to view contacts
def get_contacts():
    """
    Retrieve all contacts for the currently logged-in user.
    Returns a list of contacts in JSON format.
    """
    try:
        # Query contacts belonging to current user
        contacts = Contact.query.filter_by(user_id=current_user.id).all()
        contacts_list = []
        # Convert contact objects to dictionaries for JSON serialization
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
        # Handle database errors
        return jsonify({'erro': str(err)}), 500

@app.route('/api/contacts', methods=['POST'])
@login_required  # User must be logged in to add contacts
def add_contact():
    """
    Add a new contact for the currently logged-in user.
    Expects JSON with name, phone, and optional email/address.
    Returns success message with new contact ID.
    """
    # Get JSON data from request
    data = request.get_json(silent=True) or {}
    
    # Validate required fields
    if not data.get('name') or not data.get('phone'):
        return jsonify({'erro': 'Nome e telefone são obrigatórios'}), 400
    
    try:
        # Create new contact object
        new_contact = Contact(
            user_id=current_user.id,  # Associate with current user
            name=data['name'],
            phone=data['phone'],
            email=data.get('email', ''),  # Use empty string if not provided
            address=data.get('address', '')
        )
        # Add to database and commit
        db.session.add(new_contact)
        db.session.commit()
        
        # Return success with new contact ID
        return jsonify({
            'mensagem': 'Contacto adicionado com sucesso!',
            'id': new_contact.id
        })
    except SQLAlchemyError as err:
        # Rollback transaction on error
        db.session.rollback()
        return jsonify({'erro': str(err)}), 500

@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
@login_required  # User must be logged in to update contacts
def update_contact(contact_id):
    """
    Update an existing contact.
    URL parameter: contact_id - ID of the contact to update
    Expects JSON with fields to update.
    """
    # Get JSON data from request
    data = request.get_json(silent=True) or {}
    
    try:
        # Find contact that belongs to current user
        contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
        
        # Return 404 if contact not found or doesn't belong to user
        if not contact:
            return jsonify({'erro': 'Contacto não encontrado ou não autorizado'}), 404
        
        # Update fields only if provided in request
        if data.get('name'):
            contact.name = data['name']
        if data.get('phone'):
            contact.phone = data['phone']
        if data.get('email') is not None:  # Allow empty string to clear email
            contact.email = data['email']
        if data.get('address') is not None:  # Allow empty string to clear address
            contact.address = data['address']
        
        # Save changes to database
        db.session.commit()
        return jsonify({'mensagem': 'Contacto atualizado com sucesso!'})
    except SQLAlchemyError as err:
        # Rollback transaction on error
        db.session.rollback()
        return jsonify({'erro': str(err)}), 500

@app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
@login_required  # User must be logged in to delete contacts
def delete_contact(contact_id):
    """
    Delete a contact.
    URL parameter: contact_id - ID of the contact to delete
    """
    try:
        # Find contact that belongs to current user
        contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
        
        # Return 404 if contact not found or doesn't belong to user
        if not contact:
            return jsonify({'erro': 'Contacto não encontrado ou não autorizado'}), 404
        
        # Delete contact from database
        db.session.delete(contact)
        db.session.commit()
        return jsonify({'mensagem': 'Contacto eliminado com sucesso!'})
    except SQLAlchemyError as err:
        # Rollback transaction on error
        db.session.rollback()
        return jsonify({'erro': str(err)}), 500

@app.route('/api/contacts/search', methods=['GET'])
@login_required  # User must be logged in to search contacts
def search_contacts():
    """
    Search contacts by name, phone, or email.
    Query parameter: q - search query string
    Returns filtered list of contacts.
    """
    # Get search query from URL parameters
    query = request.args.get('q', '')
    
    # If no query, return all contacts
    if not query:
        return get_contacts()
    
    try:
        # Search for contacts matching query in name, phone, or email
        contacts = Contact.query.filter(
            Contact.user_id == current_user.id,  # Only current user's contacts
            db.or_(  # Match any of these conditions
                Contact.name.like(f'%{query}%'),   # Name contains query
                Contact.phone.like(f'%{query}%'),  # Phone contains query
                Contact.email.like(f'%{query}%')   # Email contains query
            )
        ).all()
        
        # Convert contact objects to dictionaries for JSON serialization
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
        # Handle database errors
        return jsonify({'erro': str(err)}), 500

# Run the application if this file is executed directly
if __name__ == '__main__':
        # Создание таблиц в базе данных (если их нет)
    with app.app_context():
        db.create_all()
    app.run(debug=True)  # Run in debug mode for development