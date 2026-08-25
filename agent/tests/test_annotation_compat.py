"""배포 파이썬(3.12)에서 애너테이션이 실제로 해석되는지 (#174 회귀).

## 왜 이 테스트가 필요한가

로컬 개발 venv는 Python 3.14이고 **PEP 649로 애너테이션을 지연 평가**한다.
배포 이미지(agent/Dockerfile)와 CI는 **3.12**라 즉시 평가한다. 그래서 타입을
import하지 않고 애너테이션에 쓰면 로컬 테스트는 전부 통과하는데 배포와 CI에서만
NameError로 죽는다.

실제로 그 사고가 났다. `extra_warnings: Sequence[str]`를 추가하면서
`typing.Sequence`를 import하지 않았고, 로컬 239개 테스트가 통과하는 동안
CI에서는 테스트 파일 4개가 수집 단계에서 깨지고 있었다.

`typing.get_type_hints()`는 애너테이션을 강제로 해석하므로, 3.14에서도
3.12와 같은 실패를 재현할 수 있다.
"""

import importlib
import inspect
import pkgutil
import typing
from pathlib import Path

import pytest

AGENT_ROOT = Path(__file__).parent.parent


def _module_names():
    names = ["main"]
    for pkg_dir, prefix in [("src", "src."), ("src/nodes", "src.nodes.")]:
        for m in pkgutil.iter_modules([str(AGENT_ROOT / pkg_dir)]):
            names.append(prefix + m.name)
    return sorted(names)


@pytest.mark.parametrize("module_name", _module_names())
def test_애너테이션이_즉시평가_환경에서도_해석된다(module_name):
    mod = importlib.import_module(module_name)
    unresolved = []
    for attr, obj in vars(mod).items():
        if not (inspect.isfunction(obj) or inspect.isclass(obj)):
            continue
        if getattr(obj, "__module__", None) != module_name:
            continue          # 다른 모듈에서 import해 온 심볼은 그쪽 책임
        try:
            typing.get_type_hints(obj)
        except Exception as exc:
            unresolved.append(f"{attr}: {type(exc).__name__}: {exc}")
    assert not unresolved, (
        f"{module_name}의 애너테이션이 해석되지 않는다. 로컬(3.14)은 지연 평가라 "
        f"통과하지만 배포·CI(3.12)에서는 NameError로 죽는다:\n  "
        + "\n  ".join(unresolved))
