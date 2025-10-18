from flask import Blueprint, jsonify, request, session
from src.models.user import User, db

user_bp = Blueprint('user', __name__)

def require_auth():
    """Kimlik doğrulama gereksinimi kontrolü"""
    if 'user_id' not in session:
        return jsonify({'error': 'Giriş yapılmamış'}), 401
    return None

@user_bp.route('/users', methods=['GET'])
def get_users():
    """Tüm kullanıcıları listele (sadece admin)"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    # Admin kontrolü
    current_user = User.query.get(session['user_id'])
    if current_user.role != 'admin':
        return jsonify({'error': 'Yetkisiz erişim'}), 403
    
    users = User.query.filter_by(is_active=True).all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users', methods=['POST'])
def create_user():
    """Yeni kullanıcı oluştur (sadece admin)"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    # Admin kontrolü
    current_user = User.query.get(session['user_id'])
    if current_user.role != 'admin':
        return jsonify({'error': 'Yetkisiz erişim'}), 403
    
    data = request.json
    
    # Gerekli alanları kontrol et
    required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} alanı gerekli'}), 400
    
    # Kullanıcı adı ve email kontrolü
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Bu kullanıcı adı zaten kullanılıyor'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Bu email adresi zaten kullanılıyor'}), 400
    
    user = User(
        username=data['username'],
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        department=data.get('department', ''),
        role=data.get('role', 'user')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Belirli bir kullanıcıyı getir"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    current_user = User.query.get(session['user_id'])
    
    # Kullanıcı sadece kendi bilgilerini veya admin tüm kullanıcıları görebilir
    if current_user.id != user_id and current_user.role != 'admin':
        return jsonify({'error': 'Yetkisiz erişim'}), 403
    
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Kullanıcıyı güncelle"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    current_user = User.query.get(session['user_id'])
    
    # Kullanıcı sadece kendi bilgilerini veya admin tüm kullanıcıları güncelleyebilir
    if current_user.id != user_id and current_user.role != 'admin':
        return jsonify({'error': 'Yetkisiz erişim'}), 403
    
    user = User.query.get_or_404(user_id)
    data = request.json
    
    # Güncellenebilir alanlar
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'email' in data:
        # Email benzersizlik kontrolü
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'error': 'Bu email adresi zaten kullanılıyor'}), 400
        user.email = data['email']
    if 'department' in data:
        user.department = data['department']
    
    # Sadece admin rol değiştirebilir
    if 'role' in data and current_user.role == 'admin':
        user.role = data['role']
    
    # Sadece admin kullanıcıyı devre dışı bırakabilir
    if 'is_active' in data and current_user.role == 'admin':
        user.is_active = data['is_active']
    
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Kullanıcıyı sil (soft delete - sadece admin)"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    current_user = User.query.get(session['user_id'])
    if current_user.role != 'admin':
        return jsonify({'error': 'Yetkisiz erişim'}), 403
    
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return '', 204
