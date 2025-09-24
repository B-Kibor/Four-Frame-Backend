# API Endpoints for Frontend

Base URL: http://localhost:5002

## Authentication
- POST /api/auth/register - Register user
- POST /api/auth/login - Login user  
- GET /api/auth/profile - Get user profile
- PATCH /api/auth/profile - Update profile

## Movies
- GET /api/movies/ - Get all movies
- POST /api/movies/ - Create movie (requires auth)
- GET /api/movies/{id} - Get movie details
- PATCH /api/movies/{id} - Update movie (requires auth)
- DELETE /api/movies/{id} - Delete movie (requires auth)

## Reviews
- POST /api/movies/{id}/reviews - Add review (requires auth)
- PATCH /api/movies/reviews/{id} - Update review (requires auth)
- DELETE /api/movies/reviews/{id} - Delete review (requires auth)

## Favorites
- POST /api/movies/{id}/favorite - Toggle favorite (requires auth)
- GET /api/movies/favorites - Get user favorites (requires auth)

## Genres
- GET /api/genres/ - Get all genres
- POST /api/genres/ - Create genre (requires auth)
- DELETE /api/genres/{id} - Delete genre (requires auth)

## Example Frontend Fetch:
```javascript
// Get movies
fetch('http://localhost:5002/api/movies/')
  .then(res => res.json())
  .then(data => console.log(data))

// Login
fetch('http://localhost:5002/api/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'user', password: 'pass'})
})
```