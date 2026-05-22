from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Contact(BaseModel):
    email: str
    linkedin: str
    github: str
    phone: str | None = None
    site: str | None = None


class Experience(BaseModel):
    company: str
    role: str
    dates: str
    location: str | None = None
    bullets: list[str]


class Project(BaseModel):
    name: str
    description: str
    url: str | None = None
    bullets: list[str]


class Education(BaseModel):
    institution: str
    degree: str
    dates: str
    location: str | None = None
    bullets: list[str] = []


class MasterResume(BaseModel):
    name: str
    contact: Contact
    summary_pool: list[str]
    skills: dict[str, list[str]]
    experience: list[Experience]
    projects: list[Project]
    education: list[Education]
    awards: list[str] = []


class TailoredOutput(BaseModel):
    summary: str
    skills: list[dict[str, str]]  # [{"Category Name": "Skill1, Skill2, ..."}, ...]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gpt-4o"
    output_dir: str = "outputs"
    latex_cmd: str = "pdflatex"
