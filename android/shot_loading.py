"""离屏验证加载遮罩长什么样（Windows 上跑 Kivy，截图到 logs/）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# app 里中文字体由 main.py 注册，独立截图脚本要自己来一遍，否则全是方块
from kivy.core.text import LabelBase
_font = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "assets", "NotoSansCJKsc-Regular.otf")
if os.path.exists(_font):
    LabelBase.register(name="Roboto", fn_regular=_font)

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.widget import Widget

from ui.loading import LoadingOverlay


class Shot(App):
    def build(self):
        Window.size = (420, 780)
        self.ov = LoadingOverlay()
        # 模拟一次视频生成：先显示主文案，2 秒后模拟轮询进度
        Clock.schedule_once(lambda dt: self.ov.show("正在生成视频，可能要几分钟…"), 0.2)
        Clock.schedule_once(lambda dt: self.ov.update("第 3 次检查生成状态…"), 2.2)
        Clock.schedule_once(self._grab, 6.0)
        return Widget()

    def _grab(self, dt):
        Window.screenshot(name=os.path.join("logs", "loading.png"))
        print("SHOT_SAVED logs/loading.png")
        Clock.schedule_once(lambda dt: self.stop(), 0.5)


if __name__ == "__main__":
    Shot().run()
