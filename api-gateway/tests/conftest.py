import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ISSUER"] = "identity-service"
os.environ["JWT_AUDIENCE"] = "gf-task-management"
os.environ["RATE_LIMIT_REQUESTS_PER_MINUTE"] = "1000"
