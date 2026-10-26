"""直接抽取 as_project/__init__.py 中的 update_side_count 做状态机测试。

不导入 AScript，只验证：
- 减少立即触发
- 增加绝不触发
- 连续减少每次都触发
- 左右完全独立
运行：
    python tools/test_state_machine.py
"""
import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "as_project", "__init__.py")

source = open(SRC, encoding="utf-8").read()
tree = ast.parse(source)
func = next(n for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "update_side_count")
module = ast.Module(body=[func], type_ignores=[])
ast.fix_missing_locations(module)

events = []
ns = {"log": lambda *args: events.append(" ".join(str(a) for a in args))}
exec(compile(module, SRC, "exec"), ns)
update = ns["update_side_count"]


def new_state():
    return {"last_count": None}


def scenario(name, expected, steps, side="left"):
    global events
    events = []
    s = new_state()
    got = []
    for raw, now in steps:
        ev = update(side, s, raw, now)
        if ev:
            got.append(ev)
    ok = got == expected
    print(("PASS" if ok else "FAIL"), name, "events=", got)
    if not ok:
        print("  expected=", expected)
        print("  log=", events)
        raise SystemExit(1)


scenario("初始基准不触发", [], [(4, 0.0)])

scenario("增加不触发", [("increase", 4, 5)], [
    (4, 0.0),
    (5, 1.0),
])

scenario("减少立即触发", [("trigger", 4, 3)], [
    (4, 0.0),
    (3, 1.0),
])

scenario("减少后恢复：先触发再增加", [
    ("trigger", 4, 3),
    ("increase", 3, 4),
], [
    (4, 0.0),
    (3, 1.0),
    (4, 1.2),
])

scenario("连续两次减少触发两次", [
    ("trigger", 4, 3),
    ("trigger", 3, 2),
], [
    (4, 0.0),
    (3, 1.0),
    (2, 2.0),
])

scenario("一次减少两个立即触发一次", [("trigger", 4, 2)], [
    (4, 0.0),
    (2, 1.0),
])

# 4 -> 1 是 bulk，不计时也不返回事件
events = []
s = new_state()
update("left", s, 4, 0.0)
assert update("left", s, 1, 1.0) is None
print("PASS 一次掉三个以上不触发 events=[]")

scenario("增加后减少只触发减少", [
    ("increase", 1, 2),
    ("trigger", 2, 1),
], [
    (1, 0.0),
    (2, 1.0),
    (1, 2.0),
])

# 左右完全独立
left_s, right_s = new_state(), new_state()
got = []
for side, s in (("left", left_s), ("right", right_s)):
    update(side, s, 4, 0.0)
for side, s, raw, now in [
    ("left", left_s, 3, 1.0),
    ("right", right_s, 2, 2.0),
    ("left", left_s, 2, 3.0),
    ("right", right_s, 4, 4.0),   # 右侧增加
    ("right", right_s, 3, 5.0),   # 右侧减少
]:
    ev = update(side, s, raw, now)
    if ev:
        got.append((side,) + ev)

expected = [
    ("left", "trigger", 4, 3),
    ("right", "trigger", 4, 2),
    ("left", "trigger", 3, 2),
    ("right", "increase", 2, 4),
    ("right", "trigger", 4, 3),
]
ok = got == expected
print(("PASS" if ok else "FAIL"), "左右独立、增加不触发", "events=", got)
if not ok:
    print("  expected=", expected)
    raise SystemExit(1)

print("all state-machine tests passed")
