from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..models import Genre
from .. import db

bp = Blueprint('genres', __name__, url_prefix='/api/genres')

@bp.route('/', methods=['GET'])
def get_genres():
    genres = Genre.query.all()
    return jsonify([g.to_dict(rules=('-movies',)) for g in genres])

@bp.route('/', methods=['POST'])
@jwt_required()
def create_genre():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    if Genre.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Genre already exists'}), 400
    
    try:
        genre = Genre(name=data['name'])
        db.session.add(genre)
        db.session.commit()
        return jsonify(genre.to_dict(rules=('-movies',))), 201
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to create genre'}), 500

@bp.route('/<int:genre_id>', methods=['DELETE'])
@jwt_required()
def delete_genre(genre_id):
    genre = Genre.query.get_or_404(genre_id)
    try:
        db.session.delete(genre)
        db.session.commit()
        return jsonify({'message': 'Genre deleted'}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete genre'}), 500