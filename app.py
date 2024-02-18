from nest.core.app import App

from config import config
from coral_credits import api


app = App(
    description="Azimuth Cloud Credit service",
    modules=[api.CoralCreditsModule],
    title="Coral Cloud Credits",
)


@app.on_event("startup")
async def startup():
    await config.create_all()
