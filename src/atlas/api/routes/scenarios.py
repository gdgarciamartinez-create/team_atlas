from fastapi import APIRouter
from pydantic import BaseModel
from atlas.bot.persistence import load_scenarios, add_scenario, delete_scenario

router = APIRouter()

class Scenario(BaseModel):
    name: str
    symbol: str
    tf: str
    params: dict
    note: str = ""

class ScenarioDel(BaseModel):
    id: str

@router.get("/scenarios/list")
def list_all():
    return load_scenarios()

@router.post("/scenarios/add")
def add(s: Scenario):
    return add_scenario(s.dict())

@router.post("/scenarios/delete")
def delete(d: ScenarioDel):
    return delete_scenario(d.id)
