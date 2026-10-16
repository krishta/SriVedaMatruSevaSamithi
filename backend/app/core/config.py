from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/svmss.db"

    jwt_secret: str = "CHANGE_ME_dev_only_placeholder_secret"
    jwt_access_ttl_min: int = 20
    jwt_refresh_ttl_days: int = 7

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    storage_backend: str = "local"
    upload_dir: str = "./data/uploads"
    receipts_dir: str = "./data/receipts"

    cors_allowed_origins: str = "http://localhost:4200"
    rate_limit_donations_per_hour: int = 10
    rate_limit_lookup_per_hour: int = 20

    ngo_name: str = "Sri Veda Matru Seva Samiti"
    ngo_address: str = "TBD_registered_address"
    ngo_upi_id: str = "TBD@upi"
    ngo_bank_account_name: str = "TBD"
    ngo_bank_account_no: str = "TBD"
    ngo_bank_ifsc: str = "TBD"
    ngo_bank_name: str = "TBD"
    # Bundled default logo, relative to the backend root — swapped for an uploaded one later.
    ngo_logo_path: str = "app/static/logo.jpg"

    seed_admin_username: str = "admin"
    seed_admin_password: str = "CHANGE_ME_on_first_login"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()