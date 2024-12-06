
### Getting started

1. Launch your postgres server
2. Change storage_dsn in config/local.yaml
3. Install dependencies:
    ```bash
        poetry install
    ```
4. Run migrations:
    ```bash
    poetry run alembic upgrade head
    ```
5. Run the server:
    ```bash
    make api/run
    ```