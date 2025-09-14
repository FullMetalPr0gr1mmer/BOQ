import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from APIs.Admin.AdminRoute import adminRoute
from APIs.BOQ import Level3Route
from APIs.BOQ.BOQReferenceRoute import BOQRouter
from APIs.BOQ.DismantlingRoute import DismantlingRouter
from APIs.BOQ.InventoryRoute import inventoryRoute
from APIs.BOQ.LLDRoute import lld_router
from APIs.BOQ.LevelsRoute import levelsRouter
#from APIs.BOQ.LogRoute import logRouter
from APIs.BOQ.ProjectRoute import projectRoute
from APIs.LE.ROPLvl1Route import ROPLvl1router
from APIs.LE.ROPLvl2Route import ROPLvl2router
from APIs.LE.ROPProjectRoute import ROPProjectrouter
from APIs.LE.RopPackageRoute import RopPackageRouter
from APIs.RAN.RANInventoryRouting import RANInventoryRouter
from APIs.RAN.RANLvl3Routing import RANLvl3Router
from APIs.RAN.RAN_LLDRouting import ran_lld_router
from APIs.Admin.UserRoute import userRoute
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
app.include_router(RANInventoryRouter)
app.include_router(ROPProjectrouter)
app.include_router(ROPLvl1router)
#app.include_router(logRouter)
app.include_router(ROPLvl2router)
app.include_router(BOQRouter)
app.include_router(RopPackageRouter)
app.include_router(Level3Route.router)
app.include_router(DismantlingRouter)
app.include_router(ran_lld_router)
app.include_router(lld_router)
app.include_router(RANLvl3Router)
app.include_router(adminRoute)
if __name__ == "__main__":
     uvicorn.run(app, host="127.0.0.1", port=8003)