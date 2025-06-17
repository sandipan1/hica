from pydantic import BaseModel
from hica.logging import logger

class test(BaseModel): 
    a: str
    b: int

new = test(a="sdfds", b=32)

logger.info("Created new test instance", instance=new.model_dump())