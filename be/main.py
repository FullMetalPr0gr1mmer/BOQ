import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from APIs import LevelsRoute, LLDRoute, Level3Route
from APIs.BOQReferenceRoute import BOQRouter
from APIs.DismantlingRoute import DismantlingRouter
from APIs.InventoryRoute import inventoryRoute
from APIs.LLDRoute import lld_router
from APIs.LevelsRoute import levelsRouter
from APIs.LogRoute import logRouter
from APIs.ProjectRoute import projectRoute
from APIs.ROPLvl1Route import ROPLvl1router
from APIs.ROPLvl2Route import ROPLvl2router
from APIs.ROPProjectRoute import ROPProjectrouter
from APIs.RopPackageRoute import RopPackageRouter
from APIs.UserRoute import userRoute
from Database.session import engine, Base

#from Models import Config, SessionProject, AuditLog

app = FastAPI()
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://10.183.72.80:5173"],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(userRoute)
app.include_router(inventoryRoute)
app.include_router(projectRoute)
app.include_router(levelsRouter)

app.include_router(ROPProjectrouter)
app.include_router(ROPLvl1router)
app.include_router(logRouter)
app.include_router(ROPLvl2router)
app.include_router(BOQRouter)
app.include_router(RopPackageRouter)
app.include_router(Level3Route.router)
app.include_router(DismantlingRouter)

app.include_router(lld_router)

if __name__ == "__main__":
     uvicorn.run(app, host="127.0.0.1", port=8003)