#!/usr/bin/env python3
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import after path setup
from src.models.user import User, db
from src.models.application import Application

# Create Flask app instance
from flask import Flask
from flask_cors import CORS

def create_app():
    flask_app = Flask(__name__)
    flask_app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    CORS(flask_app)
    db.init_app(flask_app)
    return flask_app

def create_test_data():
    flask_app = create_app()
    
    with flask_app.app_context():
        # Create all tables
        db.create_all()
        
        # Create test admin user
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                department='IT',
                role='admin'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            print("Admin user created: admin/admin123")
        
        # Create test regular user
        test_user = User.query.filter_by(username='testuser').first()
        if not test_user:
            test_user = User(
                username='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User',
                department='Tahkim',
                role='user'
            )
            test_user.set_password('test123')
            db.session.add(test_user)
            print("Test user created: testuser/test123")
        
        # Create test applications
        apps = [
            {
                'name': 'Dava Takip Sistemi',
                'description': 'Sigorta tahkim davalarının takip edildiği ana sistem',
                'url': 'https://example.com/dava-takip',
                'category': 'Ana Sistemler'
            },
            {
                'name': 'Belge Yönetimi',
                'description': 'Dava dosyaları ve belgelerin dijital arşivlenmesi',
                'url': 'https://example.com/belge-yonetimi',
                'category': 'Belge İşlemleri'
            },
            {
                'name': 'Müşteri Portalı',
                'description': 'Sigortalı ve sigortalayan kişilerin erişim portalı',
                'url': 'https://example.com/musteri-portal',
                'category': 'Müşteri Hizmetleri'
            }
        ]
        
        for app_data in apps:
            existing_app = Application.query.filter_by(name=app_data['name']).first()
            if not existing_app:
                new_app = Application(**app_data)
                db.session.add(new_app)
                print(f"Application created: {app_data['name']}")
        
        db.session.commit()
        print("Test data creation completed!")

if __name__ == '__main__':
    create_test_data()

