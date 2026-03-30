from agno.agent import Agent
from agentes_agno.core.llm import obter_modelo_openai

agente_orquestrador = Agent(
    name="Orquestrador",
    model=obter_modelo_openai(),
    instructions=[
        "Gerar service, serializer, view/viewset e urls (urls.py + router) para expor os endpoints",
        "Usar modelos_reais e, se existir, modelos_upload (derivado do models.py enviado)",
        "Se existir rag_contexto no estado da sessão, usar esse contexto recuperado para melhorar o resultado técnico",
        "Se existir contratos_documentacao no estado da sessão, alinhar endpoints, payloads e regras com a documentação",
        "Se existir plano_sicredi_boletos, priorizar implementação de integração com API online do Sicredi para emissão/consulta/cancelamento de boletos",
        "Ao ler modelos, aplicar automaticamente normalização de campos (aliases amigáveis com source=...) e regras de negócio inferidas",
        "Não gerar só CRUD básico: criar casos de uso úteis com base nos campos do model (ex.: filtros por período e status, busca full-text por campos de texto, ordenação segura, transições de status, soft delete quando fizer sentido, operações em lote, validações e uso de transações)",
        "Serializers devem ser normalizados (campos amigáveis) usando source=... para mapear campos legados; use exemplo_serializer_normalizado como referência de estilo",
        "Em services: incluir exemplos de métodos de criação com validações e regras de negócio, e métodos adicionais além de list/create/update (ex.: resumo/agregação, relatório por período, busca avançada, atualização em massa)",
        "Em services: seguir estilo de regras/validações e transações do exemplo_service, mas usando sempre core.utils.get_licenca_db_config(request) (e .using(db)) em vez de get_db_from_slug",
        "Em views/viewsets: expor ações customizadas (@action) que chamem os métodos do service (ex.: /resumo, /relatorio, /buscar, /bulk)",
        "Em urls: sempre gerar router.register com prefixos RESTful e nomes coerentes, garantindo que as ações customizadas fiquem acessíveis",
        "Sempre usar padrão multi-db (core.utils.get_licenca_db_config(request) e .using(db)) e respeitar LicencaMiddleware (request.slug, request.empresa, request.filial)",
        "Incluir pelo menos 1 arquivo de exemplo de uso (requests.http ou examples.py) mostrando criação com payload realista, listagem com filtros e chamada de 1 ação customizada",
        "Responder SOMENTE em JSON válido (sem texto extra, sem markdown) com a chave arquivos"
    ]
)
