import bcrypt

def hash_password(password: str) -> str:
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    print(hashed_password.decode('utf-8'))
    return hashed_password.decode('utf-8')  # Return as a string

hashed_password = hash_password("Vedika@123")
print(hashed_password)