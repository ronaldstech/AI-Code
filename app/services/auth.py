import hashlib
import hmac
import secrets

import mysql.connector
from mysql.connector import Error, IntegrityError

from app.config import (
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)


class AuthService:

    def __init__(self):
        self.sessions = {}
        self._initialize()

    def _connect(self):
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
        )

    def _initialize(self):
        server_connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
        )
        try:
            cursor = server_connection.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            server_connection.commit()
        finally:
            cursor.close()
            server_connection.close()

        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS users "
                "(id INT PRIMARY KEY AUTO_INCREMENT, email VARCHAR(255) UNIQUE NOT NULL, "
                "password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS chat_messages "
                "(id INT PRIMARY KEY AUTO_INCREMENT, user_id INT NOT NULL, role VARCHAR(32) NOT NULL, "
                "content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
                "FOREIGN KEY(user_id) REFERENCES users(id))"
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def signup(self, email, password):
        normalized_email = email.strip().lower()
        if len(password) < 8:
            return None, "Password must be at least 8 characters"

        password_hash = self._hash_password(password)
        try:
            with self._connect() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
                    (normalized_email, password_hash)
                )
                connection.commit()
                user_id = cursor.lastrowid
        except IntegrityError:
            return None, "An account with that email already exists"

        return self._create_session(user_id, normalized_email), None

    def login(self, email, password):
        normalized_email = email.strip().lower()
        with self._connect() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, email, password_hash FROM users WHERE email = %s",
                (normalized_email,)
            )
            user = cursor.fetchone()

        if user is None or not self._verify_password(password, user["password_hash"]):
            return None, "Invalid email or password"

        return self._create_session(user["id"], user["email"]), None

    def get_user(self, token):
        return self.sessions.get(token)

    def logout(self, token):
        self.sessions.pop(token, None)

    def get_chat_history(self, user_id):
        with self._connect() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT role, content FROM chat_messages WHERE user_id = %s "
                "ORDER BY id",
                (user_id,)
            )
            rows = cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def save_chat_message(self, user_id, role, content):
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO chat_messages (user_id, role, content) VALUES (%s, %s, %s)",
                (user_id, role, content)
            )
            connection.commit()

    def _create_session(self, user_id, email):
        token = secrets.token_urlsafe(32)
        user = {"id": user_id, "email": email}
        self.sessions[token] = user
        return {"token": token, "user": user}

    def _hash_password(self, password):
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
        return f"{salt.hex()}:{digest.hex()}"

    def _verify_password(self, password, stored_hash):
        salt_hex, digest_hex = stored_hash.split(":", 1)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 310000
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
