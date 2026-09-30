"""PEP 517 wheel hook: freeze provenance only from an exact clean checkout."""
import json
from pathlib import Path
import runpy

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithRepositoryIdentity(build_py):
    def run(self):
        root = Path(__file__).resolve().parent
        identity = runpy.run_path(str(root / 'src/pro_a/repository_identity.py'))
        frozen = identity['release_build_identity'](root)
        super().run()
        # A source mutation or HEAD change during the copy invalidates the build.
        if identity['release_build_identity'](root) != frozen:
            raise identity['RepositoryIdentityError']('REPOSITORY_IDENTITY_BUILD_DRIFT')
        source = root / 'src/pro_a'
        built = Path(self.build_lib) / 'pro_a'
        inventory = lambda base: {p.relative_to(base).as_posix(): p.read_bytes()
                                  for p in base.rglob('*.py')}
        if inventory(source) != inventory(built):
            raise identity['RepositoryIdentityError']('REPOSITORY_IDENTITY_BUILD_BYTES_MISMATCH')
        target = Path(self.build_lib) / 'pro_a' / identity['IDENTITY_FILE']
        target.write_text(json.dumps(frozen, sort_keys=True, separators=(',', ':')) + '\n',
                          encoding='utf-8')


setup(cmdclass={'build_py': BuildWithRepositoryIdentity})
