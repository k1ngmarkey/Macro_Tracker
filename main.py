app = FastAPI(title="Macro Tracker")
app.include_router(foods.router)
app.include_router(entries.router)
app.include_router(goals.router)


