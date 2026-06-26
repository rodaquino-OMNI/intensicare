from intensicare.config import settings
print('secret_key:', settings.secret_key.get_secret_value())
print('algorithm:', settings.jwt_algorithm)
print('expire:', settings.jwt_expire_minutes)
