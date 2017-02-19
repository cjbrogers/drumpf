from __future__ import print_function
from __future__ import unicode_literals
from rtmbot.core import Plugin

class MyPlugin(Plugin):

    def catch_all(self, data):
        print("catch_all(self,data)")
        print(data)
