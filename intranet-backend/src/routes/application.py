from flask import Blueprint, jsonify, request, session
from src.models.application import Application
from src.models.user import db, User

application_bp = Blueprint('application', __name__)

def require_auth():
    """Kimlik doğrulama gereksinimi kontrolü"""
    if 'user_id' not in session:
        return jsonify({'error': 'Giriş yapılmamış'}), 401
    return None

def require_admin():
    """Admin yetkisi kontrolü"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    current_user = User.query.get(session['user_id'])
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Yetkisiz erişim'}), 403
    return None

@application_bp.route('/applications', methods=['GET'])
def get_applications():
    """Tüm uygulamaları listele"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    applications = Application.query.filter_by(is_active=True).all()
    return jsonify([app.to_dict() for app in applications])

@application_bp.route('/applications', methods=['POST'])
def create_application():
    """Yeni uygulama ekle (sadece admin/manager)"""
    admin_error = require_admin()
    if admin_error:
        return admin_error
    
    data = request.json
    
    # Gerekli alanları kontrol et
    if not data.get('name') or not data.get('url'):
        return jsonify({'error': 'Name and URL are required'}), 400
    
    application = Application(
        name=data['name'],
        description=data.get('description', ''),
        url=data['url'],
        icon_url=data.get('icon_url', ''),
        category=data.get('category', 'Genel')
    )
    
    db.session.add(application)
    db.session.commit()
    return jsonify(application.to_dict()), 201

@application_bp.route('/applications/<int:app_id>', methods=['GET'])
def get_application(app_id):
    """Belirli bir uygulamayı getir"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    application = Application.query.get_or_404(app_id)
    return jsonify(application.to_dict())

@application_bp.route('/applications/<int:app_id>', methods=['PUT'])
def update_application(app_id):
    """Uygulamayı güncelle (sadece admin/manager)"""
    admin_error = require_admin()
    if admin_error:
        return admin_error
    
    application = Application.query.get_or_404(app_id)
    data = request.json
    
    application.name = data.get('name', application.name)
    application.description = data.get('description', application.description)
    application.url = data.get('url', application.url)
    application.icon_url = data.get('icon_url', application.icon_url)
    application.category = data.get('category', application.category)
    application.is_active = data.get('is_active', application.is_active)
    
    db.session.commit()
    return jsonify(application.to_dict())

@application_bp.route('/applications/<int:app_id>', methods=['DELETE'])
def delete_application(app_id):
    """Uygulamayı sil (soft delete - sadece admin/manager)"""
    admin_error = require_admin()
    if admin_error:
        return admin_error
    
    application = Application.query.get_or_404(app_id)
    application.is_active = False
    db.session.commit()
    return '', 204

@application_bp.route('/applications/categories', methods=['GET'])
def get_categories():
    """Mevcut kategorileri listele"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    categories = db.session.query(Application.category).filter_by(is_active=True).distinct().all()
    return jsonify([cat[0] for cat in categories if cat[0]])

