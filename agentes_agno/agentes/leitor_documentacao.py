from agno.agent import Agent

from agentes_agno.core.llm import obter_modelo_openai


agente_leitor_documentacao = Agent(
    name="LeitorDocumentacao",
    model=obter_modelo_openai(),
    instructions=[
        "Você recebe trechos de documentação de API (HTML/PDF já convertidos em texto).",
        "Resuma SOMENTE em JSON válido com a chave 'contratos'.",
        "Cada item de 'contratos' deve conter: endpoint, metodo, entrada, saida, regras.",
        "Quando houver ambiguidades, explicite em 'regras'.",
        "Não retornar markdown nem texto fora de JSON.",
    ],
)
