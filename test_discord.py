import discord
from discord import ui
class FakeButton(ui.Button): pass
b = FakeButton()
print(type(b))
print(hasattr(ui, 'ActionRow'))
