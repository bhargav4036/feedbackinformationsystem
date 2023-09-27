from itsdangerous import URLSafeTimedSerializer
from key import secret_key,salt1,salt2,salt3
def token(email,salt):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.dumps(email,salt=salt)