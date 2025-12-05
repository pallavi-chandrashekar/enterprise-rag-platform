from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="RAG",
    settings_files=['settings.toml', '.secrets.toml'],
    environments=True,
)

def get_settings() -> Dynaconf:
    return settings
