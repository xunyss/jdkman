from dataclasses import dataclass

from click.exceptions import NoSuchOption
from click.parser import OptionParser


@dataclass
class OptionParserPatch:
    """
    - No "Possible options" suggestion on unknown option (like suggest_commands=False)
    """
    def apply(self) -> None:
        """Patch click globally."""
        _orig = OptionParser._match_long_opt

        # noinspection PyShadowingNames
        def _patched(self, opt: str, explicit_value, state) -> None:
            if opt not in self._long_opt:
                raise NoSuchOption(opt, ctx=self.ctx)
            _orig(self, opt, explicit_value, state)

        OptionParser._match_long_opt = _patched

