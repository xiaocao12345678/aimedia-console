import os, sys
os.environ.setdefault("KIVY_NO_ARGS", "1")
sys.path.insert(0, ".")
from kivy.clock import Clock
from main import ConsoleApp

app = ConsoleApp()

def check(dt):
    p = app.pages["understand"]
    print("body   size=", p.body.size, "hint=", p.body.size_hint)
    print("parent size=", p.body.parent.size, type(p.body.parent).__name__)
    print("go     size=", p.go.size, "hint=", p.go.size_hint, "text_size=", p.go.text_size)
    print("go     texture=", p.go.texture_size, "height=", p.go.height)
    print("card   ", [c.size for c in p.body.children][:3])
    app.stop()

Clock.schedule_once(check, 2.0)
app.run()
