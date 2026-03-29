from agno.team import Team, TeamMode
from agentes_agno.agentes.orquestrador import agente_orquestrador

time_dev = Team(
    name="time_dev",
    mode=TeamMode.tasks,
    members=[agente_orquestrador],
    parse_response=False,
    debug_mode=True
)
