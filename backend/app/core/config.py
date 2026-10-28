from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_NGO_ADDRESS = "HNO 5-78\nPlot no 65, Navodaya Enclave,\nKuntloor, Hyderabad 501505"
DEFAULT_NGO_UPI_ID = "314337859395612@cnrb"
DEFAULT_NGO_BANK_ACCOUNT_NO = "120002395612"
DEFAULT_NGO_BANK_IFSC = "CNRB0013309"
DEFAULT_NGO_BANK_NAME = "Canara Bank"
DEFAULT_NGO_BANK_BRANCH = "Bandlaguda"


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
    ngo_address: str = DEFAULT_NGO_ADDRESS
    ngo_upi_id: str = DEFAULT_NGO_UPI_ID
    ngo_bank_account_name: str = ""
    ngo_bank_account_no: str = DEFAULT_NGO_BANK_ACCOUNT_NO
    ngo_bank_ifsc: str = DEFAULT_NGO_BANK_IFSC
    ngo_bank_name: str = DEFAULT_NGO_BANK_NAME
    ngo_bank_branch: str = DEFAULT_NGO_BANK_BRANCH
    # Bundled default logo, relative to the backend root — swapped for an uploaded one later.
    ngo_logo_path: str = "app/static/logo.jpg"

    seed_admin_username: str = "admin"
    seed_admin_password: str = "CHANGE_ME_on_first_login"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()