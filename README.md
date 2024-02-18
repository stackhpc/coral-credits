# coral-credits

Coral credits is a resource management system that helps build a "coral reef style" fixed capacity cloud, cooperatively sharing community resources through interfaces such as: Azimuth, OpenStack Blazar and Slurm.

You can read more about our plans here:
https://stackhpc.github.io/coral-credits

## Development

Run server locally in tox env:

```bash
tox -erun
```

Or Run service using uvicorn:

```bash
uvicorn "app:app" --host "0.0.0.0" --port "8000" --reload
```

Then go to the fastapi auto generated docs:
http://127.0.0.1/docs
