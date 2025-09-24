from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, 
         resources={r"/api/*": {
             "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
             "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"]
         }})
    
    from .routes import auth, movies, genres
    app.register_blueprint(auth.bp)
    app.register_blueprint(movies.bp)
    app.register_blueprint(genres.bp)
    
    @app.route('/')
    def home():
        return {'message': 'Movie API is running', 'status': 'success'}
    
    @app.route('/api')
    def api_info():
        return {'endpoints': ['/api/movies', '/api/auth', '/api/genres']}
    
    # Direct register route for frontend compatibility
    @app.route('/api/register', methods=['POST', 'OPTIONS'])
    def register_direct():
        if request.method == 'OPTIONS':
            from flask import make_response
            response = make_response('', 200)
            response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        data = request.get_json()
        if not data:
            return {'error': 'No data provided'}, 400
        
        # Import here to avoid circular imports
        from .routes.auth import bp as auth_bp
        with app.test_request_context('/api/auth/register', method='POST', json=data):
            from .routes.auth import register
            return register()
    
    # Direct login route for frontend compatibility
    @app.route('/api/login', methods=['POST', 'OPTIONS'])
    def login_direct():
        if request.method == 'OPTIONS':
            from flask import make_response
            response = make_response('', 200)
            response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        data = request.get_json()
        if not data:
            return {'error': 'No data provided'}, 400
        
        with app.test_request_context('/api/auth/login', method='POST', json=data):
            from .routes.auth import login
            return login()
    
    # Direct profile route for frontend compatibility
    @app.route('/api/profile', methods=['GET', 'PATCH', 'PUT', 'OPTIONS'])
    def profile_direct():
        if request.method == 'OPTIONS':
            from flask import make_response
            response = make_response('', 200)
            response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        try:
            from flask_jwt_extended import jwt_required, get_jwt_identity
            from .models import User
            
            # Check for JWT token
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return {'error': 'Missing or invalid authorization header'}, 401
            
            # Manually verify JWT and get user
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # Ensure user_id is a string
            if user_id is not None:
                user_id = str(user_id)
            
            if not user_id:
                return {'error': 'Invalid token'}, 401
            
            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}, 404
            
            if request.method == 'GET':
                return user.to_dict(rules=('-password_hash', '-reviews', '-favorites'))
            elif request.method in ['PATCH', 'PUT']:
                # Handle PATCH request
                data = request.get_json()
                if not data:
                    return {'error': 'No data provided'}, 400
                
                if 'username' in data:
                    if User.query.filter_by(username=data['username']).filter(User.id != user_id).first():
                        return {'error': 'Username already exists'}, 400
                    user.username = data['username']
                if 'email' in data:
                    user.email = data['email']
                if 'age' in data:
                    user.age = data['age']
                if 'password' in data:
                    user.set_password(data['password'])
                
                db.session.commit()
                return user.to_dict(rules=('-password_hash', '-reviews', '-favorites'))
                
        except Exception as e:
            error_msg = str(e)
            print(f"Profile error: {error_msg}")
            
            if 'expired' in error_msg.lower():
                return {'error': 'Token has expired. Please login again.'}, 401
            elif 'invalid' in error_msg.lower() or 'signature' in error_msg.lower():
                return {'error': 'Invalid token. Please login again.'}, 401
            else:
                return {'error': f'Profile request failed: {error_msg}'}, 500
    
    return app