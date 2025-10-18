from flask import Blueprint, jsonify, request, session
from src.models.user import User, db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Kullanıcı girişi"""
    data = request.json
    
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Kullanıcı adı ve şifre gerekli'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Geçersiz kullanıcı adı veya şifre'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Hesap devre dışı'}), 401
    
    # Session'a kullanıcı bilgilerini kaydet
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    
    # Son giriş zamanını güncelle
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Giriş başarılı',
        'user': user.to_dict()
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Kullanıcı çıkışı"""
    session.clear()
    return jsonify({'message': 'Çıkış başarılı'}), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    """Yeni kullanıcı kaydı"""
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
    
    # Yeni kullanıcı oluştur
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
    
    return jsonify({
        'message': 'Kullanıcı başarıyla oluşturuldu',
        'user': user.to_dict()
    }), 201

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Mevcut kullanıcı bilgilerini getir"""
    if 'user_id' not in session:
        return jsonify({'error': 'Giriş yapılmamış'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Şifre değiştirme"""
    if 'user_id' not in session:
        return jsonify({'error': 'Giriş yapılmamış'}), 401
    
    data = request.json
    
    if not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Mevcut şifre ve yeni şifre gerekli'}), 400
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Kullanıcı bulunamadı'}), 404
    
    if not user.check_password(data['current_password']):
        return jsonify({'error': 'Mevcut şifre yanlış'}), 400
    
    user.set_password(data['new_password'])
    db.session.commit()
    
    return jsonify({'message': 'Şifre başarıyla değiştirildi'}), 200

@auth_bp.route('/check-session', methods=['GET'])
def check_session():
    """Session durumunu kontrol et"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.is_active:
            return jsonify({
                'authenticated': True,
                'user': user.to_dict()
            }), 200
    
    return jsonify({'authenticated': False}), 200

