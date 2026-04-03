"""FastAPI application for the ConsultEnv Environment."""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required. Install with: pip install openenv-core[core]>=0.2.2"
    ) from e

try:
    from ..models import ConsultAction, ConsultObservation
    from .consultenv_environment import ConsultEnvEnvironment
except (ImportError, ModuleNotFoundError):
    from models import ConsultAction, ConsultObservation
    from server.consultenv_environment import ConsultEnvEnvironment


app = create_app(
    ConsultEnvEnvironment,
    ConsultAction,
    ConsultObservation,
    env_name="consultenv",
    max_concurrent_envs=1,
)


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
