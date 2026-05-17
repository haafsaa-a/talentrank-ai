from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    GROQ_API_KEY: str
    GITHUB_TOKEN: str = ""
    GOOGLE_SHEETS_CREDENTIALS: str = ""
    GOOGLE_SHEET_ID: str = ""
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str= ""
    APP_FRONTEND_URL: str = "http://localhost:5173"
    ENCRYPTION_KEY: str
    APP_BACKEND_URL: str = "http://localhost:8000"
    RESEND_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
