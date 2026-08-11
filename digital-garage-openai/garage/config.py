from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url:str='sqlite:///./garage.db'; data_root:str='./runtime-data'; vehicle_id:str='focus-st-2017'; allow_vehicle_writes:bool=False; api_host:str='127.0.0.1'; api_port:int=8080
    model_config=SettingsConfigDict(env_prefix='GARAGE_',env_file='.env',extra='ignore')
settings=Settings()
