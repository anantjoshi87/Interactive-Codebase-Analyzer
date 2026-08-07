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

        resolver = ResolverFactory.get_resolver(units)

        if resolver is None:
            return units

        resolver.resolve_imports(units)
        resolver.resolve_calls(units)
        # resolver.resolve_references(units)

        return units
