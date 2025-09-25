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
    
    # Bucket list endpoint
    @app.route('/api/bucket-list', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
    @app.route('/api/bucket-list/<int:movie_id>', methods=['DELETE', 'OPTIONS'])
    def bucket_list(movie_id=None):
        if request.method == 'OPTIONS':
            from flask import make_response
            response = make_response('', 200)
            response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            from .models import User, Movie, Favorite
            user = User.query.get(int(user_id))
            if not user:
                return {'error': 'User not found'}, 404
            
            if request.method == 'GET':
                print(f"GET bucket list for user_id: {user_id}")
                print(f"User found: {user}")
                print(f"User has {len(user.favorites)} favorites")
                
                # Filter out favorites where movie no longer exists
                favorites = []
                for fav in user.favorites:
                    print(f"Processing favorite: movie_id={fav.movie_id}, movie exists={fav.movie is not None}")
                    if fav.movie:  # Check if movie still exists
                        movie_dict = fav.movie.to_dict(rules=('-reviews', '-favorites'))
                        # Add frontend-compatible fields
                        movie_dict['poster_path'] = movie_dict.get('poster_url', '')
                        movie_dict['overview'] = movie_dict.get('description', '')
                        movie_dict['vote_average'] = movie_dict.get('rating', 0.0)
                        print(f"Adding movie to result: {movie_dict.get('title', 'No title')}")
                        favorites.append(movie_dict)
                    else:
                        print(f"Cleaning up orphaned favorite for movie_id={fav.movie_id}")
                        # Clean up orphaned favorite record
                        db.session.delete(fav)
                db.session.commit()
                print(f"Returning {len(favorites)} movies")
                return favorites
            
            elif request.method == 'POST':
                data = request.get_json()
                movie_id = data.get('movie_id')
                if not movie_id:
                    return {'error': 'Movie ID required'}, 400
                
                existing = Favorite.query.filter_by(user_id=user_id, movie_id=movie_id).first()
                if existing:
                    return {'message': 'Already in bucket list'}, 200
                
                # Check if movie exists, create if not
                movie = Movie.query.get(movie_id)
                if not movie:
                    print(f"Creating new movie record for movie_id: {movie_id}")
                    print(f"Movie data received: {data}")
                    
                    # Extract year from release_date
                    release_year = None
                    if data.get('release_date'):
                        try:
                            release_year = int(data.get('release_date')[:4])
                        except:
                            release_year = None
                    
                    movie = Movie(
                        id=movie_id,
                        title=data.get('title', 'Unknown Title'),
                        description=data.get('overview', ''),
                        release_year=release_year,
                        poster_url=f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}" if data.get('poster_path') else '',
                        rating=float(data.get('vote_average', 0.0))
                    )
                    db.session.add(movie)
                    print(f"Created movie: {movie.title}")
                
                favorite = Favorite(user_id=user_id, movie_id=movie_id)
                db.session.add(favorite)
                db.session.commit()
                return {'message': 'Added to bucket list'}, 201
            
            elif request.method == 'DELETE':
                # Get movie_id from URL parameter or request body
                if not movie_id:
                    data = request.get_json() or {}
                    movie_id = data.get('movie_id')
                if not movie_id:
                    return {'error': 'Movie ID required'}, 400
                
                favorite = Favorite.query.filter_by(user_id=user_id, movie_id=movie_id).first()
                if favorite:
                    db.session.delete(favorite)
                    db.session.commit()
                    return {'message': 'Removed from bucket list'}, 200
                return {'error': 'Not in bucket list'}, 404
                
        except Exception as e:
            print(f"Bucket list error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'error': f'Bucket list error: {str(e)}'}, 500
    
    # DELETE bucket list item endpoint
    @app.route('/api/bucket-list/<int:id>', methods=['DELETE', 'OPTIONS'])
    def delete_bucket_list_item(id):
        if request.method == 'OPTIONS':
            from flask import make_response
            response = make_response('', 200)
            response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
            response.headers['Access-Control-Allow-Methods'] = 'DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            print(f"DELETE: Looking for movie_id={id} for user_id={user_id}")
            
            from .models import Favorite
            favorite = Favorite.query.filter_by(user_id=int(user_id), movie_id=id).first()
            
            if favorite:
                print(f"Found favorite: {favorite.id}, deleting...")
                db.session.delete(favorite)
                db.session.commit()
                return {'message': 'Removed from bucket list'}, 200
            else:
                print(f"No favorite found for user {user_id} and movie {id}")
                # Show all favorites for this user
                all_favs = Favorite.query.filter_by(user_id=int(user_id)).all()
                print(f"User has {len(all_favs)} favorites: {[f.movie_id for f in all_favs]}")
                return {'message': 'Movie not in bucket list'}, 200
            
        except Exception as e:
            print(f"Delete bucket list error: {str(e)}")
            return {'error': f'Delete failed: {str(e)}'}, 500
    
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