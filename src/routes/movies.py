from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Movie, Review, Favorite, User, Genre
from .. import db

bp = Blueprint('movies', __name__, url_prefix='/api/movies')

@bp.route('/', methods=['GET'])
def get_movies():
    movies = Movie.query.all()
    return jsonify([m.to_dict(rules=('-reviews', '-favorites')) for m in movies])

@bp.route('/', methods=['POST'])
@jwt_required()
def create_movie():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    try:
        movie = Movie(
            title=data['title'],
            description=data.get('description'),
            release_year=data.get('release_year'),
            director=data.get('director'),
            poster_url=data.get('poster_url')
        )
        db.session.add(movie)
        db.session.commit()
        return jsonify({'id': movie.id, 'message': 'Movie created'}), 201
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to create movie'}), 500

@bp.route('/<int:movie_id>', methods=['GET'])
def get_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    return jsonify(movie.to_dict())

@bp.route('/<int:movie_id>', methods=['PATCH'])
@jwt_required()
def update_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        for key, value in data.items():
            if hasattr(movie, key) and key != 'id':
                setattr(movie, key, value)
        db.session.commit()
        return jsonify(movie.to_dict(rules=('-reviews', '-favorites')))
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to update movie'}), 500

@bp.route('/<int:movie_id>', methods=['DELETE'])
@jwt_required()
def delete_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    try:
        db.session.delete(movie)
        db.session.commit()
        return jsonify({'message': 'Movie deleted'}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete movie'}), 500

@bp.route('/<int:movie_id>/reviews', methods=['POST'])
@jwt_required()
def add_review(movie_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data or not all(k in data for k in ['content', 'rating']):
        return jsonify({'error': 'Content and rating are required'}), 400
    
    Movie.query.get_or_404(movie_id)
    try:
        review = Review(
            content=data['content'],
            rating=data['rating'],
            user_id=user_id,
            movie_id=movie_id
        )
        db.session.add(review)
        db.session.commit()
        return jsonify(review.to_dict(rules=('-user', '-movie'))), 201
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to add review'}), 500

@bp.route('/reviews/<int:review_id>', methods=['PATCH'])
@jwt_required()
def update_review(review_id):
    user_id = get_jwt_identity()
    review = Review.query.get_or_404(review_id)
    
    if review.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        if 'content' in data:
            review.content = data['content']
        if 'rating' in data:
            review.rating = data['rating']
        
        db.session.commit()
        return jsonify(review.to_dict(rules=('-user', '-movie')))
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to update review'}), 500

@bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    user_id = get_jwt_identity()
    review = Review.query.get_or_404(review_id)
    
    if review.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(review)
        db.session.commit()
        return jsonify({'message': 'Review deleted'}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete review'}), 500

@bp.route('/<int:movie_id>/favorite', methods=['POST'])
@jwt_required()
def toggle_favorite(movie_id):
    user_id = get_jwt_identity()
    Movie.query.get_or_404(movie_id)
    
    try:
        favorite = Favorite.query.filter_by(user_id=user_id, movie_id=movie_id).first()
        if favorite:
            db.session.delete(favorite)
            message = 'Removed from favorites'
        else:
            favorite = Favorite(user_id=user_id, movie_id=movie_id)
            db.session.add(favorite)
            message = 'Added to favorites'
        
        db.session.commit()
        return jsonify({'message': message})
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to update favorites'}), 500

@bp.route('/favorites', methods=['GET'])
@jwt_required()
def get_favorites():
    user_id = get_jwt_identity()
    try:
        favorites = db.session.query(Movie).join(Favorite).filter(Favorite.user_id == user_id).all()
        return jsonify([m.to_dict(rules=('-reviews', '-favorites')) for m in favorites])
    except Exception:
        return jsonify({'error': 'Failed to get favorites'}), 500