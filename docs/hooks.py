from pathlib import Path
import subprocess


def generate_schema(config, **kwargs):
    """Generate OpenAPI schema before building documentation."""
    docs_dir = Path(config["docs_dir"])
    schema_path = docs_dir / "schema.yml"

    # Run drf-spectacular to generate schema
    try:
        subprocess.run(
            [
                "python",
                "manage.py",
                "spectacular",
                "--color",
                "--file",
                str(schema_path),
            ],
            check=True,
        )

    except subprocess.CalledProcessError as e:
        print(f"Error generating schema: {e}")
        return
