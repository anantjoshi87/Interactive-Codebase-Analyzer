from app.services.ingestion.models import CodeUnit
from .parser.resolvers.resolver_factory import ResolverFactory
from app.services.ingestion.models import LanguageConfig


class RepoResolver:

    @staticmethod
    def resolve(
        units: list[CodeUnit],
    ) -> list[CodeUnit]:

        if not units:
            return units

        codeUnits = [u for u in units if isinstance(u, CodeUnit)]

        resolver = ResolverFactory.get_resolver(units)

        if resolver is None:
            return units

        resolver.resolve_imports(codeUnits)
        resolver.resolve_calls(codeUnits)
        # resolver.resolve_references(units)

        return units
