# Authentication (JWT) Setup

This project includes a simple JWT-based authentication demo for the API.

Environment variables
- `JWT_SECRET` : secret used to sign tokens. Generate a secure random value for production.
- `ADMIN_PASSWORD` : optional override for the demo admin user's password (default: `password`).
- `USER_PASSWORD` : optional override for the demo regular user's password (default: `password`).

Quick start
1. Install dependencies:
```bash
python3 -m pip install -r requirements.txt
python3 -m pip install PyJWT
```
2. (Optional) Set secure secret and passwords:
```bash
export JWT_SECRET=$(openssl rand -hex 32)
export ADMIN_PASSWORD="your-admin-password"
export USER_PASSWORD="your-user-password"
```
3. Start the API server:
```bash
uvicorn api.main:app --reload --port 8000
```
4. Obtain a token (example using `curl`):
```bash
curl -s -X POST "http://localhost:8000/token" -H "Content-Type: application/json" -d '{"username":"admin","password":"password"}' | jq
```
Response:
```json
{ "access_token": "<JWT>", "token_type": "bearer" }
```
5. Call protected endpoint:
```bash
curl -s -X POST "http://localhost:8000/analyze" -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" -d '{"message":"Test message"}'
```

Security notes
- This demo uses a simple in-memory store and SHA256 hashing; replace with a proper user database and a strong password hashing algorithm (bcrypt, Argon2) for production.
- Keep `JWT_SECRET` secret and rotate regularly.
- Use HTTPS in production.
